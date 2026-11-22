```console
$ textstat --version
textstat [..]

$ textstat count unicode.txt
lines=1 words=2 chars=12

$ textstat count whitespace.txt
lines=3 words=3 chars=8

$ textstat count empty.txt
lines=0 words=0 chars=0

$ textstat count missing.txt
? 1
error: missing.txt: No such file or directory (os error 2)

```
