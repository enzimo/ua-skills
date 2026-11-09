"""End-to-end checks for the coder-critic-team run ledger and report renderer."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "coder-critic-team" / "scripts"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cct = load("cct")
render = load("render_report")

T0 = "2026-11-09T14:00:00Z"


def at(minutes: int) -> str:
    return f"2026-11-09T{14 + minutes // 60:02d}:{minutes % 60:02d}:00Z"


def sh(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def write_lines(repo: Path, rel: str, count: int, tag: str, append: bool = True) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text() if append and path.exists() else ""
    path.write_text(old + "".join(f"# {tag} line {n}\n" for n in range(count)))


def commit(repo: Path, message: str) -> None:
    sh(repo, "add", "-A")
    sh(repo, "-c", "user.name=exampleuser", "-c", "user.email=exampleuser@example.com",
       "commit", "-q", "-m", message)


class Driver:
    """Drives a run the way a lead would, failing loudly on any refusal."""

    def __init__(self, base: Path):
        self.repo = base / "relay"
        self.run = base / "runs" / "relay-142"
        self.repo.mkdir(parents=True)
        sh(self.repo, "init", "-q", "-b", "main")
        write_lines(self.repo, "src/relay/delivery/worker.py", 120, "worker")
        write_lines(self.repo, "src/relay/metrics.py", 40, "metrics")
        write_lines(self.repo, "README.md", 20, "readme")
        commit(self.repo, "Initial relay")
        sh(self.repo, "switch", "-q", "-c", "feat/webhook-retry")

    def call(self, *argv: str) -> str:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cct.main(list(argv))
        if code != 0:
            raise AssertionError(f"cct {' '.join(argv[:2])} refused: {err.getvalue()}")
        return out.getvalue()

    def refused(self, *argv: str) -> str:
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = cct.main(list(argv))
        if code == 0:
            raise AssertionError(f"cct {' '.join(argv[:2])} was accepted")
        return err.getvalue()

    def post(self, minutes: int, turn) -> str:
        first = turn[0] if isinstance(turn, list) else turn
        path = self.run / "turns" / "lead-input.json"
        path.write_text(json.dumps(turn))
        return self.call("post", str(self.run), "--actor", cct.ACTOR_OF[first["type"]],
                         "--file", str(path), "--at", at(minutes))

    def init(self) -> None:
        brief = {
            "title": "Retry failed webhook deliveries with exponential backoff",
            "outcome": "Webhook deliveries that fail transiently are retried with backoff and "
                       "dead-lettered after the last attempt.",
            "acceptance_criteria": [
                "Retries 5xx and timeouts; never 4xx except 429",
                "Backoff doubles from 2 s, capped at 10 min, with full jitter",
                "No delivery is sent twice after a slow acknowledgement",
                "Dead-letter after the 8th attempt",
                "Retry counts and delays exported as metrics",
            ],
            "non_goals": ["No schema migrations", "No per-endpoint rate limiting"],
            "context": {"objective": "Reliable outbound notifications", "plan_step": "3 of 5"},
            "repo": {"name": "example-owner/relay", "path": str(self.repo), "base": "main",
                     "branch": "feat/webhook-retry"},
            "workers": {
                "coder": {"runtime": "claude-code", "model": "claude-opus-5-5", "effort": "xhigh"},
                "critic": {"runtime": "claude-code", "model": "claude-opus-5-5", "effort": "xhigh"},
            },
            "limits": {"max_checkpoints": 9, "stall_minutes": 45},
        }
        path = self.run.parent / "brief.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(brief))
        self.call("init", str(self.run), "--brief", str(path), "--at", T0)


LENSES = {lens: f"How the plan handles {lens}." for lens in cct.CORE_LENSES}
LENSES["security"] = "n/a: no new input surface or credentials."


def item(lens, severity, title, **extra):
    return {"lens": lens, "severity": severity, "title": title, **extra}


def acc(*ids):
    return [{"item": i, "decision": "accept"} for i in ids]


def run_sample(base: Path) -> Driver:
    """The sample run used by the tests and the design samples."""
    d = Driver(base)
    d.init()
    d.post(6, {"type": "plan", "summary": "One RetryPolicy, a scheduler hook and a dead-letter "
               "path; 6 units; 5 checkpoints.",
               "units": [{"name": n, "purpose": p} for n, p in [
                   ("RetryPolicy", "Decides whether and when to retry."),
                   ("schedule_retry()", "Queues the next attempt."),
                   ("BackoffCalculator", "Computes capped, jittered delays."),
                   ("DeliveryWorker.on_failure", "Routes failures to the policy."),
                   ("dead_letter()", "Stores deliveries that ran out of attempts."),
                   ("retry metrics", "Counts retries and delays.")]],
               "lenses": LENSES,
               "checkpoints": ["Backoff schedule tests", "RetryPolicy and schedule_retry()",
                               "Worker integration", "Dead-letter and failure paths",
                               "Metrics and docs"]})
    d.post(14, {"type": "review", "summary": "Sound plan; one blocker on duplicate delivery.",
                "items": [
                    item("correctness", "blocking", "A slow acknowledgement can cause a second delivery",
                         confidence="verified", where="plan: schedule_retry()",
                         suggestion="Send an idempotency key and keep it across attempts."),
                    item("correctness", "should_fix", "Honour Retry-After on 429"),
                    item("intent", "should_fix", "Criterion A4 has no planned test"),
                    item("scalability", "should_fix", "One slow receiver can starve the retry queue",
                         suggestion="Add a token bucket per endpoint."),
                    item("security", "consider", "Do not log full payloads on retry"),
                    item("complexity", "consider", "Fold BackoffCalculator into RetryPolicy"),
                    item("modularity", "consider", "Move backoff math to a shared utility"),
                    item("testing", "consider", "Use a fake clock instead of sleeping in tests"),
                ]})
    d.post(19, {"type": "response", "decisions": acc("C01", "C02", "C03", "C05", "C06", "C08") + [
        {"item": "C04", "decision": "reject",
         "rationale": "Out of scope (non-goal 2); the queue is partitioned by endpoint and "
                      "max_in_flight=4 bounds starvation."},
        {"item": "C07", "decision": "reject", "rationale": "Single consumer; keep it local."}]})
    d.post(24, {"type": "rebuttal", "positions": [
        {"item": "C04", "position": "maintain",
         "argument": "Four slow in-flight requests from one endpoint still delay every retry."},
        {"item": "C07", "position": "withdraw"}]})
    d.post(27, {"type": "final_call", "decisions": [
        {"item": "C04", "decision": "reject",
         "rationale": "Kept out of scope; logged for plan step 4 (per-endpoint limits)."}]})

    write_lines(d.repo, "tests/retry/test_policy.py", 142, "cp1")
    commit(d.repo, "Add backoff schedule tests")
    d.post(52, {"type": "checkpoint", "title": "Backoff schedule tests",
                "tests": {"command": "pytest tests/retry -q", "passed": 12, "failed": 0}})
    d.post(57, {"type": "review", "summary": "Tests cover the bounds; jitter order is off.",
                "items": [item("correctness", "should_fix", "Cap is applied before jitter"),
                          item("complexity", "consider", "Parametrise the eight bound tests"),
                          item("failure_handling", "consider", "Test the attempt after the cap")]})
    write_lines(d.repo, "src/relay/retry/policy.py", 104, "cp2")
    write_lines(d.repo, "src/relay/retry/scheduler.py", 84, "cp2")
    write_lines(d.repo, "src/relay/delivery/worker.py", 21, "cp2-trim", append=False)
    commit(d.repo, "Add RetryPolicy and schedule_retry")
    d.post(75, [{"type": "response", "decisions": acc("C09", "C10", "C11")},
                {"type": "checkpoint", "title": "RetryPolicy and schedule_retry()",
                 "tests": {"passed": 21, "failed": 0}}])
    d.post(80, {"type": "review", "summary": "Clean; one shared-state concern.",
                "items": [item("intent", "should_fix", "429 handling ignores criterion A1's wording"),
                          item("correctness", "consider", "Name the attempt counter consistently"),
                          item("concurrency", "should_fix", "Scheduler reads attempts without a lock"),
                          item("complexity", "consider", "Strategy classes for RetryPolicy")]})
    write_lines(d.repo, "src/relay/delivery/worker.py", 100, "cp3")
    write_lines(d.repo, "tests/delivery/test_worker_retry.py", 21, "cp3")
    commit(d.repo, "Integrate retries into the delivery worker")
    d.post(98, [{"type": "response", "decisions": acc("C12", "C13", "C14") + [
        {"item": "C15", "decision": "reject",
         "rationale": "One policy with three parameters; a class hierarchy adds indirection."}]},
        {"type": "checkpoint", "title": "Delivery worker integration",
         "tests": {"passed": 30, "failed": 0}}])
    d.post(104, {"type": "review", "summary": "Integration works; two blockers.",
                 "items": [item("correctness", "blocking", "Two workers can claim the same retry"),
                           item("concurrency", "blocking", "Idempotency keys kept in memory are lost on restart"),
                           item("security", "should_fix", "Retry-After is trusted without an upper bound"),
                           item("complexity", "consider", "Inline the one-line wrapper"),
                           item("concurrency", "consider", "Use an advisory lock instead of SKIP LOCKED")]})
    d.post(106, {"type": "response", "decisions": acc("C16", "C18", "C19") + [
        {"item": "C17", "decision": "partial",
         "rationale": "Keep the in-memory cache; a new table needs a migration the brief excludes."},
        {"item": "C20", "decision": "reject", "rationale": "The worker pool already uses SKIP LOCKED."}]})
    d.post(110, {"type": "rebuttal", "positions": [
        {"item": "C17", "position": "maintain",
         "argument": "After a restart the cache is empty and a slow acknowledgement is delivered twice."}]})
    d.post(114, {"type": "intervention", "reason": "blocker_dispute",
                 "summary": "Reuse deliveries.attempt_token: it survives restarts and needs no migration.",
                 "rulings": [{"item": "C17", "decision": "partial",
                              "rationale": "Store the key in the existing attempt_token column."}]})
    write_lines(d.repo, "src/relay/delivery/dead_letter.py", 34, "cp4")
    write_lines(d.repo, "tests/delivery/test_dead_letter.py", 62, "cp4")
    commit(d.repo, "Dead-letter and failure paths")
    d.post(130, {"type": "checkpoint", "title": "Dead-letter and failure paths",
                 "tests": {"passed": 37, "failed": 0}})
    d.post(134, {"type": "review", "summary": "Good coverage of the failure paths.",
                 "items": [item("failure_handling", "should_fix", "Dead-letter on non-retryable 4xx too"),
                           item("scalability", "consider", "Batch dead-letter inserts")]})
    write_lines(d.repo, "src/relay/metrics.py", 18, "cp5")
    write_lines(d.repo, "docs/retries.md", 34, "cp5")
    commit(d.repo, "Retry metrics and docs")
    d.post(146, [{"type": "response", "decisions": acc("C21", "C22")},
                 {"type": "checkpoint", "title": "Metrics and docs", "tests": {"passed": 40, "failed": 0}}])
    d.post(148, {"type": "review", "summary": "Fine.",
                 "items": [item("modularity", "consider", "Register metrics where the others are")]})
    write_lines(d.repo, "src/relay/metrics.py", 4, "final")
    commit(d.repo, "Register retry metrics with the others")
    d.post(154, [{"type": "response", "decisions": acc("C23")},
                 {"type": "checkpoint", "title": "Full suite and lint", "final": True,
                  "tests": {"command": "pytest -q && ruff check", "passed": 41, "failed": 0}}])
    d.post(158, {"type": "review", "summary": "Ready for a pull request.",
                 "items": [item("testing", "consider", "Add a test for the eighth attempt exactly")]})
    write_lines(d.repo, "tests/retry/test_policy.py", 6, "final-test")
    commit(d.repo, "Test the eighth attempt")
    d.post(160, [{"type": "response", "decisions": acc("C24")},
                 {"type": "checkpoint", "title": "Test the eighth attempt",
                  "tests": {"passed": 42, "failed": 0}}])
    d.post(161, {"type": "review", "summary": "Covered.", "items": []})
    d.post(162, {"type": "pr", "url": "https://github.com/example-owner/relay/pull/142",
                 "number": 142, "title": "Retry failed webhook deliveries with exponential backoff",
                 "draft": True})
    d.post(180, {"type": "review_result", "verdict": "approve_with_changes",
                 "reviewers": ["General reviewer", "Evidence auditor", "Failure analyst",
                               "Intent checker", "Data integrity reviewer",
                               "Failure analyst (cross-provider)"],
                 "findings": [
                     {"severity": "blocking", "confidence": "verified",
                      "title": "A dead-letter write is lost while the database is briefly unavailable",
                      "where": "src/relay/delivery/dead_letter.py:41",
                      "scenario": "The final attempt fails during a 2-second database failover."},
                     {"severity": "should_fix", "confidence": "likely",
                      "title": "One slow endpoint delays retries for every other endpoint",
                      "matches_item": "C04"},
                     {"severity": "should_fix", "title": "Jitter and maximum delay are hard-coded",
                      "where": "src/relay/retry/policy.py:18"},
                     {"severity": "consider", "confidence": "possible",
                      "title": "No test for clock skew between scheduler and worker"}]})
    d.post(182, {"type": "fix_request", "findings": ["F1"]})
    write_lines(d.repo, "src/relay/delivery/dead_letter.py", 18, "fix")
    write_lines(d.repo, "tests/delivery/test_dead_letter.py", 12, "fix")
    commit(d.repo, "Retry the dead-letter write")
    d.post(194, {"type": "checkpoint", "title": "Retry the dead-letter write",
                 "tests": {"passed": 43, "failed": 0}})
    d.post(198, {"type": "review", "summary": "The fix is complete.", "items": []})
    d.post(200, {"type": "pr", "url": "https://github.com/example-owner/relay/pull/142",
                 "update": True})
    d.post(206, {"type": "finding_update", "updates": [
        {"finding": "F1", "status": "fixed",
         "evidence": "test_dead_letter_survives_failover passes; write retried 3 times."}]})
    d.post(211, {"type": "finding_update", "updates": [
        {"finding": "F2", "status": "issue_filed",
         "issue_url": "https://github.com/example-owner/relay/issues/143"},
        {"finding": "F3", "status": "issue_filed",
         "issue_url": "https://github.com/example-owner/relay/issues/144"},
        {"finding": "F4", "status": "issue_filed",
         "issue_url": "https://github.com/example-owner/relay/issues/145"}]})
    d.post(213, {"type": "acceptance", "criteria": [
        {"id": "A1", "status": "met", "evidence": "test_policy::test_retryable_statuses"},
        {"id": "A2", "status": "met", "evidence": "test_policy::test_schedule_bounds"},
        {"id": "A3", "status": "met", "evidence": "test_worker_retry::test_slow_ack_once"},
        {"id": "A4", "status": "met", "evidence": "test_dead_letter::test_eighth_attempt"},
        {"id": "A5", "status": "partial", "evidence": "Counts exported; delays only as a sum."}]})
    d.post(215, {"type": "narrative", "summary":
                 "The pair delivered backoff-based retries for failed webhooks. The critic raised 24 "
                 "points and the coder took most of them; the one blocker they could not settle, "
                 "where to keep idempotency keys, was ruled on by the lead under the no-migration "
                 "rule. Project review found one blocking gap in the dead-letter path, which the "
                 "pair fixed, and three follow-ups now filed as issues.",
                 "next_steps": ["Merge after a human review of C04 and C17",
                                "Plan step 4 picks up per-endpoint limits (#143)"]})
    d.post(216, {"type": "close", "outcome": "ready_to_merge"})
    return d


class SampleRunTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.driver = run_sample(Path(cls.tmp.name))
        cls.driver.call("stats", str(cls.driver.run))
        cls.stats = json.loads((cls.driver.run / "stats.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_counts_come_from_the_ledger(self):
        s = self.stats
        self.assertEqual(s["items"]["total"], 24)
        self.assertEqual(s["items"]["by_decision"],
                         {"accepted": 19, "partial": 1, "rejected": 3, "withdrawn": 1, "open": 0})
        self.assertEqual(s["items"]["by_severity"], {"blocking": 3, "should_fix": 8, "consider": 13})
        self.assertEqual(s["counts"]["reviews"], 9)
        self.assertEqual(s["counts"]["rebuttals"], 2)
        self.assertEqual(s["counts"]["checkpoints"], 8)
        self.assertEqual(s["counts"]["interventions"], 1)
        self.assertEqual(s["counts"]["fix_rounds"], 1)
        self.assertEqual(s["items"]["lead_rulings"], 1)
        self.assertEqual(s["run"]["status"], "ready_to_merge")
        self.assertEqual(s["run"]["elapsed_min"], 216)
        self.assertEqual(s["warnings"], [])

    def test_diff_is_measured_with_git(self):
        diff = self.stats["diff"]
        self.assertGreater(diff["adds"], 0)
        self.assertEqual(diff["commits"], 8)
        self.assertEqual(set(diff["by_kind"]), {"source", "tests", "docs"})
        self.assertEqual(diff["by_kind"]["docs"]["adds"], 34)

    def test_review_links_findings_to_critiques(self):
        review = self.stats["review"]
        self.assertEqual(review["by_severity"], {"blocking": 1, "should_fix": 2, "consider": 1})
        self.assertEqual(review["matched_items"], 1)
        statuses = {f["id"]: f["status"] for f in review["findings"]}
        self.assertEqual(statuses, {"F1": "fixed", "F2": "issue_filed", "F3": "issue_filed",
                                    "F4": "issue_filed"})
        c04 = next(i for i in self.stats["item_list"] if i["id"] == "C04")
        self.assertEqual(c04["outcome"], "rejected")
        self.assertEqual(c04["matched_by_review"], ["F2"])
        self.assertIn("max_in_flight=4", c04["rationale"])
        self.assertIn("plan step 4", c04["final_rationale"])

    def test_timeline_covers_the_run(self):
        tl = self.stats["timeline"]
        self.assertEqual([p["label"] for p in tl["phases"]], ["Plan", "Build", "Review"])
        lanes = {s["lane"] for s in tl["spans"]}
        self.assertEqual(lanes, {"coder", "critic", "lead", "review"})
        self.assertEqual(tl["spans"][-1]["end"], 216)

    def test_report_renders_without_scripts(self):
        for mode in ("page", "t3"):
            html = render.render(self.stats, mode)
            self.assertNotIn("<script", html.lower())
            self.assertNotRegex(html, r"https?://(?!github\.com/example-owner)")
            for text in ("Retry failed webhook deliveries", "Decisions to check",
                         "Project review", "C17", "F1"):
                self.assertIn(text, html)
        t3 = render.render(self.stats, "t3")
        self.assertIn("var(--foreground", t3)
        self.assertNotRegex(t3, r"(?s)(html|body)\s*\{[^}]*background")

    def test_turn_brief_lists_the_open_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Driver(Path(tmp))
            d.init()
            d.post(5, {"type": "plan", "summary": "s", "units": [{"name": "u", "purpose": "p"}],
                       "lenses": LENSES, "checkpoints": ["one"]})
            d.post(9, {"type": "review", "summary": "s",
                       "items": [item("intent", "blocking", "Misses criterion A3")]})
            text = d.call("turn", str(d.run), "--for", "coder")
            self.assertIn("C01", text)
            self.assertIn("Misses criterion A3", text)
            self.assertIn("Nothing is waiting", d.call("turn", str(d.run), "--for", "critic"))


class ProtocolRefusalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Driver(Path(self.tmp.name))
        self.d.init()

    def tearDown(self):
        self.tmp.cleanup()

    def post_refused(self, turn, actor=None, name="lead-input.json") -> str:
        first = turn[0] if isinstance(turn, list) else turn
        path = self.d.run / "turns" / name
        path.write_text(json.dumps(turn))
        return self.d.refused("post", str(self.d.run), "--actor",
                              actor or cct.ACTOR_OF.get(first.get("type"), "lead"),
                              "--file", str(path))

    def plan(self):
        self.d.post(5, {"type": "plan", "summary": "s", "units": [{"name": "u", "purpose": "p"}],
                        "lenses": LENSES, "checkpoints": ["one"]})

    def test_out_of_turn_is_refused(self):
        msg = self.post_refused({"type": "review", "summary": "s", "items": []})
        self.assertIn("out of turn", msg)

    def test_plan_must_cover_every_lens(self):
        lenses = dict(LENSES)
        del lenses["concurrency"]
        msg = self.post_refused({"type": "plan", "summary": "s", "units": [{"name": "u", "purpose": "p"}],
                                 "lenses": lenses, "checkpoints": ["one"]})
        self.assertIn("concurrency", msg)

    def test_rejection_needs_a_rationale(self):
        self.plan()
        self.d.post(8, {"type": "review", "summary": "s", "items": [item("intent", "consider", "x")]})
        msg = self.post_refused({"type": "response", "decisions": [{"item": "C01", "decision": "reject"}]})
        self.assertIn("rationale", msg)

    def test_a_refused_bundle_records_nothing(self):
        self.plan()
        self.d.post(8, {"type": "review", "summary": "s", "items": []})
        write_lines(self.d.repo, "src/a.py", 10, "a")
        commit(self.d.repo, "a")
        self.d.post(20, {"type": "checkpoint", "title": "a", "tests": {"passed": 1, "failed": 0}})
        self.d.post(24, {"type": "review", "summary": "s",
                         "items": [item("correctness", "blocking", "Breaks on empty input")]})
        write_lines(self.d.repo, "src/b.py", 10, "b")
        commit(self.d.repo, "b")
        before = (self.d.run / "ledger.jsonl").read_text()
        msg = self.post_refused([
            {"type": "response", "decisions": [{"item": "C01", "decision": "reject", "rationale": "No."}]},
            {"type": "checkpoint", "title": "b", "tests": {"passed": 2, "failed": 0}}])
        self.assertIn("turn 2 of 2", msg)
        self.assertIn("nothing was recorded", msg)
        self.assertEqual(before, (self.d.run / "ledger.jsonl").read_text())

    def test_checkpoint_needs_committed_work(self):
        self.plan()
        self.d.post(8, {"type": "review", "summary": "s", "items": []})
        write_lines(self.d.repo, "src/relay/metrics.py", 3, "dirty")
        msg = self.post_refused({"type": "checkpoint", "title": "x", "tests": {"passed": 1, "failed": 0}})
        self.assertIn("commit", msg)

    def test_run_folder_must_be_outside_the_checkout(self):
        brief = json.loads((self.d.run.parent / "brief.json").read_text())
        path = self.d.run.parent / "brief.json"
        path.write_text(json.dumps(brief))
        msg = self.d.refused("init", str(self.d.repo / "run"), "--brief", str(path))
        self.assertIn("outside the checkout", msg)

    def build_to_final(self):
        self.plan()
        self.d.post(8, {"type": "review", "summary": "s", "items": []})
        write_lines(self.d.repo, "src/a.py", 10, "a")
        commit(self.d.repo, "a")
        self.d.post(20, {"type": "checkpoint", "title": "a", "final": True,
                         "tests": {"passed": 1, "failed": 0}})
        self.d.post(24, {"type": "review", "summary": "s",
                         "items": [item("correctness", "blocking", "Breaks on empty input")]})

    def test_changes_after_the_final_review_get_reviewed(self):
        self.build_to_final()
        self.d.post(25, {"type": "response", "decisions": acc("C01")})
        write_lines(self.d.repo, "src/a.py", 2, "fix")
        commit(self.d.repo, "fix")
        self.assertIn("not reviewed", self.post_refused(
            {"type": "pr", "url": "https://github.com/example-owner/relay/pull/1"}))
        self.d.post(30, {"type": "checkpoint", "title": "fix", "tests": {"passed": 2, "failed": 0}})
        state = json.loads(self.d.call("state", str(self.d.run), "--json"))
        self.assertEqual(state["expect"], [{"actor": "critic", "type": "review", "round": "final-2"}])

    def test_a_run_can_close_early(self):
        self.plan()
        self.d.post(9, {"type": "review_result", "ran": False, "reason": "no way to push"})
        self.d.post(10, {"type": "close", "outcome": "abandoned", "note": "goal changed"})
        self.d.call("stats", str(self.d.run))
        stats = json.loads((self.d.run / "stats.json").read_text())
        self.assertEqual(stats["run"]["status"], "abandoned")
        self.assertIn("goal changed", render.render(stats, "page"))

    def test_a_worker_file_cannot_carry_lead_turns(self):
        self.plan()
        msg = self.post_refused({"type": "intervention", "reason": "other", "summary": "x"},
                                actor="coder", name="coder-next.json")
        self.assertIn("comes from the lead", msg)
        msg = self.post_refused({"type": "note", "text": "x"}, actor="lead", name="critic-next.json")
        self.assertIn("--actor critic", msg)

    def test_untracked_files_block_a_checkpoint(self):
        self.plan()
        self.d.post(8, {"type": "review", "summary": "s", "items": []})
        write_lines(self.d.repo, "src/new_module.py", 5, "new")
        msg = self.post_refused({"type": "checkpoint", "title": "x", "tests": {"passed": 1, "failed": 0}})
        self.assertIn("untracked", msg)

    def test_amended_blocking_critique_goes_to_the_lead(self):
        self.plan()
        self.d.post(8, {"type": "review", "summary": "s",
                        "items": [item("security", "blocking", "Token logged")]})
        self.d.post(9, {"type": "response", "decisions": [
            {"item": "C01", "decision": "reject", "rationale": "Debug only."}]})
        self.assertIn("amended_suggestion", self.post_refused(
            {"type": "rebuttal", "positions": [{"item": "C01", "position": "amend", "argument": "a"}]}))
        self.d.post(10, {"type": "rebuttal", "positions": [
            {"item": "C01", "position": "amend", "argument": "Debug logs ship.",
             "amended_suggestion": "Redact the token."}]})
        state = json.loads(self.d.call("state", str(self.d.run), "--json"))
        self.assertEqual(state["expect"][0]["actor"], "lead")
        self.assertIn("Redact the token", self.d.call("show", str(self.d.run), "--item", "C01"))

    def test_malformed_turns_are_refused_not_crashed(self):
        msg = self.post_refused({"type": "plan", "summary": "s", "units": ["RetryPolicy"],
                                 "lenses": LENSES, "checkpoints": ["one"]})
        self.assertIn("JSON object", msg)
        msg = self.post_refused({"type": "plan", "summary": "s", "units": [{"name": "u", "purpose": "p"}],
                                 "lenses": LENSES, "checkpoints": [{"title": "one"}]})
        self.assertIn("string", msg)

    def test_settled_critiques_reopen_only_with_cause(self):
        self.plan()
        self.d.post(8, {"type": "review", "summary": "s", "items": [item("intent", "consider", "x")]})
        self.d.post(9, {"type": "response", "decisions": acc("C01")})
        write_lines(self.d.repo, "src/a.py", 10, "a")
        commit(self.d.repo, "a")
        self.d.post(20, {"type": "checkpoint", "title": "a", "tests": {"passed": 1, "failed": 0}})
        msg = self.post_refused({"type": "review", "summary": "s", "items": [
            item("intent", "consider", "x again", reraises="C01", new_evidence="e")]})
        self.assertIn("accepted", msg)

    def test_pr_update_needs_an_existing_pr(self):
        self.build_to_final()
        self.d.post(25, {"type": "response", "decisions": acc("C01")})
        msg = self.post_refused({"type": "pr", "url": "https://github.com/example-owner/relay/pull/1",
                                 "update": True})
        self.assertIn("no pull request to update", msg)

    def test_ready_to_merge_needs_a_review_that_ran(self):
        self.build_to_final()
        self.d.post(25, {"type": "response", "decisions": acc("C01")})
        self.d.post(26, {"type": "pr", "url": "https://github.com/example-owner/relay/pull/1"})
        self.d.post(27, {"type": "review_result", "ran": False, "reason": "skill missing"})
        self.d.post(28, {"type": "narrative", "summary": "Done."})
        self.d.post(29, {"type": "acceptance", "criteria": [
            {"id": f"A{n}", "status": "met", "evidence": "test"} for n in range(1, 6)]})
        msg = self.post_refused({"type": "close", "outcome": "ready_to_merge"})
        self.assertIn("project review has not run", msg)
        self.d.post(30, {"type": "close", "outcome": "needs_attention"})

    def test_limits_allow_another_fix_round(self):
        self.build_to_final()
        self.d.post(25, {"type": "response", "decisions": acc("C01")})
        self.d.post(26, {"type": "pr", "url": "https://github.com/example-owner/relay/pull/1"})
        self.d.post(30, {"type": "review_result", "verdict": "needs_rework", "reviewers": ["General reviewer"],
                         "findings": [{"severity": "blocking", "title": "Crash on None"}]})
        self.assertIn("must not be empty", self.post_refused({"type": "fix_request", "findings": []}))
        for n, minute in ((1, 31), (2, 41)):
            self.d.post(minute, {"type": "fix_request", "findings": ["F1"]})
            write_lines(self.d.repo, "src/a.py", 1, f"fix{n}")
            commit(self.d.repo, f"fix {n}")
            self.d.post(minute + 2, {"type": "checkpoint", "title": f"fix {n}", "tests": {"passed": 1, "failed": 0}})
            self.d.post(minute + 3, {"type": "review", "summary": "s", "items": []})
            self.d.post(minute + 4, {"type": "pr", "url": "https://github.com/example-owner/relay/pull/1",
                                     "update": True})
            self.d.post(minute + 5, {"type": "finding_update", "updates": [
                {"finding": "F1", "status": "open"}]})
            if n == 1:
                self.assertIn("raise the limit", self.post_refused({"type": "fix_request", "findings": ["F1"]}))
                self.d.post(minute + 6, {"type": "limits", "limits": {"fix_rounds": 2},
                                         "reason": "The person asked for one more try."})

    def test_loop_signal_clears_after_a_ruling(self):
        self.plan()
        self.d.post(8, {"type": "review", "summary": "s", "items": [item("modularity", "consider", "Split it")]})
        self.d.post(9, {"type": "response", "decisions": [{"item": "C01", "decision": "reject", "rationale": "No."}]})
        self.d.post(10, {"type": "rebuttal", "positions": [{"item": "C01", "position": "withdraw"}]})
        for n, minute in ((2, 20), (3, 30)):
            write_lines(self.d.repo, "src/a.py", 3, f"cp{n}")
            commit(self.d.repo, f"cp{n}")
            self.d.post(minute, {"type": "checkpoint", "title": "a", "tests": {"passed": 1, "failed": 0}})
            prior = "C01" if n == 2 else "C02"
            self.d.post(minute + 1, {"type": "review", "summary": "s", "items": [
                item("modularity", "consider", "Split it", reraises=prior, new_evidence="grew")]})
            self.d.post(minute + 2, {"type": "response", "decisions": [
                {"item": f"C0{n}", "decision": "reject", "rationale": "Still no."}]})
        state = json.loads(self.d.call("state", str(self.d.run), "--json"))
        self.assertIn("loop", [s["signal"] for s in state["signals"]])
        self.d.post(40, {"type": "intervention", "reason": "loop", "summary": "Settled: keep one module.",
                         "rulings": [{"item": "C03", "decision": "reject", "rationale": "Keep one module."}]})
        state = json.loads(self.d.call("state", str(self.d.run), "--json"))
        self.assertNotIn("loop", [s["signal"] for s in state["signals"]])


class RenderEdgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = run_sample(Path(cls.tmp.name))
        d.call("stats", str(d.run))
        cls.stats = json.loads((d.run / "stats.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_malformed_or_hostile_stats_are_refused(self):
        import copy
        mutations = [
            lambda s: s["diff"]["by_kind"]["source"].__setitem__("adds", '1" onmouseover="x'),
            lambda s: s["run"].__setitem__("status", "<b>"),
            lambda s: s["item_list"][0].__setitem__("severity", "urgent"),
            lambda s: s["timeline"]["spans"][0].__setitem__("start", "0;left:0"),
            lambda s: s["rounds"][1]["coder"]["git"].__setitem__("adds", None),
            lambda s: s["review"]["findings"][0].__setitem__("status", 3),
            lambda s: s["acceptance"].append("A9"),
            lambda s: s.__setitem__("schema", 2),
        ]
        for n, mutate in enumerate(mutations):
            bad = copy.deepcopy(self.stats)
            mutate(bad)
            with self.assertRaises(render.StatsError, msg=f"mutation {n}"):
                render.render(bad, "page")

    def test_optional_nulls_render(self):
        import copy
        s = copy.deepcopy(self.stats)
        s["run"]["workers"]["coder"]["model"] = None
        s["run"]["workers"]["critic"] = None
        s["rounds"][1]["coder"]["deviations"] = None
        s["rounds"][1]["interventions"] = None
        self.assertIn("unknown model", render.render(s, "page"))
        s["run"]["started_at"] = "yesterday"
        with self.assertRaises(render.StatsError):
            render.render(s, "page")

    def test_text_is_escaped(self):
        import copy
        s = copy.deepcopy(self.stats)
        s["run"]["title"] = '<img src=x onerror="alert(1)">'
        s["item_list"][0]["rationale"] = "</style><script>alert(1)</script>"
        s["review"]["findings"][1]["issue_url"] = "javascript:alert(1)"
        out = render.render(s, "page")
        self.assertNotIn("<img src=x", out)
        self.assertNotIn("<script", out.lower())
        self.assertNotIn("javascript:", out)

    def test_glyphs_carry_a_hover_summary(self):
        import copy
        s = copy.deepcopy(self.stats)
        item = next(i for i in s["item_list"] if i["outcome"] == "rejected"
                    and not i.get("ruling") and not i.get("final_rationale"))
        item["rationale"] = "word " * 60
        out = render.render(s, "page")
        self.assertIn('<span class="tip" aria-hidden="true">', out)
        self.assertIn(f'{item["id"]} · {render.SEVERITY_LABELS[item["severity"]]}', out)
        tips = re.findall(r'<span class="tip-d">([^<]*)</span>', out)
        long_tip = next(t for t in tips if t.startswith("Rejected by the coder: word word"))
        self.assertTrue(long_tip.endswith("word…"))
        self.assertLess(len(long_tip), 160)
        self.assertNotRegex(out, r'class="g g--[a-z]+ s--[a-z_]+"[^>]*title=')

    def test_long_runs_render(self):
        import copy
        stats = copy.deepcopy(self.stats)
        stats["timeline"]["total_min"] = 20000
        self.assertIn("Timeline", render.render(stats, "page"))


if __name__ == "__main__":
    unittest.main()
