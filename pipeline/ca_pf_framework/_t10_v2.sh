#!/bin/bash
# _t10_v2.sh --- t10CL2 的 J1–J4 判决（两级清理）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10CL2
sleep 780
echo "NOW $(date '+%m-%d %H:%M:%S')"
echo "--- 周期清理全部记录 ---"
grep -a '\[SEEDCLEAN-STEP\]' _w2_t5_short_$TAG.log 2>/dev/null | sed 's/^/  /'
echo "--- 步 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -2 | cut -c1-135
echo "--- swap ---"
EN=""
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag $TAG "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then awk '/^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status; else echo "  ⚠ 引擎不在"; fi
free -m | sed -n '2,3p' | sed 's/^/  /'
[ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo "  exit: 无"
MX=$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)
echo "--- 快照最大 = ${MX:-0} ---"
if [ -n "$MX" ] && [ "${MX:-0}" -ge 100 ] 2>/dev/null; then
  echo; echo "════ J1/J2 逐连通分量 PCA ════"
  $PY _t10_seven.py $TAG "$MX" 2>&1 | tail -22
  echo; echo "════ J1 全部场分量数 ════"
  $PY _t10_allfields.py $TAG "$MX" 2>&1 | tail -8
  echo; echo "════ J3 块表 ════"
  $PY _t10_seven.py $TAG "$MX" 2>&1 | tail -8
  echo; echo "════ 判决基线：⑦27%→(t10FIX)79% / 长厚10.48→11.68 / n_var_sig 4 / 核数46 ════"
else
  echo "  还没到 100（当前 $(echo "$MX" | head -1)）⇒ 下一轮再来"
fi
