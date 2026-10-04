#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== s295 补丁的位置与外围结构（判可达性）==="
grep -n "s295\|_nucd = getattr\|_dbgd = \|_dsig" _bk_exp.py | cut -c1-150
echo
echo "=== 关键锚点行号：if _athermal / while _do_try / s295 / 下一个同级块 ==="
grep -n "if _athermal and use_engine\|while _do_try and n_ath_tgt\|s295 形核分诊\|R581-ckpt（goal\|if _every_now\|for it in range" _bk_exp.py | cut -c1-150
echo
echo "=== s295 那段前后 6 行的缩进（看它在不在 while 之后的同级）==="
L=$(grep -n "_nucd = getattr" _bk_exp.py | head -1 | cut -d: -f1)
if [ -n "$L" ]; then
  S=$((L-8)); E=$((L+18))
  awk -v s=$S -v e=$E 'NR>=s && NR<=e{printf "%5d|%s\n", NR, $0}' _bk_exp.py | cut -c1-135
fi
