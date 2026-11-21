#!/usr/bin/env bash
# The rust-cli pack's Stop hook (project kinds design 1.3, 1.8, R4): the one home of "tests before the builder
# stops", for every agent kind (OpenHands runs it in the host conversation, not inside the guest). Claude's own
# factory_stop.py steps aside in a clone whose default branch vendors this pack.
#
#   it runs `cargo fmt --check`, `cargo clippy -- -D warnings` and `cargo test`, only when the clone has a commit or
#   a change since origin/HEAD (a hook is given no base branch); on a failure it EXITS 2 with the failing lines on
#   stderr, which OpenHands sends back as "[Stop hook feedback] ..." (cargo itself exits 1 or 101, which would not
#   refuse). Nothing ever goes to stdout: a JSON object there could decide on its own.
#   At most MAX_REFUSALS refusals a session (OPENHANDS_SESSION_ID), then the stop goes on: CI holds.
#   A suite longer than the hook's 180 s is ended by OpenHands, which does not refuse: that is CI's job.
# This hook is an aid to the builder, never the proof that a check passed (design 1.3, "A limit, by design").
set -u
exec 1>&2
MAX_REFUSALS=2
cd "${OPENHANDS_PROJECT_DIR:-.}" 2>/dev/null || exit 0
mkdir -p .factory-cache 2>/dev/null || true
base="$(git rev-parse --verify --quiet 'origin/HEAD^{commit}' || git rev-parse --verify --quiet 'origin/main^{commit}')" || exit 0
ignored=(':(exclude)evidence' ':(exclude).factory-cache' ':(exclude).verify')
if git diff --quiet "$base" -- . "${ignored[@]}" && [ -z "$(git status --porcelain -- . "${ignored[@]}")" ]; then
  exit 0   # nothing of this card's own yet: nothing to check
fi
count_file=".factory-cache/stop-refusals-${OPENHANDS_SESSION_ID:-none}"
count="$(cat "$count_file" 2>/dev/null || echo 0)"
case "$count" in ''|*[!0-9]*) count=0 ;; esac
if [ "$count" -ge "$MAX_REFUSALS" ]; then
  echo "The rust-cli Stop hook refused $count times in this session; it lets you stop now. CI still runs the same checks."
  exit 0
fi
log=".factory-cache/stop-check.log"
if cargo fmt --check >"$log" 2>&1 && cargo clippy --all-targets -- -D warnings >>"$log" 2>&1 && cargo test >>"$log" 2>&1; then
  exit 0
fi
echo $((count + 1)) > "$count_file"
echo "Do not stop yet: this project's checks fail (cargo fmt --check, cargo clippy -- -D warnings, cargo test)."
echo "Fix the cause, commit, and stop again. The last lines of .factory-cache/stop-check.log:"
tail -n 40 "$log"
exit 2
