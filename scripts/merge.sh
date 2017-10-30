#!/bin/bash
LC_ALL=C sort --batch-size=300 --mergesort -m data/lex/*.lex | python merge.py 
