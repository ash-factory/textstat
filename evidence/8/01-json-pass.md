```console
$ textstat --version
textstat [..]

$ textstat count sample.txt --json
{"lines":1,"words":2,"chars":12}

$ textstat count sample.txt
lines=1 words=2 chars=12

$ textstat count empty.txt --json
{"lines":0,"words":0,"chars":0}

$ textstat count missing.txt --json
? 1
error: missing.txt: No such file or directory (os error 2)

```
