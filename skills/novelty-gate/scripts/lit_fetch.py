#!/usr/bin/env python3
"""lit_fetch.py - literature helper for the research-topic skills (Python stdlib only).

Subcommands
  arxiv QUERY [--max N] [--since DATE] [--until DATE] [--sort relevance|submitted|updated]
      Search the arXiv API. Plain words are ANDed over all fields; a query that already
      uses arXiv field prefixes (ti:, abs:, au:, cat:, all:) is passed through.
  openalex QUERY [--max N] [--since DATE] [--until DATE]
      Search OpenAlex (no API key). Abstracts are rebuilt from the inverted index.
  citing REF [--max N] [--since DATE]
      Forward citations: works that cite REF (via OpenAlex). The fastest way to find the
      newest direct competitor of a known close prior.
  resolve REF [--no-arxiv]
      Resolve an arXiv id, DOI, OpenAlex id (W...) or a title to canonical metadata.
      Use it before citing anything, so no citation comes from memory. arXiv ids go to
      OpenAlex first (DOI 10.48550/arXiv.<id>) and fall back to the arXiv API.
  pdf REF --out DIR
      Download a PDF (arXiv id or URL) to DIR and extract text next to it (pymupdf or
      pdftotext if available). Text files carry "=== page N ===" markers.

Common options: --json (JSON Lines output), --full (do not truncate abstracts),
--save-abstracts DIR (write abs_<id>.txt per result, so quote_check.py can verify ABS quotes).
Dates are YYYY-MM-DD.

Text output, one block per result:
  N. [id] title - authors (date; category or venue; cited_by=K)
     url
     abstract (truncated to 400 characters unless --full)

Environment
  OPENALEX_API_KEY   optional free OpenAlex key (sent as an Authorization header). Without a key
                     OpenAlex allows about 100 searches a day; with a free key about ten times more.
                     Get one at openalex.org (Settings) and export it; it is never printed.
  LIT_FETCH_MAILTO   optional e-mail added to OpenAlex requests; nothing is sent unless set.

Be polite: arXiv asks for about 3 s between API calls; this script waits automatically. On
HTTP 429 (rate limit) it retries once briefly and then fails fast: switch to `openalex` or wait.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

USER_AGENT = "research-topic-skills-lit_fetch/0.1"
ARXIV_API = "https://export.arxiv.org/api/query"
OPENALEX = "https://api.openalex.org"
ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
ARXIV_ID_RE = re.compile(r"^(?:arxiv:)?((?:\d{4}\.\d{4,5})|(?:[a-z\-]+(?:\.[A-Z]{2})?/\d{7}))(v\d+)?$", re.I)
DOI_RE = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)?(10\.\d{4,9}/\S+)$", re.I)
OPENALEX_ID_RE = re.compile(r"^(?:https?://openalex\.org/)?(W\d+)$", re.I)

_last_arxiv_call = [0.0]


class FetchError(RuntimeError):
    pass


def http_get(url, binary=False, retries=3, timeout=30):
    headers = {"User-Agent": USER_AGENT}
    key = os.environ.get("OPENALEX_API_KEY")
    if key and urllib.parse.urlparse(url).netloc == "api.openalex.org":
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, headers=headers)
    delay = 2.0
    last_err = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                return data if binary else data.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429:
                try:
                    retry_after = float(e.headers.get("Retry-After") or 5)
                except ValueError:
                    retry_after = 5.0
                if attempt == 0 and retry_after <= 10:
                    time.sleep(retry_after)
                    continue
                host = urllib.parse.urlparse(url).netloc
                if "openalex" in host:
                    hint = ("OpenAlex budget exhausted for now (retry in about "
                            f"{retry_after / 3600:.1f} h). Set OPENALEX_API_KEY (a free key gives about ten times "
                            "the budget), or continue with `arxiv` and the host's web search")
                else:
                    hint = "arXiv rate limit; continue with `openalex` or the host's web search, or retry in a few minutes"
                raise FetchError(f"HTTP 429 from {host}: {hint}") from e
            if e.code in (500, 502, 503, 504) and attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise FetchError(f"HTTP {e.code} for {url}") from e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise FetchError(f"network error for {url}: {e}") from e
    raise FetchError(f"failed: {url}: {last_err}")


# ---------------------------------------------------------------- arXiv

def _arxiv_wait():
    gap = time.time() - _last_arxiv_call[0]
    if gap < 3.0:
        time.sleep(3.0 - gap)
    _last_arxiv_call[0] = time.time()


def build_arxiv_query(query, since=None, until=None):
    q = query.strip()
    if not re.search(r"\b(ti|abs|au|cat|all|co|jr|rn|id):", q):
        terms = re.findall(r'"[^"]+"|\S+', q)
        q = " AND ".join(f"all:{t}" for t in terms)
    if since or until:
        lo = (since or "1991-01-01").replace("-", "") + "0000"
        hi = (until or "2999-12-31").replace("-", "") + "2359"
        q = f"({q}) AND submittedDate:[{lo} TO {hi}]"
    return q


def parse_arxiv_feed(xml_text):
    root = ET.fromstring(xml_text)
    out = []
    for e in root.findall("a:entry", ATOM):
        raw_id = (e.findtext("a:id", default="", namespaces=ATOM) or "").strip()
        if not raw_id:
            continue
        aid = raw_id.rsplit("/abs/", 1)[-1]
        base = re.sub(r"v\d+$", "", aid)
        cat = e.find("arxiv:primary_category", ATOM)
        out.append({
            "source": "arxiv",
            "id": base,
            "version": aid[len(base):] or None,
            "title": " ".join((e.findtext("a:title", default="", namespaces=ATOM) or "").split()),
            "authors": [a.findtext("a:name", default="", namespaces=ATOM) for a in e.findall("a:author", ATOM)],
            "published": (e.findtext("a:published", default="", namespaces=ATOM) or "")[:10],
            "updated": (e.findtext("a:updated", default="", namespaces=ATOM) or "")[:10],
            "category": cat.get("term") if cat is not None else None,
            "abstract": " ".join((e.findtext("a:summary", default="", namespaces=ATOM) or "").split()),
            "url": f"https://arxiv.org/abs/{base}",
            "pdf": f"https://arxiv.org/pdf/{base}",
        })
    return out


def arxiv_search(query, max_results=20, since=None, until=None, sort="relevance"):
    sort_by = {"relevance": "relevance", "submitted": "submittedDate", "updated": "lastUpdatedDate"}[sort]
    params = {
        "search_query": build_arxiv_query(query, since, until),
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": "descending",
    }
    _arxiv_wait()
    return parse_arxiv_feed(http_get(ARXIV_API + "?" + urllib.parse.urlencode(params)))


def arxiv_by_id(aid):
    _arxiv_wait()
    items = parse_arxiv_feed(http_get(ARXIV_API + "?" + urllib.parse.urlencode({"id_list": aid})))
    return items[0] if items else None


# ---------------------------------------------------------------- OpenAlex

def _oa_params(extra):
    params = dict(extra)
    mail = os.environ.get("LIT_FETCH_MAILTO")
    if mail:
        params["mailto"] = mail
    return params


def reconstruct_abstract(inv):
    if not inv:
        return ""
    pos = sorted((p, w) for w, ps in inv.items() for p in ps)
    return " ".join(w for _, w in pos)


def parse_openalex_work(w):
    loc = w.get("primary_location") or {}
    src = loc.get("source") or {}
    arxiv_id = None
    for l in (w.get("locations") or []):
        url = (l or {}).get("landing_page_url") or ""
        m = re.search(r"arxiv\.org/abs/([^\s?#]+)", url)
        if m:
            arxiv_id = re.sub(r"v\d+$", "", m.group(1))
            break
    doi = w.get("doi")
    return {
        "source": "openalex",
        "id": (w.get("id") or "").rsplit("/", 1)[-1],
        "title": w.get("display_name") or w.get("title") or "",
        "authors": [((a or {}).get("author") or {}).get("display_name", "") for a in (w.get("authorships") or [])],
        "published": w.get("publication_date") or str(w.get("publication_year") or ""),
        "venue": src.get("display_name"),
        "doi": doi,
        "arxiv": arxiv_id,
        "cited_by": w.get("cited_by_count"),
        "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
        "url": doi or (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else loc.get("landing_page_url") or w.get("id")),
    }


def _date_filters(since, until):
    f = []
    if since:
        f.append(f"from_publication_date:{since}")
    if until:
        f.append(f"to_publication_date:{until}")
    return f


def openalex_search(query, max_results=25, since=None, until=None):
    params = {"search": query, "per-page": min(max_results, 200)}
    f = _date_filters(since, until)
    if f:
        params["filter"] = ",".join(f)
    data = json.loads(http_get(OPENALEX + "/works?" + urllib.parse.urlencode(_oa_params(params))))
    return [parse_openalex_work(w) for w in data.get("results", [])][:max_results]


def openalex_get(path):
    return json.loads(http_get(OPENALEX + "/works/" + path + ("?" + urllib.parse.urlencode(_oa_params({})) if os.environ.get("LIT_FETCH_MAILTO") else "")))


def openalex_resolve(ref):
    """Return the raw OpenAlex work for an arXiv id, DOI, W-id or title (best match)."""
    ref = ref.strip()
    m = OPENALEX_ID_RE.match(ref)
    if m:
        return openalex_get(m.group(1))
    m = DOI_RE.match(ref)
    if m:
        return openalex_get("doi:" + m.group(1))
    m = ARXIV_ID_RE.match(ref)
    if m:
        try:
            return openalex_get("doi:10.48550/arXiv." + m.group(1))
        except FetchError:
            meta = arxiv_by_id(m.group(1))
            if not meta:
                return None
            ref = meta["title"]
    params = {"filter": "title.search:" + ref.replace(",", " "), "per-page": 10}
    data = json.loads(http_get(OPENALEX + "/works?" + urllib.parse.urlencode(_oa_params(params))))
    best, best_score = None, 0.0
    for w in data.get("results", []):
        s = SequenceMatcher(None, ref.lower(), (w.get("display_name") or "").lower()).ratio()
        if s > best_score:
            best, best_score = w, s
    return best if best_score >= 0.6 else None


def citing(ref, max_results=50, since=None, until=None):
    w = openalex_resolve(ref)
    if not w:
        raise FetchError(f"could not resolve {ref!r} in OpenAlex")
    wid = (w.get("id") or "").rsplit("/", 1)[-1]
    f = [f"cites:{wid}"] + _date_filters(since, until)
    params = {"filter": ",".join(f), "per-page": min(max_results, 200), "sort": "publication_date:desc"}
    data = json.loads(http_get(OPENALEX + "/works?" + urllib.parse.urlencode(_oa_params(params))))
    return parse_openalex_work(w), [parse_openalex_work(x) for x in data.get("results", [])][:max_results]


def resolve(ref, use_arxiv=True):
    """Canonical metadata. arXiv ids: OpenAlex first (fast, no rate limit), then the arXiv API."""
    m = ARXIV_ID_RE.match(ref.strip())
    if m:
        aid = m.group(1)
        try:
            w = openalex_get("doi:10.48550/arXiv." + aid)
            meta = parse_openalex_work(w)
            meta["arxiv"] = meta.get("arxiv") or aid
            meta["url"] = f"https://arxiv.org/abs/{aid}"
            return meta
        except FetchError:
            pass
        if use_arxiv:
            return arxiv_by_id(aid)
        return None
    w = openalex_resolve(ref)
    return parse_openalex_work(w) if w else None


# ---------------------------------------------------------------- PDF

def safe_name(ref):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", ref.strip())[:120]


def extract_text(pdf_path, txt_path):
    try:
        try:
            import pymupdf as fitz  # PyMuPDF >= 1.24
        except ImportError:
            import fitz  # older PyMuPDF
        doc = fitz.open(pdf_path)
        with open(txt_path, "w", encoding="utf-8") as fh:
            for i, page in enumerate(doc, 1):
                fh.write(f"\n=== page {i} ===\n")
                fh.write(page.get_text())
        return "pymupdf"
    except ImportError:
        pass
    if shutil.which("pdftotext"):
        subprocess.run(["pdftotext", "-layout", pdf_path, txt_path], check=True)
        return "pdftotext"
    return None


def fetch_pdf(ref, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    m = ARXIV_ID_RE.match(ref.strip())
    if m:
        url = f"https://arxiv.org/pdf/{m.group(1)}"
        name = safe_name(m.group(1))
    elif ref.startswith("http"):
        url = ref
        name = safe_name(urllib.parse.urlparse(ref).path.rsplit("/", 1)[-1] or "paper")
    else:
        raise FetchError("pdf needs an arXiv id or a URL (resolve titles first)")
    if name.lower().endswith(".pdf"):
        name = name[:-4]
    data = http_get(url, binary=True, timeout=60)
    if not data.startswith(b"%PDF"):
        raise FetchError(f"not a PDF (bot wall, landing page or paywall?): {url}")
    pdf_path = os.path.join(out_dir, name + ".pdf")
    with open(pdf_path, "wb") as fh:
        fh.write(data)
    txt_path = os.path.join(out_dir, name + ".txt")
    how = extract_text(pdf_path, txt_path)
    return {"url": url, "pdf": pdf_path, "text": txt_path if how else None, "extractor": how, "bytes": len(data)}


# ---------------------------------------------------------------- output

def fmt_item(i, it, full=False):
    authors = it.get("authors") or []
    auth = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
    tag = it.get("id") if it.get("source") == "arxiv" else (it.get("arxiv") or it.get("id"))
    extra = "; ".join(x for x in [it.get("published"), it.get("category") or it.get("venue"),
                                  f"cited_by={it['cited_by']}" if it.get("cited_by") is not None else None] if x)
    abstract = it.get("abstract") or ""
    if not full and len(abstract) > 400:
        abstract = abstract[:400].rstrip() + " ..."
    lines = [f"{i}. [{tag}] {it.get('title', '')} - {auth} ({extra})", f"   {it.get('url', '')}"]
    if abstract:
        lines.append(f"   {abstract}")
    return "\n".join(lines)


def save_abstracts(items, out_dir):
    if not out_dir:
        return
    os.makedirs(out_dir, exist_ok=True)
    for it in items:
        key = it.get("arxiv") or it.get("id") or "item"
        if it.get("source") == "arxiv":
            key = it.get("id")
        path = os.path.join(out_dir, "abs_" + safe_name(str(key)) + ".txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join([it.get("title", ""), ", ".join(it.get("authors") or []),
                                 str(it.get("published", "")), str(it.get("url", "")), "", it.get("abstract", "")]) + "\n")


def emit(items, as_json, full):
    if as_json:
        for it in items:
            print(json.dumps(it, ensure_ascii=False))
    else:
        if not items:
            print("(no results)")
        for i, it in enumerate(items, 1):
            print(fmt_item(i, it, full))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, search=True):
        sp.add_argument("--json", action="store_true", help="JSON Lines output")
        sp.add_argument("--full", action="store_true", help="do not truncate abstracts")
        sp.add_argument("--save-abstracts", metavar="DIR", help="write abs_<id>.txt per result")
        if search:
            sp.add_argument("--max", type=int, default=20)
            sp.add_argument("--since")
            sp.add_argument("--until")

    sp = sub.add_parser("arxiv")
    sp.add_argument("query")
    sp.add_argument("--sort", choices=["relevance", "submitted", "updated"], default="relevance")
    common(sp)
    sp = sub.add_parser("openalex")
    sp.add_argument("query")
    common(sp)
    sp = sub.add_parser("citing")
    sp.add_argument("ref")
    common(sp)
    sp = sub.add_parser("resolve")
    sp.add_argument("ref")
    sp.add_argument("--no-arxiv", action="store_true", help="never call the arXiv API")
    common(sp, search=False)
    sp = sub.add_parser("pdf")
    sp.add_argument("ref")
    sp.add_argument("--out", required=True)
    args = p.parse_args(argv)

    try:
        if args.cmd == "arxiv":
            items = arxiv_search(args.query, args.max, args.since, args.until, args.sort)
            save_abstracts(items, args.save_abstracts)
            emit(items, args.json, args.full)
            if not items and not args.json:
                print("hint: the arXiv API matches exact tokens (no stemming or synonyms). "
                      "Try 2-3 distinctive terms, a quoted phrase, or `openalex` for relevance search.")
        elif args.cmd == "openalex":
            items = openalex_search(args.query, args.max, args.since, args.until)
            save_abstracts(items, args.save_abstracts)
            emit(items, args.json, args.full)
        elif args.cmd == "citing":
            base, items = citing(args.ref, args.max, args.since, args.until)
            save_abstracts(items, args.save_abstracts)
            if not args.json:
                print(f"Works citing: {base.get('title')} ({base.get('published')}) {base.get('url')}\n")
            emit(items, args.json, args.full)
            if not items and not args.json:
                print("hint: OpenAlex may attach citations to another version of the work (preprint vs. "
                      "published). Resolve the other version by title and run `citing` on it too.")
        elif args.cmd == "resolve":
            meta = resolve(args.ref, use_arxiv=not args.no_arxiv)
            if not meta:
                print(f"UNRESOLVED: {args.ref} (not found; do not cite it as verified)", file=sys.stderr)
                return 2
            save_abstracts([meta], args.save_abstracts)
            emit([meta], args.json, args.full)
        elif args.cmd == "pdf":
            print(json.dumps(fetch_pdf(args.ref, args.out), ensure_ascii=False))
    except FetchError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
