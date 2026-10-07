#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
/root/miniconda3/envs/ml/bin/python _r73c_log.py 2>&1 | head -2
echo '--- 找 "场 -> 变体" 映射的真实属性名'
grep -nE 'vmap|vtag|variant' windowB_surface.py | grep -iE 'self\.|def ' | head -14
echo
echo '--- LevelSetMulti.__init__ 的签名（看变体信息怎么进）'
grep -n 'class LevelSetMulti' -A 14 windowB_surface.py | head -18
