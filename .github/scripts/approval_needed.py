"""Verify the door's SSH signature on every commit in a sensitive pull request.

Only base-branch policy and public signers are trusted. The candidate is read as Git objects.
"""

import argparse
import fnmatch
import json
import re
import subprocess
import tempfile
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}")
TRUST = ("manual/class.json", "machine/door_allowed_signers", "tools/approval_needed.py", ".github/workflows/*")


def _git(repo, *args, check=True):
    return subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "-C", str(repo), *args],
        check=check,
        capture_output=True,
        timeout=30,
    )


def _keys(old, new, path=()):
    def children(value):
        if isinstance(value,dict):
            return value
        return dict(enumerate(value)) if isinstance(value,list) else {}

    if type(old) is type(new) and old == new:
        return
    if type(old) is not type(new) or not isinstance(old,(list,dict)):
        yield path
    left,right=children(old),children(new)
    absent=object()
    for key in left.keys() | right.keys():
        yield from _keys(left.get(key,absent),right.get(key,absent),(*path,str(key)))


def _protected(repo, file, relative, before, after, rules, *, conflicted=False):
    if any(fnmatch.fnmatchcase(relative, p) for p in rules if "#" not in p):
        return True
    qualified = [p.partition("#")[2] for p in rules if "#" in p and fnmatch.fnmatchcase(relative, p.partition("#")[0])]
    if not qualified:
        return False
    if conflicted or not file.endswith(".json"):
        return True

    def read(rev):
        result = _git(repo, "show", rev + ":" + file, check=False)
        return json.loads(result.stdout) if not result.returncode else None

    for keys in _keys(read(before), read(after)):
        k = "/".join(keys)
        if any(
            not k
            or fnmatch.fnmatchcase(k, rule)
            or fnmatch.fnmatchcase(k, rule.removesuffix("/**"))
            or fnmatch.fnmatchcase(rule.split("*")[0], k + "/*")
            for rule in qualified
        ):
            return True
    return False


def _merge_baseline(repo, parents):
    """Return Git's automatic merge tree and paths that required a resolution."""
    left, *remaining = parents
    conflicts = set()
    for index, right in enumerate(remaining):
        result = _git(repo, "merge-tree", "--write-tree", "--name-only", "--no-messages", "-z", left, right, check=False)
        if result.returncode not in (0, 1):
            result.check_returncode()
        tree, *paths = result.stdout.decode().split("\0")
        if not SHA.fullmatch(tree):
            raise ValueError("Invalid automatic merge tree")
        conflicts.update(filter(None, paths))
        if index == len(remaining) - 1:
            return tree, conflicts

        # Keep the merged ancestry when folding an octopus merge in parent order.
        left = _git(
            repo, "-c", "user.name=Factory", "-c", "user.email=factory@localhost",
            "commit-tree", "--no-gpg-sign", tree, "-p", left, "-p", right, "-m", "Automatic merge baseline",
        ).stdout.decode().strip()


def check(repo, base, head, *, prefix="", project=False):
    """Return a list of check failures without checking out either tree."""
    fix = "Fix: have Factory sign the entire approved change and reopen its reviewed pull request."
    if prefix not in ("", "OpenHands/factory/") or not all(SHA.fullmatch(r) for r in (base, head)):
        return ["Invalid repository revision. " + fix]
    try:
        policy_path = ".github/factory-approval.json" if project else "manual/class.json"
        signer_path = ".github/door_allowed_signers" if project else "machine/door_allowed_signers"
        policy = json.loads(_git(repo, "show", base + ":" + prefix + policy_path).stdout)
        if not isinstance(policy["sensitive"], list) or not policy["sensitive"]:
            return ["The base classification is incomplete. " + fix]
        rules = [rule for rule in policy["sensitive"] if isinstance(rule, str)]
        trust, exceptions = TRUST, ()
        if project:
            trust += (policy_path, signer_path, ".github/scripts/approval_needed.py")
            excluded = policy.get("sensitive_exceptions", [])
            if not isinstance(excluded, list):
                raise ValueError("Invalid sensitive exceptions")
            exceptions = tuple(re.compile(pattern) for pattern in excluded)
        commits = [line.split() for line in _git(
            repo, "rev-list", "--parents", "--max-count=1001", base + ".." + head,
        ).stdout.decode().splitlines()]
        if len(commits) > 1000:
            return ["The change exceeds 1000 commits. Fix: split the change for review."]
        common = _git(repo, "merge-base", base, head, check=False)
        if common.returncode == 1 or any(len(entry) == 1 for entry in commits):
            return ["The pull request has unrelated history. " + fix]
        common.check_returncode()

        def touches_sensitive(before, after, conflicts=frozenset()):
            changed = _git(repo, "diff", "--no-renames", "--name-only", "-z", before, after).stdout.decode().split("\0")
            for name in sorted((set(changed) | conflicts) - {""}):
                if prefix and not name.startswith(prefix):
                    continue
                rel = name.removeprefix(prefix)
                if any(fnmatch.fnmatchcase(rel, pattern) for pattern in trust) or (
                    not any(pattern.fullmatch(rel) for pattern in exceptions)
                    and _protected(repo, name, rel, before, after, rules, conflicted=name in conflicts)
                ):
                    return True
            return False

        sensitive = touches_sensitive(common.stdout.decode().strip(), head)
        for commit, *parents in commits:
            if sensitive:
                break
            if len(parents) == 1:
                sensitive = touches_sensitive(parents[0], commit)
            else:
                tree, conflicts = _merge_baseline(repo, parents)
                sensitive = touches_sensitive(tree, commit, conflicts)
        if not sensitive:
            return []
        signers = _git(repo, "show", base + ":" + prefix + signer_path, check=False)
        if signers.returncode or not any(
            line.strip() and not line.lstrip().startswith(b"#") for line in signers.stdout.splitlines()
        ):
            next_step = "Hold this change for a person's word." if project else fix
            return ["The base has no trusted public door signer. " + next_step]
        with tempfile.TemporaryDirectory() as temp:
            allowed = Path(temp) / "allowed-signers"
            allowed.write_bytes(signers.stdout)
            for commit, *_ in commits:
                content = _git(repo, "cat-file", "commit", commit).stdout.split(b"\n\n", 1)[0]
                if (
                    b"\ngpgsig -----BEGIN SSH SIGNATURE-----\n" not in content
                    or _git(
                        repo,
                        "-c",
                        "gpg.format=ssh",
                        "-c",
                        "gpg.ssh.allowedSignersFile=" + str(allowed),
                        "-c",
                        "gpg.minTrustLevel=fully",
                        "verify-commit",
                        commit,
                        check=False,
                    ).returncode
                ):
                    return [f"Commit {commit} has no trusted door signature. " + fix]
        return []
    except (OSError, ValueError, KeyError, TypeError, re.error, subprocess.SubprocessError):
        return ["The base policy, changed paths or signatures could not be verified. " + fix]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("base")
    parser.add_argument("head")
    parser.add_argument("--project", action="store_true")
    args = parser.parse_args()
    problems = check(args.repository, args.base, args.head, project=args.project)
    print("\n".join(problems) or "Approval evidence verified.")
    raise SystemExit(int(bool(problems)))
