#!/bin/bash
# _t10_judge.sh --- 等 step 100 快照，出 **J1–J3 判决**（与 η=0.375 基线同口径对比）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10E253
sleep 840
echo "NOW $(date '+%m-%d %H:%M:%S')"
echo "--- 步/节拍 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null \
  | grep -oE '^ *\[ *[0-9]+\]|[0-9.]+s/步' | paste - - | tail -4
echo "--- 末步 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -1 | cut -c1-135
echo "--- swap ---"
EN=""
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag $TAG "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then awk '/^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status; else echo "  ⚠ 引擎不在"; fi
free -m | sed -n '2,3p' | sed 's/^/  /'
[ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo "  exit: 无"
MX=$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)
echo "--- 快照最大 = ${MX:-0} ---"

if [ -n "$MX" ] && [ "${MX:-0}" -ge 100 ] 2>/dev/null; then
  echo
  echo "════════ J1/J2：逐连通分量 PCA（口径与基线完全一致）════════"
  $PY _t10_seven.py $TAG "$MX" 2>&1 | sed -n '4,26p'
  echo
  echo "════════ J1：全部场的分量数分布（⑦ 一场一板条）════════"
  $PY _t10_allfields.py $TAG "$MX" 2>&1 | tail -8
  echo
  echo "════════ J3：CSV 块表（n_var_sig / blk_laths）════════"
  $PY _t10_seven.py $TAG "$MX" 2>&1 | tail -6
  echo
  echo "════════ 判决（基线 = η0.375 @ step100：⑦27% / 长厚10.48 / n_var_sig 4）════════"
  echo "  J1 ⑦ 需 > 27% ；J2 长/厚中位 需 ≥ 10 ；J3 n_var_sig 需 ≥ 4"
fi
