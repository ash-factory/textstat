---
name: verify-cli
description: "How to prove a change of a Rust command-line project of the software factory on the running build: build the commit, run the real command, and record its transcript under evidence/ in the form CI replays. Read it before you prove a change, on every card with the label check:running-app, and for a check of this project that its kind file carries by self-check."
---

# Verify the command (the transcript form)

This project's kind is `rust-cli` (`.github/factory.json`): its evidence form is **a transcript**. A transcript is
the real command and its real output. CI's `evidence-replay` job runs it again at the pull request's head and fails
on any difference, so a transcript that was not run, or that a later commit makes wrong, turns the pull request red.

## When

- A card with the label `check:running-app`: after **each unit of work that changes what the command prints or
  does**, not only at the end.
- A card with the label of one of this project's own checks carried by `self-check` (its kind file's `checks`):
  that check's own transcript, named after the check (`<NN>-<check>-pass.md`).

## Launch

`scripts/verify/start` in your clone. It refuses (exit 2) while a change outside `evidence/` and `.verify/` is
uncommitted: commit the unit first, a check is always of a commit. It builds that commit and prints one line:
`bin=target/debug/<name> commit=<sha>`.

## Drive

Run the command the way a user does, in a new empty folder (`mktemp -d`), with the inputs the card's expected
results name: the normal case, the empty input, and the error case. Read its exit code.

## Evidence

1. Write the transcript `evidence/<issue>/<NN>-<state>-<pass|fail>.md`, in trycmd's literate form:

   ````
   ```console
   $ <name> --json greet Ada
   {"greeting":"Hello, Ada!"}

   $ <name> greet
   ? 2
   error: greet needs a name

   ```
   ````

   One `console` block; each command on a `$ ` line, then its exact output; a line `? <code>` when it exits with a
   code other than 0. Only a part that changes from run to run (a time, a temporary path) may be written `[..]`
   inside a line. The commit that `--version` prints is one of them: write `<name> [..]`, because CI replays the
   transcript on a later commit (the one that adds it). Never hide output with a `...` line: CI refuses it.
2. Add one row to `evidence/<issue>/selfcheck.md` (the header the first time):

   ```
   | NN | app commit | build | transcript | ran | expected | seen | result |
   |---|---|---|---|---|---|---|---|
   | 01 | <commit start printed> | <the line start printed> | 01-json-pass.md | <the commands> | <expected> | <seen> | pass |
   ```

3. Commit: `evidence: check NN at <sha7>`.
4. **On a fail**: write it as a `fail` transcript and row, fix it in a new commit, and check again. The fail stays
   in the history: it shows the fault was met and fixed.

## Before the pull request

Run the factory's proof check with the exact command your start message names. Open the pull request only when it
prints `proof holds`.
