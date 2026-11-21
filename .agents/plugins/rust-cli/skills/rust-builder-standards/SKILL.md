---
name: rust-builder-standards
description: "How code is written in a Rust command-line project of the software factory: the crate's layout, the checks every commit passes (cargo fmt, clippy with warnings as errors, cargo test), tests, errors and output. Read it before you write or change Rust code in this project."
---

# Rust standards of this project kind

They add to the project's builder rules and `AGENTS.md`; where they differ, `AGENTS.md` wins.

## The crate

- One package: the library in `src/lib.rs` (and its modules) holds the behaviour; `src/main.rs` only reads the
  arguments, calls the library and prints. A change of behaviour is a change of the library, with its test.
- `<name> --version` prints `<name> <commit>` (the commit is set at build time from `APP_COMMIT`, by `build.rs`).
  Keep it: the verification and the walk check the build by it.
- No new dependency without a line in the pull request that says why the standard library is not enough. Never a
  dependency from git or a path outside the repository.

## The checks before you stop (the pack's Stop hook runs them; CI runs them again)

- `cargo fmt --check` (format with `cargo fmt`).
- `cargo clippy --all-targets -- -D warnings`: a warning is an error. Never silence one with `#[allow(...)]` without
  a comment that says why.
- `cargo test`: unit tests beside the code (`#[cfg(test)] mod tests`), the command's tests in `tests/`, and the
  planner's acceptance tests in `tests/acceptance/` (never change, skip or delete them).

## Errors and output

- No `unwrap()` or `expect()` on input from the user, a file or the environment: return an error, print it on
  stderr, and exit with a non-zero code. Normal output goes to stdout only.
- Machine-readable output (`--json`) is stable: a field is never renamed or removed in a change that does not say
  so in its card.

## Proof

- A change a user sees in the command's output is proved by a transcript (the skill `verify-cli`), which CI replays.
