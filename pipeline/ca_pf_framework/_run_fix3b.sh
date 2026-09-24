#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
# 杀掉跑在坏代码上的后台套件
for p in $(ps -eo pid,args | grep '[v]erify_ca3d' | awk '{print $1}'); do kill $p 2>/dev/null; done
for p in $(ps -eo pid,args | grep '[_]run_suite_after' | awk '{print $1}'); do kill $p 2>/dev/null; done
sleep 1
/root/miniconda3/envs/ml/bin/python _fix_shape.py
/root/miniconda3/envs/ml/bin/python _verify_fix3.py