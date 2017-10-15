#!/bin/bash
head -n $1 data/wet.paths | awk '{print "https://commoncrawl.s3.amazonaws.com/"$1}' | xargs -n1 wget -P data/wet
