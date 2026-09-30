#!/bin/bash
# _r30_mb1L.sh —— R40：**MB-1 的长步数迭代**（P1-19/P1-24 的直接产物）
#
# ## 为什么重跑（读判决，不要读动机）
# * P1-24 查明：旧读法里的"撞壁"是**孤儿伪影**（3/7 → 0/7）；`mb1s` 的**核心**
#   1500 步只从 1775 长到 **2879 nm**（≈0.7 nm/步），**根本没到极限**。
# * ⇒ P-SA-2a 要判的是"**块停住没有**" ⇒ 必须跑到**核心出现平台**为止。
#   按 0.7 nm/步、要从 2.9 µm 长到接近盒的一半（6 µm）需要 **~4400 步** ⇒ 取 **6000 步**。
#
# ## 与 R31 的 MB-1 **逐项相同**，只改两处（有意为之，必须记账）
#   ① `--steps 1500 → 6000`（唯一的目的：跑到平台）
#   ② `--snap-every 200 → 250`（6000/250 = 24 个快照 ⇒ 离线重算的点够密）
#   ⚠ 其余（盒、种子、`--beta-h`、`--block-gap-nm`、`--nthreads`）**一个字都没动**。
#
# ## 判据（预先登记，与 R31 **同一套**，另加两条）
#   P-SA-2a  mb1L 的**核心** a 跨度出现平台（rate_late/rate_early < 0.25）
#            **且** `box_touch_core == 0`（孤儿免疫的撞壁判据，R39 新增）
#   P-SA-2b  `nf2` 从 0 增到 >0
#   P-SA-2c  负对照 mb1Ls **不出现**平台（或其平台与 `box_touch_core=1` 同时）
#   ★ P-SA-2e（**新**）两臂的**核心**长轴差随时间**单调扩大**（邻居效应增强）
#   ★ P-SA-2f（**新**）两臂的核心 a 跨度都**远小于**盒半宽（⇒ 排除撞壁解释）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

COMMON="--arm dry --N 96 --dx-nm 125 --plate-L 1600 --plate-W 700 \
  --plate-T 635 --plate-t-physical 510 --gamma0 0.25 --beta-h 6.477 \
  --norm-smooth 0 --reinit-dt 1e-4 --steps 6000 --every 40 --snap-every 250 \
  --pair-every 40 --nthreads 3"

"$PY" -u _bk_exp.py $COMMON --laths 1,1,1,3,3,3 --multi-block --block-gap-nm 5000 \
  --tag mb1L --out _exp/_bk_mb > _w2_r40_mb1L.log 2>&1 &
P1=$!
"$PY" -u _bk_exp.py $COMMON --laths 1,1,1 --multi-block --block-gap-nm 5000 \
  --tag mb1Ls --out _exp/_bk_mb > _w2_r40_mb1Ls.log 2>&1 &
P2=$!
echo "已启动：mb1L pid=$P1   mb1Ls pid=$P2  $(date '+%F %T')"
wait $P1; echo "mb1L 结束 rc=$?"
wait $P2; echo "mb1Ls 结束 rc=$?"
echo "=== R40 MB-1L DONE $(date '+%F %T') ==="
