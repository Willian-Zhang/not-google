#!/bin/bash
scp requirements.txt *.py $1
scp -r testbeds scripts modules $1
scp data/wet.paths $1/data/
