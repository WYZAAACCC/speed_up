#!/bin/bash
# _t5_nvprobe160.sh --- ★ 在 N=160 上**直接实测**峰值 RSS，两点定斜率+截距 ⇒ nv_max
#
# 为什么必须实测：`_r579_report.py` 的 `nv_max` 用的是**数组清单**，
# 而实测 RSS ≈ 数组 × 2.4（构造期临时量 + FFT 工作区 + 解释器，不在清单里）。
# 这个因子此前只有 **N=80** 与 **N=160/nv=23** 两个侧面数据点，必须在本构型上量。
#
# 做法：只 **construction + 1 步**（不进入长跑），用 `/usr/bin/time -v` 取
#       **Maximum resident set size** ⇒ 两个 nv 点线性拟合 ⇒ 外推到 22 GB。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_nvprobe160.log
: > "$LOG"

{
  echo "════ N=160 峰值 RSS 实测（construction + 1 步） $(date '+%m-%d %H:%M:%S') ════"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

for M in 8 32; do
  TAG=nvp$M
  D=_exp/_bk_t5/dry_$TAG
  rm -rf "$D" 2>/dev/null
  echo "── nv=1×$M=$M ──" >> "$LOG"
  /usr/bin/time -v $PY _t5_short.py --tag $TAG --N 160 --nvar 1 --m $M --B 0 \
      --steps 1 --cores 0-3 --mem-limit-gb 18 --every 1 --snap-every 1000 \
      --pair-every 1000 --ckpt-every 0 --nuc-init 0 --no-nucleation \
      > _w2_t5_short_$TAG.log 2> _w2_t5_time_$TAG.txt
  grep -E 'Maximum resident set size|Elapsed \(wall clock\)' _w2_t5_time_$TAG.txt \
    | sed 's/^/    /' >> "$LOG"
  # 数组清单（引擎自己打印的，若在）
  grep -a '数组总计\|总根数\|块数口径' _w2_t5_short_$TAG.log | head -2 | cut -c1-150 | sed 's/^/    /' >> "$LOG"
  free -m | sed -n 2p | awk '{printf "    跑后内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"
  sleep 3
done

echo "" >> "$LOG"
echo "════ 结果 ════" >> "$LOG"
cat "$LOG"
