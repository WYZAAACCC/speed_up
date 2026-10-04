#!/bin/bash
# _t5_relaunch291.sh --- s291 之后重启两个 **burst 臂**（t5FIX / t5BKMo）。
#
# ## 为什么必须重启
# s291 修的是 `_bk_exp.py` 的 **athermal 记账**（被拒不消耗目标）。
# `t5FIX`（`--burst-km 1`）与 `t5BKMo`（`--burst-km 1`）跑的是**旧记账**
# ⇒ 必须用新代码重跑；`t5ETAo`（**无 burst**）不受影响 ⇒ **不动它**，省算力也省时间。
#
# ## 纪律
# · 按 **PID** 杀（绝不 `pkill -f`，会把本脚本自己杀掉）
# · 数据**改名保留**（绝不删除）
# · 重启后**复验 argv**（证明开关真的传进去了）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_relaunch291.log
TS=$(date +%m%d_%H%M)

{
  echo "════ s291 重启 burst 臂  $TS ════"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

# ── ① 停掉旧的 waitfix 守望（它盯的是旧 t5FIX 的快照号，会误判）──
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *_t5_waitfix.sh*) echo "  KILL waitfix pid=$P" >> "$LOG"; kill -9 "$P" 2>/dev/null ;; esac
done

# ── ② 按 tag 找 PID 并杀 ──
for T in t5FIX t5BKMo; do
  for P in $(ls /proc | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
    case "$C" in
      *bk_exp.py*"--tag $T "*) echo "  KILL $T pid=$P" >> "$LOG"; kill -9 "$P" 2>/dev/null ;;
    esac
  done
done
sleep 6

# ── ③ 数据改名保留 ──
for T in t5FIX t5BKMo; do
  D=_exp/_bk_t5/dry_$T
  if [ -d "$D" ]; then
    mv "$D" "${D}_superseded_s291_$TS" && echo "  $T 旧数据 → $(basename ${D}_superseded_s291_$TS)" >> "$LOG"
  fi
done

# ── ④ 语法门 ──
for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  if $PY -m py_compile "$f" 2>>"$LOG"; then echo "  ✅ $f 语法 OK" >> "$LOG"
  else echo "  ❌ $f 语法错 ⇒ 中止" >> "$LOG"; exit 1; fi
done

# ── ⑤ 起两臂（argv 与原跑**逐字相同**，只把核错开以免互抢）──
setsid $PY _t5_short.py --tag t5FIX --N 80 --nvar 12 --m 23 --B 3 --steps 6000 \
    --cores 0-5 --mem-limit-gb 9.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.375 --burst-km 1 --diag-terms \
    < /dev/null > _w2_t5_short_t5FIX.log 2>&1 &
echo "  已起 t5FIX（--ed-eta 0.375 --burst-km 1 --diag-terms）" >> "$LOG"

sleep 25
setsid $PY _t5_short.py --tag t5BKMo --N 80 --nvar 12 --m 23 --B 3 --steps 3000 \
    --cores 6-11 --mem-limit-gb 7.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --burst-km 1 --diag-terms \
    < /dev/null > _w2_t5_short_t5BKMo.log 2>&1 &
echo "  已起 t5BKMo（--burst-km 1 --diag-terms）" >> "$LOG"

# ── ⑥ 复验 argv（**证明开关真的传进去了**）──
sleep 60
{
  echo "  ── 复验（60 s 后）──"
  for T in t5FIX t5BKMo t5ETAo; do
    P=$(ls /proc | grep -E '^[0-9]+$' | while read -r X; do
          tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null | grep -q -- "--tag $T " && echo "$X"; done | head -1)
    if [ -n "$P" ]; then
      echo "  [$T] pid=$P 历龄=$(ps -o etime= -p $P | tr -d ' ')"
      tr '\0' ' ' < /proc/$P/cmdline | grep -oE '\-\-ed-eta [0-9.]+|\-\-burst-km [0-9]+|\-\-diag-terms|\-\-B [0-9]+|\-\-steps [0-9]+' | sed 's/^/       /'
    else
      echo "  [$T] ⚠ 无进程"
    fi
  done
  free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG" 2>&1
echo "done" >> "$LOG"
