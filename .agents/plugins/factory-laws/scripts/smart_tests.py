"""Trace acceptance lines to tests and run a bounded sample of changed-line mutations.

The input is a card as read by CI from its project. Everything executed belongs to a
read-only CI job. Mutations are applied only in disposable checkouts.
"""

import argparse
import ast
import difflib
import hashlib
from itertools import chain
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import card_labels
import law_evidence


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True, timeout=60).stdout


def _python_tests(text, number):
    def methods(node, prefix=""):
        for item in node.body:
            if isinstance(item, ast.ClassDef) and item.name.startswith("Test"):
                yield from methods(item, prefix + item.name + "::")
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) or not item.name.startswith("test"):
                continue
            labels = set()
            for d in item.decorator_list:
                if isinstance(d, ast.Call) and ast.unparse(d.func) == "pytest.mark.acceptance" and len(d.args) == 2:
                    if all(isinstance(a, ast.Constant) for a in d.args) and d.args[0].value == f"#{number}":
                        labels.add(d.args[1].value)
            yield prefix + item.name, labels

    return dict(methods(ast.parse(text)))


def _rust_tests(text, number):
    entries = {}
    marks = set()
    test = False
    for line in text.splitlines():
        line = line.strip()
        marker = re.fullmatch(r"//\s*acceptance:\s*#(\d+)\s+(A[1-9]\d*)", line)
        if marker and int(marker[1]) == number:
            marks.add(marker[2])
        elif line.startswith("#[test]"):
            test = True
        elif line and not line.startswith(("#[", "//")):
            func = re.match(r"(?:pub\s+)?fn\s+(\w+)", line)
            if test and func:
                entries[func[1]] = marks
            marks, test = set(), False
    return entries


def _run(argv, cwd, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError
    env = {
        k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "LANG", "CARGO_HOME", "RUSTUP_HOME", "TMPDIR", "SYSTEMROOT"}
    }
    env.update(PYTHONDONTWRITEBYTECODE="1", CARGO_NET_OFFLINE="true")
    with subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        text=True,
        errors="replace",
    ) as child:
        try:
            output, _ = child.communicate(timeout=remaining)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.communicate()
            raise TimeoutError from None
        return child.returncode, output


def _rust_verdict(root, path, name, deadline):
    code, log = _run(["cargo", "test", "--offline", "--no-run", "--message-format=json"], root, deadline)
    if code:
        return 2
    binaries = []
    for line in log.splitlines():
        if not line.startswith("{"):
            continue
        artifact = json.loads(line)
        if not artifact.get("profile", {}).get("test") or not artifact.get("executable"):
            continue
        src = Path(artifact["target"]["src_path"])
        binaries.append((src, artifact["executable"]))
    file = (root / path).resolve()
    direct = [exe for src, exe in binaries if src == file]
    candidates = []
    for exe in direct or [exe for src, exe in binaries if src.parent in file.parents]:
        code, listing = _run([exe, "--list"], root, deadline)
        if code:
            return 2
        for case in listing.splitlines():
            if case.endswith(": test"):
                qualified = case.removesuffix(": test")
                if qualified == name or qualified.endswith("::" + name):
                    candidates.append((exe, qualified))
    if len(candidates) != 1:
        return 2
    exe, qualified = candidates[0]
    code, log = _run([exe, "--exact", qualified], root, deadline)
    if code == 0 and re.search(r"test result: ok\. 1 passed; 0 failed; 0 ignored;", log):
        return 0
    if code and re.search(r"test result: FAILED\. 0 passed; 1 failed; 0 ignored;", log):
        return 101
    return 2


def _test(root, path, name, deadline):
    if path.suffix == ".rs":
        return _rust_verdict(root, path, name, deadline)
    code, log = _run([sys.executable, "-m", "pytest", "-q", f"{path}::{name}"], root, deadline)
    if code == 0 and not re.search(r"\b[1-9]\d* passed\b", log):
        return 2
    return code


def acceptance(root, base, card):
    root = Path(root)
    # Older cards were created before numbering. Their checklist order supplies the labels.
    lines = law_evidence.checklist(card.get("body"))
    needed = dict(lines)
    if len(needed) != len(lines) or not lines:
        return [f"#{card['number']} has an empty or ambiguous checklist. Fix: number each acceptance line once."]
    deadline = time.monotonic() + 600
    covered = set()
    with tempfile.TemporaryDirectory(prefix="acceptance-base-") as temp:
        before = None
        for candidate in git(root, "ls-files", "-co", "--exclude-standard", "-z").split("\0"):
            p = Path(candidate)
            if not candidate or p.suffix not in (".rs", ".py") or not (root / p).is_file() or (root / p).is_symlink():
                continue
            if p.suffix == ".py" and not (p.name.startswith("test_") or p.stem.endswith("_test")):
                continue
            parse = _rust_tests if p.suffix == ".rs" else _python_tests
            texts = (root / p).read_text()
            tests = parse(texts, card["number"])
            if not any(tests.values()):
                continue
            old = subprocess.run(["git", "show", f"{base}:{candidate}"], cwd=root, capture_output=True, text=True)
            original = parse(old.stdout, card["number"]) if not old.returncode else {}
            for name, labels in tests.items():
                if not labels - covered or _test(root, p, name, deadline) != 0:
                    continue
                if name in original:
                    if before is None:
                        before = Path(temp) / "before"
                        git(root, "clone", "--quiet", "--no-hardlinks", "--no-checkout", str(root.resolve()), str(before))
                        git(before, "checkout", "--quiet", "--detach", base)
                    dest = before / p
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(texts)
                    status = _test(before, p, name, deadline)
                    git(before, "restore", "--", candidate)
                    if status != (101 if p.suffix == ".rs" else 1):
                        continue
                covered.update(labels)
    return [
        f"Acceptance line {line} of #{card['number']} ({msg}) has no passing regression test. "
        f"Fix: mark a new test or one that fails on the base with #{card['number']} {line}."
        for line, msg in needed.items()
        if line not in covered
    ]


def _changed(root, base):
    paths = {}
    for rel in git(root, "diff", "--name-only", "--diff-filter=AMR", "-z", base, "HEAD").split("\0"):
        p = Path(rel)
        if p.suffix not in (".py", ".rs") or "tests" in p.parts or p.name.startswith("test_") or p.name == "tests.rs":
            continue
        if rel.startswith((".github/", ".agents/")) or not (root / p).is_file() or (root / p).is_symlink():
            continue
        patch = git(root, "diff", "--unified=0", base, "HEAD", "--", rel)
        lines = set()
        for match in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", patch, re.M):
            start = int(match[1])
            lines.update(range(start, start + int(match[2] or 1)))
        if lines:
            paths[rel] = lines
    return paths


def _python_mutants(root, paths):
    from mutmut.mutation.file_mutation import create_mutations

    for rel, lines in paths.items():
        if not rel.endswith(".py"):
            continue
        old = (root / rel).read_text()
        module, mutations, _, _ = create_mutations(rel, old, covered_lines=lines)
        for change in mutations:
            new = module.deep_replace(change.original_node, change.mutated_node).code
            if new == old:
                continue
            diff = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), "a/" + rel, "b/" + rel))
            yield rel, diff


def _rust_mutants(root, paths, base, deadline):
    patch = root / ".mutants-changed.diff"
    patch.write_text(git(root, "diff", base, "HEAD", "--", "*.rs"))
    code, out = _run(["cargo", "mutants", "--list", "--json", "--diff", "--in-diff", str(patch)], root, deadline)
    if code:
        raise ValueError("cargo-mutants could not enumerate the changed Rust lines")
    for mutant in json.loads(out):
        if mutant["file"] in paths:
            rel = mutant["file"]
            before, after, hunk = mutant["diff"].split("\n", 2)
            if before != "--- " + rel or not after.startswith("+++ ") or not hunk.startswith("@@ "):
                raise ValueError("unexpected cargo-mutants diff")
            yield rel, f"--- a/{rel}\n+++ b/{rel}\n{hunk}"


def mutations(root, base, *, limit=20, seconds=600):
    """Return counts, stable mutant fingerprints and diagnostics. No modification to the checkout."""
    root = Path(root).resolve()
    deadline = time.monotonic() + seconds
    result = {"tested": 0, "survivors": [], "errors": [], "killed": []}
    with tempfile.TemporaryDirectory(prefix="factory-mutants-") as temp:
        work = Path(temp) / "project"
        git(root, "clone", "--no-hardlinks", "--quiet", str(root), str(work))
        sha = git(root, "rev-parse", "HEAD").strip()
        base = git(root, "rev-parse", "--verify", base + "^{commit}").strip()
        git(work, "checkout", "--quiet", "--detach", sha)
        paths = _changed(work, base)
        if not paths and not (work / "tests/mutants/known.json").is_file():
            return result
        rust = (work / "Cargo.toml").is_file()
        argv = ["cargo", "test", "--offline"] if rust else [sys.executable, "-m", "pytest", "-q"]
        if _run(argv, work, deadline)[0]:
            raise ValueError("the unmodified head's tests failed")
        known_path = work / "tests/mutants/known.json"
        known = json.loads(known_path.read_text()) if known_path.exists() else []
        candidates = _rust_mutants(work, paths, base, deadline) if rust else _python_mutants(work, paths)
        previous = Path.cwd()
        try:
            # mutmut reads the project's configuration from its working directory.
            os.chdir(work)
            for rel, diff in chain(((k["file"], k["diff"]) for k in known), candidates):
                if result["tested"] >= min(20, limit):
                    break
                identity = hashlib.sha256(diff.encode()).hexdigest()[:16]
                if identity in result["killed"] or any(s["id"] == identity for s in result["survivors"]):
                    continue
                # git apply checks paths. A replay may write only its named ordinary source.
                if not re.fullmatch(r"[\w./-]+\.(?:py|rs)", rel) or ".." in Path(rel).parts or rel.startswith("/"):
                    raise ValueError("invalid mutant source")
                if any(
                    line.startswith(("rename ", "copy ", "new file ", "deleted file ", "old mode ", "new mode ", "diff --git"))
                    for line in diff.splitlines()
                ):
                    raise ValueError("invalid mutation patch")
                headers = [line for line in diff.splitlines() if line.startswith(("--- ", "+++ "))]
                if headers != ["--- a/" + rel, "+++ b/" + rel]:
                    raise ValueError("mutation patch needs one source file")
                proc = subprocess.run(
                    ["git", "apply", "--unidiff-zero", "-"], input=diff, text=True, capture_output=True, cwd=work
                )
                if proc.returncode:
                    raise ValueError("a saved mutation no longer applies; update its replay")
                try:
                    status, output = _run(argv, work, deadline)
                    if status == 0:
                        result["survivors"].append({"file": rel, "id": identity, "diff": diff})
                    elif (not rust and status == 1 and re.search(r"\b[1-9]\d* failed", output)) or (
                        rust and "test result: FAILED" in output
                    ):
                        result["killed"].append(identity)
                    else:
                        result["errors"].append(f"{rel} {identity} could not run to a test verdict")
                    result["tested"] += 1
                finally:
                    git(work, "restore", "--", rel)
        finally:
            os.chdir(previous)
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("job", choices=("acceptance", "mutants"))
    p.add_argument("--base", required=True)
    p.add_argument("--card", required=True, type=Path)
    a = p.parse_args(argv)
    card = json.loads(a.card.read_text())
    kinds = {v["name"] if isinstance(v, dict) else v for v in card.get("labels", [])}
    types = {k.removeprefix(card_labels.TYPE) for k in kinds if k.startswith(card_labels.TYPE)}
    if card.get("number") and len(types) != 1:
        print("The card needs exactly one work type. Fix: correct its type before running the checks.")
        return 1
    required = bool(types & ({"slice", "bug", "module"} if a.job == "acceptance" else {"module"})) or card_labels.CHECK + a.job in kinds
    if not required and (a.job == "acceptance" or not card.get("number")):
        print("This check is not required for this card.")
        return 0
    try:
        if a.job == "acceptance":
            errors = acceptance(Path.cwd(), a.base, card)
        else:
            result = mutations(Path.cwd(), a.base)
            print(json.dumps(result))
            errors = [
                f"test-weak: {m['file']} {m['id']} survived. Fix: strengthen the test and replay this mutant."
                for m in result["survivors"]
            ] + result["errors"]
    except (ValueError, OSError, KeyError, SyntaxError, TimeoutError, subprocess.SubprocessError) as e:
        errors = [f"{a.job} could not finish ({type(e).__name__}). Fix: check its dependency, source and ten-minute budget."]
    else:
        pull = os.getenv("FACTORY_PULL_REQUEST", "")
        run_id, attempt = os.getenv("GITHUB_RUN_ID", ""), os.getenv("GITHUB_RUN_ATTEMPT", "")
        if required and card.get("number") and all(value.isdecimal() for value in (pull, run_id, attempt)):
            outcome = "fail" if errors else "pass"
            print(f"::notice file=.agents/plugins/factory-laws/scripts/smart_tests.py,line=1,title={law_evidence.ANNOTATION}"
                  f"::{a.job} {outcome} {pull} {run_id}/{attempt} {law_evidence.card_digest(card)}")
    for error in errors:
        print(error)
    return int(required and bool(errors))


if __name__ == "__main__":
    sys.exit(main())
