#!/bin/bash
# _t10_verdict.sh --- 等 t10FIX 的 step 100 快照 ⇒ 出 J1–J4 判决（用 tail 读、避开 head 截断与陈旧读）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10FIX
sleep 800
echo "NOW $(date '+%m-%d %H:%M:%S')"
echo "--- 步（tail 读，读两次一致性）---"
A=$(grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -1)
sleep 3
B=$(grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -1)
echo "$A" | cut -c1-140
[ "$A" != "$B" ] && echo "  ⚠ 两次读不一致（陈旧读）⇒ 再读一次：" && echo "$B" | cut -c1-140
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
  echo; echo "════ J1/J2：逐连通分量 PCA ════"
  $PY _t10_seven.py $TAG "$MX" 2>&1 | tail -24
  echo; echo "════ J1：全部场分量数分布 ════"
  $PY _t10_allfields.py $TAG "$MX" 2>&1 | tail -8
  echo; echo "════ J3：CSV 块表 ════"
  $PY _t10_seven.py $TAG "$MX" 2>&1 | tail -8
  echo; echo "════ 判决（基线 η0.375@step100：⑦27% / 长厚10.48 / n_var_sig 4 / 核数45）════"
else
  echo "  还没到 100 ⇒ 下一轮再来"
fi
