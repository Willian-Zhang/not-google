#!/bin/bash
LC_ALL=C sort -m data/lex/*.lex | python merge.py 
