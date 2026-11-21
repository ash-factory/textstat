#!/usr/bin/env bash
# The rust-cli pack's SessionStart hook (project kinds design 1.3, 1.8): start the project's own setup,
# .openhands/setup.sh (OpenHands' name for it; nothing in OpenHands 1.63.0 runs it by itself), in the background and
# return at once, so the guest's first step waits at most this hook's 20 s limit.
#
# Not the hooks' native "async": an async hook is ended at its timeout or at the session's end, and `cargo fetch` may
# outlive both. Every file goes to .factory-cache/ (each template's .gitignore names it): the builder commits with
# `git add -A`, so a log under the guarded .openhands/ would be committed and turn `guard` red.
#   .factory-cache/setup.log   the setup's output and errors
#   .factory-cache/setup-ok    the clone's commit, written when the setup ended well
# Nothing on stdout. Exit 0 always: a setup that fails is seen in its log and by the missing marker, and CI holds.
set -u
cd "${OPENHANDS_PROJECT_DIR:-.}" 2>/dev/null || exit 0
mkdir -p .factory-cache || exit 0
rm -f .factory-cache/setup-ok
if [ ! -f .openhands/setup.sh ]; then
  echo "no .openhands/setup.sh in $(pwd): nothing to set up" > .factory-cache/setup.log
  exit 0
fi
commit="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
setsid bash -c 'bash .openhands/setup.sh && printf "%s\n" "$1" > .factory-cache/setup-ok' setup "$commit" \
  </dev/null >.factory-cache/setup.log 2>&1 &
exit 0
