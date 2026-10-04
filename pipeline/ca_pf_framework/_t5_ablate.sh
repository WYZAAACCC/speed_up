#!/bin/bash
# _t5_ablate.sh --- ★★★★★★ **单变量归因**：`t5FIX` 的"早期更差"来自 η 还是 KM 律？
#
# ## 为什么需要（步对齐比较的结论）
# `t5FIX`（η=0.375 **与** KM 律**同时开**）在 step 200/320/400 上四项指标**全都略差**
# （宽比 6.04 vs 6.54 · 瓣中位 3.0 vs 1.5）⇒ **但两个开关同时开 ⇒ 无法归因** ⚠
#
# ## 设计（**单变量**，各与 `t5N276F` 只差一个开关）
#   A 臂 `t5ETAo`：只 `--ed-eta 0.375`（**不传** `--burst-km`）⇒ 隔离**修法 A**
#   B 臂 `t5BKMo`：只 `--burst-km 1`（**η=1**）          ⇒ 隔离 **KM 律**
#   基准：`t5N276F`（两个都不开）
# ## 判据（**预先写死**）
#   在**同一 step** 上比较宽比/长厚/瓣中位/单块场：
#   * 若 **只有 `t5ETAo` 更差** ⇒ 归因**修法 A**（需调 η 或查拥挤机制）;
#   * 若 **只有 `t5BKMo` 更差** ⇒ 归因 **KM 律**（首档爆发 10 个核 vs 3 个 ⇒ 拥挤）;
#   * 若**两者都差** ⇒ **两个机制都在加剧拥挤** ⇒ 需同时处理。
#
# ⚠ 内存：每臂 N=80/nv=276 ≈ 5.3 GB ⇒ 先停掉**已完成使命**的验证臂（`t5BK1`/`t5ETA`）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_ablate.log

echo '── 停掉已完成使命的验证臂（数据改名保留，不删）──'
for T in t5BK1 t5ETA; do
  ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -v grep | while read -r PID REST; do
    case "$REST" in
      *"--tag $T"*) echo "  KILL $T pid=$PID"; kill -9 "$PID" 2>/dev/null ;;
    esac
  done
  D=_exp/_bk_t5/dry_$T
  [ -d "$D" ] && mv "$D" "${D}_superseded_$(date +%m%d_%H%M)" && echo "  $T 数据已改名保留"
done
sleep 4
echo '── 停后内存 ──'
free -m | sed -n 2p | sed 's/^/  /'

{
  echo "════ 单变量归因：t5ETAo（只 η）vs t5BKMo（只 KM 律）· 基准 t5N276F（都关）════"
  echo "  判据：谁更差就归因到谁；两者都差 ⇒ 两机制都在加剧拥挤"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

# A 臂：只 η
setsid $PY _t5_short.py --tag t5ETAo --N 80 --nvar 12 --m 23 --B 3 --steps 3000 \
    --cores 0-3 --mem-limit-gb 7.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.375 --diag-terms < /dev/null > _w2_t5_short_t5ETAo.log 2>&1 &
echo "  已起 A 臂 t5ETAo（只 --ed-eta 0.375）" >> "$LOG"
sleep 20
# B 臂：只 KM 律
setsid $PY _t5_short.py --tag t5BKMo --N 80 --nvar 12 --m 23 --B 3 --steps 3000 \
    --cores 4-7 --mem-limit-gb 7.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --burst-km 1 --diag-terms < /dev/null > _w2_t5_short_t5BKMo.log 2>&1 &
echo "  已起 B 臂 t5BKMo（只 --burst-km 1）" >> "$LOG"

sleep 280
{
  echo "  ── 280 s 后 ──"
  for T in t5ETAo t5BKMo; do
    P=$(ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -- "--tag $T" | grep -v grep | awk '{print $1}' | head -1)
    printf '  ★ %s：末步=%s 事件=%s ' "$T" \
      "$(tail -1 _exp/_bk_t5/dry_$T/series.csv 2>/dev/null | cut -d, -f1)" \
      "$(grep -cE '模式 \*\*' _w2_t5_short_$T.log 2>/dev/null)"
    if [ -n "$P" ]; then
      tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null \
        | grep -oE '\-\-ed-eta [0-9.]+|\-\-burst-km [0-9]+' | tr '\n' ' ' | sed 's/^/argv: /'
    else
      echo -n '⚠ 进程不在'
      tail -3 _w2_t5_short_$T.log | cut -c1-120 | tr '\n' '|'
    fi
    echo
  done
  echo "  ── ★ 每档核数（判 KM 律是否生效）──"
  for T in t5ETAo t5BKMo; do
    echo "     [$T] $(grep -oE 'T=[0-9.]+ K' _w2_t5_short_$T.log 2>/dev/null | sort | uniq -c | head -4 | tr '\n' ' ')"
  done
  echo "  ── ★ Vt 轨迹 ──"
  echo "     [t5ETAo 只η] $(grep -oE 'Vt=[0-9.]+' _w2_t5_short_t5ETAo.log 2>/dev/null | tail -6 | tr '\n' ' ')"
  echo "     [t5BKMo 只KM] $(grep -oE 'Vt=[0-9.]+' _w2_t5_short_t5BKMo.log 2>/dev/null | tail -6 | tr '\n' ' ')"
  free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
