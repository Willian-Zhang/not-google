#!/bin/bash
scp requirements.txt *.py $1
scp -r testbeds scripts $1