# Vision: textstat

<!-- Draft by the advisor on 27 Nov 2026 from the README and the command's code, on the owner's word "write the project visions". The owner corrects it. Only the owner's word changes this file. -->

## Who it is for

- **V1.** A person at a terminal who wants quick counts of a text file, and the factory's practice of a Rust command line project.

## What it does

- **V2.** `textstat count` prints the lines, words and characters of a file, and with `--json` the same counts as JSON.
- **V3.** `textstat --version` names the exact commit the command was built from.
- **V4.** A wrong call prints one usage line and exits with a non-zero code.

## What it must never do

- **V5.** Never change or write the file it reads.
- **V6.** Never need the network.
- **V7.** Never hold real user data, sign-ins or secrets.

## Owner preferences

- **V8.** Every change is small, one card per pull request, tested with `cargo test`, `cargo fmt --check` and `cargo clippy`, and proven by a terminal transcript.
