| NN | app commit | build | transcript | ran | expected | seen | result |
|---|---|---|---|---|---|---|---|
| 01 | 26647fb6028481f9bfb541ea3a3b14311315374e | bin=target/debug/textstat commit=26647fb6028481f9bfb541ea3a3b14311315374e | 01-count-pass.md | Version and count on UTF-8, whitespace, empty, and missing files | Build commit and exact counts on stdout, exit 1 with stderr and empty stdout for missing file | Build commit matched, all counts matched, missing file exited 1 with a diagnostic and empty stdout | pass |
