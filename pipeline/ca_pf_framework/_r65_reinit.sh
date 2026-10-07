#!/bin/bash
# R65: 查 `sussman_reinit` 的触发条件 —— 面侵蚀的最后一个候选来源（B）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== 引擎里谁调用 sussman_reinit'
grep -nE "sussman_reinit" windowB_surface.py | head -8
echo
echo '=== reinit 的触发条件（reinit_every / reinit_dt / reinit_band 的用法）'
grep -nE "reinit_every|reinit_dt|reinit_band" windowB_surface.py _bk_exp.py | head -16
echo
echo '=== _bk_exp 传给 advance 的 reinit 参数'
grep -nE "reinit" _bk_exp.py | sed -n '1,14p'
