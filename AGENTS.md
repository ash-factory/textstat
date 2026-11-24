# textstat

textstat: a factory project

- Test command: `cargo test` (before you stop, the rust-cli pack's Stop hook also runs `cargo fmt --check` and `cargo clippy --all-targets -- -D warnings`; CI runs all three).
- Run the command: `cargo run -- <args>`. `--version` prints `textstat <commit>`: keep it, the verification and the walk check the build by it. Only `scripts/verify/start` and CI are sure to build the current commit into it (they set `APP_COMMIT`); a plain `cargo run` may print an older one.
- The library lives in `src/lib.rs` and its modules; `src/main.rs` only reads the arguments and prints. Builders' own tests live beside the code and in `tests/`. The Rust standards: the skill `rust-builder-standards` (in `.agents/plugins/rust-cli/`).
- Proof of a change the command's user sees: a transcript (the skill `verify-cli`), which CI's `evidence-replay` runs again.
- `tests/acceptance/` holds the planner's acceptance tests. Make them pass; never change, skip or delete them.
- One slice per pull request. A slice lists the paths it owns in its issue.
- Only the governance keeper changes this file.

## Builder: after you open the pull request

- Add the `openhands-review` label, then end your turn. Exception: if your card has the label `review:none`, never add `openhands-review` (here or after a send-back); the factory approves such a card on its checks, or asks for the AI review itself when the label came too late. Do not wait for the review. Do not merge and do not switch on auto-merge. The factory does the rest:
  - A red check, a review that asks for changes, a merge conflict or an open review thread sends you back to this pull request with the words "Revise existing PR". The reason is in the pull request's comment "Factory record".
  - A green and approved head is merged by the factory. A branch that is behind `main` is updated by the factory.
- When you are sent back:
  - Your token cannot read check runs. Read CI with `gh run list --branch <your branch> --limit 5` and a failing log with `gh run view <run id> --log-failed`. A failing `test` or `guard` run means: fix it before anything else.
  - Read the whole review of the reviewer `elementradee-source`. Its verdict line (`✅ APPROVED` or `🔄 CHANGES REQUESTED`) is at its end. A review in state COMMENTED whose verdict is `🔄 CHANGES REQUESTED` means: fix the findings.
  - Read every inline comment (`gh api repos/ash-factory/textstat/pulls/<number>/comments`) and every unresolved review thread, whoever wrote it.
  - Answer every review comment: fix it, or reply with evidence why no change is needed. Then resolve its thread. GitHub does not merge while a review thread is open.
  - "Merge conflict" in the factory record means: merge `main` into your branch, fix the conflict inside your owned paths, test, and push.
  - After you push, or after you posted your evidence that no change is needed, remove and re-add the `openhands-review` label (not on a `review:none` card), then end your turn. Never request a review from `all-hands-bot`.
  - Do not open another pull request and do not convert this one to a draft.
- Say nothing about another slice, another pull request or another worker's work unless you link the issue, pull request or check you read it from.
- Never change `tests/acceptance/`, `AGENTS.md` or `.github/`. If one of them is wrong, say so in the pull request.

## Project rules

| Rule | Check or judgement |
| --- | --- |
| Run the test suite. | `test` |
| Keep protected files in reviewed changes. | `guard` |
| Keep each feature driver with its test. | `feature-map` |
