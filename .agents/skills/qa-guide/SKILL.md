---
name: qa-guide
description: "This project's walk rules for OpenHands' /qa-changes: which build to use, how to use the command the way a user does, the key scenarios, and the known limits. Read it when you walk a checkpoint of textstat."
---

# QA guide: textstat

OpenHands' QA guide form (environment setup, key scenarios, known limits), for the walk at a checkpoint (the factory's walk design, `design/walk/DESIGN.md`). The walk is of the landed build (main's landed commit, which the walk's message names), never of a pull request's head.

## Environment setup

- Your folder is a clone at main's landed commit. Build it there: `APP_COMMIT=$(git rev-parse HEAD) cargo build --release`, or take the `build` artifact of main's CI run at that commit.
- Check the build first: `target/release/textstat --version` answers `textstat <main's commit>`.
- Run every command in a new empty folder (`mktemp -d`), never in the clone, so that no file of the repository changes what the command sees.

## Key scenarios

- `--version`: the name and the landed commit.
- Each command the checkpoint's cards changed, with the normal input, the empty input and a wrong input: its output on stdout, its errors on stderr, its exit code.
- Every `--json` output the cards touched: it parses, and its fields are the ones the cards name.
- Report each scenario as its commands and their output (a transcript), as `/qa-changes` asks.

## Known limits

- Nothing runs on the server for this kind (release target `none`): there is no live address to walk.
- A command that needs the network or a file outside the new folder is walked only when its card says how.
