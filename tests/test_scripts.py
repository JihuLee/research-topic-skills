"""Offline tests for the helper scripts. Run: python3 -m unittest discover -s tests -v

Set LIT_FETCH_LIVE=1 to also run one small live query against arXiv and OpenAlex.
"""
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures")


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lit = load("lit_fetch", "shared/scripts/lit_fetch.py")
ledger = load("ledger", "shared/scripts/ledger.py")
freeze = load("freeze", "shared/scripts/freeze.py")
lint = load("report_lint", "shared/scripts/report_lint.py")
qc = load("quote_check", "shared/scripts/quote_check.py")
scan = load("corpus_scan", "skills/topic-scout/scripts/corpus_scan.py")
guard = load("guard", "shared/scripts/guard.py")
settings = load("scout_settings", "skills/topic-scout/scripts/scout_settings.py")
pinit = load("profile_init", "shared/scripts/profile_init.py")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def dump(obj, path, **kw):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, **kw)


def run(fn, argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = fn(argv)
    return rc, buf.getvalue()


class TestLitFetch(unittest.TestCase):
    def test_parse_arxiv(self):
        items = lit.parse_arxiv_feed(read(os.path.join(FIX, "arxiv_feed.xml")))
        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual(it["id"], "2501.01234")
        self.assertEqual(it["version"], "v2")
        self.assertEqual(it["title"], "A Test Paper on Graph Message Passing")
        self.assertEqual(it["published"], "2025-01-03")
        self.assertEqual(it["category"], "cs.CV")
        self.assertEqual(it["authors"], ["Ada Lovelace", "Alan Turing"])

    def test_parse_openalex(self):
        w = json.loads(read(os.path.join(FIX, "openalex_work.json")))
        it = lit.parse_openalex_work(w)
        self.assertEqual(it["abstract"], "We propose a test.")
        self.assertEqual(it["arxiv"], "2406.00001")
        self.assertEqual(it["id"], "W1234567890")
        self.assertEqual(it["venue"], "Test Conference")

    def test_query_builder(self):
        q = lit.build_arxiv_query('graph "message passing"', since="2025-05-01")
        self.assertIn('all:"message passing"', q)
        self.assertIn("submittedDate:[202505010000 TO 299912312359]", q)
        self.assertEqual(lit.build_arxiv_query("ti:attention AND cat:cs.LG"), "ti:attention AND cat:cs.LG")

    def test_id_patterns(self):
        self.assertTrue(lit.ARXIV_ID_RE.match("2509.12821"))
        self.assertTrue(lit.ARXIV_ID_RE.match("arXiv:2509.12821v3"))
        self.assertTrue(lit.ARXIV_ID_RE.match("cs/0601001"))
        self.assertTrue(lit.DOI_RE.match("https://doi.org/10.1117/1.JMM.20.4.041206"))
        self.assertFalse(lit.ARXIV_ID_RE.match("A title with words"))

    @unittest.skipUnless(os.environ.get("LIT_FETCH_LIVE"), "live network test")
    def test_live(self):
        self.assertTrue(lit.arxiv_search("graph neural networks", max_results=2))
        self.assertTrue(lit.openalex_search("graph neural networks", max_results=2))
        self.assertIsNotNone(lit.resolve("1706.03762"))


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.path = os.path.join(self.d, "ledger.jsonl")

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_add_check_update_validate(self):
        e1 = {"id": "T1", "date": "2026-01-01", "title": "Over-smoothing in deep graph networks",
              "claim": "Deep graph neural networks degrade when many message passing layers are stacked", "verdict": "killed",
              "killers": [{"title": "Some tracker paper", "url": "https://example.org/a", "why": "same effect"}]}
        e2 = {"id": "T2", "date": "2026-01-02", "title": "Weather forecasting with sparse stations",
              "claim": "Interpolating sparse weather station data with kriging improves short-range forecasts", "verdict": "killed"}
        for e in (e1, e2):
            rc, _ = run(ledger.main, ["add", self.path, "--json", json.dumps(e)])
            self.assertEqual(rc, 0)
        rc, out = run(ledger.main, ["check", self.path, "--claim", "stacking many message passing layers makes graph networks degrade"])
        self.assertEqual(rc, 0)
        first = [l for l in out.splitlines() if re.match(r"^\d\.\d\d ", l)][0]
        self.assertIn("T1", first)
        rc, _ = run(ledger.main, ["update", self.path, "--id", "T2", "--set", "verdict=closed", "--set", "novelty=2"])
        self.assertEqual(rc, 0)
        rc, out = run(ledger.main, ["validate", self.path])
        self.assertEqual(rc, 0, out)
        rc, out = run(ledger.main, ["add", self.path, "--json", json.dumps(dict(e1, verdict="maybe", id="T3"))])
        self.assertIn("REJECTED", out)

    def test_from_summary(self):
        rc, out = run(ledger.main, ["add", self.path, "--from-summary", os.path.join(FIX, "good_gate_report.md"), "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertEqual(out.count("DRY-RUN"), 2)
        self.assertIn('"verdict": "near-miss"', out)

    def test_template_ledger_valid(self):
        rc, out = run(ledger.main, ["validate", os.path.join(ROOT, "templates", "ledger.example.jsonl")])
        self.assertEqual(rc, 0, out)


class TestFreeze(unittest.TestCase):
    def test_roundtrip_and_tamper(self):
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "thresholds.json")
            dump({"min_effect": 0.4, "kill_if": "x"}, p)
            rc, out = run(freeze.main, ["freeze", p])
            self.assertEqual(rc, 0)
            dump({"kill_if": "x", "min_effect": 0.4}, p, indent=4)  # reformat only
            rc, _ = run(freeze.main, ["verify", p])
            self.assertEqual(rc, 0)
            dump({"kill_if": "x", "min_effect": 0.3}, p)  # relaxed threshold
            rc, _ = run(freeze.main, ["verify", p])
            self.assertEqual(rc, 1)
            dump({"min_effect": "0.4"}, p)
            rc, out = run(freeze.main, ["freeze", p])
            self.assertIn("looks like a number", out)
            dump({"min_effect": 0.5}, p)
            rc, _ = run(freeze.main, ["amend", p, "--reason", "tighten before results"])
            self.assertEqual(rc, 0)
            rc, _ = run(freeze.main, ["verify", p])
            self.assertEqual(rc, 0)
            log = [json.loads(l) for l in read(p + ".amendments.jsonl").splitlines()]
            self.assertEqual(log[-1]["reason"], "tighten before results")
        finally:
            shutil.rmtree(d)


class TestReportLint(unittest.TestCase):
    def test_good_gate(self):
        rc, out = run(lambda a: lint.lint_gate(*a), [os.path.join(FIX, "good_gate_report.md"), None, None])
        self.assertEqual(rc, 0, out)

    def test_bad_gate(self):
        rc, out = run(lambda a: lint.lint_gate(*a), [os.path.join(FIX, "bad_gate_report.md"), None, None])
        self.assertEqual(rc, 1)
        for expected in ("literature_cutoff must be", "novelty 3 < entry_threshold", "baselines.native missing",
                         "full text (FT)", "no name, no kill", "coverage is empty"):
            self.assertIn(expected, out)

    def test_evidence_crosscheck(self):
        d = tempfile.mkdtemp()
        try:
            ev = os.path.join(d, "evidence.jsonl")
            write(ev, json.dumps({"id": "E1", "tag": "ABS"}) + "\n")
            rc, out = run(lambda a: lint.lint_gate(*a), [os.path.join(FIX, "good_gate_report.md"), ev, None])
            self.assertEqual(rc, 1)
            self.assertIn("tag ABS != report tag FT", out)
        finally:
            shutil.rmtree(d)

    def test_brief_template_fails_and_filled_passes(self):
        tpl = os.path.join(ROOT, "skills", "research-brief", "assets", "brief_template.md")
        rc, out = run(lambda a: lint.lint_brief(*a), [tpl, None, 3, None])
        self.assertEqual(rc, 1)
        self.assertIn("unfilled field", out)
        self.assertIn("placeholder", out)
        d = tempfile.mkdtemp()
        try:
            thr = os.path.join(d, "thresholds.json")
            dump({"min_effect": 0.4}, thr)
            run(freeze.main, ["freeze", thr])
            h = read(thr + ".sha256").split()[0]
            parts = ["# Filled brief"]
            for sid in lint.DEFAULT_SECTIONS:
                body = f"- {sid} content: concrete text for this section, written out in full."
                if sid == "literature":
                    body += "\n- https://arxiv.org/abs/1 fact one\n- https://arxiv.org/abs/2 fact two\n- https://arxiv.org/abs/3 fact three"
                if sid == "gates":
                    body += f"\n- Frozen thresholds sha256: {h}"
                if sid == "splits":
                    body += "\n| Use | Size |\n|---|---:|\n| Dev | 200 |"
                parts.append(f"<!-- section:{sid} -->\n## {sid}\n{body}\n")
            brief = os.path.join(d, "brief.md")
            write(brief, "\n".join(parts))
            rc, out = run(lambda a: lint.lint_brief(*a), [brief, thr, 3, None])
            self.assertEqual(rc, 0, out)
        finally:
            shutil.rmtree(d)


class TestHumanReports(unittest.TestCase):
    """Folder layout: report.md (human), details.md (audit), gate_summary.json."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        text = read(os.path.join(FIX, "good_gate_report.md"))
        summary = json.loads(re.search(r"```json\s+gate-summary\s*\n(.*?)```", text, re.S).group(1))
        dump(summary, os.path.join(self.d, "gate_summary.json"))
        write(os.path.join(self.d, "details.md"), text.split("```json")[0])
        self.good = ("# Novelty check: calibration ideas\n\n## Result\nNo idea is recommended. One idea is a near miss.\n\n"
                     "## C1 · Label smoothing under shift — Near miss\nnovelty score 3/5 · feasibility score 5/5\n\n"
                     "**Why.** The closest paper tests calibration in distribution only. It does not test shift.\n\n"
                     "## C2 · Temperature scaling and AUROC — Rejected\n"
                     "**Why.** AUROC depends only on the ranking of scores. One monotone transform keeps the ranking.\n\n"
                     "## Next step\n- Say: \"check C1 in full\"\n")

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_folder_layout_passes(self):
        write(os.path.join(self.d, "report.md"), self.good)
        ko = self.good.replace("No idea is recommended. One idea is a near miss.", "추천할 아이디어는 없다. 하나는 Near miss다.")
        write(os.path.join(self.d, "report.ko.md"), ko)
        rc, out = run(lambda a: lint.lint_gate(*a), [self.d, None, None])
        self.assertEqual(rc, 0, out)

    def test_internal_codes_and_raw_words_fail(self):
        bad = self.good.replace("It does not test shift.", "It does not test shift [FT] (E3).").replace("— Rejected", "— KILLED")
        write(os.path.join(self.d, "report.md"), bad)
        rc, out = run(lambda a: lint.lint_gate(*a), [self.d, None, None])
        self.assertEqual(rc, 1)
        for needle in ("evidence tag", "evidence id", "raw status word", "verdict label 'Rejected' missing"):
            self.assertIn(needle, out)

    def test_missing_human_report_fails(self):
        rc, out = run(lambda a: lint.lint_gate(*a), [self.d, None, None])
        self.assertEqual(rc, 1)
        self.assertIn("report.md missing", out)

    def test_ledger_reads_folder_summary(self):
        lp = os.path.join(self.d, "ledger.jsonl")
        rc, out = run(ledger.main, ["add", lp, "--from-summary", self.d, "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertEqual(out.count("DRY-RUN"), 2)

    def test_scout_folder(self):
        rows = [{"id": "C1", "source": "landscape", "level": "low", "status": "annotated", "hypothesis": "h1", "rank": 3.2},
                {"id": "C2", "source": "landscape", "level": "low", "status": "annotated", "hypothesis": "h2", "rank": 2.1},
                {"id": "C3", "source": "landscape", "level": "low", "status": "dropped", "hypothesis": "h3", "rank": 0}]
        write(os.path.join(self.d, "candidates.jsonl"), "\n".join(json.dumps(r) for r in rows) + "\n")
        write(os.path.join(self.d, "report.md"), "# Topic scout\n\n## Result\nTwo ideas are not checked yet.\n\n"
                                                   "## C1 · First idea — Not checked\n\n## C2 · Second idea — Not checked\n")
        rc, out = run(lint.lint_scout, self.d)
        self.assertEqual(rc, 0, out)
        write(os.path.join(self.d, "report.md"), "# Topic scout\n\n## C1 · only one — Not checked [SEC]\n")
        rc, out = run(lint.lint_scout, self.d)
        self.assertEqual(rc, 1)
        self.assertIn("candidate C2 not mentioned", out)


class TestQuoteCheck(unittest.TestCase):
    def test_ligature_hyphenation_and_failure(self):
        d = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(d, "lit"))
            write(os.path.join(d, "lit", "p.txt"),
                  "=== page 3 ===\nWe further approximate S to be indepen-\ndent of x, and hence a constant C, for the sake of eﬃciency.")
            ev = os.path.join(d, "evidence.jsonl")
            rows = [
                {"id": "E1", "tag": "FT", "source": "lit/p.txt", "quote": "approximate S to be independent of x, and hence a constant C"},
                {"id": "E2", "tag": "FT", "source": "lit/p.txt", "quote": "for the sake of efficiency"},
                {"id": "E3", "tag": "SEC", "quote": "anything"},
            ]
            write(ev, "\n".join(json.dumps(r) for r in rows) + "\n")
            rc, out = run(qc.main, [ev])
            self.assertEqual(rc, 0, out)
            rows.append({"id": "E4", "tag": "FT", "source": "lit/p.txt", "quote": "the method is exact in every dimension"})
            write(ev, "\n".join(json.dumps(r) for r in rows) + "\n")
            rc, out = run(qc.main, [ev])
            self.assertEqual(rc, 1)
            self.assertIn("E4", out)
        finally:
            shutil.rmtree(d)


class TestCorpusScan(unittest.TestCase):
    def test_scan(self):
        d = tempfile.mkdtemp()
        try:
            write(os.path.join(d, "paper.tex"), "For simplicity we assume isotropic noise.\nWe leave this to future work.\n")
            write(os.path.join(d, "train.py"), 
                "import torch\nx = torch.clamp(x, 0, 1)\ny = z.detach()\neps = 1e-6\nfor i in range(10):\n    a = torch.linalg.inv(m)\n")
            out_md = os.path.join(d, "scan.md")
            rc, _ = run(scan.main, [d, "--out", out_md])
            self.assertEqual(rc, 0)
            text = read(out_md)
            for needle in ("paper.tex:1", "paper.tex:2", "train.py:2", "train.py:3", "train.py:4", "inv() inside loop"):
                self.assertIn(needle, text)
        finally:
            shutil.rmtree(d)


class TestScoutSettings(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.prof = os.path.join(self.d, "prof")
        rc, _ = run(pinit.main, ["--dir", self.prof, "--interests", "medical imaging; uncertainty",
                                 "--exclusions", "systems", "--level", "medium", "--depth", "standard"])
        self.assertEqual(rc, 0)
        self.proj = os.path.join(self.d, "proj")
        os.makedirs(self.proj)
        write(os.path.join(self.proj, "train.py"), "x = 1\n")
        write(os.path.join(self.proj, "paper.tex"), "We assume.\n")

    def tearDown(self):
        shutil.rmtree(self.d)

    def res(self, req, cwd=None):
        return settings.resolve(req, profile=self.prof, cwd=cwd or self.proj, today="2026-11-05", env={})

    def test_defaults_and_auto_corpus(self):
        s = self.res("주제 찾아줘")
        self.assertEqual((s["level"]["value"], s["level"]["source"]), ("medium", "profile"))
        self.assertEqual((s["depth"]["value"], s["finalists"]["value"], s["gate_mode"]), ("standard", 1, "light"))
        self.assertEqual(s["corpus"]["paths"], [self.proj])
        self.assertEqual(s["cutoff"]["value"], "2026-11-05")

    def test_korean_phrases(self):
        s = self.res("탐색적으로 빠르게 주제 찾아줘, 분야는 의료영상")
        self.assertEqual((s["level"]["value"], s["depth"]["value"], s["finalists"]["value"]), ("low", "quick", 0))
        self.assertEqual(s["corpus"]["paths"], [])
        self.assertEqual(s["direction"], "의료영상")
        s = self.res("내 코드 기반으로 꼼꼼하게 주제 찾아줘")
        self.assertEqual((s["level"]["value"], s["depth"]["value"], s["finalists"]["value"], s["gate_mode"]),
                         ("high", "full", 3, "full"))

    def test_explicit_overrides_and_paths(self):
        other = os.path.join(self.d, "papers")
        os.makedirs(other)
        s = self.res(f"find topics level: high depth: quick cutoff 2026-01-31 out: ./scout from {other}")
        self.assertEqual((s["level"]["source"], s["depth"]["source"]), ("request (explicit)", "request (explicit)"))
        self.assertEqual(s["cutoff"]["value"], "2026-01-31")
        self.assertEqual(s["corpus"]["paths"], [other])
        self.assertEqual(s["out_dir"]["value"], os.path.join(self.proj, "scout"))

    def test_out_dir_is_not_a_corpus_path(self):
        s = self.res("탐색적으로 빠르게 주제 찾아줘. out: /nonexistent/run-dir.")
        self.assertEqual(s["out_dir"]["value"], "/nonexistent/run-dir")
        self.assertFalse(any("not found" in n for n in s["notes"]))

    def test_extra_language(self):
        self.assertIsNone(self.res("find me a topic")["extra_language"]["value"])
        self.assertEqual(self.res("주제 찾아줘, 한국어로도")["extra_language"]["value"], "ko")
        self.assertEqual(self.res("find topics, also in Korean")["extra_language"]["value"], "ko")
        self.assertEqual(self.res("find topics lang: ja")["extra_language"]["value"], "ja")
        # profile key, and the legacy output_language key
        p2 = os.path.join(self.d, "prof2")
        rc, _ = run(pinit.main, ["--dir", p2, "--interests", "x", "--extra-language", "ko"])
        self.assertEqual(rc, 0)
        self.assertEqual(settings.load_constants(p2)["extra_report_language"], "ko")
        s = settings.resolve("find topics", profile=p2, cwd=self.proj, today="2026-11-05", env={})
        self.assertEqual((s["extra_language"]["value"], s["extra_language"]["source"]), ("ko", "profile"))
        prof = os.path.join(p2, "profile.md")
        write(prof, read(prof).replace('"extra_report_language": "ko"', '"output_language": "ko"'))
        s = settings.resolve("find topics", profile=p2, cwd=self.proj, today="2026-11-05", env={})
        self.assertEqual(s["extra_language"]["value"], "ko")
        self.assertEqual(settings.load_constants(self.prof)["extra_report_language"], None)

    def test_low_ignores_corpus_and_conflicts(self):
        s = self.res("level: low, use ./train.py")
        self.assertEqual(s["corpus"]["paths"], [])
        self.assertTrue(any("not read" in n for n in s["notes"]))
        s = self.res("내 코드로 탐색적으로")
        self.assertEqual(s["level"]["value"], "medium")
        self.assertTrue(any("both" in n for n in s["notes"]))

    def test_missing_profile(self):
        s = settings.resolve("주제 찾아줘", profile=None, cwd=self.proj, today="2026-11-05", env={"HOME": self.d})
        # the real home may hold a profile; only check the status field is well-formed
        self.assertIn(s["profile"]["status"], ("found", "missing"))
        rc, out = run(settings.main, ["--request", "x", "--profile", os.path.join(self.d, "nope"), "--cwd", self.d])
        self.assertIn("level: medium", out)

    def test_profile_init_refuses_overwrite_and_template_parses(self):
        rc, out = run(pinit.main, ["--dir", self.prof, "--interests", "x"])
        self.assertEqual(rc, 1)
        c = settings.load_constants(self.prof)
        self.assertEqual(c["interests"], ["medical imaging", "uncertainty"])
        tpl = settings.load_constants(os.path.join(ROOT, "templates"))
        self.assertIn(tpl["scout_level"], settings.LEVELS)
        self.assertIn(tpl["scout_depth"], settings.DEPTHS)


class TestGuard(unittest.TestCase):
    def test_env_sentinel_override(self):
        d = tempfile.mkdtemp()
        try:
            sub = os.path.join(d, "a", "b")
            os.makedirs(sub)
            self.assertTrue(guard.check(sub, {})[0])
            self.assertFalse(guard.check(sub, {"RESEARCH_TOPIC_SKILLS_DISABLE": "1"})[0])
            write(os.path.join(d, ".no-research-topic-skills"), "")
            ok, msg = guard.check(sub, {})
            self.assertFalse(ok)
            self.assertIn("sentinel", msg)
            self.assertTrue(guard.check(sub, {"RESEARCH_TOPIC_SKILLS_ALLOW": "yes"})[0])
            rc, _ = run(guard.main, ["--cwd", sub])
            self.assertEqual(rc, 3)
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
