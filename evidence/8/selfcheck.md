| NN | app commit | build | transcript | ran | expected | seen | result |
|---|---|---|---|---|---|---|---|
| 01 | d6657fc9fdab9c7ebe1b8df41dcfdb89c33b7a91 | bin=target/debug/textstat commit=d6657fc9fdab9c7ebe1b8df41dcfdb89c33b7a91 | 01-json-pass.md | Version, count in both modes on UTF-8, and JSON mode on empty and missing files | Matching build commit, integer JSON counts, exact default line, and exit 1 with a diagnostic for the missing file | Build commit and counts matched, default output matched byte for byte, and the missing file exited 1 on stderr with empty stdout | pass |
