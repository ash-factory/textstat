# Review guide

A draft of the advisor (15 Nov 2026). OpenHands' reviewer station and its planner station read this file by name (`.agents/skills/custom-codereview-guide.md`). Nothing is pushed.

## Scope of this repository

(One paragraph per app: what belongs here and what does not. The reviewer's scope gate uses it.)

## Depth by type of work

Read the issue's `type:` label.

| Type | Review |
|---|---|
| `small`, `research` | Short pass: the required checks are green and the change stays inside the files that the card names. Do not read further. Approve |
| `bug`, `harness` | Full review. The failing-first test of the card exists and is green |
| `slice`, `module` | Full review, with live evidence |

## Live evidence

A change that a person or a caller sees needs live evidence in the pull request: the transcript of the real command, `evidence/<issue>/<NN>-<state>-pass.md` (its commands and their exact output), which CI's `evidence-replay` ran again at the head. Without it, do not approve.

A card with `check:running-app` whose pull request has no passing self-check under `evidence/` for its head gets changes requested: the last row of `evidence/<issue>/selfcheck.md` is `pass`, its transcript is there, `evidence-replay` is green on the head, and no commit after the checked one changes anything outside `evidence/`. Read the transcripts against the card's expected results: the inputs, the output, the exit code of the error case.

In the verdict, name each proof file you opened (its path under `evidence/`).

## A changed contract, a root card

A pull request with the label `contract-changed` uses a part that changed in `main` after it was written; the factory's `factory-contract` comment on it names the merged pull request, the part, and the names whose signature changed (or "no name changed"). Review it against the new contract: check that the head holds that merge, and run each use the comment names. A use that still expects the old contract is a `fix` finding.

A root card (`Root:` and `Covers:` in its body): check that the fix is in the part `Root:` names, that a test is at that part's own interface, and that the listed uses are all the uses (search again). A fix at a caller is a `fix` finding unless the card says why.

## Changed tests

The check `tests-kept` lists every changed test file in its job summary. A test whose id stays can still be loosened (a weaker assertion, a wider tolerance, a caught exception). Judge each changed test: a change that the card's acceptance criteria do not ask for is a `fix` finding. A skip or quarantine is allowed only in a commit that names the test's open `failure-seen` issue.

## Classes of findings

Put each finding in one class, and say which in its first word.

| Class | Meaning | What the builder does |
|---|---|---|
| `fix` | A defect on the changed lines, shown on the current head | Fixes it in this pull request |
| `ask` | The card is unclear or the change touches the intent | Puts the label `needs-owner` on the issue with the question, and stops |
| `note` | True, and not a reason to hold the merge | Nothing; the Harness Engineer reads the notes |

A finding with no class counts as `ask`.

## The cause of a review that asks for changes

A review that ends with changes requested names, on its own line just before the verdict, the one cause of the main `fix` finding: `Cause: <name>`. First list the causes this repository already has (`gh label list --search cause: --limit 100`) and reuse the one that fits, word for word; name a new one (two to four words) only when none fits. The factory puts the cause on the card and counts it: the same cause on two cards opens a learn issue that changes the factory's rules (`design/learn_loop/DESIGN.md` in the factory).

## Rounds

The factory's sweep counts the reviews on one pull request that end with changes requested. After the third it puts the label `needs-owner` on the issue, with the finding that repeats. You change no label. When the same finding comes back a second time, say so in the first line of your review, so that the count has its reason.
