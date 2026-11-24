"""Run the project's rules, learned-pattern limits, feature map and learn-PR checks."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def _rules(root):
    agents = root / "AGENTS.md"
    jobs = set()
    for f in (root / ".github/workflows").glob("*"):
        if f.suffix not in (".yml",".yaml"):
            continue
        group = False
        for line in f.read_text().splitlines():
            if line and not line[0].isspace() and not line.startswith("#"):
                group = line.strip() == "jobs:"
            if group and (match := re.fullmatch(r"  ([\w-]+):\s*(?:#.*)?",line)):
                jobs.add(match[1])
    inside, count, bad_rows = False, 0, False
    for line in agents.read_text().splitlines() if agents.is_file() else []:
        if not line.strip().startswith("|"):
            inside = False
            continue
        fields = [v.strip().strip("`") for v in line.strip()[1:].removesuffix("|").split("|")]
        if fields == ["Rule","Check or judgement"]:
            inside = True
        elif inside and (len(fields) != 2 or not fields[0]):
            bad_rows = True
            yield f"{fields[0]} has no unambiguous check or judgement. Fix: supply one rule and one carrier cell."
        elif inside and not re.fullmatch(r":?-{3,}:?", fields[0]):
            rule, carrier = fields
            count += 1
            if not (carrier in jobs or re.fullmatch(r"judgement:\s*\S.+", carrier, re.I)):
                yield f"{rule} names {carrier or 'no check'}. Fix: name a CI job or explain the judgement."
    if count == 0 and not bad_rows:
        yield "The project's rules table is missing or malformed. Fix: add the Rule and Check or judgement columns to AGENTS.md."


def _learn(body):
    if not re.search(r"^Learn:\s*(?:[\w.-]+/[\w.-]+)?#\d+\s*$", body, re.M | re.I):
        return
    match = re.search(r"^Layer:\s*(structure|check|test|verification|text)\s*$", body, re.M | re.I)
    if not match:
        yield "The learn change has no Layer. Fix: name the structure, check, test, verification or text that changes."
    elif match[1].lower() == "text" and not re.search(r"^Why-not-a-check:\s*\S.+$", body, re.M | re.I):
        yield "Layer text needs Why-not-a-check. Fix: explain why a check cannot enforce this lesson."


def _inside(root, name):
    path = (root / name).resolve()
    if root.resolve() not in path.parents:
        raise ValueError("the check's path must be inside this repository")
    return path


def _limits(root, base):
    config = ".github/factory-baseline.json"
    current = json.loads((root / config).read_text())["rules"]
    previous = {}
    if base:
        old = subprocess.run(["git", "show", f"{base}:{config}"], cwd=root, capture_output=True, text=True)
        if old.returncode == 0:
            previous = {r["id"]: r for r in json.loads(old.stdout)["rules"]}
    for rule in current:
        old = previous.pop(rule["id"], None)
        if old and (rule["count"] > old["count"] or (old["glob"], old["pattern"]) != (rule["glob"], rule["pattern"])):
            yield f"Limit {rule['id']} was loosened. Fix: preserve its pattern and lower its count as cases are removed."
        regex = re.compile(rule["pattern"])
        count = sum(
            len(regex.findall(_inside(root, f.relative_to(root)).read_text())) for f in root.glob(rule["glob"]) if f.is_file()
        )
        if base and count < rule["count"]:
            yield f"{rule['id']} is down to {count} cases. Fix: lower the stored limit to {count} in this change."
        if count > rule["count"]:
            yield f"{rule['id']} allows {rule['count']} cases and found {count}. Fix: remove the extra cases."
    for key in previous:
        yield f"The learned check {key} disappeared. Fix: keep its limit at zero after the last case is removed."


def _features(root):
    tested = set()
    for f in root.glob(".agents/skills/verify-*/features/*.md"):
        if f.name == "README.md" or f.name.startswith("_"):
            continue
        for field in ("Driver", "Driver-test"):
            matches = re.findall(rf"^{field}:\s*`?([^\s`]+)`?\s*$", f.read_text(), re.M)
            if len(matches) != 1 or not _inside(root, matches[0]).is_file():
                yield f"{f.name} has no usable {field} ({', '.join(matches)}). Fix: name the driver and its executable test."
            elif field == "Driver-test" and matches[0] not in tested:
                path = matches[0]
                if path.endswith(".py"):
                    run = subprocess.run(
                        [sys.executable, "-m", "pytest", "-q", path], cwd=root, capture_output=True, text=True, timeout=120
                    )
                    if run.returncode or not re.search(r"\b[1-9]\d* passed", run.stdout):
                        yield f"{f.name} driver test {path} did not pass. Fix: repair the driver or its test."
                else:
                    yield f"{f.name} has an unsupported driver test {path}. Fix: name a pytest driver contract."
                tested.add(path)


def diagnostic(check_id, status, output):
    if status and not re.search(r"Fix:\s*\S", output):
        return [f"{check_id} failed without a repair instruction. Fix: add a specific Fix: line to its diagnostic."]
    return []


def check(root, name, body="", base=None):
    root = Path(root)
    try:
        if name == "learn-layer":
            return list(_learn(body))
        if name == "rules-table":
            return list(_rules(root))
        if name == "ratchet":
            return list(_limits(root, base))
        if name == "feature-map":
            return list(_features(root))
        raise ValueError("unknown project check")
    except (OSError, ValueError, KeyError, TypeError, re.error, subprocess.TimeoutExpired) as error:
        return [f"{name} could not read its source ({error}). Fix: repair the named project file."]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", choices=["rules-table", "learn-layer", "ratchet", "feature-map"])
    parser.add_argument("--base")
    parser.add_argument("--event", type=Path)
    args = parser.parse_args()
    event = json.loads(args.event.read_text()) if args.event else {}
    errors = check(Path.cwd(), args.name, (event.get("pull_request") or {}).get("body") or "", args.base)
    for error in errors:
        print(error)
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
