#!/usr/bin/env bash
# OpenHands' setup script of this repository (its own name for it). The rust-cli pack's SessionStart hook runs it in
# the background at the start of each builder's conversation; its output is in .factory-cache/setup.log.
set -euo pipefail
cargo --version
cargo fetch
