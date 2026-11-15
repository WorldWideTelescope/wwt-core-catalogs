#!/bin/bash
# fetch ids one at a time (chandra.harvard.edu throttles with 503); park results in _hold_nowcs
export USERPROFILE='C:\Users\adavi' HOMEDRIVE='C:' HOMEPATH='\Users\adavi'
PY=C:/Users/adavi/anaconda3/envs/wwt/python.exe
for pass in 1 2 3; do
  for i in $(cat "$1"); do
    [ -f _hold_nowcs/$i/metadata.json ] && continue
    [ -f candidates/$i ] || continue
    PYTHONIOENCODING=utf-8 $PY ../../pipeline.py fetch $i >> _fetch_slow.log 2>&1
    if [ -f cache_todo/$i/metadata.json ]; then mv cache_todo/$i _hold_nowcs/; echo "ok $i" >> _fetch_slow.log; else rm -rf cache_todo/$i; echo "FAIL $i pass $pass" >> _fetch_slow.log; sleep 30; fi
    sleep 3
  done
done
echo FINISHED >> _fetch_slow.log
