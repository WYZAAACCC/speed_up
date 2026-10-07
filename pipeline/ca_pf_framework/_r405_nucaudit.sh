#!/usr/bin/env bash
# _r405_nucaudit.sh -- 核实：这些算例到底**有没有形核通道在跑**？
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
echo "=== 命令行的形核参数（从 run.log 抓）==="
grep -oE '\-\-nuc-[a-z-]+ [0-9.a-z]+|--alpha-km [0-9.]+|--nuc-law [a-z]+|--nuc-mode [a-z]+' \
  _w2_r386_run.log 2>/dev/null | sort -u
echo
echo "=== 形核事件有没有发生过 ==="
for f in _w2_r386_run.log _w2_r370_permB1_400.log _w2_r361_run.log; do
  [ -f "$f" ] || continue
  printf '  %-32s 形核事件行 = %s ；拒绝行 = %s\n' "$f" \
    "$(grep -c 'athermal 形核' "$f" || true)" \
    "$(grep -c '被引擎拒' "$f" || true)"
done
echo
echo "=== 播种之后有没有新场出现（nv 变化）==="
grep -oE 'nv=[0-9]+|场数=[0-9]+|nreg=[0-9]+' _w2_r386_run.log 2>/dev/null | sort -u | head
echo
echo "=== nuc_cfg 是否被调用（_bk_exp.py 的接线）==="
grep -n 'g.nuc_cfg\|nuc_cfg(' _bk_exp.py | head -5
echo
echo "=== 代码里形核的物理定义（docstring 摘）==="
grep -n 'repeated nucleation\|反复形核\|autocatalytic' windowB_surface.py | head -5
