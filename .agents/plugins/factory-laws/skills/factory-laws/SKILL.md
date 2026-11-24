---
name: factory-laws
description: Apply project rules and report the check that enforces each one.
---

Use the rules table in AGENTS.md. Each row names its CI job or explains which judgement a person must make. A learn pull request names its issue with `Learn: #<number>` and identifies the change with `Layer: structure`, `check`, `test`, `verification` or `text`. If the layer is text, add `Why-not-a-check:` with the reason.


## Acceptance tests

The `acceptance` job wants, for each numbered line `A<k>` of the card's checklist, one test that passes on your head and either is new or fails on the base. Mark that test with the card number and the line, in your own test files (never in `tests/acceptance/`):

- Python: the decorator `@pytest.mark.acceptance("#<card>", "A<k>")` on the test function.
- Rust: the line `// acceptance: #<card> A<k>` directly above the test's `#[test]`.

One test may carry several marks. The job's Fix line names the exact mark it is missing.
