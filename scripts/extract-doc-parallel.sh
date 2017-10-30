#!/bin/bash
mkdir -p "data/lex"
# source .env/bin/activate

after="0"
printf %s\\n data/wet/*.warc.wet.gz |  xargs -n 1 -P $1 scripts/extract-doc-one.sh