#!/bin/bash
file=$1
startID=$(cat "data/docIDwet.tsv" | grep "$file"| cut -f1)
endId=$(cat "data/docIDwet.tsv" | grep "$file"| cut -f2)
# echo $file
python extract_doc.py \
    --redis "/tmp/redis.sock" --redisDB 0 \
    --startID "$startID" \
    --docIDwet "data/docIDwet-re.tsv" \
    "$file"