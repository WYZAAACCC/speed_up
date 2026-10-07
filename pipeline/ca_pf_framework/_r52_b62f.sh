#!/bin/bash
# _r52_b62f.sh —— R52 **正式跑**：第一个同时满足用户条件 1/2/3/4 的构型
#
# ## 为什么现在才敢跑
# 前五次冒烟全部因"两块在 t=0 就已接触"而作废（`BLOCK_SELFAC.md` §7.2m）。
# R52 查出根因（**P1-30**）：布局公式 `_cb = c0 − _d·a_b`（`_d` 带符号）
# **只在两块长轴近乎平行时**才把它们分到 c0 两侧；
# V1&V2 的长轴近乎**反平行**（`a_1·a_0 = −0.996`）⇒ 两块心落到**同一点**。
# 修法：块心沿**固定布局轴**排开（间距精确），生长方向再翻成指向 c0 的一侧。
# 正对照（`_r52_b62s.sh`，20 步冒烟）：
#   J-0a 日志块心距 = 3007 nm（请求 3000）✅
#   J-0b 落盘实测     = 2999 nm ✅
#   J-0c `nf2(t=0)`   = **0** ⇒ "✅ 真正分离" ✅
#
# ## 满足的四条
#   1 解析板条：`t/Δx = 10.16`（§33 判据 ≥10）
#   2 堆成块  ：每块 3 根同变体板条沿各自 n* 堆叠（跨度 3.81 µm）
#   3 多块互影响：2 块（V1×3 + V2×3），块心距 **3000 nm**、端面间隙 1000 nm，
#                且 V1/V2 是**经典自协调对**（`n*` 反平行）
#   4 本机可行：N=144 / 盒 9 µm / nreg=7 ⇒ ≈4.7 GB、≈10.6 秒/步、900 步 ≈2.6 h
#
# ## 预登记判据（跑完照此判，**不许事后改**）
#   J-0 `nf2(t=0) == 0`
#   J-1 `t/Δx = 10.16 ≥ 10`
#   J-2 `nslab_n == M`（或去重场数 == M）⇒ 两块都堆成块
#   J-3 `nf2` 随步数单调增 ⇒ 两块真的开始互相影响（P-SA-2 的前提）
#   J-4 `box_touch_core == 0`（旧 `box_touch` 只报不判）⇒ 没撞壁
#   J-5 累积对账（`_r49_samearm.py`）：tip/side 的 `Σv·Δstep / (Δsep/2)` ∈ [0.5, 2]
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

TAG=b62f
rm -rf "_exp/_bk_mb/dry_$TAG"
echo "=== R52 $TAG 启动 $(date '+%F %T')"
"$PY" -u _bk_exp.py --arm dry --N 144 --dx-nm 62.5 \
  --laths 1,1,1,2,2,2 --multi-block --block-gap-nm 3000 \
  --plate-L 2000 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps 900 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
  --tag "$TAG" --out _exp/_bk_mb > "_w2_r52_${TAG}.log" 2>&1
rc=$?
echo "=== R52 $TAG 结束 rc=$rc $(date '+%F %T')"
