#!/bin/bash
# _r115_fpctrl.sh —— **6 块盒子里的保面机制对照**（`--facet-proj 0` vs `10`）。
#
# ## 为什么必须跑（本轮的**新观测**，不是预设）
#
# `_r114_prog.sh` 读到：`saPair` 在 **step 20** 时
#   `nblk_sig` 从 **6 → 11**、`blk_nprof` 从 `2/2/2/2/2/2` 变成 `2/1/1/1/…/1`
# ⇒ **播好的"2 根一块"在 20 步内就裂成了单根**。
#
# 这直接冲击**用户条件 ②**（"多个马氏体板条可以正常生长堆叠形成块"）——
# 而且是在**已经通过 t=0 验收**（`nf2(t=0)=0`、`nblk_sig=6`、`blk_nprof=2/2/2/2/2/2`）的盒子里。
#
# **第一嫌疑是保面机制**：`facet_project()` 把每个场的体内点云投影成一个盒子，
# `excl` 只排除"同变体**其他场**的膨胀掩码"（`pad=2`）。
# 若排除不够 ⇒ 相邻两根的盒子互相"削" ⇒ 中间出现缝隙 ⇒ **连通分量一分为二**。
#
# ## 设计（**严格单变量**）
#   与 `saOdd` **逐项相同**（同 ODD 集、同几何、同步数、同线程），**只差 `--facet-proj`**。
#     `saOdd`     —— `--facet-proj 10`（已在跑）
#     `saOddFp0`  —— `--facet-proj 0`（本脚本）
#
# ## 预登记判据
#   **F-1** `--facet-proj 0` 臂的 `nblk_sig` **保持 6**（不裂）
#           ⇒ 裂块是**保面机制**造成的（机制缺陷，要修）
#   **F-2** 若两臂**都裂** ⇒ 与保面无关，是别的原因（需另查：γ_RS 驱动？F3 界面数值耗散？）
#   **F-3** 两臂 `nf2(t=0) == 0` 且 `nblk_sig(t=0) == 6`（隔离有效）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
ODD="1,1,3,3,5,5,7,7,9,9,11,11"

rm -rf _exp/_bk_mb/dry_saOddFp0
echo "=== R115 保面对照开始 $(date '+%F %T')"
$PY -u _bk_exp.py --arm dry --N 112 --dx-nm 62.5 \
  --plate-L 600 --plate-W 350 --plate-T 510 --plate-t-physical 400 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --laths "$ODD" --multi-block --block-gap-nm 1200 \
  --facet-proj 0 --steps 400 --every 20 --snap-every 20 --pair-every 20 \
  --nthreads 3 --tag saOddFp0 --out _exp/_bk_mb > _w2_r115_saOddFp0.log 2>&1
echo "=== R115 结束 rc=$? $(date '+%F %T')"
