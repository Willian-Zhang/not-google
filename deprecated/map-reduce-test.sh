#!/bin/bash
tar cvzf env.tgz .env
hadoop fs -rm -r "$2"
/usr/bin/hadoop jar "/opt/cloudera/parcels/CDH-5.9.0-1.cdh5.9.0.p0.23/lib/hadoop-mapreduce/hadoop-streaming.jar" \
    -archives "env.tgz" \
    -D mapreduce.job.maps=8 -D mapreduce.job.reduces=1 \
    -mapper "env.tgz/.env/bin/python $1" -file "$1" \
    -input "dummy" -output "$2"
