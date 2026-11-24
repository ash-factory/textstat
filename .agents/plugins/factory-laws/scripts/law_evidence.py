"""Read a law job's verdict for one pull request head and the current card."""

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from urllib.error import HTTPError

import card_labels

WORKFLOW = ".github/workflows/factory-laws.yml"
JOBS = ("acceptance", "mutants")
ANNOTATION = "Factory law evidence"
READ_ERRORS = (OSError, ValueError, KeyError, TypeError, RuntimeError, ImportError, AttributeError)


def checklist(body):
    lines = re.findall(r"^\s*- \[[ xX]\]\s+(?:(A\d+)[.:)]?\s+)?(.+)$", body or "", re.M)
    return [(number or f"A{i}", text) for i, (number, text) in enumerate(lines, 1)]


def card_digest(card):
    labels = {row["name"] if isinstance(row, dict) else row for row in card["labels"]}
    relevant = sorted(label for label in labels if label.startswith((card_labels.TYPE, card_labels.CHECK)))
    data = [card["number"], relevant, checklist(card.get("body"))]
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Result:
    verdict: str
    reason: str
    url: str = ""
    attempt: int | None = None


def canonical(run, sha):
    path = (run.get("path") or "").partition("@")[0]
    return run.get("head_sha") == sha and path == WORKFLOW and run.get("event") == "pull_request"


def _declarations(get, sha):
    try:
        content = get("GET", f"/contents/{WORKFLOW}?ref={sha}")
    except HTTPError as error:
        if error.code == 404:
            return None
        raise
    if (not isinstance(content, dict) or content.get("type") != "file"
            or content.get("encoding") != "base64" or not isinstance(content.get("content"), str)):
        raise ValueError("expected base64 workflow file")
    raw = base64.b64decode(content["content"].replace("\n", "").replace("\r", ""), validate=True)

    import yaml

    class UniqueKeysLoader(yaml.BaseLoader):
        def construct_mapping(self, node, deep=False):
            mapping = super().construct_mapping(node, deep=deep)
            if len(mapping) != len(node.value):
                raise ValueError("duplicate workflow mapping key")
            return mapping

    try:
        workflow = yaml.load(raw, Loader=UniqueKeysLoader)
    except yaml.YAMLError as error:
        raise ValueError("invalid workflow YAML") from error
    jobs = workflow.get("jobs") if isinstance(workflow, dict) else None
    if not isinstance(jobs, dict) or not all(isinstance(job, dict) for job in jobs.values()):
        raise ValueError("expected a workflow jobs mapping")
    return jobs.keys()


def _pages(get, path, key):
    rows = []
    sep = "&" if "?" in path else "?"
    for page in range(1, 101):
        answer = get("GET", f"{path}{sep}per_page=100&page={page}")
        batch, total = answer[key], answer["total_count"]
        if not isinstance(batch, list) or not isinstance(total, int):
            raise ValueError("expected paginated Actions results")
        rows.extend(batch)
        if len(rows) == total:
            return rows
        if len(rows) > total or len(batch) < 100:
            break
    raise ValueError("incomplete Actions results")


def _latest(runs, pr):
    candidates = []
    for run in runs:
        if not canonical(run, pr["head"]["sha"]):
            continue
        pulls = run.get("pull_requests") or []
        linked = any(p["number"] == pr["number"] for p in pulls)
        if linked or (not pulls and run.get("head_branch") in (None, pr["head"].get("ref"))):
            candidates.append((run, linked))
    return max(candidates, key=lambda pair: (pair[0].get("created_at") or "", pair[0]["id"]),
               default=(None, False))


def _job_result(name, digest, pull, run, job, annotations):
    attempt, run_url = run["run_attempt"], run.get("html_url") or ""
    if job is None:
        conclusion = run.get("conclusion") if run.get("status") == "completed" else None
        reason = (f"the workflow concluded {conclusion} without a job result" if conclusion else
                  "this run attempt has no job result yet")
        return Result("not proven", reason, run_url, attempt)
    url, conclusion = job.get("html_url") or run_url, job.get("conclusion") or ""
    if job.get("status") != "completed" or conclusion == "action_required":
        return Result("not proven", "the job is still waiting or running", url, attempt)
    if conclusion == "failure":
        return Result("failed", "the job concluded failure", url, attempt)
    if conclusion != "success":
        return Result("not proven", f"the job concluded {conclusion or 'without a verdict'}", url, attempt)
    try:
        check_url = job["check_run_url"]
        check_id = re.search(r"/check-runs/(\d+)$", check_url)
        if not check_id:
            raise ValueError("missing check run id")
        rows = annotations(f"/check-runs/{check_id[1]}/annotations")
        markers = {row["message"] for row in rows if row.get("title") == ANNOTATION}
    except READ_ERRORS as error:
        return Result("unreadable", f"could not read the job annotations ({_problem(error)})", url, attempt)
    if markers != {f"{name} pass {pull} {run['id']}/{attempt} {digest}"}:
        return Result("not proven", "the job has no matching verdict for the current card", url, attempt)
    return Result("proven", "the job evaluated the current card", url, attempt)


def _problem(error):
    return f"HTTP {error.code}" if isinstance(error, HTTPError) else type(error).__name__


def read(get, annotations, pr, card, requested, *, workflow_runs=None):
    """Return each requested check's verdict, reason, and evidence location. Reads only."""
    if not requested:
        return {}
    sha, pr_url = pr["head"]["sha"], pr.get("html_url") or ""
    try:
        declared = _declarations(get, sha)
    except READ_ERRORS as error:
        return {name: Result("unreadable", f"could not read {WORKFLOW} on {sha} ({_problem(error)})", pr_url)
                for name in requested}

    results = {name: Result("cannot run", f"{WORKFLOW} is missing on {sha}" if declared is None else
                            f"{WORKFLOW} has no {name} job on {sha}", pr_url)
               for name in requested if declared is None or name not in declared}
    remaining = set(requested) - results.keys()
    if not remaining:
        return results
    pending = Result("not proven", "no canonical workflow run for this pull request and head", pr_url)
    run_url = pr_url
    try:
        if workflow_runs is None:
            workflow_runs = _pages(get, f"/actions/runs?head_sha={sha}", "workflow_runs")
        # A run GitHub no longer links to the pull request (its association is emptied after the merge; #232's end
        # report, 24 Nov) is judged like a linked one: the job's marker names this pull request, run and attempt.
        run, _linked = _latest(workflow_runs, pr)
        if run is not None:
            run_url = run.get("html_url") or pr_url
            digest = card_digest(card)
            attempt = run["run_attempt"]
            if not isinstance(attempt, int) or attempt < 1:
                raise ValueError("missing workflow attempt")
            jobs = _pages(get, f"/actions/runs/{run['id']}/attempts/{attempt}/jobs", "jobs")
            current = {}
            for job in jobs:
                name = job["name"]
                if name not in remaining or job["run_id"] != run["id"] or job.get("run_attempt", attempt) != attempt:
                    continue
                if name in current:
                    raise ValueError("ambiguous law job")
                current[name] = job
            results.update({name: _job_result(name, digest, pr["number"], run, current.get(name), annotations)
                            for name in remaining})
            return results
    except READ_ERRORS as error:
        pending = Result("unreadable", f"could not read the current run and card evidence ({_problem(error)})", run_url)
    results.update(dict.fromkeys(remaining, pending))
    return results
