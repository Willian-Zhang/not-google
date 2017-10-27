#!/bin/bash
mkdir -p "data/lex"
# source .env/bin/activate

after="0"
for file in data/wet/*.warc.wet.gz; do
    lexFile="data/lex/$(basename $file .warc.wet.gz).lex"
    python extract_lex.py --binary \
        --redis "/tmp/redis.sock" --redisDB 0 \
        --startID "$after" \
        --docIDwet data/docIDwet.tsv \
        "$file" \
        | LC_ALL=C  sort > "$lexFile"
    after=$(tail  -n 1 "data/docIDwet.tsv" | cut -f2)
    echo "$after\t$(basename $file .warc.wet.gz)" >> "data/url-table-table.tsv"
done
