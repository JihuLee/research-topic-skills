"""Offline tests for the helper scripts. Run: python3 -m unittest discover -s tests -v

Set LIT_FETCH_LIVE=1 to also run one small live query against arXiv and OpenAlex.
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
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
sys.path.insert(0, os.path.join(ROOT, "shared", "scripts"))
lessons = load("lessons", "shared/scripts/lessons.py")
tracks = load("tracks", "shared/scripts/tracks.py")


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


class TestLedgerFamiliesAndIndex(unittest.TestCase):
    def test_index_history_parent_and_expanded_check(self):
        d = tempfile.mkdtemp()
        try:
            lp = os.path.join(d, "ledger.jsonl")
            base = {"date": "2026-01-01", "verdict": "near-miss", "tags": ["calibration"],
                    "killers": [{"title": "Prior paper A"}]}
            run(ledger.main, ["add", lp, "--json", json.dumps(dict(base, id="T1", title="Label smoothing under shift",
                              claim="Label smoothing beats temperature scaling under distribution shift."))])
            run(ledger.main, ["add", lp, "--json", json.dumps(dict(base, id="T1R", parent="T1", date="2026-02-01",
                              verdict="killed", title="Label smoothing under shift, revised",
                              claim="Revised label smoothing claim."))])
            run(ledger.main, ["add", lp, "--json", json.dumps({"id": "T2", "date": "2026-01-05", "verdict": "killed",
                              "title": "Rank metric flip", "claim": "AUROC changes after temperature scaling.", "tags": ["ood"]})])
            idx = read(os.path.join(d, "ledger_index.md"))
            self.assertIn("3 entries in 2 topic families", idx)
            self.assertIn("T1R · killed", idx)
            self.assertIn("(+1 earlier: T1)", idx)
            self.assertNotIn("- 2026-01-01 T1 ", idx)
            rc, _ = run(ledger.main, ["update", lp, "--id", "T2", "--set", "verdict=closed"])
            row = [json.loads(l) for l in read(lp).splitlines() if '"T2"' in l][0]
            self.assertEqual(row["history"][0]["previous"], {"verdict": "killed"})
            self.assertIn("T2 · closed", read(os.path.join(d, "ledger_index.md")))
            with self.assertRaises(SystemExit):
                run(ledger.main, ["update", lp, "--id", "T2", "--set", "id=X"])
            rc, out = run(ledger.main, ["validate", lp])
            self.assertEqual(rc, 0, out)
            # a renamed idea: the plain claim misses it, a paraphrase finds it
            rc, out = run(ledger.main, ["check", lp, "--claim", "Monotone recalibration alters ranking quality."])
            self.assertNotIn("T2 ", out)
            rc, out = run(ledger.main, ["check", lp, "--claim", "Monotone recalibration alters ranking quality.",
                                        "--also", "AUROC changes after temperature scaling of scores"])
            self.assertIn("T2 ", out)
            write(lp, read(lp) + json.dumps({"id": "T3", "date": "2026-03-01", "verdict": "killed", "title": "x",
                                             "claim": "y", "parent": "NOPE"}) + "\n")
            rc, out = run(ledger.main, ["validate", lp])
            self.assertEqual(rc, 1)
            self.assertIn("parent", out)
        finally:
            shutil.rmtree(d)


LESSONS_MD = """# Lessons

Checklist for the novelty gate.

## Novelty
- [L1|pinned||h0/x0/n9] Check: simulated ground truth is never presented as real-sensor ground truth.
- [L2|scoped|detection,metrics|h3/x0/n4] Check: a ranking change is not forced by the metric's invariance.
  - rank metrics under one monotone transform
- an unmarked lesson about checking the leaderboard of the last three months

## Data
- [L3|core|data|h0/x0/n6] Check: the license of every asset was checked separately.
- [L4|core|data|h0/x2/n3] Check: the licence of each asset is checked separately.
"""


class TestLessons(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        write(os.path.join(self.d, "lessons.md"), LESSONS_MD)
        write(os.path.join(self.d, "profile.md"), "# p\n\n```json profile\n" + json.dumps(
            {"lessons_core_cap": 2, "lessons_review_every_gates": 2, "lessons_max_active": 40}) + "\n```\n")

    def tearDown(self):
        shutil.rmtree(self.d)

    def plan(self, ops, dry=False):
        pp = os.path.join(self.d, "plan.json")
        dump({"ops": ops}, pp)
        return run(lessons.main, ["apply", self.d, pp] + (["--dry-run"] if dry else []))

    def test_starter_template_matches_and_is_empty(self):
        tpl = read(os.path.join(ROOT, "templates", "lessons.md"))
        self.assertEqual(tpl, pinit.LESSONS)
        self.assertEqual(lessons.parse(tpl.split("\n")), [])

    def test_parse_and_select(self):
        ls = lessons.parse(LESSONS_MD.split("\n"))
        self.assertEqual([l.id for l in ls], ["L1", "L2", "U1", "L3", "L4"])
        self.assertEqual(ls[1].sub, ["  - rank metrics under one monotone transform"])
        rc, out = run(lessons.main, ["select", self.d, "--tags", "metrics"])
        for i in ("L1", "L2", "L3", "L4", "unmarked lesson"):
            self.assertIn(i, out)
        rc, out = run(lessons.main, ["select", self.d])
        self.assertNotIn("[L2|", out)
        self.assertIn("Their tags: detection, metrics", out)

    def test_apply_ops_and_archive(self):
        before = read(os.path.join(self.d, "lessons.md"))
        rc, out = self.plan([{"op": "adopt", "ref": "U1", "tier": "scoped", "tags": ["benchmark"]}], dry=True)
        self.assertIn("DRY-RUN ADOPT U1 -> L5", out)
        self.assertEqual(read(os.path.join(self.d, "lessons.md")), before)
        rc, out = self.plan([
            {"op": "adopt", "ref": "U1", "tier": "scoped", "tags": ["benchmark"]},
            {"op": "merge", "into": "L3", "ids": ["L4"]},
            {"op": "add", "text": "Check: the official evaluation script was used.", "tier": "core", "tags": ["eval"], "section": "Novelty"},
            {"op": "edit", "id": "L2", "tier": "core"},
            {"op": "archive", "id": "L1", "reason": "test"},
        ])
        self.assertEqual(rc, 0, out)
        text = read(os.path.join(self.d, "lessons.md"))
        self.assertIn("- [L5|scoped|benchmark|h0/x0/n0] an unmarked lesson", text)
        self.assertIn("- [L3|core|data|h0/x2/n9] Check: the license", text)
        self.assertIn("- [L6|core|eval|h0/x0/n0] Check: the official", text)
        self.assertIn("[L2|core|detection,metrics|", text)
        self.assertLess(text.index("[L6|"), text.index("## Data"))
        self.assertNotIn("[L1|", text)
        self.assertNotIn("[L4|", text)
        arch = read(os.path.join(self.d, "lessons_archive.md"))
        self.assertIn("[L4|core|data|h0/x2/n3]", arch)
        self.assertIn("merged into L3", arch)
        self.assertIn("archived", arch)
        rc, out = run(lessons.main, ["similar", self.d, "--text", "simulated ground truth presented as real"])
        self.assertIn("L1 (archived)", out.splitlines()[0])
        with self.assertRaises(SystemExit):
            self.plan([{"op": "archive", "id": "L2"}])

    def test_unmarked_refs_stay_stable_within_a_plan(self):
        write(os.path.join(self.d, "lessons.md"), "# L\n\n- first plain\n- second plain\n  - detail\n- third plain\n")
        rc, out = self.plan([{"op": "adopt", "ref": "U1", "tier": "core", "tags": ["a"]},
                             {"op": "archive", "ref": "U2", "reason": "covered by the skill"},
                             {"op": "adopt", "ref": "U3", "tier": "scoped", "tags": ["b"]}])
        self.assertEqual(rc, 0, out)
        text = read(os.path.join(self.d, "lessons.md"))
        self.assertIn("- [L1|core|a|h0/x0/n0] first plain", text)
        self.assertIn("- [L3|scoped|b|h0/x0/n0] third plain", text)
        self.assertNotIn("second plain", text)
        arch = read(os.path.join(self.d, "lessons_archive.md"))
        self.assertIn("- [L2|core||h0/x0/n0] second plain", arch)
        self.assertIn("  - detail", arch)

    def test_tally_review_and_counter(self):
        out_dir = os.path.join(self.d, "gate1")
        os.makedirs(out_dir)
        dump({"lessons": [{"id": "L2", "result": "caught"}, {"id": "L3", "result": "clear"},
                          {"id": "L4", "result": "false_alarm"}, {"id": "L1", "result": "n/a"}]},
             os.path.join(out_dir, "gate_summary.json"))
        rc, out = run(lessons.main, ["tally", self.d, out_dir])
        self.assertIn("caught 1, clear 1, false_alarm 1, n/a 1", out)
        self.assertIn("REVIEW DUE", out)  # pinned + core = 3 > cap 2
        text = read(os.path.join(self.d, "lessons.md"))
        self.assertIn("[L2|scoped|detection,metrics|h4/x0/n5]", text)
        self.assertIn("[L3|core|data|h0/x0/n7]", text)
        self.assertIn("[L4|core|data|h0/x3/n4]", text)
        self.assertIn("[L1|pinned||h0/x0/n9]", text)
        rc, out = run(lessons.main, ["tally", self.d, out_dir])
        self.assertIn("already tallied", out)
        rc, out = run(lessons.main, ["review", self.d, "--json"])
        r = json.loads(out)
        self.assertEqual([u["ref"] for u in r["unmarked"]], ["U1"])
        self.assertIn(["L3", "L4"], [x["ids"] for x in r["near_duplicates"]])
        self.assertEqual([x["id"] for x in r["never_caught"]], ["L3"])  # L1 is pinned
        self.assertEqual([x["id"] for x in r["false_alarms"]], ["L4"])
        self.assertEqual([x["id"] for x in r["promote"]], ["L2"])
        self.assertTrue(r["core_over_cap"])
        run(lessons.main, ["mark-reviewed", self.d])
        state = json.loads(read(os.path.join(self.d, "lessons_state.json")))
        self.assertEqual(state["gates_since_review"], 0)


class TestTracks(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.prof = os.path.join(self.d, "prof")
        run(pinit.main, ["--dir", self.prof, "--interests", "a; b"])
        self.lp = os.path.join(self.prof, "ledger.jsonl")
        rows = [{"id": "2026-01-01-C2", "date": "2026-01-01", "title": "Old idea in track", "claim": "x",
                 "verdict": "killed", "track": "calib"},
                {"id": "2026-01-02-C5", "date": "2026-01-02", "title": "Idea elsewhere",
                 "claim": "label smoothing calibration under shift", "verdict": "killed", "track": "other"}]
        write(self.lp, "\n".join(json.dumps(r) for r in rows) + "\n")

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_settings_create_record_show(self):
        s = settings.resolve(profile=self.prof, cwd=self.d, today="2026-11-14", env={}, track="calib")
        self.assertEqual(s["scope"]["value"], "track")
        self.assertIsNone(s["track"])
        self.assertTrue(any("one-sentence focus" in n for n in s["notes"]))
        s = settings.resolve(profile=self.prof, cwd=self.d, today="2026-11-14", env={}, track="calib",
                             focus="Calibration of detectors under shift", track_tags="calibration")
        self.assertEqual((s["track"]["status"], s["track"]["next_candidate"]), ("created", "C3"))
        self.assertEqual(s["direction"], "Calibration of detectors under shift")
        self.assertTrue(s["out_dir"]["value"].endswith("scout-2026-11-14-calib"))
        self.assertIn("scope: track calib (created)", settings.card(s))
        out = os.path.join(self.d, "run1")
        os.makedirs(out)
        write(os.path.join(out, "candidates.jsonl"), "\n".join(json.dumps(r) for r in [
            {"id": "C3", "hypothesis": "first new idea", "status": "dropped"},
            {"id": "C4", "hypothesis": "second new idea", "status": "annotated"}]) + "\n")
        rc, o = run(tracks.main, ["record", self.prof, "calib", out])
        self.assertIn("recorded 2 new", o)
        self.assertIn("next C5", o)
        write(os.path.join(out, "candidates.jsonl"), json.dumps({"id": "C4", "hypothesis": "second new idea", "status": "gated"}) + "\n")
        rc, o = run(tracks.main, ["record", self.prof, "calib", out])
        self.assertIn("0 new and 1 updated", o)
        rc, o = run(tracks.main, ["show", self.prof, "calib"])
        for needle in ("next candidate: C5", "C3 [dropped]", "C4 [gated]", "2026-01-01-C2 [killed]"):
            self.assertIn(needle, o)
        self.assertNotIn("Idea elsewhere", o)
        s = settings.resolve(profile=self.prof, cwd=self.d, today="2026-11-14", env={}, track="calib")
        self.assertEqual((s["track"]["status"], s["track"]["earlier"], s["track"]["closed"]), ("found", 3, 2))
        rc, o = run(tracks.main, ["list", self.prof])
        self.assertIn("calib", o)

    def test_scope_from_profile_and_global_default(self):
        s = settings.resolve(profile=self.prof, cwd=self.d, today="2026-11-14", env={})
        self.assertEqual((s["scope"]["value"], s["scope"]["source"]), ("global", "profile"))
        prof = os.path.join(self.prof, "profile.md")
        write(prof, read(prof).replace('"scout_scope": "global"', '"scout_scope": "track"'))
        s = settings.resolve(profile=self.prof, cwd=self.d, today="2026-11-14", env={})
        self.assertEqual(s["scope"]["value"], "track")
        self.assertTrue(any("no track was named" in n for n in s["notes"]))
        s = settings.resolve(profile=self.prof, cwd=self.d, today="2026-11-14", env={}, scope="global")
        self.assertEqual((s["scope"]["value"], s["scope"]["source"]), ("global", "request"))

    def test_ledger_track_views(self):
        rc, o = run(ledger.main, ["index", self.lp, "--track", "calib"])
        self.assertIn("track calib", o)
        self.assertIn("Old idea in track", o)
        self.assertNotIn("Idea elsewhere", o)
        rc, o = run(ledger.main, ["list", self.lp, "--track", "other"])
        self.assertIn("Idea elsewhere", o)
        self.assertNotIn("Old idea", o)
        rc, o = run(ledger.main, ["check", self.lp, "--claim", "label smoothing calibration under shift", "--track", "calib"])
        self.assertIn("other track: other", o)
        run(ledger.main, ["index", self.lp])
        self.assertIn("(track: other)", read(os.path.join(self.prof, "ledger_index.md")))
        summ = os.path.join(self.d, "g")
        os.makedirs(summ)
        dump({"date": "2026-11-14", "track": "calib", "candidates": [{"id": "C7", "title": "t", "claim": "c",
              "status": "killed", "novelty": 2, "feasibility": 4}]}, os.path.join(summ, "gate_summary.json"))
        rc, o = run(ledger.main, ["add", self.lp, "--from-summary", summ])
        self.assertIn('"track": "calib"', [l for l in read(self.lp).splitlines() if "2026-11-14-C7" in l][0])
        write(self.lp, read(self.lp) + json.dumps({"id": "bad", "date": "2026-01-03", "title": "t", "claim": "c",
                                                   "verdict": "killed", "track": "Bad Name"}) + "\n")
        rc, o = run(ledger.main, ["validate", self.lp])
        self.assertEqual(rc, 1)
        self.assertIn("track must be", o)


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

    def test_after_results_only_tightens(self):
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "thresholds.json")
            base = {"min_effect": 0.4, "kill_if": "x", "baselines": ["native", "default"], "budget": {"gpu_hours": 4}}
            dump(base, p)
            self.assertEqual(run(freeze.main, ["freeze", p])[0], 0)
            dump(dict(base, min_effect=0.3), p)
            rc, _ = run(freeze.main, ["freeze", p])
            self.assertEqual(rc, 1)  # re-freezing a changed file is refused
            for relaxed in (dict(base, min_effect=0.3), dict(base, kill_if="y"), dict(base, baselines=["native"]),
                            dict(base, budget={"gpu_hours": 8})):
                dump(relaxed, p)
                rc, _ = run(freeze.main, ["amend", p, "--reason", "r", "--after-results"])
                self.assertEqual(rc, 1, relaxed)
            dump(dict(base, min_effect=0.5, baselines=["native", "default", "equal_compute"]), p)
            rc, _ = run(freeze.main, ["amend", p, "--reason", "tighten", "--after-results"])
            self.assertEqual(rc, 0)
            self.assertEqual(run(freeze.main, ["verify", p])[0], 0)
            log = [json.loads(l) for l in read(p + ".amendments.jsonl").splitlines()]
            self.assertEqual(log[-1]["changes"], ["$.baselines", "$.min_effect"])
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

    def test_bare_codes_only_warn(self):
        ok = self.good.replace("It does not test shift.", "It does not test full FT of the backbone or E5 embeddings.")
        write(os.path.join(self.d, "report.md"), ok)
        rc, out = run(lambda a: lint.lint_gate(*a), [self.d, None, None])
        self.assertEqual(rc, 0, out)
        self.assertIn("possible evidence tag", out)
        self.assertIn("possible evidence id", out)

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


    def test_fuzzy_accepts_small_edits_but_not_meaning_flips(self):
        d = tempfile.mkdtemp()
        try:
            body = ("Intro text that is unrelated to the claim. We find that label smoothing improves the calibration "
                    "of the network on in-distribution test data, and the gain is 15% across all architectures we "
                    "evaluated. Another sentence follows here, ending the text.")
            write(os.path.join(d, "p.txt"), body)
            ev = os.path.join(d, "evidence.jsonl")
            def check(quote):
                write(ev, json.dumps({"id": "E1", "tag": "FT", "source": "p.txt", "quote": quote}) + "\n")
                return run(qc.main, [ev])
            rc, out = check("label smoothing improves calibration of the network on in-distribution test data, and the gain is 15%")
            self.assertEqual(rc, 0, out)
            self.assertIn("fuzzy", out)
            for bad, word in (("label smoothing does not improve the calibration of the network on in-distribution test data", "not"),
                              ("the gain is 25% across all architectures we evaluated", "25%"),
                              ("another sentence follows here, not ending the text.", "not")):
                rc, out = check(bad)
                self.assertEqual(rc, 1, out)
                self.assertIn(word, out)
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

    def test_refuses_home_root_and_parents(self):
        d = tempfile.mkdtemp()
        old_home = os.environ.get("HOME")
        try:
            home = os.path.join(d, "home", "user")
            os.makedirs(os.path.join(home, "project"))
            write(os.path.join(home, "project", "a.py"), "x = 1\n")
            os.environ["HOME"] = home
            for bad in (home, os.path.join(d, "home"), os.path.sep, "~"):
                rc, _ = run(scan.main, [bad])
                self.assertEqual(rc, 2, bad)
            rc, _ = run(scan.main, [os.path.join(home, "project"), "--out", os.path.join(d, "o.md")])
            self.assertEqual(rc, 0)
        finally:
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home
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

    def res(self, cwd=None, **kw):
        return settings.resolve(profile=self.prof, cwd=cwd or self.proj, today="2026-11-05", env={}, **kw)

    def test_defaults_and_auto_corpus(self):
        s = self.res()
        self.assertEqual((s["level"]["value"], s["level"]["source"]), ("medium", "profile"))
        self.assertEqual((s["depth"]["value"], s["finalists"]["value"], s["gate_mode"]), ("standard", 1, "light"))
        self.assertEqual(s["corpus"]["paths"], [self.proj])
        self.assertEqual(s["cutoff"]["value"], "2026-11-05")
        self.assertIsNone(s["direction"])

    def test_flags(self):
        s = self.res(level="low", depth="quick", field="depth estimation")
        self.assertEqual((s["level"]["value"], s["depth"]["value"], s["finalists"]["value"]), ("low", "quick", 0))
        self.assertEqual((s["level"]["source"], s["gate_mode"]), ("request", "none"))
        self.assertEqual(s["direction"], "depth estimation")
        self.assertEqual(s["corpus"]["paths"], [])
        s = self.res(level="high", depth="full")
        self.assertEqual((s["finalists"]["value"], s["gate_mode"]), (3, "full"))
        self.assertEqual(self.res(depth="full", gate=1)["finalists"]["value"], 1)

    def test_paths_cutoff_out(self):
        other = os.path.join(self.d, "papers")
        os.makedirs(other)
        s = self.res(corpus=[other, "./missing"], cutoff="2026-01-31", out="./scout")
        self.assertEqual(s["corpus"]["paths"], [other])
        self.assertTrue(any("not found" in n for n in s["notes"]))
        self.assertEqual(s["cutoff"]["value"], "2026-01-31")
        self.assertEqual(s["out_dir"]["value"], os.path.join(self.proj, "scout"))

    def test_extra_language(self):
        self.assertIsNone(self.res()["extra_language"]["value"])
        self.assertEqual(self.res(extra_language="ko")["extra_language"]["value"], "ko")
        self.assertIsNone(self.res(extra_language="none")["extra_language"]["value"])
        p2 = os.path.join(self.d, "prof2")
        rc, _ = run(pinit.main, ["--dir", p2, "--interests", "x", "--extra-language", "ko"])
        self.assertEqual(rc, 0)
        self.assertEqual(settings.load_constants(p2)["extra_report_language"], "ko")
        s = settings.resolve(profile=p2, cwd=self.proj, today="2026-11-05", env={})
        self.assertEqual((s["extra_language"]["value"], s["extra_language"]["source"]), ("ko", "profile"))
        prof = os.path.join(p2, "profile.md")
        write(prof, read(prof).replace('"extra_report_language": "ko"', '"output_language": "ko"'))
        s = settings.resolve(profile=p2, cwd=self.proj, today="2026-11-05", env={})
        self.assertEqual(s["extra_language"]["value"], "ko")
        self.assertEqual(settings.load_constants(self.prof)["extra_report_language"], None)

    def test_home_is_never_a_corpus(self):
        old_home = os.environ.get("HOME")
        try:
            os.environ["HOME"] = self.proj
            s = self.res(corpus=[self.proj, os.path.sep])
            self.assertTrue(all(not settings.too_broad(p) for p in s["corpus"]["paths"]))
            self.assertEqual(sum("corpus path not used" in n for n in s["notes"]), 2)
        finally:
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home

    def test_low_ignores_corpus(self):
        s = self.res(level="low", corpus=[os.path.join(self.proj, "train.py")])
        self.assertEqual(s["corpus"]["paths"], [])
        self.assertTrue(any("not read" in n for n in s["notes"]))

    def test_missing_profile_and_cli(self):
        s = settings.resolve(profile=None, cwd=self.proj, today="2026-11-05", env={"HOME": self.d})
        # the real home may hold a profile; only check the status field is well-formed
        self.assertIn(s["profile"]["status"], ("found", "missing"))
        rc, out = run(settings.main, ["--profile", os.path.join(self.d, "nope"), "--cwd", self.d, "--depth", "quick"])
        self.assertIn("depth: quick (request)", out)
        self.assertIn("profile not found at", out)
        with self.assertRaises(SystemExit):
            run(settings.main, ["--depth", "deep"])

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
