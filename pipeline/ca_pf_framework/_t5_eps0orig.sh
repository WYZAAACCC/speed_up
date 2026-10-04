#!/bin/bash
# _t5_eps0orig.sh --- 读 `T16_verify_rve.py` 里 `EPS0` 的来历（CALPHAD/文献/晶格参数?）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
E=$(grep -n '^EPS0' T16_verify_rve.py | head -1 | cut -d: -f1)
echo "  EPS0 定义在第 $E 行 ⇒ 打印它**之前 40 行**的注释（来历应写在注释里）"
sed -n "$((E-40)),$((E+2))p" T16_verify_rve.py | nl -ba -v$((E-40)) | cut -c1-150
