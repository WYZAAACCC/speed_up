#!/bin/bash
# _r51_b62q.sh —— R51 **方案 B″**：只把**变体对**从 `1,3` 换成 `1,2`
#
# ## 为什么（`BLOCK_SELFAC.md` §7.2j，实测）
# B′（9 µm 盒 / 变体 1&3）仍然失败：**引擎精确判据 t=0 接触面 = 963**。
# 把盒从 6 µm 加到 9 µm **没用** ⇒ 根因不是盒子，是**两块长轴夹角**：
#   变体 1 & 3 = **58.80°** ⇒ 引擎的 `c0 − d_b·a_b` 对称摆放把两个质心拉到 0.88 µm
#                             （< 半长 1.00 µm）⇒ 必然重叠；
#   变体 1 & 2 = ** 5.26°** ⇒ 长轴近乎平行 ⇒ 摆放能真正分开。
# 而且 `n*(1)·n*(2) = −0.996`（**惯习面反平行**）⇒ **物理上就是经典自协调对**
# ⇒ 用它做"两块相互影响"比用 1&3 **更该做**。
#
# ## 预登记判据（先写死）
#   J-0  `nf2(t=0) == 0`（两块初始不接触）—— **不过就作废**
#   J-1  `t/Δx = 10.16 ≥ 10`
#   J-2  `nslab_n == M`（或去重场数 == M）
#   J-3  `nf2` 随步数单调增（两块真的开始互相影响）
#   J-4  `box_touch_core == 0` 全程
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

MODE="${1:-smoke}"
case "$MODE" in
  smoke) STEPS=60 ;;
  full)  STEPS=900 ;;
  *) echo "用法: $0 [smoke|full]"; exit 2 ;;
esac

echo "=== R51 b62q 模式=$MODE steps=$STEPS  $(date '+%F %T')"
"$PY" -u _bk_exp.py --arm dry --N 144 --dx-nm 62.5 \
  --laths 1,1,1,2,2,2 --multi-block --block-gap-nm 1500 \
  --plate-L 2000 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps "$STEPS" --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
  --tag b62q --out _exp/_bk_mb > "_w2_r51_b62q_${MODE}.log" 2>&1
rc=$?
echo "=== R51 b62q rc=$rc  $(date '+%F %T')"
echo "--- J-0 初始接触检查"
"$PY" _r51_b62chk.py _exp/_bk_mb/dry_b62q/series.csv 2>&1 | tail -3
exit $rc
