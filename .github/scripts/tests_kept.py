"""The check `tests-kept`: a pull request may not run a narrower suite than its base (design/test_integrity 3.2; P-46).

    python .github/scripts/tests_kept.py --base-dir <base checkout> --head-dir . --base <sha> --head <sha>
        --repo <owner/repo> [--card <n>]

It fails (exit 1) when, against the base:
- a test id of the base is missing at the head, or is newly marked skip, skipif or xfail;
- the suite's configuration narrows collection (a new `-k`, `-m`, `--deselect`, `--ignore` or `--ignore-glob` in
  `addopts`, or a new `collect_ignore` in a `conftest.py`);
unless the commit of the head that did it names an open `failure-seen` issue of that test (`Refs #<n>`), or the
card's type is `harness` and the card names the test (the planner's own decision to remove it).

Its message says what to do. It lists every changed test file in the job summary, for the reviewer (a loosened
assertion keeps its id and is the review's to judge). Exit 2: the check itself could not run (loud, not green).

The pure core is `judge(base, head, base_conf, head_conf, excused)`.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import card_labels

HERE = Path(__file__).resolve().parent
NARROW = re.compile(r"(?<![\w-])(-k|-m|--deselect|--ignore|--ignore-glob)(?=[\s=]|$)")
CONFIGS = ("pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini")
MARKER = "factory-test-failure id:"


# pytest's own order and test (its configuration docs): pytest.ini and .pytest.ini always count; the others only
# when they hold pytest's section
CONFIG_SECTIONS = (("pytest.ini", None), (".pytest.ini", None), ("pyproject.toml", "[tool.pytest"),
                   ("tox.ini", "[pytest]"), ("setup.cfg", "[tool:pytest]"))


def own_root(folder):
    """pytest's options that make `folder` its own root: the configuration file pytest itself would pick there, else
    none at all. pytest looks upward from its arguments, and --rootdir alone does not stop that (a base checked out
    inside the head's folder would run with the head's options)."""
    for name, section in CONFIG_SECTIONS:
        path = Path(folder) / name
        if path.is_file() and (section is None or section in path.read_text(errors="replace")):
            return [f"--rootdir={folder}", "-c", str(path)]
    return [f"--rootdir={folder}", "-c", os.devnull]


def collect(folder):
    """{test id: [marks]} of the suite in `folder`, read by the plugin `collect_marks`."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "marks.jsonl"
        env = {**{k: v for k, v in os.environ.items() if k not in ("GH_TOKEN", "GITHUB_TOKEN")},  # no token to Q's code
               "COLLECT_MARKS_OUT": str(out),
               "PYTHONPATH": os.pathsep.join(filter(None, [str(HERE), os.environ.get("PYTHONPATH")]))}
        done = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                               "-p", "collect_marks", *own_root(folder)], cwd=folder, env=env, capture_output=True, text=True, timeout=900)
        if not out.exists():
            raise RuntimeError(f"collection did not finish in {folder}: {(done.stdout + done.stderr)[-400:]}")
        rows = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
    return {r["id"]: r["marks"] for r in rows}


def configuration(folder):
    """The narrowing options of the suite's configuration and the conftest files that set collect_ignore."""
    found = set()
    for name in CONFIGS:
        path = Path(folder) / name
        if path.is_file():
            for line in path.read_text(errors="replace").splitlines():
                if "addopts" in line or line.startswith((" ", "\t", '"', "'")):
                    found |= {f"{name}: {m}" for m in NARROW.findall(line)}
    for path in Path(folder).rglob("conftest.py"):
        if ".git" in path.parts or "node_modules" in path.parts:
            continue
        if re.search(r"^\s*collect_ignore(_glob)?\s*[=+]", path.read_text(errors="replace"), re.M):
            found.add(f"{path.relative_to(folder)}: collect_ignore")
    return found


def judge(base, head, base_conf, head_conf, excused=frozenset()):
    """[problem lines]; empty when the suite is kept. `excused`: ids a named issue or a harness card allows."""
    problems = []
    for test, marks in sorted(base.items()):
        if test in excused:
            continue
        if test not in head:
            problems.append(f"removed: {test}")
        else:
            new = sorted(set(head[test]) - set(marks))
            if new:
                problems.append(f"newly {', '.join(new)}: {test}")
    if "*config*" not in excused:
        problems += [f"narrowed by configuration: {x}" for x in sorted(head_conf - base_conf)]
    return problems


def git(folder, *args):
    return subprocess.run(["git", *args], cwd=folder, capture_output=True, text=True, check=True).stdout


def named_issues(folder, base, head):
    """The issue numbers that a commit of base..head names with `Refs #<n>`, by the commit's message."""
    text = git(folder, "log", "--format=%B%x00", f"{base}..{head}")
    return {int(n) for n in re.findall(r"(?i)\bRefs:? *#(\d+)", text)}


def get(repo, path, token):
    request = urllib.request.Request(f"https://api.github.com/repos/{repo}{path}", headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "factory-tests-kept"})
    with urllib.request.urlopen(request, timeout=30) as answer:
        return json.loads(answer.read())


def excuses(issues, card, candidates):
    """The ids of `candidates` that are allowed: an open `failure-seen` issue of that id named by a commit, or a
    `harness` card that names the test. `issues`: [issue] named by the commits; `card`: the card or None."""
    allowed = set()
    for issue in issues:
        labels = {x["name"] for x in issue.get("labels", [])}
        first = (issue.get("body") or "").split("\n", 1)[0]
        if issue.get("state") == "open" and card_labels.FAILURE_SEEN in labels and first.startswith(MARKER):
            allowed.add(first[len(MARKER):].strip())
    if card and card_labels.TYPE + "harness" in {x["name"] for x in card.get("labels", [])}:
        text = f"{card.get('title') or ''}\n{card.get('body') or ''}"
        allowed |= {c for c in candidates if c in text}
        if "collect_ignore" in text or "addopts" in text:
            allowed.add("*config*")
    return allowed & (set(candidates) | {"*config*"})


def summary(lines):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as handle:
            handle.write("\n".join(lines) + "\n")


def main(argv):
    a = argparse.ArgumentParser()
    for flag in ("--base-dir", "--head-dir", "--base", "--head", "--repo"):
        a.add_argument(flag, required=True)
    a.add_argument("--card")
    args = a.parse_args(argv)
    try:
        base, head = collect(args.base_dir), collect(args.head_dir)
        base_conf, head_conf = configuration(args.base_dir), configuration(args.head_dir)
        problems = judge(base, head, base_conf, head_conf)
        if problems:
            token = os.environ.get("GH_TOKEN", "")
            issues = [get(args.repo, f"/issues/{n}", token) for n in sorted(named_issues(args.head_dir, args.base, args.head))]
            card = get(args.repo, f"/issues/{args.card}", token) if args.card else None
            problems = judge(base, head, base_conf, head_conf, excuses(issues, card, list(base)))
        changed = [p for p in git(args.head_dir, "diff", "--name-only", f"{args.base}...{args.head}").splitlines()
                   if re.search(r"(^|/)(tests?/|test_[^/]*\.py$|[^/]*_test\.py$|conftest\.py$)", p)]
    except Exception as error:  # noqa: BLE001 - the check could not run: red, never green
        print(f"::error::tests-kept could not run: {type(error).__name__}: {str(error)[:300]}")
        return 2
    summary(["### Changed test files (the reviewer judges each)"] + [f"- `{p}`" for p in changed or ["none"]])
    if problems:
        print("::error::A test was removed or skipped, or the suite was narrowed: " + "; ".join(problems[:20]))
        print("Fix the cause, or name the test's open failure-seen issue in the commit that skips it (Refs #<n>).")
        return 1
    print(f"The suite is kept: {len(head)} tests at the head, {len(base)} at the base.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
