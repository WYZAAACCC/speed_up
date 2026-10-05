#!/bin/bash
# _t10_prt2verdict.sh --- 等 t10PRT2 的 step 100 ⇒ 出「死核率」判决（后台作业，不占上下文）
#   判据（预登记，不放宽）：基线 t10CL2 = 47 事件中 10 个死核（21%）
#     目标：死核率显著下降至 ~0；且六项保持（长厚≥10、长宽不退化、n_var_sig≥4、⑦=100%）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10PRT2
OUT=_w2_t10_prt2_verdict.log
: > "$OUT"
for i in $(seq 1 30); do
  MX=$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)
  if [ -n "$MX" ] && [ "${MX:-0}" -ge 100 ] 2>/dev/null; then break; fi
  sleep 180
done
{
  echo "════ t10PRT2 判决  $(date '+%m-%d %H:%M:%S') ════"
  echo "  快照最大 = ${MX:-0}"
  echo
  echo "── ① 死核率（与 t10CL2 同口径）──"
  $PY _t10_deadseed.py $TAG "${MX:-0}" 2>&1 | tail -22
  echo
  echo "── ② 形核事件 / 场号唯一性 ──"
  $PY _t10_ev70.py 2>/dev/null | tail -6
  echo "  （注：_t10_ev70.py 读的是 t10CL2 日志，此行仅供参考）"
  echo
  echo "── ③ 七项（逐连通分量 PCA）──"
  $PY _t10_seven.py $TAG "${MX:-0}" 2>&1 | tail -24
  echo
  echo "── ④ 全部场分量数 ──"
  $PY _t10_allfields.py $TAG "${MX:-0}" 2>&1 | tail -9
  echo
  echo "── ⑤ [SEEDCARVED] 统计 ──"
  echo -n "  行数 = "; grep -ac '\[SEEDCARVED\]' _w2_t5_short_$TAG.log 2>/dev/null
  echo -n "  protected 含 0 的行数（应 0）= "
  grep -a '\[SEEDCARVED\]' _w2_t5_short_$TAG.log 2>/dev/null | grep -c 'protected=\[0[,\]]'
  echo "  被保护最多的场（前 8）："
  grep -a '\[SEEDCARVED\]' _w2_t5_short_$TAG.log 2>/dev/null \
    | grep -oE 'protected=\[[0-9, ]*\]' | sort | uniq -c | sort -rn | head -8 | sed 's/^/    /'
  echo
  echo "── ⑥ 两级清理 / swap ──"
  echo -n "  播种清理 = "; grep -ac '\[SEEDCLEAN\]' _w2_t5_short_$TAG.log 2>/dev/null
  echo -n "  周期清理 = "; grep -ac '\[SEEDCLEAN-STEP\]' _w2_t5_short_$TAG.log 2>/dev/null
  free -m | sed -n '2,3p' | sed 's/^/  /'
  echo "  swap 盯守尾："; tail -2 _w2_t10_swapfix2.log 2>/dev/null | sed 's/^/    /'
  echo
  echo "  基线：t10CL2 = 47 事件 / 10 死核(21%) / ⑦=100% / 长厚 11.31 / n_var_sig 4"
} >> "$OUT" 2>&1
cat "$OUT"
