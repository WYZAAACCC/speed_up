#!/bin/bash
# R64: 找"关掉/减弱弹性驱动"的开关，为下一步的预登记实验做准备
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== _bk_exp.py 里与弹性相关的开关'
grep -nE "add_argument" _bk_exp.py | grep -iE "el|elastic|lambda|ed" | head -12
echo
echo '=== 引擎侧 elastic_driving 的定义与可调量'
grep -nE "def elastic_driving|lambda_el" windowB_surface.py | head -10
echo
echo '=== _bk_exp 里怎么调 elastic_driving'
grep -nE "elastic_driving|lambda_el|pf\b" _bk_exp.py | head -12
