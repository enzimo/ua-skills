"""End-to-end checks for the coder-critic-team run ledger and report renderer."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
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


def sh(repo: Path, *args: str, check: bool = True) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=check,
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

    def __init__(self, base: Path, worktree: bool = False):
        """With worktree=True the coder works in a linked worktree of relay-main, which
        pushes to a bare origin.git; otherwise in the main checkout itself."""
        self.repo = base / "relay"
        self.main = base / "relay-main" if worktree else self.repo
        self.run = base / "runs" / "relay-142"
        self.main.mkdir(parents=True)
        sh(self.main, "init", "-q", "-b", "main")
        write_lines(self.main, "src/relay/delivery/worker.py", 120, "worker")
        write_lines(self.main, "src/relay/metrics.py", 40, "metrics")
        write_lines(self.main, "README.md", 20, "readme")
        commit(self.main, "Initial relay")
        if worktree:
            sh(base, "init", "-q", "--bare", "origin.git")
            sh(self.main, "remote", "add", "origin", str(base / "origin.git"))
            sh(self.main, "push", "-q", "-u", "origin", "main")
            sh(self.main, "worktree", "add", "-q", "-b", "feat/webhook-retry", str(self.repo), "main")
        else:
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

    def init(self, **extra) -> str:
        return self.call("init", str(self.run), "--brief", str(self.brief_file(**extra)), "--at", T0)

    def brief_file(self, **extra) -> Path:
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
        brief.update(extra)
        path = self.run.parent / "brief.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(brief))
        return path


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
        self.assertEqual(self.stats["schema"], 2)
        (review,) = self.stats["reviews"]
        self.assertEqual(review["stage"], "after_pr")
        self.assertEqual(review["findings"], ["F1", "F2", "F3", "F4"])
        self.assertEqual(review["by_severity"], {"blocking": 1, "should_fix": 2, "consider": 1})
        self.assertEqual(self.stats["counts"]["findings_matched"], 1)
        statuses = {f["id"]: f["status"] for f in self.stats["findings"]}
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
            text = d.call("turn", str(d.run), "--for", "coder", "--full")
            self.assertIn("C01", text)
            self.assertIn("Misses criterion A3", text)
            self.assertIn("Nothing is waiting", d.call("turn", str(d.run), "--for", "critic"))

    def test_the_brief_goes_to_a_file_and_the_handoff_stays_short(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Driver(Path(tmp))
            d.init()
            brief = d.run / "turns" / "coder-brief.md"
            first = d.call("turn", str(d.run), "--for", "coder")
            self.assertIn(str(brief), first)
            self.assertIn("roles/coder.md", first)  # a first turn names the role file
            d.post(5, {"type": "plan", "summary": "s", "units": [{"name": "u", "purpose": "p " * 400}],
                       "lenses": LENSES, "checkpoints": ["one"]})
            out = d.post(9, {"type": "review", "summary": "s",
                             "items": [item("intent", "blocking", "Misses criterion A3")]})
            handoff = next(line for line in out.splitlines() if line.startswith("Handoff for the coder"))
            self.assertIn(str(brief), handoff)
            self.assertNotIn("roles/coder.md", handoff)
            self.assertLess(len(handoff), 400)
            self.assertIn("Misses criterion A3", brief.read_text())
            # Later coder briefs point to the plan instead of repeating it.
            d.post(10, {"type": "response", "decisions": acc("C01")})
            text = brief.read_text()
            self.assertIn("0002-coder-plan.json", text)
            self.assertNotIn("p p p", text)
            self.assertLess(len(text), 2500)


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
        # A review from before the run is recorded before the pull request turn.
        late = {**earlier_review(), "findings": []}
        self.assertIn("before the pull request turn", self.post_refused(late))
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
                {"finding": "F1", "status": "open", "note": "Still crashes on an empty list."}]})
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


PR_URL = "https://github.com/example-owner/relay/pull/101"


def earlier_review(count: int = 3) -> dict:
    """A project review that ran before the run, on the pull request's earlier head."""
    severities = ["blocking", "should_fix", "consider"]
    return {"type": "review_result", "stage": "before_run", "verdict": "needs_rework",
            "reviewers": ["General reviewer", "Failure analyst"], "head_sha": "474defec0000",
            "source": "review run relay-101-a",
            "findings": [{"severity": severities[min(n, 2)], "title": f"Problem {n + 1}",
                          "ref": f"GEN-{n + 1}", "scenario": f"Scenario {n + 1}."}
                         for n in range(count)]}


class ExistingPullRequestTest(unittest.TestCase):
    """A run that fixes the findings of an earlier review on a pull request that already exists."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Driver(Path(self.tmp.name))
        self.d.init(pull_request={"url": PR_URL, "number": 101})

    def tearDown(self):
        self.tmp.cleanup()

    def brief(self, role: str) -> str:
        return self.d.call("turn", str(self.d.run), "--for", role, "--full")

    def state(self) -> dict:
        return json.loads(self.d.call("state", str(self.d.run), "--json"))

    def build(self, findings: int = 3) -> None:
        d = self.d
        d.post(1, earlier_review(findings))
        self.assertIn("Problem 2", self.brief("coder"))  # the plan turn lists what to fix
        d.post(5, {"type": "plan", "summary": "s", "units": [{"name": "u", "purpose": "p"}],
                   "lenses": LENSES, "checkpoints": ["one"]})
        self.assertIn("GEN-1", self.brief("critic"))
        d.post(8, {"type": "review", "summary": "s", "items": []})
        self.assertIn("No checkpoint has named these yet: F1, F2, F3", self.brief("coder"))
        write_lines(d.repo, "src/a.py", 10, "a")
        commit(d.repo, "a")
        d.post(20, {"type": "checkpoint", "title": "a", "final": True, "addresses": ["F2", "F1"],
                    "tests": {"passed": 1, "failed": 0}})
        self.assertIn("Check each fix against the finding's scenario", self.brief("critic"))
        d.post(24, {"type": "review", "summary": "s",
                    "items": [item("correctness", "consider", "The F2 fix misses an empty list")]})
        d.post(25, {"type": "response", "decisions": acc("C01")})

    def test_the_pr_turn_records_the_existing_pull_request(self):
        self.assertIn("#101", (self.d.run / "brief.md").read_text())
        self.build()
        text = self.brief("coder")
        self.assertIn("already exists", text)
        self.assertIn("Do not open another pull request", text)
        self.assertNotIn("as a draft", text)
        path = self.d.run / "turns" / "coder-next.json"
        path.write_text(json.dumps({"type": "pr", "url": "https://github.com/example-owner/relay/pull/7"}))
        msg = self.d.refused("post", str(self.d.run), "--actor", "coder", "--file", str(path))
        self.assertIn("do not open another", msg)
        self.d.post(26, {"type": "pr", "url": PR_URL + "/", "number": 101})
        self.d.call("stats", str(self.d.run))
        stats = json.loads((self.d.run / "stats.json").read_text())
        self.assertTrue(stats["run"]["pr"]["existing"])

    def test_an_intervention_reaches_the_brief_with_its_actions(self):
        self.d.post(1, {"type": "intervention", "reason": "other", "summary": "Keep the branch name.",
                        "actions": ["Do not rename feat/webhook-retry."]})
        text = self.brief("coder")
        self.assertIn("Keep the branch name.", text)
        self.assertIn("Do not rename feat/webhook-retry.", text)

    def test_an_earlier_review_is_rechecked_after_the_pull_request(self):
        d = self.d
        refuse = lambda turn: self.refuse(turn)  # noqa: E731
        self.build()
        self.assertIn("starts after the pull request", refuse({"type": "fix_request", "findings": ["F1"]}))
        d.post(26, {"type": "pr", "url": PR_URL, "number": 101})
        expect = self.state()["expect"]
        self.assertEqual(expect[0]["type"], "finding_update")
        self.assertEqual(expect[0]["items"], ["F1", "F2", "F3"])
        self.assertTrue(any(e["type"] == "review_result" and "optional" in e["why"] for e in expect))
        self.assertIn("required for open", refuse({"type": "finding_update", "updates": [
            {"finding": "F3", "status": "open"}]}))
        d.post(40, {"type": "finding_update", "updates": [
            {"finding": "F1", "status": "fixed", "evidence": "test_a passes."},
            {"finding": "F2", "status": "fixed", "evidence": "test_b passes.", "matches_item": "C01"}]})
        d.post(41, {"type": "narrative", "summary": "Done."})
        d.post(42, {"type": "acceptance", "criteria": [
            {"id": f"A{n}", "status": "met", "evidence": "test"} for n in range(1, 6)]})
        msg = refuse({"type": "close", "outcome": "ready_to_merge"})
        self.assertIn("F3 were not re-checked", msg)
        d.post(43, {"type": "finding_update", "updates": [
            {"finding": "F3", "status": "open", "note": "Scoped out by the brief; a follow-up."}]})
        self.assertIn("F3 are still open", refuse({"type": "close", "outcome": "ready_to_merge"}))
        d.post(44, {"type": "close", "outcome": "needs_attention"})
        d.call("stats", str(d.run))
        stats = json.loads((d.run / "stats.json").read_text())
        # Open on purpose, with its reason, is not a gap in the report.
        self.assertEqual(stats["warnings"], [])
        (review,) = stats["reviews"]
        self.assertEqual((review["stage"], review["by_status"]["fixed"], review["by_status"]["open"]),
                         ("before_run", 2, 1))
        by_id = {f["id"]: f for f in stats["findings"]}
        self.assertEqual(by_id["F1"]["addressed_in"], ["final"])
        self.assertEqual(stats["item_list"][0]["relates_to_findings"], ["F2"])
        self.assertEqual(stats["item_list"][0]["matched_by_review"], [])
        tl = stats["timeline"]
        # The earlier review took none of the run's time; the re-check is the lead's.
        self.assertEqual({sp["lane"] for sp in tl["spans"]}, {"coder", "critic", "lead"})
        self.assertEqual([p["label"] for p in tl["phases"]], ["Plan", "Build", "Re-check"])
        lead = sum(sp["end"] - sp["start"] for sp in tl["spans"] if sp["lane"] == "lead")
        self.assertEqual(lead, 18)
        for mode in ("page", "t3"):
            out = render.render(stats, mode)
            self.assertIn("Earlier review", out)
            self.assertIn("ran before this run, at 474defec00", out)
            self.assertIn("Scoped out by the brief; a follow-up.", out)
            self.assertIn("Addressed in Final review.", out)
            self.assertIn("F1 (GEN-1)", out)
            self.assertNotIn("Project review raised this again", out)
            self.assertIn("Lead worked 18 min", out)

    def refuse(self, turn) -> str:
        path = self.d.run / "turns" / "lead-input.json"
        path.write_text(json.dumps(turn))
        return self.d.refused("post", str(self.d.run), "--actor", cct.ACTOR_OF[turn["type"]],
                              "--file", str(path))

    def test_a_second_review_can_follow_the_pull_request(self):
        d = self.d
        self.build()
        self.assertIn("already recorded", self.refuse(earlier_review()))
        d.post(26, {"type": "pr", "url": PR_URL})
        d.post(30, {"type": "review_result", "verdict": "approve_with_changes",
                    "reviewers": ["General reviewer"],
                    "findings": [{"severity": "consider", "title": "A new nit"}]})
        d.call("stats", str(d.run))
        stats = json.loads((d.run / "stats.json").read_text())
        self.assertEqual([r["findings"] for r in stats["reviews"]], [["F1", "F2", "F3"], ["F4"]])
        self.assertIn("review", {sp["lane"] for sp in stats["timeline"]["spans"]})
        out = render.render(stats, "page")
        self.assertLess(out.index("Earlier review<small>"), out.index("Review of the pull request<small>"))

    def test_findings_sort_by_number_and_long_lists_start_closed(self):
        d = self.d
        self.build(findings=12)
        d.post(26, {"type": "pr", "url": PR_URL})
        d.post(30, {"type": "finding_update", "updates": [
            {"finding": f"F{n}", "status": "fixed", "evidence": f"Check {n}."} for n in range(1, 12)]
            + [{"finding": "F12", "status": "open", "note": "Left for the next step."}]})
        d.call("stats", str(d.run))
        out = render.render(json.loads((d.run / "stats.json").read_text()), "page")
        order = re.findall(r'<span class="mono">(F\d+)', out)
        self.assertEqual(order, [f"F{n}" for n in range(1, 13)])
        self.assertEqual(out.count('<details class="finding" open>'), 1)  # only the open one
        self.assertIn("<b>Still open:</b> Left for the next step.", out)

    def test_a_changed_checkout_after_the_critic_is_signalled(self):
        d = self.d
        d.post(5, {"type": "plan", "summary": "s", "units": [{"name": "u", "purpose": "p"}],
                   "lenses": LENSES, "checkpoints": ["one"]})
        (d.repo / "notes-from-critic.txt").write_text("x")
        out = d.post(8, {"type": "review", "summary": "s", "items": []})
        self.assertIn("Signal: checkout_changed", out)


class InitBaseTest(unittest.TestCase):
    """cct.py init records the commit the run starts from, not the tip of a stale base."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.d = Driver(self.base)  # main and feat/webhook-retry at the first commit
        sh(self.base, "init", "-q", "--bare", "origin.git")
        sh(self.d.repo, "remote", "add", "origin", str(self.base / "origin.git"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_local_base_behind_its_remote_is_not_counted(self):
        repo = self.d.repo
        stale = sh(repo, "rev-parse", "main")
        sh(repo, "switch", "-q", "main")
        write_lines(repo, "src/relay/metrics.py", 5, "upstream")
        commit(repo, "A commit the local main does not have yet")
        sh(repo, "push", "-q", "-u", "origin", "main")
        start = sh(repo, "rev-parse", "HEAD")
        sh(repo, "switch", "-q", "-C", "feat/webhook-retry", "origin/main")
        sh(repo, "branch", "-f", "main", stale)  # local main is now behind origin/main
        # origin/main moves on again; the branch made from it does not need it.
        sh(repo, "switch", "-q", "-c", "elsewhere", "origin/main")
        write_lines(repo, "src/relay/other.py", 3, "later")
        commit(repo, "Later work on main")
        sh(repo, "push", "-q", "origin", "elsewhere:main")
        sh(repo, "switch", "-q", "feat/webhook-retry")

        out = self.d.init()
        self.assertIn(f"Base commit: {start[:10]}", out)
        brief = json.loads((self.d.run / "ledger.jsonl").read_text().splitlines()[0])["data"]
        self.assertEqual(brief["repo"]["base_sha"], start)
        self.assertIn(f"the run starts at `{start[:10]}`", (self.d.run / "brief.md").read_text())

        self.d.post(5, {"type": "plan", "summary": "s", "units": [{"name": "u", "purpose": "p"}],
                        "lenses": LENSES, "checkpoints": ["one"]})
        self.d.post(8, {"type": "review", "summary": "s", "items": []})
        write_lines(repo, "src/relay/retry.py", 10, "run")
        commit(repo, "The run's only commit")
        self.d.post(20, {"type": "checkpoint", "title": "a", "tests": {"passed": 1, "failed": 0}})
        state = cct.Run(self.d.run)
        g = state.checkpoints[-1]["data"]["git"]
        self.assertEqual((g["from"], g["commits"], g["adds"], g["dels"]), (start, 1, 10, 0))
        self.d.call("stats", str(self.d.run))
        diff = json.loads((self.d.run / "stats.json").read_text())["diff"]
        self.assertEqual((diff["commits"], diff["adds"], diff["files"]), (1, 10, 1))

    def test_a_missing_work_branch_or_base_is_refused(self):
        msg = self.d.refused("init", str(self.d.run), "--brief", str(self.d.brief_file(
            repo={"name": "example-owner/relay", "path": str(self.d.repo), "base": "mian",
                  "branch": "feat/webhook-retry"})))
        self.assertIn("the base 'mian' is not a commit", msg)
        sh(self.d.repo, "switch", "-q", "main")
        sh(self.d.repo, "branch", "-q", "-D", "feat/webhook-retry")
        msg = self.d.refused("init", str(self.d.run), "--brief", str(self.d.brief_file()))
        self.assertIn("work branch 'feat/webhook-retry' does not exist", msg)
        self.assertFalse(self.d.run.exists())

    def test_a_pull_request_branch_that_tracks_the_base_is_not_behind(self):
        repo = self.d.repo
        sh(repo, "push", "-q", "-u", "origin", "main")
        sh(repo, "switch", "-q", "-C", "feat/webhook-retry", "origin/main")  # tracks origin/main
        write_lines(repo, "src/relay/retry.py", 4, "pull request")
        commit(repo, "The pull request's commit")
        sh(repo, "push", "-q", "origin", "feat/webhook-retry")  # without -u
        sh(repo, "switch", "-q", "main")
        write_lines(repo, "src/relay/metrics.py", 2, "main moves on")
        commit(repo, "Main moves on")
        sh(repo, "push", "-q", "origin", "main")
        sh(repo, "switch", "-q", "feat/webhook-retry")
        head = sh(repo, "rev-parse", "HEAD")
        self.assertIn(f"Base commit: {head[:10]}", self.d.init(pull_request={"url": PR_URL, "number": 101}))

    def test_a_pull_request_branch_behind_its_remote_is_refused(self):
        repo = self.d.repo
        write_lines(repo, "src/relay/retry.py", 4, "earlier session")
        commit(repo, "Pushed in an earlier session")
        sh(repo, "push", "-q", "-u", "origin", "feat/webhook-retry")
        sh(repo, "reset", "-q", "--hard", "HEAD~1")  # this checkout never pulled it
        path = self.d.brief_file(pull_request={"url": PR_URL, "number": 101})
        msg = self.d.refused("init", str(self.d.run), "--brief", str(path))
        self.assertIn("1 commit(s) behind origin/feat/webhook-retry", msg)
        self.assertFalse(self.d.run.exists())
        sh(repo, "merge", "-q", "--ff-only", "origin/feat/webhook-retry")
        self.assertIn(f"Base commit: {sh(repo, 'rev-parse', 'HEAD')[:10]}",
                      self.d.init(pull_request={"url": PR_URL, "number": 101}))


def tree(root: Path) -> list:
    """Every path below root, links included and not followed."""
    out = []
    for top, dirs, files in os.walk(root):
        out += [str((Path(top) / n).relative_to(root)) for n in dirs + files]
    return sorted(out)


def quiet(func, *argv: str) -> int:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return func(list(argv))


def closed_run(base: Path, outcome: str = "needs_attention", with_pr: bool = True,
               worktree: bool = False) -> Driver:
    """A short run, closed, with its statistics and both reports in the run folder."""
    d = Driver(base, worktree=worktree)
    d.init()
    (d.run / "turns" / "plan.md").write_text("The plan.\n")
    d.post(5, {"type": "plan", "summary": "s", "units": [{"name": "u", "purpose": "p"}],
               "lenses": LENSES, "checkpoints": ["one"], "plan_file": "turns/plan.md"})
    d.post(8, {"type": "review", "summary": "s", "items": []})
    write_lines(d.repo, "src/a.py", 10, "a")
    commit(d.repo, "a")
    d.post(20, {"type": "checkpoint", "title": "a", "final": True, "tests": {"passed": 1, "failed": 0}})
    d.post(24, {"type": "review", "summary": "s", "items": []})
    if worktree:
        sh(d.repo, "push", "-q", "-u", "origin", "feat/webhook-retry")
    if with_pr:
        d.post(26, {"type": "pr", "url": "https://github.com/example-owner/relay/pull/1", "number": 1})
        d.post(30, {"type": "review_result", "ran": False, "reason": "skill missing"})
    if outcome != "abandoned":
        d.post(31, {"type": "narrative", "summary": "Done."})
    d.post(32, {"type": "close", "outcome": outcome})
    d.call("stats", str(d.run))
    for mode, name in (("page", "report.html"), ("t3", "report-t3.html")):
        assert quiet(render.main, str(d.run / "stats.json"), "--mode", mode, "--out", str(d.run / name)) == 0
    return d


class TidyTest(unittest.TestCase):
    """cct.py tidy removes a merged run's working files and keeps the report."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def tidy(self, run: Path, *flags: str) -> str:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cct.main(["tidy", str(run), *flags])
        return f"{code}\n{out.getvalue()}{err.getvalue()}"

    def test_tidy_removes_the_run_files_and_keeps_the_report(self):
        d = closed_run(self.base)
        (d.run / "notes.txt").write_text("the lead's own notes\n")
        (d.run / "turns" / "lead-next.json").write_text("{}\n")  # a turn file nobody posted
        page = (d.run / "report.html").read_text()
        before = tree(d.run)
        out = self.tidy(d.run, "--merged")
        self.assertTrue(out.startswith("0\n"), out)
        self.assertEqual(tree(d.run), ["notes.txt", "report-t3.html", "report.html", "stats.json",
                                       "turns", "turns/lead-input.json"])
        removed = sorted(set(before) - set(tree(d.run)) - {"roles", "diffs"})
        self.assertEqual(sorted(line.strip() for line in out.splitlines() if line.startswith("  ")
                                and line.strip() in removed), removed)
        for name in ("ledger.jsonl", "brief.md", "roles/critic.md", "turns/coder-brief.md",
                     "turns/plan.md", "turns/0002-coder-plan.json", "turns/lead-next.json",
                     "diffs/final.patch"):
            self.assertIn(name, removed)
        self.assertLess(out.index("  brief.md"), out.index("  ledger.jsonl"))  # the ledger goes last
        self.assertIn("Kept the report: stats.json, report.html, report-t3.html", out)
        self.assertIn("Left in place, not written by cct.py (2):\n  notes.txt\n  turns/lead-input.json", out)
        # The report renders from what is left, exactly as before.
        stats = json.loads((d.run / "stats.json").read_text())
        self.assertEqual(render.render(stats, "page"), page)
        self.assertIn("is not a run folder", self.tidy(d.run, "--merged"))

    def test_a_tidy_that_stopped_part_way_can_be_finished(self):
        d = closed_run(self.base)
        for name in ("roles/protocol.md", "roles/coder.md", "roles/critic.md",
                     "turns/0002-coder-plan.json", "diffs/final.patch"):
            (d.run / name).unlink()
        out = self.tidy(d.run, "--merged")
        self.assertTrue(out.startswith("0\n"), out)
        self.assertNotIn("roles/", out)
        self.assertNotIn("0002-coder-plan.json", out)
        self.assertIn("  turns/0003-critic-review.json", out)
        self.assertEqual(tree(d.run), ["report-t3.html", "report.html", "stats.json",
                                       "turns", "turns/lead-input.json"])

    def test_tidy_refuses_and_removes_nothing(self):
        empty = self.base / "empty"
        empty.mkdir()
        only_stats = self.base / "only-stats"
        only_stats.mkdir()
        (only_stats / "stats.json").write_text("{}\n")
        closed = closed_run(self.base / "closed")
        open_run = Driver(self.base / "open")
        open_run.init()
        abandoned = closed_run(self.base / "abandoned", outcome="abandoned", with_pr=False)
        no_pr = closed_run(self.base / "no-pr", with_pr=False)
        stats = closed.run / "stats.json"
        cases = [
            ("not a run folder", empty, ("--merged",), "is not a run folder"),
            ("only statistics", only_stats, ("--merged",), "is not a run folder"),
            ("not closed", open_run.run, ("--merged",), "the run is not closed"),
            ("no --merged", closed.run, (), "add --merged"),
            ("abandoned", abandoned.run, ("--merged",), "closed as abandoned"),
            ("no pull request", no_pr.run, ("--merged",), "recorded no pull request"),
        ]
        for name, run, flags, why in cases:
            with self.subTest(name):
                before = tree(run)
                out = self.tidy(run, *flags)
                self.assertTrue(out.startswith("2\n"), out)
                self.assertIn(why, out)
                self.assertIn("nothing was removed", out)
                self.assertEqual(tree(run), before)
        good = stats.read_text()
        old, other = json.loads(good), json.loads(good)
        old["run"]["events"] -= 1
        other["run"]["started_at"] = "2026-11-08T09:00:00Z"
        for name, text, why in (("missing", None, "has no stats.json"),
                                ("not statistics", "[]", "is not the statistics"),
                                ("written before the close", json.dumps(old), "written before the run closed"),
                                ("from another run", json.dumps(other), "from another run")):
            with self.subTest(f"stats.json {name}"):
                stats.unlink()
                if text is not None:
                    stats.write_text(text)
                before = tree(closed.run)
                out = self.tidy(closed.run, "--merged")
                self.assertIn(why, out)
                self.assertEqual(tree(closed.run), before)
                stats.write_text(good)

    def test_tidy_follows_no_link(self):
        d = closed_run(self.base)
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "final.patch").write_text("keep me\n")
        (outside / "plan.json").write_text("keep me too\n")
        archive = d.run / "turns" / "0002-coder-plan.json"
        archive.unlink()
        try:
            os.symlink(outside / "plan.json", archive)
            shutil.rmtree(d.run / "diffs")
            os.symlink(outside, d.run / "diffs")
        except (OSError, NotImplementedError):
            self.skipTest("links cannot be made here")
        out = self.tidy(d.run, "--merged")
        self.assertTrue(out.startswith("0\n"), out)
        self.assertIn("  diffs/ (a link, not followed)", out)
        self.assertIn("  turns/0002-coder-plan.json (a link or special file, not followed)", out)
        self.assertEqual(sorted(p.name for p in outside.iterdir()), ["final.patch", "plan.json"])
        self.assertTrue(archive.is_symlink() and (d.run / "diffs").is_symlink())


    @unittest.skipIf(not hasattr(os, "geteuid") or os.geteuid() == 0,
                     "needs a user that read-only folders stop")
    def test_a_removal_error_reports_what_was_removed(self):
        d = closed_run(self.base)
        turns = d.run / "turns"
        turns.chmod(0o555)
        try:
            out = self.tidy(d.run, "--merged")
        finally:
            turns.chmod(0o755)
        self.assertTrue(out.startswith("2\n"), out)
        self.assertIn("  brief.md\n  diffs/final.patch\n  roles/coder.md", out)
        self.assertIn("Refused: could not remove turns/0002-coder-plan.json (Permission denied); the "
                      "files listed above were removed", out)
        self.assertTrue((d.run / "ledger.jsonl").exists())
        out = self.tidy(d.run, "--merged")
        self.assertTrue(out.startswith("0\n"), out)
        self.assertIn("  turns/0002-coder-plan.json", out)
        self.assertNotIn("  brief.md", out)


class TidyWorktreeTest(unittest.TestCase):
    """cct.py tidy --worktree removes a clean, merged linked worktree and its local branch."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def tidy(self, d: Driver, *flags: str) -> str:
        return TidyTest.tidy(self, d.run, "--merged", "--worktree", *flags)

    def branches(self, d: Driver) -> str:
        return sh(d.main, "branch", "--list", "feat/webhook-retry")

    def assert_removed(self, d: Driver, out: str) -> None:
        self.assertTrue(out.startswith("0\n"), out)
        self.assertIn(f"Removed the worktree {d.repo}", out)
        self.assertFalse(d.repo.exists())
        self.assertEqual(self.branches(d), "")
        self.assertEqual(tree(d.run), ["report-t3.html", "report.html", "stats.json",
                                       "turns", "turns/lead-input.json"])
        self.assertIn("README.md", os.listdir(d.main))  # the main checkout stays

    def test_removes_the_worktree_and_the_local_branch_only(self):
        d = closed_run(self.base, worktree=True)
        pushed = sh(self.base / "origin.git", "rev-parse", "refs/heads/feat/webhook-retry")
        self.assert_removed(d, self.tidy(d))
        self.assertEqual(sh(self.base / "origin.git", "rev-parse", "refs/heads/feat/webhook-retry"), pushed)

    def test_a_merged_branch_whose_remote_branch_is_gone_is_removed(self):
        d = closed_run(self.base, worktree=True)
        sh(d.main, "merge", "-q", "--ff-only", "feat/webhook-retry")
        sh(d.main, "push", "-q", "origin", "main", ":feat/webhook-retry")
        sh(d.main, "fetch", "-q", "--prune")
        self.assertEqual(sh(d.repo, "rev-parse", "--verify", "--quiet", "feat/webhook-retry@{upstream}",
                            check=False), "")
        self.assert_removed(d, self.tidy(d))

    def test_a_main_checkout_behind_the_merge_is_updated_first(self):
        d = closed_run(self.base, worktree=True)
        tree_id = sh(d.main, "rev-parse", "feat/webhook-retry^{tree}")
        merge = sh(d.main, "-c", "user.name=exampleuser", "-c", "user.email=exampleuser@example.com",
                   "commit-tree", tree_id, "-p", "main", "-p", "feat/webhook-retry", "-m", "Merge #1")
        sh(d.main, "push", "-q", "origin", f"{merge}:refs/heads/main", ":feat/webhook-retry")
        sh(d.main, "fetch", "-q", "--prune")  # main in the main checkout is now behind origin/main
        out = self.tidy(d)
        self.assertIn("not merged into the main checkout's HEAD (main in", out)
        self.assertIn(f"update main there first ('git -C {d.main} pull --ff-only', when it has no "
                      "changes)", out)
        self.assertNotIn("Removed", out)
        self.assertTrue(d.repo.exists())
        sh(d.main, "merge", "-q", "--ff-only", "origin/main")
        self.assert_removed(d, self.tidy(d))

    def test_a_main_checkout_on_another_branch_is_not_updated(self):
        d = closed_run(self.base, worktree=True)
        sh(d.main, "switch", "-q", "-c", "other-work")
        sh(d.main, "push", "-q", "origin", ":feat/webhook-retry")
        sh(d.main, "fetch", "-q", "--prune")
        out = self.tidy(d)
        self.assertIn("not merged into the main checkout's HEAD (other-work in", out)
        self.assertIn("not on the base branch main, and tidy does not switch or update it", out)
        self.assertNotIn("--ff-only", out)
        self.assertNotIn("fetch", out)
        self.assertTrue(d.repo.exists())

    def test_refuses_and_removes_nothing(self):
        d = closed_run(self.base, worktree=True)
        head = sh(d.repo, "rev-parse", "HEAD")

        def change(path: str, text: str) -> None:
            (d.repo / path).write_text(text)

        cases = [
            ("uncommitted change", lambda: change("src/a.py", "changed\n"),
             lambda: sh(d.repo, "checkout", "-q", "--", "src/a.py"), "uncommitted changes"),
            ("untracked file", lambda: change("new.txt", "new\n"),
             lambda: (d.repo / "new.txt").unlink(), "untracked files (new.txt)"),
            ("commit after the pr turn", lambda: (change("src/b.py", "b\n"), commit(d.repo, "b")),
             lambda: sh(d.repo, "reset", "-q", "--hard", head), "the last pr turn recorded"),
            ("locked", lambda: sh(d.main, "worktree", "lock", str(d.repo)),
             lambda: sh(d.main, "worktree", "unlock", str(d.repo)), "is locked"),
            ("not merged where git looks", lambda: (sh(d.main, "push", "-q", "origin", ":feat/webhook-retry"),
                                                    sh(d.main, "fetch", "-q", "--prune")),
             lambda: sh(d.repo, "push", "-q", "-u", "origin", "feat/webhook-retry"),
             "would not delete feat/webhook-retry without force"),
            ("worktree gone", lambda: sh(d.main, "worktree", "remove", str(d.repo)),
             lambda: None, "is gone"),
        ]
        for name, make, undo, why in cases:
            with self.subTest(name):
                make()
                before = (tree(d.run), d.repo.exists() and tree(d.repo), self.branches(d))
                out = self.tidy(d)
                self.assertTrue(out.startswith("2\n"), out)
                self.assertIn(why, out)
                self.assertIn("nothing was removed", out)
                self.assertEqual((tree(d.run), d.repo.exists() and tree(d.repo), self.branches(d)), before)
                undo()

    def test_the_main_checkout_is_never_removed(self):
        d = closed_run(self.base)
        before = tree(d.repo)
        out = self.tidy(d)
        self.assertIn("is the repository's main checkout", out)
        self.assertEqual(tree(d.repo), before)
        self.assertTrue((d.run / "ledger.jsonl").exists())


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
            lambda s: s["findings"][0].__setitem__("status", 3),
            lambda s: s["findings"][0].__setitem__("stage", "later"),
            lambda s: s["reviews"][0].__setitem__("verdict", "fine"),
            lambda s: s["acceptance"].append("A9"),
            lambda s: s.__setitem__("schema", 3),
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
        s["findings"][1]["issue_url"] = "javascript:alert(1)"
        s["findings"][0]["note"] = "<b>bold</b>"
        out = render.render(s, "page")
        self.assertNotIn("<img src=x", out)
        self.assertNotIn("<script", out.lower())
        self.assertNotIn("javascript:", out)
        self.assertNotIn("<b>bold</b>", out)

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

    def test_compact_keeps_every_section_and_drops_the_long_texts(self):
        import copy
        s = copy.deepcopy(self.stats)
        item = next(i for i in s["item_list"] if i["outcome"] == "accepted")
        item["detail"] = "long detail " * 80
        full, compact = render.render(s, "t3", detail="full"), render.render(s, "t3")
        self.assertIn('data-detail="compact"', compact)
        self.assertIn('data-detail="full"', render.render(s, "page"))
        self.assertIn("long detail long detail", full)
        self.assertNotIn("long detail long detail", compact)
        self.assertLess(len(compact), len(full))
        for text in ("At a glance", "Timeline", "Acceptance criteria", "Rounds", "Decisions to check",
                     "Where the critique landed", "What changed", "Project review", "Next steps",
                     item["title"], "compact view"):
            self.assertIn(text, compact)
        self.assertLess(compact.index('id="h-tl"'), compact.index('id="h-criteria"'))

    def test_statistics_written_before_schema_2_still_render(self):
        import copy
        old = copy.deepcopy(self.stats)
        review = dict(old.pop("reviews")[0])
        review["findings"] = [{k: v for k, v in f.items() if k != "stage"} for f in old.pop("findings")]
        del review["stage"]
        old["review"], old["schema"] = review, 1
        out = render.render(old, "page")
        self.assertIn("Project review", out)
        self.assertIn("issue #143", out)
        old["review"] = "none"
        with self.assertRaises(render.StatsError):
            render.render(old, "page")

    def test_long_runs_render(self):
        import copy
        stats = copy.deepcopy(self.stats)
        stats["timeline"]["total_min"] = 20000
        self.assertIn("Timeline", render.render(stats, "page"))


if __name__ == "__main__":
    unittest.main()
