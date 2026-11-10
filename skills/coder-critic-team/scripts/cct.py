#!/usr/bin/env python3
"""Run ledger for a coder-critic team.

The team lead is the only writer. It records each worker turn, asks whose turn
comes next, prints the brief for that turn, and computes the statistics the
work report shows. Standard library only; Python 3.9 or newer.

    cct.py init  RUN_DIR --brief BRIEF.json
    cct.py post  RUN_DIR --actor coder|critic|lead --file TURN.json
    cct.py state RUN_DIR [--json]
    cct.py turn  RUN_DIR --for coder|critic [--full]
    cct.py show  RUN_DIR (--item C03 | --event 12 | --items)
    cct.py stats RUN_DIR [--out stats.json]
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:  # POSIX lock; the lead is the only writer, the lock guards accidents.
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX hosts
    fcntl = None

SCHEMA = 2
SKILL_DIR = Path(__file__).resolve().parent.parent
LEDGER = "ledger.jsonl"

CORE_LENSES = [
    "intent", "correctness", "security", "scalability", "modularity",
    "complexity", "concurrency", "failure_handling", "testing",
]
EXTRA_LENSES = ["data_integrity", "compatibility", "operability"]
LENS_LABELS = {
    "intent": "Intent", "correctness": "Correctness", "security": "Security",
    "scalability": "Scalability", "modularity": "Modularity",
    "complexity": "Unnecessary complexity", "concurrency": "Concurrency",
    "failure_handling": "Failure handling", "testing": "Testing",
    "data_integrity": "Data integrity", "compatibility": "Compatibility",
    "operability": "Operability",
}
SEVERITIES = ["blocking", "should_fix", "consider"]
CONFIDENCE = ["verified", "likely", "possible"]
DECISIONS = ["accept", "partial", "reject"]
POSITIONS = ["withdraw", "maintain", "amend"]
REVIEW_VERDICTS = ["approve", "approve_with_changes", "needs_rework", "goal_unclear"]
REVIEW_STAGES = ["after_pr", "before_run"]
FINDING_STATUS = ["open", "fixed", "issue_filed", "proposed", "accepted_risk", "wont_fix"]
CRITERION_STATUS = ["met", "partial", "unmet", "unverified"]
OUTCOMES = ["ready_to_merge", "needs_attention", "blocked", "abandoned"]
INTERVENTION_REASONS = [
    "blocker_dispute", "loop", "stall", "scope_drift", "tests_failing",
    "worker_replaced", "clarification", "budget", "other",
]
LIMIT_KEYS = ["max_checkpoints", "stall_minutes", "fix_rounds"]
ACTOR_OF = {
    "plan": "coder", "response": "coder", "final_call": "coder",
    "checkpoint": "coder", "pr": "coder",
    "review": "critic", "rebuttal": "critic",
    "brief": "lead", "intervention": "lead", "note": "lead", "limits": "lead",
    "review_result": "lead", "fix_request": "lead", "finding_update": "lead",
    "acceptance": "lead", "narrative": "lead", "close": "lead",
}
# Lead turns that may come at any point; check_turn adds the conditions.
LEAD_ANYTIME = {"intervention", "note", "limits", "narrative", "acceptance", "close",
                "finding_update", "review_result", "fix_request"}
DONE = {"accepted", "partial", "rejected", "withdrawn"}
REOPENABLE = {"rejected", "partial", "withdrawn"}


class CctError(Exception):
    """A turn or command that the protocol refuses; the message says why."""


# --------------------------------------------------------------------- utils

def now_iso(at: Optional[str] = None) -> str:
    if at:
        parsed = dt.datetime.fromisoformat(at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def minutes_between(a: str, b: str) -> float:
    parse = lambda ts: dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))  # noqa: E731
    return round((parse(b) - parse(a)).total_seconds() / 60.0, 1)


def git(repo: str, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, check=False
    )
    if check and proc.returncode != 0:
        raise CctError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def numstat(repo: str, rev_range: str) -> List[Dict[str, Any]]:
    files = []
    for line in git(repo, "diff", "--numstat", "-M", rev_range).splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        adds, dels, path = parts[0], parts[1], parts[-1]
        binary = adds == "-"
        files.append({"path": path, "adds": 0 if binary else int(adds),
                      "dels": 0 if binary else int(dels), "binary": binary,
                      "kind": file_kind(path)})
    return files


TEST_RE = re.compile(
    r"(^|/)(tests?|__tests__|spec|specs)/|(^|/)test_[^/]+$|_test\.[^/]+$|"
    r"\.(test|spec)\.[^/]+$|Tests?\.[^/]+$"
)
DOC_RE = re.compile(r"(^|/)docs?/|\.(md|rst|adoc|txt)$|(^|/)(README|CHANGELOG|LICENSE)[^/]*$",
                    re.IGNORECASE)


def file_kind(path: str) -> str:
    if TEST_RE.search(path):
        return "tests"
    if DOC_RE.search(path):
        return "docs"
    return "source"


def worktree_problem(repo: str) -> str:
    """Why the checkout cannot be reviewed as commits, or an empty string."""
    changed = git(repo, "status", "--porcelain", "--untracked-files=no")
    if changed:
        return "commit every change first; the critic reviews commits"
    untracked = git(repo, "ls-files", "--others", "--exclude-standard").splitlines()
    if untracked:
        names = ", ".join(untracked[:5]) + (" …" if len(untracked) > 5 else "")
        return (f"untracked files are not in any commit ({names}); add them, or ignore "
                "them in .gitignore or .git/info/exclude")
    return ""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CctError(f"{path} is not valid JSON: {exc}") from exc


def need(obj: Dict[str, Any], key: str, where: str, kind: type = str) -> Any:
    if not isinstance(obj, dict):
        raise CctError(f"{where}: expected a JSON object")
    value = obj.get(key)
    if value is None or (kind is str and isinstance(value, str) and not value.strip()):
        raise CctError(f"{where}: '{key}' is required")
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise CctError(f"{where}: '{key}' must be a {kind.__name__}")
    return value


def text_of(obj: Dict[str, Any], key: str, where: str) -> str:
    value = obj.get(key, "")
    if not isinstance(value, str):
        raise CctError(f"{where}: '{key}' must be a string")
    return value


def list_of(obj: Dict[str, Any], key: str, where: str, of: type,
            required: bool = True, nonempty: bool = False) -> List[Any]:
    value = obj.get(key)
    if value is None and not required:
        return []
    if not isinstance(value, list):
        raise CctError(f"{where}: '{key}' must be a list")
    if nonempty and not value:
        raise CctError(f"{where}: '{key}' must not be empty")
    for n, element in enumerate(value, 1):
        if not isinstance(element, of) or (of is str and not element.strip()):
            kind = "non-empty string" if of is str else "JSON object"
            raise CctError(f"{where}: entry {n} of '{key}' must be a {kind}")
    return value


def one_of(value: Any, allowed: List[str], where: str) -> str:
    if value not in allowed:
        raise CctError(f"{where}: '{value}' is not one of {', '.join(allowed)}")
    return value


def id_order(value: str) -> Tuple[str, int]:
    """Sort C2 before C10 and F2 before F10."""
    match = re.match(r"([A-Za-z]*)(\d+)", value)
    return (match.group(1), int(match.group(2))) if match else (value, 0)


def web_link(obj: Dict[str, Any], key: str, where: str) -> str:
    value = need(obj, key, where).strip()
    if not re.match(r"https?://\S+$", value):
        raise CctError(f"{where}: '{key}' must be an http(s) link")
    return value


def span(ids: List[str]) -> str:
    if not ids:
        return "none"
    if len(ids) <= 3:
        return ", ".join(ids)
    return f"{ids[0]}–{ids[-1]} ({len(ids)})"


def round_label(key: str) -> str:
    if key == "plan":
        return "Plan"
    if key.startswith("final"):
        return "Final review" + (f" {key.split('-')[1]}" if "-" in key else "")
    if key.startswith("cp"):
        return f"Checkpoint {key[2:]}"
    if key.startswith("fix"):
        base, _, again = key[3:].partition("-")
        return f"Fix round {base}" + (f" ({again})" if again else "")
    return key


def past(decision: str) -> str:
    return {"accept": "accepted", "partial": "partial", "reject": "rejected"}[decision]


# -------------------------------------------------------------------- ledger

class Run:
    """The ledger of one run and the state derived from it."""

    def __init__(self, run_dir: Path):
        self.dir = run_dir.resolve()
        self.path = self.dir / LEDGER
        self.dry = False  # set on trial copies: validate without side effects
        if not self.path.exists():
            raise CctError(f"{self.dir} has no {LEDGER}; run 'cct.py init' first")
        self.events: List[Dict[str, Any]] = []
        for n, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                try:
                    self.events.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise CctError(f"{self.path}:{n} is corrupt: {exc}") from exc
        if not self.events or self.events[0]["type"] != "brief":
            raise CctError(f"{self.path} does not start with a brief")
        self.brief = self.events[0]["data"]
        self.replay()

    # The state is rebuilt from scratch on every load, so it never drifts from
    # the ledger.
    def replay(self) -> None:
        self.items: Dict[str, Dict[str, Any]] = {}
        self.findings: Dict[str, Dict[str, Any]] = {}
        self.rounds: List[Dict[str, Any]] = []
        self.checkpoints: List[Dict[str, Any]] = []
        self.limits: Dict[str, Any] = dict(self.brief.get("limits") or {})
        self.fix_rounds = 0
        self.in_fix = False
        self.pr: Optional[Dict[str, Any]] = None
        self.reviews: List[Dict[str, Any]] = []
        self.acceptance: Optional[Dict[str, Any]] = None
        self.narrative: Optional[Dict[str, Any]] = None
        self.closed: Optional[Dict[str, Any]] = None
        self.interventions: List[Dict[str, Any]] = []
        self.pending_review: Optional[str] = None  # round awaiting the critic
        for event in self.events[1:]:
            self.apply(event)

    def round_named(self, key: str) -> Dict[str, Any]:
        for rnd in self.rounds:
            if rnd["key"] == key:
                return rnd
        rnd = {"key": key, "events": [], "items": []}
        self.rounds.append(rnd)
        return rnd

    def apply(self, event: Dict[str, Any]) -> None:
        kind, data, rkey = event["type"], event["data"], event.get("round")
        if rkey:
            self.round_named(rkey)["events"].append(event["seq"])
        if kind == "plan":
            self.pending_review = "plan"
        elif kind == "checkpoint":
            self.checkpoints.append(event)
            self.pending_review = rkey
            for fid in data.get("addresses", []):
                self.findings[fid].setdefault("addressed_in", []).append(rkey)
        elif kind == "review":
            self.pending_review = None
            for item in data["items"]:
                self.items[item["id"]] = {**item, "round": rkey, "raised_seq": event["seq"],
                                          "state": "awaiting_decision", "history": []}
                self.round_named(rkey)["items"].append(item["id"])
        elif kind == "response":
            for dec in data["decisions"]:
                item = self.items[dec["item"]]
                item["history"].append({"by": "coder", "kind": kind, **dec})
                item["decision"] = dec["decision"]
                item["rationale"] = dec.get("rationale", "")
                item["decided_by"] = "coder"
                item["state"] = ("awaiting_rebuttal" if self.rebuttal_eligible(item, dec["decision"])
                                 else past(dec["decision"]))
        elif kind == "final_call":
            for dec in data["decisions"]:
                item = self.items[dec["item"]]
                item["history"].append({"by": "coder", "kind": kind, **dec})
                item["decision"] = dec["decision"]
                item["final_rationale"] = dec.get("rationale", "")
                item["decided_by"] = "coder"
                item["state"] = past(dec["decision"])
        elif kind == "rebuttal":
            for pos in data["positions"]:
                item = self.items[pos["item"]]
                item["history"].append({"by": "critic", "kind": "rebuttal", **pos})
                item["rebuttal"] = pos
                if pos["position"] == "withdraw":
                    item["state"] = "withdrawn"
                elif item["severity"] == "blocking":
                    item["state"] = "awaiting_ruling"
                else:
                    item["state"] = "awaiting_final_call"
        elif kind == "intervention":
            self.interventions.append(event)
            for rule in data.get("rulings", []):
                item = self.items[rule["item"]]
                item["history"].append({"by": "lead", "kind": "ruling", **rule})
                item["decision"] = rule["decision"]
                item["ruling"] = rule
                item["decided_by"] = "lead"
                item["state"] = past(rule["decision"])
        elif kind == "limits":
            self.limits.update(data["limits"])
        elif kind == "pr":
            if data.get("update"):
                self.pr = {**(self.pr or {}), "head_sha": data["head_sha"], "updated_seq": event["seq"]}
            else:
                self.pr = {**data, "seq": event["seq"]}
        elif kind == "review_result":
            stage = data.get("stage", "after_pr")
            self.reviews.append({**data, "stage": stage, "seq": event["seq"]})
            for finding in data.get("findings", []):
                self.findings[finding["id"]] = {**finding, "status": "open", "stage": stage}
        elif kind == "fix_request":
            self.fix_rounds += 1
            self.in_fix = True
            for fid in data["findings"]:
                self.findings[fid]["fix_round"] = self.fix_rounds
                self.findings[fid].pop("rechecked", None)
        elif kind == "finding_update":
            for upd in data["updates"]:
                finding = self.findings[upd["finding"]]
                # Each update replaces the last one's reason, so no stale note
                # or evidence stays next to a new status.
                for key in ("note", "evidence", "issue_url"):
                    finding.pop(key, None)
                finding.update({k: v for k, v in upd.items() if k != "finding"})
                finding["update_seq"] = event["seq"]
                if self.in_fix and finding.get("fix_round") == self.fix_rounds:
                    finding["rechecked"] = True
            if self.in_fix and not self.unchecked_fix_findings():
                self.in_fix = False
        elif kind == "acceptance":
            self.acceptance = data
        elif kind == "narrative":
            self.narrative = data
        elif kind == "close":
            self.closed = data

    def rebuttal_eligible(self, item: Dict[str, Any], decision: str) -> bool:
        if decision == "accept":
            return False
        return item["round"] == "plan" or item["severity"] == "blocking"

    def items_where(self, pred) -> List[str]:
        return [iid for iid, item in self.items.items() if pred(item)]

    def unchecked_fix_findings(self) -> List[str]:
        return [fid for fid, f in self.findings.items()
                if f.get("fix_round") == self.fix_rounds and not f.get("rechecked")]

    def limit(self, key: str, default: Any) -> Any:
        value = self.limits.get(key)
        return default if value is None else value

    def checkpoint_round(self, final: bool) -> str:
        """The round name the next checkpoint gets."""
        if self.in_fix:
            base = f"fix{self.fix_rounds}"
        elif final or self.final_checkpoints():
            base = "final"
        else:
            return f"cp{sum(1 for c in self.checkpoints if c['round'].startswith('cp')) + 1}"
        k = sum(1 for c in self.checkpoints if c["round"] == base or c["round"].startswith(base + "-"))
        return base if k == 0 else f"{base}-{k + 1}"

    def final_checkpoints(self) -> List[Dict[str, Any]]:
        return [c for c in self.checkpoints if c["round"].startswith("final")]

    def last_review_items(self) -> List[str]:
        reviews = [e for e in self.events if e["type"] == "review"]
        return [i["id"] for i in reviews[-1]["data"]["items"]] if reviews else []

    def reviewed_head(self) -> Optional[str]:
        return self.checkpoints[-1]["data"]["git"]["head"] if self.checkpoints else None

    def blocking_open(self) -> List[str]:
        return [fid for fid, f in self.findings.items()
                if f["severity"] == "blocking" and f["status"] == "open"]

    def review_at(self, stage: str) -> Optional[Dict[str, Any]]:
        return next((r for r in self.reviews if r["stage"] == stage), None)

    def review_ran(self) -> bool:
        return any(r.get("ran") for r in self.reviews)

    def not_rechecked(self) -> List[str]:
        """Findings of a review from before the run that nobody checked at the pull request's head."""
        if not self.pr:
            return []
        return [fid for fid, f in self.findings.items()
                if f.get("stage") == "before_run" and f.get("update_seq", 0) < self.pr["seq"]]

    def undecided(self) -> List[str]:
        """Open findings with no recorded reason: nobody has said what happens to them."""
        return [fid for fid, f in self.findings.items()
                if f["status"] == "open" and not f.get("note")]

    # Whose move is it? Every entry is a valid next turn; open critiques first.
    def expectations(self) -> List[Dict[str, Any]]:
        if self.closed:
            return []
        exp: List[Dict[str, Any]] = []
        for state, actor, kind in (("awaiting_decision", "coder", "response"),
                                   ("awaiting_rebuttal", "critic", "rebuttal"),
                                   ("awaiting_final_call", "coder", "final_call"),
                                   ("awaiting_ruling", "lead", "intervention")):
            ids = self.items_where(lambda i, s=state: i["state"] == s)
            if ids:
                exp.append({"actor": actor, "type": kind, "items": ids})
        if exp:
            if exp[-1]["type"] == "intervention":
                exp[-1]["why"] = "a blocking critique the critic kept needs your ruling"
            return exp
        if self.pending_review:
            return [{"actor": "critic", "type": "review", "round": self.pending_review}]
        if not any(e["type"] == "plan" for e in self.events):
            return [{"actor": "coder", "type": "plan"}]
        if self.in_fix:
            base = f"fix{self.fix_rounds}"
            fix_cps = [c for c in self.checkpoints
                       if c["round"] == base or c["round"].startswith(base + "-")]
            if not fix_cps:
                return [{"actor": "coder", "type": "checkpoint", "round": base,
                         "why": "fix the requested blocking findings"}]
            if (self.pr or {}).get("updated_seq", 0) < self.checkpoints[-1]["seq"]:
                return [{"actor": "coder", "type": "checkpoint", "round": self.checkpoint_round(False),
                         "why": "only if you changed code since the critic's review"},
                        {"actor": "coder", "type": "pr", "update": True,
                         "why": "push the reviewed fixes to the pull request"}]
            return [{"actor": "lead", "type": "finding_update", "items": self.unchecked_fix_findings(),
                     "why": "re-check each finding the fix round addressed"}]
        if not self.final_checkpoints():
            return [{"actor": "coder", "type": "checkpoint", "round": self.checkpoint_round(False),
                     "why": "keep building; mark the last checkpoint final"}]
        if not self.pr:
            return [{"actor": "coder", "type": "checkpoint", "round": self.checkpoint_round(True),
                     "why": "only if you changed code after the final review"},
                    {"actor": "coder", "type": "pr"}]
        if not self.reviews:
            return [{"actor": "lead", "type": "review_result",
                     "why": "run project-review-process on the pull request"}]
        todo = []
        stale = self.not_rechecked()
        if stale:
            todo.append({"actor": "lead", "type": "finding_update", "items": stale,
                         "why": "re-check each earlier finding at the pull request's head: "
                                "fixed with evidence, or open with a note"})
        if not self.review_at("after_pr"):
            todo.append({"actor": "lead", "type": "review_result",
                         "why": "optional: a new project-review-process review of the pull request"})
        blocking = [fid for fid in self.blocking_open() if fid not in stale]
        if blocking and self.fix_rounds < int(self.limit("fix_rounds", 1)):
            todo.append({"actor": "lead", "type": "fix_request", "items": blocking,
                         "why": "or record them as accepted_risk, or close as blocked"})
        unfiled = [fid for fid in self.undecided()
                   if self.findings[fid]["severity"] != "blocking" and fid not in stale]
        if unfiled:
            todo.append({"actor": "lead", "type": "finding_update", "items": unfiled,
                         "why": "file or propose follow-ups for non-blocking findings"})
        if not self.acceptance:
            todo.append({"actor": "lead", "type": "acceptance"})
        if not self.narrative:
            todo.append({"actor": "lead", "type": "narrative"})
        todo.append({"actor": "lead", "type": "close"})
        return todo

    def signals(self, now: Optional[str] = None) -> List[Dict[str, str]]:
        sig: List[Dict[str, str]] = []
        if self.closed:
            return sig
        stall = float(self.limit("stall_minutes", 45))
        idle = minutes_between(self.events[-1]["ts"], now or now_iso())
        if idle > stall:
            sig.append({"signal": "stall",
                        "detail": f"no recorded turn for {idle:.0f} min (limit {stall:.0f})"})
        for root, chain in self.reraise_chains().items():
            if len(chain) >= 2 and not any(self.items[i].get("decided_by") == "lead"
                                           for i in [root] + chain):
                sig.append({"signal": "loop",
                            "detail": f"{root} has been raised again {len(chain)} times"})
        rule = self.items_where(lambda i: i["state"] == "awaiting_ruling")
        if rule:
            sig.append({"signal": "blocker_dispute",
                        "detail": f"blocking critique(s) {span(rule)} need a ruling"})
        cps = self.checkpoints
        if len(cps) >= 2 and all((c["data"]["tests"].get("failed") or 0) > 0 for c in cps[-2:]):
            sig.append({"signal": "tests_failing",
                        "detail": "the last two checkpoints reported failing tests"})
        if cps and cps[-1]["data"]["git"]["adds"] + cps[-1]["data"]["git"]["dels"] == 0:
            sig.append({"signal": "no_progress", "detail": "the last checkpoint changed no lines"})
        max_cp = self.limits.get("max_checkpoints")
        if max_cp and len(cps) > int(max_cp):
            sig.append({"signal": "budget",
                        "detail": f"{len(cps)} checkpoints exceed the limit of {max_cp}"})
        return sig

    def reraise_chains(self) -> Dict[str, List[str]]:
        chains: Dict[str, List[str]] = {}
        for iid, item in self.items.items():
            root = item.get("reraises")
            while root and self.items.get(root, {}).get("reraises"):
                root = self.items[root]["reraises"]
            if root:
                chains.setdefault(root, []).append(iid)
        return chains


def append(run: Run, actor: str, kind: str, data: Dict[str, Any],
           rnd: Optional[str] = None, at: Optional[str] = None) -> Dict[str, Any]:
    event = {"seq": run.events[-1]["seq"] + 1, "ts": now_iso(at), "actor": actor,
             "type": kind, "data": data}
    if rnd:
        event["round"] = rnd
    if not run.dry:
        line = json.dumps(event, ensure_ascii=False, sort_keys=True)
        with open(run.path, "a", encoding="utf-8") as fh:
            if fcntl:
                fcntl.flock(fh, fcntl.LOCK_EX)
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    run.events.append(event)
    run.apply(event)
    return event


# ---------------------------------------------------------------- validation

def check_turn(run: Run, turn: Dict[str, Any], actor: str
               ) -> Tuple[str, Dict[str, Any], Optional[str]]:
    """Validate one turn against the protocol and normalise it for the ledger."""
    kind = need(turn, "type", "turn")
    if kind not in ACTOR_OF or kind == "brief":
        raise CctError(f"unknown turn type '{kind}'")
    if ACTOR_OF[kind] != actor:
        raise CctError(f"a {kind} turn comes from the {ACTOR_OF[kind]}, not the {actor}")
    where = f"{actor} {kind}"
    if run.closed:
        raise CctError("the run is closed")
    exp = run.expectations()
    expected = [e for e in exp if e["actor"] == actor and e["type"] == kind]
    if not expected and not (actor == "lead" and kind in LEAD_ANYTIME):
        wanted = "; ".join(f"{e['actor']} {e['type']}" for e in exp) or "nothing"
        raise CctError(f"{where} is out of turn; expected: {wanted}")
    data: Dict[str, Any] = {}
    rnd: Optional[str] = None

    if kind == "plan":
        data["summary"] = need(turn, "summary", where)
        units = list_of(turn, "units", where, dict, nonempty=True)
        for n, unit in enumerate(units, 1):
            need(unit, "name", f"{where} unit {n}")
            need(unit, "purpose", f"{where} unit {n}")
        data["units"] = [{"name": u["name"], "purpose": u["purpose"]} for u in units]
        lenses = need(turn, "lenses", where, dict)
        required = CORE_LENSES + [l for l in run.brief.get("extra_lenses", [])]
        missing = [l for l in required if not isinstance(lenses.get(l), str) or not lenses[l].strip()]
        if missing:
            raise CctError(f"{where}: say how the plan handles each lens (or 'n/a: why'); "
                           f"missing: {', '.join(missing)}")
        data["lenses"] = {l: lenses[l] for l in required}
        data["checkpoints"] = list_of(turn, "checkpoints", where, str, nonempty=True)
        data["tests"] = list_of(turn, "tests", where, str, required=False)
        if turn.get("plan_file"):
            data["plan_file"] = rel_existing(run, need(turn, "plan_file", where), where)
        rnd = "plan"

    elif kind == "review":
        rnd = run.pending_review
        data["summary"] = need(turn, "summary", where)
        items = list_of(turn, "items", where, dict)
        base = len(run.items)
        normalised = []
        for n, item in enumerate(items, 1):
            iw = f"{where} item {n}"
            entry = {
                "id": f"C{base + n:02d}",
                "lens": one_of(need(item, "lens", iw), CORE_LENSES + EXTRA_LENSES, iw),
                "severity": one_of(need(item, "severity", iw), SEVERITIES, iw),
                "title": need(item, "title", iw),
                "detail": text_of(item, "detail", iw),
                "where": text_of(item, "where", iw),
                "suggestion": text_of(item, "suggestion", iw),
                "confidence": one_of(item.get("confidence", "likely"), CONFIDENCE, iw),
            }
            if item.get("reraises"):
                prior = run.items.get(item["reraises"])
                if not prior:
                    raise CctError(f"{iw}: reraises unknown item {item['reraises']}")
                if prior["state"] not in REOPENABLE or prior.get("decided_by") == "lead":
                    raise CctError(f"{iw}: {item['reraises']} is {prior['state']}"
                                   + (" by a lead ruling" if prior.get("decided_by") == "lead" else "")
                                   + "; only a critique the coder did not take in full can be raised again")
                entry["reraises"] = item["reraises"]
                entry["new_evidence"] = need(item, "new_evidence", iw)
            normalised.append(entry)
        data["items"] = normalised
        if turn.get("verdict"):
            data["verdict"] = text_of(turn, "verdict", where)

    elif kind in ("response", "final_call"):
        state = "awaiting_decision" if kind == "response" else "awaiting_final_call"
        pending = run.items_where(lambda i: i["state"] == state)
        decisions = list_of(turn, "decisions", where, dict)
        got = [d.get("item") for d in decisions]
        if sorted(map(str, got)) != sorted(pending):
            raise CctError(f"{where}: answer exactly {span(pending)}; got "
                           f"{', '.join(map(str, got)) or 'none'}")
        for dec in decisions:
            dw = f"{where} {dec['item']}"
            one_of(need(dec, "decision", dw), DECISIONS, dw)
            if dec["decision"] != "accept":
                need(dec, "rationale", dw)
            text_of(dec, "rationale", dw)
        data["decisions"] = [{k: d[k] for k in ("item", "decision", "rationale") if k in d}
                             for d in decisions]
        if turn.get("note"):
            data["note"] = text_of(turn, "note", where)
        rnd = run.items[pending[0]]["round"]

    elif kind == "rebuttal":
        pending = run.items_where(lambda i: i["state"] == "awaiting_rebuttal")
        positions = list_of(turn, "positions", where, dict)
        got = [p.get("item") for p in positions]
        if sorted(map(str, got)) != sorted(pending):
            raise CctError(f"{where}: give a last word on exactly {span(pending)}")
        for pos in positions:
            pw = f"{where} {pos['item']}"
            one_of(need(pos, "position", pw), POSITIONS, pw)
            if pos["position"] != "withdraw":
                need(pos, "argument", pw)
            if pos["position"] == "amend":
                need(pos, "amended_suggestion", pw)
        data["positions"] = [{k: p[k] for k in ("item", "position", "argument", "amended_suggestion")
                              if k in p} for p in positions]
        rnd = run.items[pending[0]]["round"]

    elif kind == "checkpoint":
        final = turn.get("final", False)
        if not isinstance(final, bool):
            raise CctError(f"{where}: 'final' must be true or false")
        rnd = run.checkpoint_round(final)
        data["title"] = need(turn, "title", where)
        data["notes"] = text_of(turn, "notes", where)
        data["final"] = rnd.startswith("final")
        tests = need(turn, "tests", where, dict)
        if "not_run" in tests:
            need(tests, "not_run", f"{where} tests")
        else:
            for key in ("passed", "failed"):
                need(tests, key, f"{where} tests", int)
        data["tests"] = tests
        data["deviations"] = list_of(turn, "deviations", where, str, required=False)
        addresses = list_of(turn, "addresses", where, str, required=False)
        for fid in addresses:
            if fid not in run.findings:
                raise CctError(f"{where}: 'addresses' names unknown finding {fid}")
        if addresses:
            data["addresses"] = sorted(set(addresses), key=id_order)
        data["git"] = checkpoint_git(run, rnd)

    elif kind == "pr":
        update = turn.get("update", False)
        if not isinstance(update, bool) or update != bool(expected[0].get("update")):
            raise CctError(f"{where}: " + ("record the fix push with \"update\": true"
                                           if expected[0].get("update") else
                                           "there is no pull request to update yet"))
        if not update:
            data["url"] = need(turn, "url", where)
            existing = run.brief.get("pull_request")
            if existing:
                if data["url"].strip().rstrip("/") != existing["url"].rstrip("/"):
                    raise CctError(f"{where}: the brief names the existing pull request "
                                   f"{existing['url']}; push to that one and record it, do not "
                                   "open another")
                data["existing"] = True
        for key in ("url", "title"):
            if key in turn:
                data[key] = text_of(turn, key, where)
        if "number" in turn:
            data["number"] = need(turn, "number", where, int)
        if "draft" in turn:
            data["draft"] = bool(turn["draft"])
        if update:
            data["update"] = True
            rnd = f"fix{run.fix_rounds}"
        repo = run.brief["repo"]["path"]
        problem = worktree_problem(repo)
        if problem:
            raise CctError(f"{where}: {problem}")
        head = git(repo, "rev-parse", "HEAD")
        if head != run.reviewed_head():
            raise CctError(f"{where}: HEAD has commits the critic has not reviewed; record a "
                           "checkpoint for them first")
        data["head_sha"] = head
        upstream = git(repo, "rev-parse", "@{u}", check=False)
        if upstream and upstream != head:
            data["warning"] = "the remote branch differs from the local HEAD; push before review"

    elif kind == "intervention":
        data["reason"] = one_of(need(turn, "reason", where), INTERVENTION_REASONS, where)
        data["summary"] = need(turn, "summary", where)
        rulings = list_of(turn, "rulings", where, dict, required=False)
        seen = set()
        for rule in rulings:
            iid = rule.get("item")
            rw = f"{where} ruling {iid}"
            item = run.items.get(iid)
            if not item:
                raise CctError(f"{rw}: unknown item")
            if iid in seen:
                raise CctError(f"{rw}: ruled twice in one intervention")
            seen.add(iid)
            if item["state"] != "awaiting_ruling" and item["state"] not in DONE:
                raise CctError(f"{rw}: it is {item['state'].replace('_', ' ')}; let that turn "
                               "finish, then rule")
            one_of(need(rule, "decision", rw), DECISIONS, rw)
            need(rule, "rationale", rw)
        data["rulings"] = [{k: r[k] for k in ("item", "decision", "rationale")} for r in rulings]
        data["actions"] = list_of(turn, "actions", where, str, required=False)
        if rulings:
            rnd = run.items[rulings[0]["item"]]["round"]

    elif kind == "note":
        data["text"] = need(turn, "text", where)

    elif kind == "limits":
        limits = need(turn, "limits", where, dict)
        for key, value in limits.items():
            one_of(key, LIMIT_KEYS, f"{where} key")
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                raise CctError(f"{where}: {key} must be a positive number")
        if not limits:
            raise CctError(f"{where}: give at least one limit")
        data["limits"] = limits
        data["reason"] = need(turn, "reason", where)

    elif kind == "review_result":
        ran = turn.get("ran", True)
        if not isinstance(ran, bool):
            raise CctError(f"{where}: 'ran' must be true or false")
        stage = one_of(turn.get("stage", "after_pr"), REVIEW_STAGES, f"{where} stage")
        if run.review_at(stage):
            raise CctError(f"{where}: the review result is already recorded"
                           + (" for a review from before the run" if stage == "before_run" else ""))
        if stage == "before_run":
            if not ran:
                raise CctError(f"{where}: record a review from before the run only when it ran")
            if run.pr:
                raise CctError(f"{where}: a review from before the run is recorded before the pull "
                               "request turn; record this one without 'stage'")
        elif ran and not run.pr:
            raise CctError(f"{where}: record a review that ran once the pull request is open; for a "
                           "review that ran before this run, add \"stage\": \"before_run\"")
        data["ran"] = ran
        data["stage"] = stage
        if not ran:
            data["reason"] = need(turn, "reason", where)
            data["findings"] = []
        else:
            data["verdict"] = one_of(need(turn, "verdict", where), REVIEW_VERDICTS, where)
            data["guide"] = text_of(turn, "guide", where) or "pull-requests"
            data["reviewers"] = list_of(turn, "reviewers", where, str, nonempty=True)
            data["skipped"] = list_of(turn, "skipped", where, str, required=False)
            for key in ("head_sha", "source"):
                if turn.get(key):
                    data[key] = text_of(turn, key, where)
            findings = []
            base = len(run.findings)
            for n, f in enumerate(list_of(turn, "findings", where, dict, required=False), 1):
                fw = f"{where} finding {n}"
                entry = {
                    "id": f"F{base + n}",
                    "severity": one_of(need(f, "severity", fw), SEVERITIES, fw),
                    "confidence": one_of(f.get("confidence", "likely"), CONFIDENCE, fw),
                    "title": need(f, "title", fw),
                    "where": text_of(f, "where", fw),
                    "scenario": text_of(f, "scenario", fw),
                    "direction": text_of(f, "direction", fw),
                }
                if f.get("ref"):
                    entry["ref"] = text_of(f, "ref", fw)
                if f.get("matches_item"):
                    if f["matches_item"] not in run.items:
                        raise CctError(f"{fw}: matches unknown item {f['matches_item']}")
                    entry["matches_item"] = f["matches_item"]
                findings.append(entry)
            data["findings"] = findings
        if turn.get("report_file"):
            data["report_file"] = rel_existing(run, need(turn, "report_file", where), where)

    elif kind == "fix_request":
        ids = list_of(turn, "findings", where, str, nonempty=True)
        if not run.review_ran():
            raise CctError(f"{where}: record the project review first")
        if not run.pr:
            raise CctError(f"{where}: a fix round starts after the pull request turn; until then "
                           "the findings of an earlier review are part of the brief")
        if run.in_fix:
            raise CctError(f"{where}: fix round {run.fix_rounds} is still open")
        if run.items_where(lambda i: i["state"] not in DONE) or run.pending_review:
            raise CctError(f"{where}: let the open coder-critic turn finish first")
        if run.fix_rounds >= int(run.limit("fix_rounds", 1)):
            raise CctError(f"{where}: the brief allows {run.limit('fix_rounds', 1)} fix round(s); "
                           "raise the limit with a 'limits' turn first")
        for fid in ids:
            if fid not in run.blocking_open():
                raise CctError(f"{where}: {fid} is not an open blocking finding")
        data["findings"] = ids
        data["note"] = text_of(turn, "note", where)

    elif kind == "finding_update":
        if not run.findings:
            raise CctError(f"{where}: there are no review findings to update")
        updates = list_of(turn, "updates", where, dict, nonempty=True)
        for upd in updates:
            uw = f"{where} {upd.get('finding')}"
            if upd.get("finding") not in run.findings:
                raise CctError(f"{uw}: unknown finding")
            one_of(need(upd, "status", uw), FINDING_STATUS, uw)
            if upd["status"] == "issue_filed":
                web_link(upd, "issue_url", uw)
            if upd["status"] == "fixed":
                need(upd, "evidence", uw)
            if upd["status"] in ("accepted_risk", "wont_fix", "proposed"):
                need(upd, "note", uw)
            if upd["status"] == "open" and not str(upd.get("note") or "").strip():
                raise CctError(f"{uw}: 'note' is required for open: say what is left and why it "
                               "stays open")
            for key in ("issue_url", "evidence", "note"):
                text_of(upd, key, uw)
            if upd.get("matches_item") and upd["matches_item"] not in run.items:
                raise CctError(f"{uw}: matches unknown item {upd['matches_item']}")
        data["updates"] = [{k: u[k] for k in ("finding", "status", "issue_url", "evidence", "note",
                                               "matches_item") if u.get(k)} for u in updates]

    elif kind == "acceptance":
        criteria = list_of(turn, "criteria", where, dict)
        known = [c["id"] for c in run.brief["acceptance_criteria"]]
        got = [c.get("id") for c in criteria]
        if sorted(map(str, got)) != sorted(known):
            raise CctError(f"{where}: give a status for each of {', '.join(known)}")
        for c in criteria:
            cw = f"{where} {c['id']}"
            one_of(need(c, "status", cw), CRITERION_STATUS, cw)
            need(c, "evidence", cw)
        data["criteria"] = [{k: c[k] for k in ("id", "status", "evidence")} for c in criteria]

    elif kind == "narrative":
        data["summary"] = need(turn, "summary", where)
        if len(data["summary"].split()) > 130:
            raise CctError(f"{where}: keep the summary under 130 words; details belong in the rounds")
        data["next_steps"] = list_of(turn, "next_steps", where, str, required=False)

    elif kind == "close":
        data["outcome"] = one_of(need(turn, "outcome", where), OUTCOMES, where)
        data["note"] = text_of(turn, "note", where)
        check_close(run, data["outcome"], where)
    return kind, data, rnd


def check_close(run: Run, outcome: str, where: str) -> None:
    if outcome == "abandoned":
        return
    if not run.narrative:
        raise CctError(f"{where}: record a narrative before closing")
    if outcome != "ready_to_merge":
        return
    problems = []
    if not run.pr:
        problems.append("there is no pull request")
    if not run.review_ran():
        problems.append("the project review has not run")
    stale = run.not_rechecked()
    if stale:
        problems.append(f"{span(stale)} were not re-checked at the pull request's head")
    if run.items_where(lambda i: i["state"] not in DONE):
        problems.append("some critiques are not settled")
    stuck = [fid for fid, f in run.findings.items()
             if f["severity"] == "blocking" and f["status"] not in ("fixed", "accepted_risk")]
    if stuck:
        problems.append(f"{', '.join(stuck)} still block the merge")
    still_open = [fid for fid, f in run.findings.items()
                  if f["status"] == "open" and f["severity"] != "blocking"]
    if still_open:
        problems.append(f"{', '.join(still_open)} are still open (file or propose a follow-up, or "
                        "record accepted_risk or wont_fix)")
    if not run.acceptance:
        problems.append("the acceptance criteria are not checked")
    elif any(c["status"] == "unmet" for c in run.acceptance["criteria"]):
        problems.append("an acceptance criterion is unmet")
    if problems:
        raise CctError(f"{where}: not ready to merge: {'; '.join(problems)}. "
                       "Close as needs_attention or blocked instead")


def rel_existing(run: Run, path: str, where: str) -> str:
    target = (run.dir / path).resolve()
    if not target.exists():
        raise CctError(f"{where}: {path} does not exist in the run folder")
    try:
        return str(target.relative_to(run.dir))
    except ValueError as exc:
        raise CctError(f"{where}: {path} must be inside the run folder") from exc


def checkpoint_git(run: Run, rnd: str) -> Dict[str, Any]:
    repo = run.brief["repo"]["path"]
    problem = worktree_problem(repo)
    if problem:
        raise CctError(f"checkpoint: {problem}")
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    head = git(repo, "rev-parse", "HEAD")
    start = run.reviewed_head() or run.brief["repo"]["base_sha"]
    if head == start:
        raise CctError("checkpoint: no new commits since the last checkpoint")
    files = numstat(repo, f"{start}..{head}")
    patch_rel = f"diffs/{rnd}.patch"
    if not run.dry:
        (run.dir / "diffs").mkdir(exist_ok=True)
        (run.dir / patch_rel).write_text(git(repo, "diff", "-M", f"{start}..{head}") + "\n",
                                         encoding="utf-8")
    info = {
        "from": start, "head": head, "branch": branch,
        "commits": int(git(repo, "rev-list", "--count", f"{start}..{head}") or 0),
        "adds": sum(f["adds"] for f in files), "dels": sum(f["dels"] for f in files),
        "files": len(files), "patch": patch_rel,
    }
    expected = run.brief["repo"].get("branch")
    if expected and branch != expected:
        info["warning"] = f"checked out '{branch}', the brief names '{expected}'"
    return info


# ------------------------------------------------------------------ commands

def cmd_init(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir).resolve()
    brief = read_json(Path(args.brief))
    where = "brief"
    for key in ("title", "outcome"):
        need(brief, key, where)
    criteria = need(brief, "acceptance_criteria", where, list)
    if not criteria:
        raise CctError("brief: list at least one acceptance criterion")
    brief["acceptance_criteria"] = [
        {"id": c.get("id") or f"A{n}", "text": need(c, "text", f"brief criterion {n}")}
        if isinstance(c, dict) else {"id": f"A{n}", "text": str(c)}
        for n, c in enumerate(criteria, 1)]
    for key in ("features", "non_goals", "constraints"):
        brief[key] = list_of(brief, key, where, str, required=False)
    repo = need(brief, "repo", where, dict)
    for key in ("path", "base", "branch"):
        need(repo, key, "brief.repo")
    repo["path"] = str(Path(repo["path"]).resolve())
    top = Path(git(repo["path"], "rev-parse", "--show-toplevel")).resolve()
    if run_dir == top or top in run_dir.parents:
        raise CctError("keep the run folder outside the checkout so it never enters the PR")
    repo["base_sha"] = git(repo["path"], "rev-parse", repo["base"])
    workers = need(brief, "workers", where, dict)
    for role in ("coder", "critic"):
        need(need(workers, role, "brief.workers", dict), "model", f"brief.workers.{role}")
    for lens in list_of(brief, "extra_lenses", where, str, required=False):
        one_of(lens, EXTRA_LENSES, "brief.extra_lenses")
    brief.setdefault("extra_lenses", [])
    limits = brief.setdefault("limits", {})
    if not isinstance(limits, dict):
        raise CctError("brief: 'limits' must be a JSON object")
    for key in limits:
        one_of(key, LIMIT_KEYS, "brief.limits")
    if brief.get("pull_request") is not None:
        existing = need(brief, "pull_request", where, dict)
        entry = {"url": web_link(existing, "url", "brief.pull_request")}
        if existing.get("number") is not None:
            entry["number"] = need(existing, "number", "brief.pull_request", int)
        brief["pull_request"] = entry
    brief.setdefault("follow_up_issues", "file")
    one_of(brief["follow_up_issues"], ["file", "propose"], "brief.follow_up_issues")
    if run_dir.exists() and any(run_dir.iterdir()):
        raise CctError(f"{run_dir} is not empty; use a new run folder")
    for sub in ("turns", "diffs", "roles"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    for name in ("protocol.md", "coder.md", "critic.md"):
        shutil.copyfile(SKILL_DIR / "references" / name, run_dir / "roles" / name)
    (run_dir / "brief.md").write_text(brief_markdown(brief), encoding="utf-8")
    event = {"seq": 1, "ts": now_iso(args.at), "actor": "lead", "type": "brief", "data": brief}
    (run_dir / LEDGER).write_text(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n",
                                  encoding="utf-8")
    print(f"Run folder ready: {run_dir}")
    print(f"Next: start the coder with the turn brief from 'cct.py turn {run_dir} --for coder'.")


def brief_markdown(brief: Dict[str, Any]) -> str:
    lines = [f"# {brief['title']}", "", brief["outcome"], ""]
    if brief.get("features"):
        lines += ["## Features", ""] + [f"- {f}" for f in brief["features"]] + [""]
    lines += ["## Acceptance criteria", ""]
    lines += [f"- **{c['id']}** {c['text']}" for c in brief["acceptance_criteria"]] + [""]
    if brief.get("non_goals"):
        lines += ["## Non-goals", ""] + [f"- {g}" for g in brief["non_goals"]] + [""]
    if brief.get("constraints"):
        lines += ["## Constraints", ""] + [f"- {c}" for c in brief["constraints"]] + [""]
    ctx = brief.get("context") or {}
    if ctx:
        lines += ["## How this fits the larger plan", ""]
        lines += [f"- {str(k).replace('_', ' ').capitalize()}: {v}" for k, v in ctx.items()] + [""]
    repo = brief["repo"]
    lines += ["## Repository", "",
              f"- Checkout: `{repo['path']}`",
              f"- Base: `{repo['base']}` ({repo['base_sha'][:10]})",
              f"- Work branch: `{repo['branch']}`"]
    if brief.get("pull_request"):
        lines.append(f"- Pull request: {pr_name(brief['pull_request'])} already exists. Push to it; "
                     "do not open another")
    lines.append("")
    lenses = CORE_LENSES + brief.get("extra_lenses", [])
    lines += ["## Review lenses", "", ", ".join(LENS_LABELS[l] for l in lenses), ""]
    return "\n".join(lines)


def pr_name(pr: Dict[str, Any]) -> str:
    return (f"#{pr['number']} ({pr['url']})" if pr.get("number") else pr["url"])


def cmd_post(args: argparse.Namespace) -> None:
    run = Run(Path(args.run_dir))
    source = None if args.file == "-" else Path(args.file).resolve()
    if source and source.name.endswith("-next.json"):
        owner = source.name[: -len("-next.json")]
        if owner in ("coder", "critic") and owner != args.actor:
            raise CctError(f"{source.name} is the {owner}'s turn file; post it with --actor {owner}")
    src = sys.stdin.read() if source is None else source.read_text(encoding="utf-8")
    try:
        payload = json.loads(src)
    except json.JSONDecodeError as exc:
        raise CctError(f"turn file is not valid JSON: {exc}") from exc
    turns = payload if isinstance(payload, list) else [payload]
    if not turns or not all(isinstance(t, dict) for t in turns):
        raise CctError("give a turn object or a non-empty list of turn objects")
    # Check the whole list on a side-effect-free copy first, so a refused turn
    # records nothing.
    trial = copy.deepcopy(run)
    trial.dry = True
    for n, turn in enumerate(turns, 1):
        prefix = f"turn {n} of {len(turns)}: " if len(turns) > 1 else ""
        try:
            kind, data, rnd = check_turn(trial, turn, args.actor)
        except CctError as exc:
            raise CctError(f"{prefix}{exc}; nothing was recorded") from exc
        except (TypeError, AttributeError, KeyError, ValueError) as exc:
            raise CctError(f"{prefix}malformed turn ({type(exc).__name__}: {exc}); "
                           "nothing was recorded") from exc
        append(trial, args.actor, kind, data, rnd, args.at)
    for turn in turns:
        kind, data, rnd = check_turn(run, turn, args.actor)
        event = append(run, args.actor, kind, data, rnd, args.at)
        archive = run.dir / "turns" / f"{event['seq']:04d}-{args.actor}-{kind}.json"
        archive.write_text(json.dumps(turn, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(describe(event))
    if source and source.parent == run.dir / "turns" and source.name.endswith("-next.json"):
        source.unlink()
    print_next(run)
    if args.actor == "critic":
        # The tree was clean at the checkpoint, so a change now is the critic's.
        # The turn is already recorded; a checkout that cannot be read is not
        # a refusal.
        try:
            problem = worktree_problem(run.brief["repo"]["path"])
        except CctError as exc:
            problem = ""
            print(f"Warning: could not check the checkout after the critic's turn ({exc})")
        if problem:
            print("Signal: checkout_changed — the checkout changed during the critic's turn "
                  f"({problem}); restore it and remind the critic that it reads only")
    print_handoffs(run)


def describe(event: Dict[str, Any]) -> str:
    kind, data, rnd = event["type"], event["data"], event.get("round")
    head = f"Recorded #{event['seq']} {event['actor']} {kind}" + (f" ({rnd})" if rnd else "")
    if kind == "review":
        ids = [i["id"] for i in data["items"]]
        sev = {s: sum(1 for i in data["items"] if i["severity"] == s) for s in SEVERITIES}
        detail = ", ".join(f"{n} {s.replace('_', ' ')}" for s, n in sev.items() if n)
        return f"{head}: {span(ids)}" + (f" [{detail}]" if detail else " — no critiques")
    if kind in ("response", "final_call"):
        tally = {d: sum(1 for x in data["decisions"] if x["decision"] == d) for d in DECISIONS}
        return f"{head}: " + ", ".join(f"{n} {d}" for d, n in tally.items() if n)
    if kind == "rebuttal":
        tally = {p: sum(1 for x in data["positions"] if x["position"] == p) for p in POSITIONS}
        return f"{head}: " + ", ".join(f"{n} {p}" for p, n in tally.items() if n)
    if kind == "checkpoint":
        g = data["git"]
        warn = f" WARNING: {g['warning']}" if g.get("warning") else ""
        fixes = f", names {span(data['addresses'])}" if data.get("addresses") else ""
        return (f"{head}: {data['title']} — {g['commits']} commit(s), +{g['adds']} −{g['dels']}, "
                f"diff at {g['patch']}{fixes}{warn}")
    if kind == "pr":
        warn = f" WARNING: {data['warning']}" if data.get("warning") else ""
        return f"{head}: {data.get('url', 'update')} at {data['head_sha'][:10]}{warn}"
    if kind == "review_result":
        if not data["ran"]:
            return f"{head}: not run — {data['reason']}"
        sev = {s: sum(1 for f in data["findings"] if f["severity"] == s) for s in SEVERITIES}
        when = " (before the run)" if data.get("stage") == "before_run" else ""
        ids = [f["id"] for f in data["findings"]]
        return (f"{head}{when}: {data['verdict']}, " + ", ".join(f"{n} {s}" for s, n in sev.items())
                + (f"; findings {span(ids)}" if ids else ""))
    return head


def print_next(run: Run) -> None:
    exp = run.expectations()
    if not exp:
        print("Next: nothing; the run is closed.")
        return
    for e in exp:
        bits = [f"{e['actor']} {e['type']}"]
        if e.get("round"):
            bits.append(f"round {e['round']}")
        if e.get("items"):
            bits.append(f"items {span(e['items'])}")
        if e.get("why"):
            bits.append(e["why"])
        print("Next: " + " — ".join(bits))
    for s in run.signals():
        print(f"Signal: {s['signal']} — {s['detail']}")


def print_handoffs(run: Run) -> None:
    """Write the brief for each worker whose turn it is and print what to hand over."""
    for role in ("coder", "critic"):
        # Rewrite both, so a worker that is not up never finds a stale brief.
        path = write_brief(run, role)
        if any(e["actor"] == role for e in run.expectations()):
            print(f"Handoff for the {role} (pass it unchanged): {handoff(run, role, path)}")


def cmd_state(args: argparse.Namespace) -> None:
    run = Run(Path(args.run_dir))
    state = {
        "title": run.brief["title"],
        "events": len(run.events),
        "last": {k: run.events[-1][k] for k in ("seq", "ts", "actor", "type")},
        "checkpoints": len(run.checkpoints),
        "items": {s: len(run.items_where(lambda i, s=s: i["state"] == s))
                  for s in sorted({i["state"] for i in run.items.values()})},
        "limits": run.limits,
        "expect": run.expectations(),
        "signals": run.signals(),
        "closed": bool(run.closed),
    }
    if args.json:
        print(json.dumps(state, indent=2, ensure_ascii=False))
        return
    print(f"{state['title']} — {state['events']} events, {state['checkpoints']} checkpoints")
    print("Items: " + (", ".join(f"{n} {s}" for s, n in state["items"].items()) or "none yet"))
    print_next(run)


OUTCOME_WORDS = {"accepted": "accepted", "partial": "partly accepted", "rejected": "rejected",
                 "withdrawn": "withdrawn by the critic"}


def item_line(item: Dict[str, Any], with_outcome: bool = True) -> str:
    sev = item["severity"].replace("_", " ")
    line = f"- **{item['id']}** [{sev} · {LENS_LABELS[item['lens']]} · {item['confidence']}] {item['title']}"
    if item.get("where"):
        line += f" (at `{item['where']}`)"
    extra = []
    if item.get("detail"):
        extra.append(item["detail"])
    if item.get("suggestion"):
        extra.append(f"Suggestion: {item['suggestion']}")
    if item.get("reraises"):
        extra.append(f"Raises {item['reraises']} again; new evidence: {item['new_evidence']}")
    if with_outcome and item.get("history"):
        first = next((h for h in item["history"] if h["kind"] == "response"), None)
        if first:
            extra.append(f"Coder: {first['decision']}"
                         + (f" — {first['rationale']}" if first.get("rationale") else ""))
        if item.get("rebuttal"):
            r = item["rebuttal"]
            extra.append(f"Critic's last word: {r['position']}"
                         + (f" — {r['argument']}" if r.get("argument") else ""))
            if r.get("amended_suggestion"):
                extra.append(f"Amended suggestion: {r['amended_suggestion']}")
        if item.get("final_rationale"):
            extra.append(f"Coder's final call: {item['decision']} — {item['final_rationale']}")
        if item.get("ruling"):
            extra.append(f"Lead ruling: {item['ruling']['decision']} — {item['ruling']['rationale']}")
    return line + "".join(f"\n  {x}" for x in extra)


def settled_line(item: Dict[str, Any]) -> str:
    by = " by the lead" if item.get("decided_by") == "lead" else ""
    return (f"- {item['id']} {OUTCOME_WORDS.get(item['state'], item['state'])}{by}: "
            f"{item['title']}")


def build_brief(run: Run, role: str) -> str:
    """Everything one worker needs for its next turn, as Markdown."""
    mine = [e for e in run.expectations() if e["actor"] == role]
    repo = run.brief["repo"]
    out = [f"# Turn brief for the {role}: {run.brief['title']}", "",
           f"- Run folder: `{run.dir}`",
           f"- Your role: `{run.dir / 'roles' / (role + '.md')}` and the protocol: "
           f"`{run.dir / 'roles' / 'protocol.md'}`",
           f"- Brief: `{run.dir / 'brief.md'}`",
           f"- Checkout: `{repo['path']}` on `{repo['branch']}`"
           + (" (read only for you)" if role == "critic" else ""), ""]
    if not mine:
        others = "; ".join(f"{e['actor']} {e['type']}" for e in run.expectations()) or "nothing"
        out += ["## Nothing is waiting for you", "", f"Waiting for: {others}."]
        return "\n".join(out) + "\n"
    out += ["## Do now", ""]
    if len(mine) > 1:
        out += ["Do one of these:", ""]
    for e in mine:
        out += turn_section(run, role, e)
    out += context_sections(run, role, mine)
    out += ["## Reply", "",
            f"Write your turn as JSON to `{run.dir / 'turns' / (role + '-next.json')}` "
            "(see the protocol for its fields) and reply with that path and one line "
            "saying what you did. Do not paste the JSON into your reply."]
    return "\n".join(out) + "\n"


def write_brief(run: Run, role: str) -> Path:
    path = run.dir / "turns" / f"{role}-brief.md"
    path.write_text(build_brief(run, role), encoding="utf-8")
    return path


TURN_WORDS = {"plan": "write the plan", "review": "review", "response": "decide on the critiques",
              "final_call": "make the final call", "rebuttal": "give your last word",
              "checkpoint": "build to the next checkpoint", "pr": "push to the pull request"}


def handoff(run: Run, role: str, path: Path) -> str:
    """The short message the lead passes on; the brief itself stays in the file."""
    mine = [e for e in run.expectations() if e["actor"] == role]
    what = " or ".join(dict.fromkeys(
        TURN_WORDS[e["type"]] + (f" ({round_label(e['round']).lower()})"
                                 if e["type"] == "review" else "") for e in mine))
    first = not any(e["actor"] == role for e in run.events)
    start = (f"Read your role `{run.dir / 'roles' / (role + '.md')}` and the protocol "
             f"`{run.dir / 'roles' / 'protocol.md'}` first. " if first else "")
    return (f"Your next turn in the coder-critic run is ready: {what}. {start}"
            f"Read the turn brief `{path}` and do what it says. Reply with the path of your "
            "turn file and one line.")


def cmd_turn(args: argparse.Namespace) -> None:
    run = Run(Path(args.run_dir))
    role = args.for_
    if args.full:
        print(build_brief(run, role), end="")
        return
    path = write_brief(run, role)
    if not any(e["actor"] == role for e in run.expectations()):
        others = "; ".join(f"{e['actor']} {e['type']}" for e in run.expectations()) or "nothing"
        print(f"Nothing is waiting for the {role}. Waiting for: {others}.")
        return
    print(f"Brief written: {path} ({path.stat().st_size / 1024:.1f} KB)")
    print(f"Handoff for the {role} (pass it unchanged): {handoff(run, role, path)}")


def turn_section(run: Run, role: str, e: Dict[str, Any]) -> List[str]:
    t = e["type"]
    if t == "plan":
        lines = ["Explore the checkout, then write the plan: the units (functions, classes, "
                 "modules) to create or change, why, and how the plan handles every lens. "
                 "Do not write code yet. Propose the checkpoints.", ""]
        return lines + findings_to_fix(run, role, full=True)
    if t == "review" and e["round"] == "plan":
        d = next(x for x in reversed(run.events) if x["type"] == "plan")["data"]
        return (["Review the coder's plan before any code is written.", ""] + plan_lines(run, d)
                + findings_to_fix(run, role, full=True))
    if t == "review":
        cp = run.checkpoints[-1]
        d, g = cp["data"], cp["data"]["git"]
        if e["round"].startswith("final"):
            what = "the final checkpoint; review the whole change as it will ship"
        elif e["round"].startswith("fix"):
            what = "the fix-round checkpoint"
        else:
            what = f"checkpoint {e['round']}"
        lines = [f"Review {what}: \"{d['title']}\".", "",
                 f"- Commits `{g['from'][:10]}..{g['head'][:10]}` ({g['commits']}), "
                 f"+{g['adds']} −{g['dels']} in {g['files']} file(s)",
                 f"- Diff: `{run.dir / g['patch']}`",
                 f"- Whole change so far: `git -C {repo_path(run)} diff "
                 f"{run.brief['repo']['base_sha'][:10]}..{g['head'][:10]}`",
                 f"- Tests: {tests_text(d['tests'])}"]
        if d.get("notes"):
            lines.append(f"- Coder's notes: {d['notes']}")
        for dev in d.get("deviations", []):
            lines.append(f"- Deviation from plan: {dev}")
        if e["round"].startswith("fix"):
            lines += ["", "This round fixes these project-review findings:"]
            lines += [finding_line(run.findings[f]) for f in fix_findings(run)]
        elif d.get("addresses"):
            lines += ["", "The coder says this checkpoint fixes these review findings. Check each "
                          "fix against the finding's scenario:"]
            lines += [finding_line(run.findings[f]) for f in d["addresses"]]
        return lines + [""]
    if t == "response":
        rnd = run.items[e["items"][0]]["round"]
        lines = ["Decide on each critique: accept, partial or reject, with your rationale for "
                 "partial or reject.", ""] + [item_line(run.items[i], False) for i in e["items"]] + [""]
        if rnd.startswith("cp"):
            lines += ["If you accept every blocking critique, record the response and keep "
                      "working to your next checkpoint in the same turn (a list of two turns). "
                      "If you reject or partly accept a blocking critique, stop after the "
                      "response: the critic gets a last word first.", ""]
        elif rnd != "plan":
            lines += ["If you change code for what you accept, record the response and then a "
                      "new checkpoint in the same turn; the critic reviews it before the pull "
                      "request. If you reject or partly accept a blocking critique, stop after "
                      "the response.", ""]
        return lines
    if t == "final_call":
        return (["The critic kept these after your decision. Make the final call on each, "
                 "with your rationale.", ""] + [item_line(run.items[i]) for i in e["items"]] + [""])
    if t == "rebuttal":
        return (["The coder did not fully accept these. Give your last word on each: withdraw, "
                 "maintain or amend (with an amended suggestion), with your argument. This is "
                 "your only rebuttal. A blocking critique you maintain or amend goes to the "
                 "lead; any other goes back to the coder.", ""]
                + [item_line(run.items[i]) for i in e["items"]] + [""])
    if t == "checkpoint":
        if e["round"].startswith("fix") and e.get("why", "").startswith("fix"):
            return (["Fix these blocking project-review findings, commit, and record a checkpoint. "
                     "Change nothing else.", ""] + [finding_line(run.findings[f]) for f in fix_findings(run)]
                    + [""])
        if e.get("why", "").startswith("only if"):
            return ["If you changed code since the critic's last review, commit it and record a "
                    "checkpoint so the critic reviews it.", ""]
        lines = ["Build to your next checkpoint: commit, run the relevant tests, and record a "
                 "checkpoint with what you did, the test counts and any deviation from the plan. "
                 "Mark the last checkpoint before the pull request with \"final\": true.", ""]
        return lines + findings_to_fix(run, role, full=False)
    if t == "pr":
        if e.get("update"):
            return ["Push the reviewed fix commits to the pull request branch and record a pr "
                    "turn with \"update\": true.", ""]
        existing = run.brief.get("pull_request")
        if existing:
            return [f"Pull request {pr_name(existing)} already exists. Push the branch to it "
                    "without force. Do not open another pull request, and leave its draft or "
                    "ready state as it is. Bring its description, base and labels up to date "
                    "where the brief asks for that, then record a pr turn with its URL"
                    + (" and number." if existing.get("number") else "."), ""]
        return ["Push the branch and open the pull request as a draft (unless the brief says "
                "otherwise); record a pr turn with its URL and number.", ""]
    return [t, ""]


def context_sections(run: Run, role: str, mine: List[Dict[str, Any]]) -> List[str]:
    """What a fresh worker needs besides the task: the plan, decisions, news."""
    out: List[str] = []
    asked = {i for e in mine for i in e.get("items", [])}
    settled = [i for i in run.items.values() if i["state"] in DONE and i["id"] not in asked]
    if role == "coder" and any(e["type"] in ("checkpoint", "pr") for e in mine):
        plan = next((x for x in reversed(run.events) if x["type"] == "plan"), None)
        if plan and any(e["type"] == "checkpoint" for e in mine):
            # The coder wrote the plan; point to it instead of repeating it every turn.
            d = plan["data"]
            full = d.get("plan_file") or f"turns/{plan['seq']:04d}-coder-plan.json"
            out += ["## The plan", "", f"Your plan is in `{run.dir / full}`.", "",
                    "Planned checkpoints:"] + [f"- {c}" for c in d["checkpoints"]] + [""]
            out += ["Recorded so far:"]
            out += [f"- {round_label(c['round'])}: {c['data']['title']}"
                    for c in run.checkpoints] or ["- none yet"]
            out.append("")
        last = run.last_review_items()
        to_apply = [run.items[i] for i in last if run.items[i]["state"] in ("accepted", "partial")]
        if to_apply:
            out += ["## Apply what was accepted in the last review", ""]
            out += [item_line(i) for i in to_apply] + [""]
            settled = [i for i in settled if i["id"] not in last]
    news_kinds = ("response", "final_call", "intervention") if role == "critic" \
        else ("review", "rebuttal", "intervention")
    seen = max([e["seq"] for e in run.events if e["actor"] == role] or [0])
    news = [e for e in run.events if e["seq"] > seen and e["type"] in news_kinds]
    if news:
        out += ["## Since your last turn", ""]
        for e in news:
            out += news_lines(e)
        out.append("")
    if settled and role == "critic":
        out += ["## Settled critiques (do not raise again without new evidence)", ""]
        out += [settled_line(i) for i in settled] + [""]
    elif settled:
        # The coder decided these itself; the count and the command are enough.
        out += ["## Settled critiques", "",
                f"{len(settled)} settled ({span([i['id'] for i in settled])}). Their text is in "
                f"the critic's review files in `{run.dir / 'turns'}`.", ""]
    return out


def plan_lines(run: Run, d: Dict[str, Any], short: bool = False) -> List[str]:
    lines = [f"Summary: {d['summary']}", ""]
    if d.get("plan_file"):
        lines += [f"Full plan: `{run.dir / d['plan_file']}`", ""]
    lines += ["Units:"] + [f"- `{u['name']}` — {u['purpose']}" for u in d["units"]] + [""]
    if not short:
        lines += ["How the plan handles each lens:"]
        lines += [f"- {LENS_LABELS[k]}: {v}" for k, v in d["lenses"].items()] + [""]
    lines += ["Planned checkpoints:"] + [f"- {c}" for c in d["checkpoints"]] + [""]
    return lines


def findings_to_fix(run: Run, role: str, full: bool) -> List[str]:
    """The findings of a review that ran before this run, which the run is to fix."""
    prior = [f for f in run.findings.values() if f.get("stage") == "before_run"]
    if not prior:
        return []
    review = run.review_at("before_run") or {}
    todo = [f for f in prior if not f.get("addressed_in")]
    lines = ["## Review findings this run fixes", ""]
    if review.get("report_file"):
        lines += [f"The review's report: `{run.dir / review['report_file']}`.", ""]
    if full:
        lines += [finding_line(f) for f in prior] + [""]
    else:
        done = [f["id"] for f in prior if f.get("addressed_in")]
        lines += [f"No checkpoint has named these yet: {', '.join(f['id'] for f in todo) or 'none'}."
                  + (f" Named so far: {span(done)}." if done else ""), ""]
        lines += [f"- {f['id']} {f['title']}" for f in todo] + ([""] if todo else [])
    if role == "coder":
        lines += ["In each checkpoint turn, list the findings it fixes in \"addresses\" "
                  "(for example [\"F2\", \"F3\"]); the critic checks each fix against the "
                  "finding.", ""]
    return lines


def repo_path(run: Run) -> str:
    return run.brief["repo"]["path"]


def fix_findings(run: Run) -> List[str]:
    return [fid for fid, f in run.findings.items() if f.get("fix_round") == run.fix_rounds]


def tests_text(tests: Dict[str, Any]) -> str:
    if "not_run" in tests:
        return f"not run ({tests['not_run']})"
    text = f"{tests['passed']} passed, {tests['failed']} failed"
    if tests.get("command"):
        text += f" (`{tests['command']}`)"
    return text


def finding_line(f: Dict[str, Any]) -> str:
    ref = f" ({f['ref']})" if f.get("ref") else ""
    line = f"- **{f['id']}**{ref} [{f['severity'].replace('_', ' ')} · {f['confidence']}] {f['title']}"
    if f.get("where"):
        line += f" (at `{f['where']}`)"
    for key in ("scenario", "direction"):
        if f.get(key):
            line += f"\n  {key.capitalize()}: {f[key]}"
    return line


def news_lines(e: Dict[str, Any]) -> List[str]:
    d = e["data"]
    if e["type"] in ("response", "final_call"):
        word = "Coder" if e["type"] == "response" else "Coder's final call"
        return [f"- {word} on {x['item']}: {x['decision']}"
                + (f" — {x['rationale']}" if x.get("rationale") else "") for x in d["decisions"]]
    if e["type"] == "rebuttal":
        return [f"- Critic's last word on {p['item']}: {p['position']}"
                + (f" — {p['argument']}" if p.get("argument") else "")
                + (f" Amended: {p['amended_suggestion']}" if p.get("amended_suggestion") else "")
                for p in d["positions"]]
    if e["type"] == "intervention":
        lines = [f"- Lead stepped in ({d['reason'].replace('_', ' ')}): {d['summary']}"]
        lines += [f"  Ruling on {r['item']}: {r['decision']} — {r['rationale']}" for r in d["rulings"]]
        lines += [f"  - {a}" for a in d.get("actions", [])]
        return lines
    if e["type"] == "review":
        ids = [i["id"] for i in d["items"]]
        return [f"- Critic's review of {e['round']}: {d['summary']}"
                + (f" (critiques {span(ids)})" if ids else " (no critiques)")]
    return []


def cmd_show(args: argparse.Namespace) -> None:
    run = Run(Path(args.run_dir))
    if args.item:
        item = run.items.get(args.item)
        if not item:
            raise CctError(f"no item {args.item}")
        print(item_line(item))
        print(f"  State: {item['state']} (raised in {item['round']})")
    elif args.event:
        event = next((e for e in run.events if e["seq"] == args.event), None)
        if not event:
            raise CctError(f"no event #{args.event}")
        print(json.dumps(event, indent=2, ensure_ascii=False))
    else:
        for item in run.items.values():
            print(f"{item['id']} {item['round']:<8} {item['severity']:<10} {item['state']:<20} {item['title']}")


# --------------------------------------------------------------------- stats

def cmd_stats(args: argparse.Namespace) -> None:
    run = Run(Path(args.run_dir))
    stats = compute_stats(run)
    out = Path(args.out) if args.out else run.dir / "stats.json"
    out.write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    for warning in stats["warnings"]:
        print(f"Warning: {warning}")


def compute_stats(run: Run) -> Dict[str, Any]:
    brief, events = run.brief, run.events
    t0, t_end = events[0]["ts"], events[-1]["ts"]
    rel = lambda ts: minutes_between(t0, ts)  # noqa: E731
    warnings: List[str] = []
    repo = brief["repo"]
    head = (run.pr or {}).get("head_sha") or git(repo["path"], "rev-parse", "--verify", "--quiet",
                                                 repo["branch"], check=False)
    files: List[Dict[str, Any]] = []
    commits = 0
    if head:
        files = numstat(repo["path"], f"{repo['base_sha']}...{head}")
        commits = int(git(repo["path"], "rev-list", "--count", f"{repo['base_sha']}..{head}") or 0)
        reviewed = run.reviewed_head()
        if reviewed and reviewed != head:
            extra = git(repo["path"], "rev-list", "--count", f"{reviewed}..{head}", check=False)
            warnings.append(f"{extra or 'some'} commit(s) on the branch came after the critic's last review")
        elif not reviewed and commits:
            warnings.append("the critic reviewed none of the branch's commits")
    else:
        warnings.append("the work branch was not found, so the diff is empty")
    by_kind: Dict[str, Dict[str, int]] = {}
    for f in files:
        k = by_kind.setdefault(f["kind"], {"adds": 0, "dels": 0, "files": 0})
        k["adds"] += f["adds"]
        k["dels"] += f["dels"]
        k["files"] += 1

    items = list(run.items.values())
    final_of = lambda i: i["state"] if i["state"] in DONE else "open"  # noqa: E731
    by_decision = {k: 0 for k in ("accepted", "partial", "rejected", "withdrawn", "open")}
    by_severity = {s: 0 for s in SEVERITIES}
    lenses = CORE_LENSES + [l for l in EXTRA_LENSES if l in brief.get("extra_lenses", [])
                            or any(i["lens"] == l for i in items)]
    by_lens = {l: {k: 0 for k in by_decision} for l in lenses}
    for i in items:
        by_decision[final_of(i)] += 1
        by_severity[i["severity"]] += 1
        by_lens[i["lens"]][final_of(i)] += 1
    if by_decision["open"]:
        warnings.append(f"{by_decision['open']} critique(s) were never settled")

    rounds_out = []
    for rnd in run.rounds:
        evs = [e for e in events if e["seq"] in rnd["events"]]
        cp = next((e for e in evs if e["type"] == "checkpoint"), None)
        plan = next((e for e in evs if e["type"] == "plan"), None)
        review = next((e for e in evs if e["type"] == "review"), None)
        prev_ts = next(e["ts"] for e in reversed(events) if e["seq"] < evs[0]["seq"])
        coder = None
        if plan:
            coder = {"kind": "plan", "summary": plan["data"]["summary"],
                     "units": [u["name"] for u in plan["data"]["units"]],
                     "checkpoints": plan["data"]["checkpoints"]}
        elif cp:
            coder = {"kind": "checkpoint", "title": cp["data"]["title"], "notes": cp["data"]["notes"],
                     "tests": cp["data"]["tests"], "deviations": cp["data"]["deviations"],
                     "addresses": cp["data"].get("addresses", []), "git": cp["data"]["git"]}
        rounds_out.append({
            "key": rnd["key"], "label": round_label(rnd["key"]),
            "start_min": rel(prev_ts), "end_min": rel(evs[-1]["ts"]),
            "coder": coder,
            "critic": {"summary": review["data"]["summary"], "items": rnd["items"]} if review else None,
            "rebuttals": sum(1 for e in evs if e["type"] == "rebuttal"),
            "interventions": [e["seq"] for e in evs if e["type"] == "intervention"],
        })

    item_list = []
    for i in items:
        entry = {k: i.get(k) for k in ("id", "round", "lens", "severity", "confidence", "title",
                                       "detail", "where", "suggestion", "rationale",
                                       "final_rationale", "reraises", "rebuttal", "ruling",
                                       "decided_by")}
        first = next((h for h in i["history"] if h["kind"] == "response"), None)
        entry["first_decision"] = first["decision"] if first else None
        entry["outcome"] = final_of(i)
        entry["matched_by_review"] = [f["id"] for f in run.findings.values()
                                      if f.get("matches_item") == i["id"]
                                      and f.get("stage") != "before_run"]
        entry["relates_to_findings"] = [f["id"] for f in run.findings.values()
                                        if f.get("matches_item") == i["id"]
                                        and f.get("stage") == "before_run"]
        item_list.append(entry)

    spans, marks = timeline(run, rel)
    last_cp = run.checkpoints[-1]["data"]["tests"] if run.checkpoints else None
    findings = [{k: v for k, v in f.items() if k not in ("update_seq", "rechecked")}
                for f in run.findings.values()]
    reviews_out = []
    for r in run.reviews:
        mine = [f for f in findings if f["stage"] == r["stage"]]
        reviews_out.append({
            **{k: v for k, v in r.items() if k not in ("findings", "seq")},
            "at_min": rel(next(e["ts"] for e in events if e["seq"] == r["seq"])),
            "findings": [f["id"] for f in mine],
            "by_severity": {s: sum(1 for f in mine if f["severity"] == s) for s in SEVERITIES},
            "by_status": {st: sum(1 for f in mine if f["status"] == st) for st in FINDING_STATUS},
        })
    if not run.reviews:
        warnings.append("project review has not been recorded")
    for r in run.reviews:
        if not r["ran"]:
            warnings.append(f"project review did not run: {r['reason']}")
    if run.undecided():
        warnings.append(f"finding(s) {', '.join(run.undecided())} have no follow-up recorded")
    if run.not_rechecked():
        warnings.append(f"finding(s) {span(run.not_rechecked())} from the earlier review were not "
                        "re-checked at the pull request's head")
    criteria = {c["id"]: c for c in (run.acceptance or {}).get("criteria", [])}
    acceptance = [{**c, **({k: criteria[c["id"]][k] for k in ("status", "evidence")}
                           if c["id"] in criteria else {"status": "unverified", "evidence": ""})}
                  for c in brief["acceptance_criteria"]]
    if not run.acceptance:
        warnings.append("acceptance criteria were not checked")

    return {
        "schema": SCHEMA,
        "generated_at": now_iso(),
        "run": {
            "title": brief["title"], "outcome": brief["outcome"],
            "context": brief.get("context") or {}, "non_goals": brief.get("non_goals", []),
            "repo": {k: repo.get(k) for k in ("name", "base", "branch", "base_sha")},
            "head_sha": head or None, "pr": run.pr, "status": (run.closed or {}).get("outcome", "in_progress"),
            "close_note": (run.closed or {}).get("note", ""),
            "started_at": t0, "ended_at": t_end, "elapsed_min": rel(t_end),
            "workers": brief["workers"], "events": len(events), "limits": run.limits,
        },
        "narrative": run.narrative or {"summary": "", "next_steps": []},
        "acceptance": acceptance,
        "counts": {
            "critic_turns": sum(1 for e in events if e["type"] in ("review", "rebuttal")),
            "reviews": sum(1 for e in events if e["type"] == "review"),
            "rebuttals": sum(1 for e in events if e["type"] == "rebuttal"),
            "checkpoints": len(run.checkpoints),
            "worker_turns": sum(1 for e in events if e["actor"] in ("coder", "critic")),
            "interventions": len(run.interventions),
            "fix_rounds": run.fix_rounds,
            "findings": len(findings),
            "findings_matched": sum(1 for f in findings if f.get("matches_item")),
        },
        "items": {
            "total": len(items), "by_decision": by_decision, "by_severity": by_severity,
            "by_lens": by_lens,
            "accepted_share": round(by_decision["accepted"] / len(items), 3) if items else None,
            "reraised": sum(1 for i in items if i.get("reraises")),
            "lead_rulings": sum(1 for i in items if i.get("decided_by") == "lead"),
        },
        "rounds": rounds_out,
        "item_list": item_list,
        "interventions": [{"seq": e["seq"], "at_min": rel(e["ts"]), "round": e.get("round"),
                           **e["data"]} for e in run.interventions],
        "timeline": {"total_min": rel(t_end), "spans": spans, "marks": marks,
                     "phases": phase_bands(run, rel)},
        "diff": {
            "adds": sum(f["adds"] for f in files), "dels": sum(f["dels"] for f in files),
            "files": len(files), "commits": commits, "by_kind": by_kind,
            "files_list": sorted(files, key=lambda f: -(f["adds"] + f["dels"])),
        },
        "tests": ({**last_cp, "reported_by": "coder"} if last_cp else None),
        "reviews": reviews_out,
        "findings": findings,
        "warnings": warnings,
    }


SPAN_WORDS = {"plan": "plan", "review": "review", "response": "response",
              "final_call": "final call", "rebuttal": "last word", "checkpoint": "checkpoint",
              "pr": "pull request", "intervention": "intervention", "review_result": "project review",
              "fix_request": "fix request", "finding_update": "re-check and follow-ups",
              "acceptance": "acceptance check", "narrative": "summary", "close": "close"}


def timeline(run: Run, rel) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Credit the time before each recorded turn to whoever produced it.

    The review lane is the project review itself. Re-checking findings and
    filing follow-ups is the lead's work, and so is everything else it records.
    A review from before the run took none of the run's time.
    """
    spans: List[Dict[str, Any]] = []
    marks: List[Dict[str, Any]] = []
    prev = run.events[0]["ts"]
    for e in run.events[1:]:
        before_run = e["type"] == "review_result" and e["data"].get("stage") == "before_run"
        if e["type"] in ("note", "limits") or before_run:
            continue
        ran = e["type"] == "review_result" and e["data"].get("ran")
        lane = "review" if ran else e["actor"]
        word = SPAN_WORDS.get(e["type"], e["type"])
        start, end = rel(prev), rel(e["ts"])
        if spans and spans[-1]["lane"] == lane and spans[-1]["end"] == start:
            spans[-1]["end"] = end
            if word not in spans[-1]["label"].split(", "):
                spans[-1]["label"] += f", {word}"
        else:
            spans.append({"lane": lane, "start": start, "end": end, "label": word})
        if e["type"] == "plan":
            marks.append({"at": end, "label": "plan"})
        elif e["type"] == "checkpoint":
            marks.append({"at": end, "label": e["round"]})
        elif e["type"] == "pr":
            marks.append({"at": end, "label": "push" if e["data"].get("update") else "PR"})
        elif e["type"] == "intervention":
            marks.append({"at": end, "label": "lead"})
        prev = e["ts"]
    return spans, marks


def phase_bands(run: Run, rel) -> List[Dict[str, Any]]:
    events = run.events
    end = rel(events[-1]["ts"])
    plan_end = max((rel(e["ts"]) for e in events if e.get("round") == "plan"), default=end)
    pr = next((e for e in events if e["type"] == "pr"), None)
    build_end = rel(pr["ts"]) if pr else end
    bands = [{"label": "Plan", "start": 0.0, "end": plan_end}]
    if build_end > plan_end:
        bands.append({"label": "Build", "start": plan_end, "end": build_end})
    if pr and end > build_end:
        # After the pull request the lead either reviews it or re-checks what an
        # earlier review found.
        recheck = run.review_at("before_run") and not run.review_at("after_pr")
        bands.append({"label": "Re-check" if recheck else "Review", "start": build_end, "end": end})
    return bands


# ---------------------------------------------------------------------- main

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="cct.py", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init", help="create a run folder and record the brief")
    p.add_argument("run_dir")
    p.add_argument("--brief", required=True)
    p.add_argument("--at", help=argparse.SUPPRESS)
    p.set_defaults(func=cmd_init)
    p = sub.add_parser("post", help="record one turn, or a list of turns, from a JSON file")
    p.add_argument("run_dir")
    p.add_argument("--actor", required=True, choices=["coder", "critic", "lead"],
                   help="who wrote the turn; a worker's file may hold only that worker's turns")
    p.add_argument("--file", required=True, help="turn JSON file, or - for stdin")
    p.add_argument("--at", help="record a past time (UTC ISO 8601) when importing a turn")
    p.set_defaults(func=cmd_post)
    p = sub.add_parser("state", help="whose turn it is, open items and stall signals")
    p.add_argument("run_dir")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_state)
    p = sub.add_parser("turn", help="write the brief for a worker's next turn and print the handoff")
    p.add_argument("run_dir")
    p.add_argument("--for", dest="for_", required=True, choices=["coder", "critic"])
    p.add_argument("--full", action="store_true",
                   help="print the whole brief instead of writing it to the run folder, for a "
                        "worker that cannot read the run folder")
    p.set_defaults(func=cmd_turn)
    p = sub.add_parser("show", help="print an item, an event or the item list")
    p.add_argument("run_dir")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--item")
    g.add_argument("--event", type=int)
    g.add_argument("--items", action="store_true")
    p.set_defaults(func=cmd_show)
    p = sub.add_parser("stats", help="compute report statistics from the ledger and git")
    p.add_argument("run_dir")
    p.add_argument("--out")
    p.set_defaults(func=cmd_stats)
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except CctError as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
