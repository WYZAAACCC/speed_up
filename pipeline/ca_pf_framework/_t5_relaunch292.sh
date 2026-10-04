#!/bin/bash
# _t5_relaunch292.sh --- s292 代价闸之后重启 burst 臂 + 重挂守望器。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_relaunch292.log
TS=$(date +%m%d_%H%M)
{
  echo "════ s292 重启 burst 臂  $TS ════"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

# ① 停旧守望器（它盯旧快照号，且杀进程时会被"进程不在"误判）
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *_t5_wait291.sh*) echo "  KILL wait291 pid=$P" >> "$LOG"; kill -9 "$P" 2>/dev/null ;; esac
done

# ② 按 tag 杀两臂（PID 精确杀；**不动 t5ETAo** —— 它无 burst）
for T in t5FIX t5BKMo; do
  for P in $(ls /proc | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
    case "$C" in *bk_exp.py*"--tag $T "*) echo "  KILL $T pid=$P" >> "$LOG"; kill -9 "$P" 2>/dev/null ;; esac
  done
done
sleep 6

# ③ 数据改名保留
for T in t5FIX t5BKMo; do
  D=_exp/_bk_t5/dry_$T
  [ -d "$D" ] && mv "$D" "${D}_superseded_s292_$TS" && echo "  $T 旧数据 → $(basename ${D}_superseded_s292_$TS)" >> "$LOG"
done

# ④ 语法门
for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" 2>>"$LOG" && echo "  ✅ $f 语法 OK" >> "$LOG" || { echo "  ❌ $f 语法错 ⇒ 中止" >> "$LOG"; exit 1; }
done
# ④b ★ 硬门：证明 s292 闸真的在代码里（不靠"我改过"）
echo -n "  s292 闸存在性：_do_try 代码行 " >> "$LOG"
awk '/while _do_try and n_ath_tgt < _tgt/{n++} END{print n+0" 处"}' _bk_exp.py >> "$LOG"
echo -n "  s291 记账存在性：受控自增 " >> "$LOG"
awk '/^ *if _ev or not _burst_on:$/{n++} END{print n+0" 处"}' _bk_exp.py >> "$LOG"

# ⑤ 起两臂（argv 与 s291 逐字相同）
setsid $PY _t5_short.py --tag t5FIX --N 80 --nvar 12 --m 23 --B 3 --steps 6000 \
    --cores 0-5 --mem-limit-gb 9.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.375 --burst-km 1 --diag-terms \
    < /dev/null > _w2_t5_short_t5FIX.log 2>&1 &
echo "  已起 t5FIX" >> "$LOG"
sleep 25
setsid $PY _t5_short.py --tag t5BKMo --N 80 --nvar 12 --m 23 --B 3 --steps 3000 \
    --cores 6-11 --mem-limit-gb 7.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --burst-km 1 --diag-terms \
    < /dev/null > _w2_t5_short_t5BKMo.log 2>&1 &
echo "  已起 t5BKMo" >> "$LOG"

# ⑥ 重挂守望器（等 560；闸后节拍应回到 ~8 s/步）
setsid nohup bash _t5_wait291.sh 560 21600 > /dev/null 2>&1 < /dev/null &
echo "  已重挂守望器 _t5_wait291.sh 560 21600" >> "$LOG"

# ⑦ 复验 argv
sleep 60
{
  echo "  ── 复验（60 s 后）──"
  for T in t5FIX t5BKMo t5ETAo; do
    P=$(ls /proc | grep -E '^[0-9]+$' | while read -r X; do
          tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null | grep -q -- "--tag $T " && echo "$X"; done | head -1)
    if [ -n "$P" ]; then
      echo "  [$T] pid=$P 历龄=$(ps -o etime= -p $P | tr -d ' ') $(tr '\0' ' ' < /proc/$P/cmdline | grep -oE '\-\-ed-eta [0-9.]+|\-\-burst-km [0-9]+' | tr '\n' ' ')"
    else echo "  [$T] ⚠ 无进程"; fi
  done
  free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
