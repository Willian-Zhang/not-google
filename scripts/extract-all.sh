#!/bin/bash
mkdir -p "data/lex"
source .env/bin/activate

after="0"
for file in data/wet/*.warc.wet.gz; do
    lexFile="data/lex/$(basename $file .warc.wet.gz)"
    python extract_lex.py --binary --urlTable "data/url-table.tsv" --startID "$after" "$file" | LC_ALL=C  sort > "$lexFile"
    after=$(tail  -n 1 "data/url-table.tsv" | cut -f1)
    echo "$after\t$(basename $file .warc.wet.gz)" >> "data/url-table-table.tsv"
done
