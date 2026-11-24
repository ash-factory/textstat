"""A pytest plugin for the check `tests-kept` (design/test_integrity/DESIGN.md 3.2; P-46; ticket D3).

Loaded into a collection only (`python -m pytest --collect-only -q -p collect_marks`, with this folder on
PYTHONPATH). It writes one JSON line per collected test to the file named by COLLECT_MARKS_OUT: the test's id and
its skip and xfail marks (`skip`, `skipif`, `xfail`; a `skipif` counts whatever its condition, since a new one is a
narrowing of the suite). It changes no test and runs none.
"""
import json
import os

MARKS = ("skip", "skipif", "xfail")


def pytest_collection_finish(session):
    out = os.environ.get("COLLECT_MARKS_OUT")
    if not out:
        return
    with open(out, "w") as handle:
        for item in session.items:
            marks = sorted({m.name for m in item.iter_markers() if m.name in MARKS})
            handle.write(json.dumps({"id": item.nodeid, "marks": marks}) + "\n")
