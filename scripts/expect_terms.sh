#!/bin/bash
wc -l data/lex-old/*.lex | grep total | cut -f2 -d ' ' > data/expect_terms.tsv
