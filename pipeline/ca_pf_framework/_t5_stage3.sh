#!/bin/bash
# _t5_stage3.sh --- 阶段③ 的实现审计（"骨架"具体缺什么）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `hardened` / `harden_f` 的所有出现 ════'
grep -n 'hardened\|harden_f' windowB_surface.py 2>/dev/null | sed 's/^/  /'
echo
echo '════ ② 变体选择（`var_rule`）的完整实现段（**不截断**）════'
sed -n '2060,2100p' windowB_surface.py | cat -n | sed 's/^/  /'
