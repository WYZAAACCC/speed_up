#!/bin/bash
# _t5_final.sh --- ★★★★★★ 最终完整重跑（原条件 + 两个修复）
#
# ## 用户总目标第 5 项
# 「全部解决完以后就**按照和之前实验一样的初始条件继续做大实验**，
#   持续监控……直到以上所有的监控项都没有问题为止」
#
# ## 与 `t5N276F` 的唯一差异（**只多两个修复开关**）
#   + `--ed-eta 0.375`（**修法 A**：弹性罚能折减 = 塑性弛豫/TRIP）
#   + `--burst-km 1`   （**burst 修复**：KM 分数律）
#   + `--diag-terms`   （纯记账，读 `|Δed|`）
# ## 预期
#   核不再溶解 ⇒ 「一场一根」在**演化层面**也成立 ⇒ 长宽比/成块/块间影响/自协调随之改善。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python

# ── ① 先停掉慢速的严格版 dx 复核（其目的已由 t5DX64 达成），腾内存 ──
echo '── 停 t5DX32（严格版 dx 复核，目的已达成）──'
ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -v grep | while read -r PID REST; do
  case "$REST" in
    *"--tag t5DX32"*) echo "  KILL pid=$PID"; kill -9 "$PID" 2>/dev/null ;;
  esac
done
sleep 4
D=_exp/_bk_t5/dry_t5DX32
[ -d "$D" ] && mv "$D" "${D}_superseded_$(date +%m%d_%H%M)" && echo "  数据已改名保留"
echo '── 停后内存 ──'
free -m | sed -n 2p | sed 's/^/  /'

TAG=t5FIX
LOG=_w2_t5_$TAG.log
{
  echo "════ ★ 最终完整重跑 t5FIX（原条件 + 修法 A + burst 修复）════"
  echo "  与 t5N276F 唯一差异：+ `--ed-eta 0.375` + `--burst-km 1` + `--diag-terms`"
  echo "  配置：N=80 · nvar 12 · m 23 · B 3 · steps 6000 · elong 7.00 · overlap 62.5 · 断点续跑"
  echo "  预期：核不再溶解 ⇒ 一场一根（演化层面）⇒ 长宽比/成块/自协调改善"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" && echo "  ✅ $f 语法 OK" >> "$LOG" || { echo "  ❌ $f 语法错" >> "$LOG"; exit 1; }
done

setsid $PY _t5_short.py --tag $TAG --N 80 --nvar 12 --m 23 --B 3 --steps 6000 \
    --cores 0-5 --mem-limit-gb 9.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.375 --burst-km 1 --diag-terms \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG" >> "$LOG"
sleep 290
{
  echo "  ── 290 s 后 ──"
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -- "--tag $TAG" | grep -v grep | awk '{print $1}' | head -1)
  if [ -n "$P" ]; then
    ps -o pid,etime,time,pcpu --no-headers -p "$P" | sed 's/^/     进程 /'
    echo "  ★ argv（关键：--ed-eta 0.375 与 --burst-km 1）:"
    tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null \
      | grep -oE '\-\-ed-eta [0-9.]+|\-\-burst-km [0-9]+|\-\-B [0-9]+|\-\-N [0-9]+' | sed 's/^/     /'
    echo "  ★ 构造横幅："
    grep -nE '总根数|体积是瓶颈|可容|块数口径' _w2_t5_short_$TAG.log 2>/dev/null | head -4 | cut -c1-170 | sed 's/^/     /'
  else
    echo "  ⚠ 未找到进程 ⇒ 日志尾部："; tail -6 _w2_t5_short_$TAG.log | cut -c1-155 | sed 's/^/     /'
  fi
  printf '  末步 = %s ｜ 事件 = %s ｜ 快照 = %s\n' \
    "$(tail -1 _exp/_bk_t5/dry_$TAG/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(grep -cE '模式 \*\*' _w2_t5_short_$TAG.log 2>/dev/null)" \
    "$(ls -1 _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | wc -l)"
  echo "  ── ★ Vt 轨迹（判"是否还在溶解"）──"
  grep -E '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -6 | cut -c1-118 | sed 's/^/     /'
  echo "  ── ★ 每档核数（burst 是否爆发）──"
  grep -oE 'T=[0-9.]+ K' _w2_t5_short_$TAG.log 2>/dev/null | sort | uniq -c | head -6 | sed 's/^/     /'
  free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
