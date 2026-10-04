#!/bin/bash
# _t5_relaunch293.sh --- s293（用户 2026-10-04 批准）之后重启**三臂**。
#   t5FIX  = η + KM + 平行建块
#   t5BKMo = KM + 平行建块
#   t5ETAo = η  + 平行建块
# 初始条件与之前**完全一致**（N=80 nvar12 m23 B3 · plate 1000/500/510 · Ms 873 · 降温曲线）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_relaunch293.log
TS=$(date +%m%d_%H%M)
{
  echo "════ s293 平行建块：重启三臂  $TS ════"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *_t5_wait291.sh*) kill -9 "$P" 2>/dev/null; echo "  KILL wait291 pid=$P" >> "$LOG" ;; esac
done
for T in t5FIX t5BKMo t5ETAo; do
  for P in $(ls /proc | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
    case "$C" in *bk_exp.py*"--tag $T "*) echo "  KILL $T pid=$P" >> "$LOG"; kill -9 "$P" 2>/dev/null ;; esac
  done
done
sleep 6
for T in t5FIX t5BKMo t5ETAo; do
  D=_exp/_bk_t5/dry_$T
  [ -d "$D" ] && mv "$D" "${D}_superseded_s293_$TS" && echo "  $T 旧数据 → $(basename ${D}_superseded_s293_$TS)" >> "$LOG"
done

for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" 2>>"$LOG" && echo "  ✅ $f 语法 OK" >> "$LOG" || { echo "  ❌ $f 语法错 ⇒ 中止" >> "$LOG"; exit 1; }
done
# ★ 硬门：直接数代码行证明三处补丁在位（不靠"我改过"）
echo -n "  s293 平行建块代码行： " >> "$LOG"
awk '/_fresh_now = \(n_fresh_ok < int\(_Bt\)\)/{n++} END{print n+0" 处"}' _bk_exp.py >> "$LOG"
echo -n "  s293 透传行： " >> "$LOG"
awk "/'--nuc-block-parallel', str\(a.nuc_block_parallel\)/{n++} END{print n+0\" 处\"}" _t5_short.py >> "$LOG"
echo -n "  s292 代价闸行： " >> "$LOG"
awk '/while _do_try and n_ath_tgt < _tgt/{n++} END{print n+0" 处"}' _bk_exp.py >> "$LOG"
echo -n "  s291 记账行： " >> "$LOG"
awk '/^ *if _ev or not _burst_on:$/{n++} END{print n+0" 处"}' _bk_exp.py >> "$LOG"

launch () {   # tag cores mem steps extra...
  local TAG=$1 CORES=$2 MEM=$3 STEPS=$4; shift 4
  setsid $PY _t5_short.py --tag $TAG --N 80 --nvar 12 --m 23 --B 3 --steps $STEPS \
      --cores $CORES --mem-limit-gb $MEM --every 20 --snap-every 40 --pair-every 100 \
      --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
      --diag-terms --nuc-block-parallel 1 "$@" \
      < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
  echo "  已起 $TAG（$* --nuc-block-parallel 1）" >> "$LOG"
}
launch t5FIX  0-5  9.0 6000 --ed-eta 0.375 --burst-km 1
sleep 22
launch t5BKMo 6-11 7.0 3000 --burst-km 1
sleep 22
launch t5ETAo 12-15 7.0 3000 --ed-eta 0.375

setsid nohup bash _t5_wait291.sh 560 21600 > /dev/null 2>&1 < /dev/null &
echo "  已重挂守望器 _t5_wait291.sh 560 21600" >> "$LOG"

sleep 70
{
  echo "  ── 复验（70 s 后）──"
  for T in t5FIX t5BKMo t5ETAo; do
    P=$(ls /proc | grep -E '^[0-9]+$' | while read -r X; do
          tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null | grep -q -- "--tag $T " && echo "$X"; done | head -1)
    if [ -n "$P" ]; then
      echo "  [$T] pid=$P $(tr '\0' ' ' < /proc/$P/cmdline | grep -oE '\-\-ed-eta [0-9.]+|\-\-burst-km [0-9]+|\-\-nuc-block-parallel [0-9]+' | tr '\n' ' ')"
    else echo "  [$T] ⚠ 无进程"; fi
  done
  free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
