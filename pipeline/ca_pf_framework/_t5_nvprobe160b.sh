#!/bin/bash
# _t5_nvprobe160b.sh --- N=160 峰值 RSS 实测（修正版：去掉 _t5_short.py 不认的 --nuc-init）
#
# 上一次失败原因：`--nuc-init 0` 不在 `_t5_short.py` 的透传列表里 ⇒
#   `_t5_short.py: error: unrecognized arguments: --nuc-init 0`，**根本没进入构造**
#   （`time -v` 只报了 14 MB / 0.24 s —— 这正是"量具报了个假数"的典型，
#    判据：**RSS < 200 MB 就说明没构造**，不得当成测量结果）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_nvprobe160b.log
: > "$LOG"
{
  echo "════ N=160 峰值 RSS 实测（修正版） $(date '+%m-%d %H:%M:%S') ════"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

for M in 16 48; do
  TAG=nvq$M
  rm -rf "_exp/_bk_t5/dry_$TAG" 2>/dev/null
  echo "── nv=1×$M=$M ──" >> "$LOG"
  /usr/bin/time -v $PY _t5_short.py --tag $TAG --N 160 --nvar 1 --m $M --B 0 \
      --steps 1 --nthreads 4 --cores 4-7 --mem-limit-gb 16 --every 1 \
      --snap-every 1000 --pair-every 1000 --ckpt-every 0 --no-nucleation \
      > _w2_t5_short_$TAG.log 2> _w2_t5_time_$TAG.txt
  RSS=$(grep 'Maximum resident set size' _w2_t5_time_$TAG.txt | grep -oE '[0-9]+')
  EL=$(grep 'Elapsed (wall clock)' _w2_t5_time_$TAG.txt | sed 's/.*): //')
  {
    echo "    RSS = ${RSS} kB = $(echo "scale=1; ${RSS:-0}/1048576" | bc) GB   用时 $EL"
    grep -a '数组\|不可用\|Error\|Traceback\|error' _w2_t5_short_$TAG.log | head -3 | cut -c1-140 | sed 's/^/      /'
    if [ -n "$RSS" ] && [ "$RSS" -lt 200000 ]; then
      echo "      ⚠⚠ RSS < 200 MB ⇒ **没进入构造**，本点作废（不得当测量结果）"
      tail -2 _w2_t5_short_$TAG.log | cut -c1-140 | sed 's/^/      /'
    fi
  } >> "$LOG"
  free -m | sed -n 2p | awk '{printf "    跑后：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"
  sleep 3
done
echo "done $(date '+%H:%M:%S')" >> "$LOG"
