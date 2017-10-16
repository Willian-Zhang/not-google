#!/bin/bash
source .env/bin/activate
for file in data/wet/*.warc.wet.gz; do
    python extract_lex.py -c "$file" | sort > "data/lex/$(basename $file .warc.wet.gz)"
done
