#!/bin/bash
# _r51_b62r.sh —— R51 **方案 B‴**：修掉"块心间距 < plate-L"这条小学算术
#
# ## 四次冒烟的共同教训（`BLOCK_SELFAC.md` §7.2l）
#   **`--block-gap-nm` 是"块心间距"，两块不重叠的条件是 `块心间距 > plate-L`。**
#   前三次分别给了 1800/1500/1500 而 plate-L = 1600/2000/2000 ⇒ **按定义就重叠**。
#   换盒（6→9 µm）、换变体对（1&3 → 1&2）**都没用**，因为与它们无关。
#
# ## 本方案
#   `--plate-L 2000` + **`--block-gap-nm 3000`** ⇒ 端面间隙 = 3000 − 2000 = **1000 nm** ✅
#   簇跨度 = 3000 + 2000 = 5000 nm；盒 9000 nm ⇒ 两侧各余 2000 nm ✅
#   变体对用 **1 & 2**（长轴夹角 5.26°、`n*·n* = −0.996` ⇒ 经典自协调对，§7.2j）
#
# ## 预算（§7.2c 实测标度律）
#   `N³·nreg/1e6 = 144³×7/1e6 = 20.9` ⇒ ≈10.6 秒/步、≈4.7 GB ⇒ 900 步 ≈ 2.6 h
#
# ## 预登记判据
#   J-0 `nf2(t=0) == 0` ｜ J-1 `t/Δx=10.16` ｜ J-2 `nslab_n == M`
#   J-3 `nf2` 单调增 ｜ J-4 `box_touch_core == 0`
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

echo "=== R51 b62r 模式=$MODE steps=$STEPS  $(date '+%F %T')"
"$PY" -u _bk_exp.py --arm dry --N 144 --dx-nm 62.5 \
  --laths 1,1,1,2,2,2 --multi-block --block-gap-nm 3000 \
  --plate-L 2000 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps "$STEPS" --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
  --tag b62r --out _exp/_bk_mb > "_w2_r51_b62r_${MODE}.log" 2>&1
rc=$?
echo "=== R51 b62r rc=$rc  $(date '+%F %T')"
echo "--- J-0 初始接触检查（必须 nf2(t=0)==0）"
"$PY" _r51_b62chk.py _exp/_bk_mb/dry_b62r/series.csv 2>&1 | tail -3
exit $rc
