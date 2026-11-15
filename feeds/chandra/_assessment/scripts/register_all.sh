#!/bin/bash
# usage: _register_all.sh <subdir> <idfile> <tag>
export USERPROFILE='C:\Users\adavi' HOMEDRIVE='C:' HOMEPATH='\Users\adavi'
S="C:/Users/adavi/AppData/Local/Temp/claude/d9357d7fbd45e143/be1bb7b1-812a-4bb0-b1b9-f45283c9abd3/scratchpad"
REGLOG="wcs/_register_log_$3.csv" python -u _assessment/scripts/register.py . "$S/regwork_$3" "$1" $(cat "$2") > "_register_$3.out" 2>&1
echo FINISHED >> "_register_$3.out"
