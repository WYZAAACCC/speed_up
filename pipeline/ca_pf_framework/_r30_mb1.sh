#!/bin/bash
# _r30_mb1.sh —— ★ R31 **MB-1 多块相遇实验**（目标第 (2) 项的第一个仿真）
#
# 物理问题（`BLOCK_SELFAC.md §7.1` 的 **P-SA-2**）：
#   一个块在**遇到另一个块**时会不会停下？（R30 已证：单变体盒子里**没有任何
#   停止机制**，板条一直长到盒壁 —— `dry_cl1b` step2000 撞壁。）
#
# 两臂（配对：**唯一差别是有没有邻居**）：
#   mb1  = 2 块（V1×3 + V3×3），t=0 由**精确判据**确认分离（异变体接触面 = 0）
#   mb1s = 1 块（V1×3），同盒同种子同步数，**没有邻居** ⇒ 预期长到盒壁（负对照）
#
# 几何（扫描实测选定，`_r30_gapscan2.sh`）：
#   N=96 / Δx=125 nm / 盒 12 µm；种子 plate-L=1600 nm、W=700 nm、T=635（物理 510）
#   ⇒ 板条会在跑的过程中沿**各自的 a** 长到相遇（这是"相遇"的正确装置：
#     真实板条本来就是从小核长大的）。
#
# 判据（预先写死，跑之前就定）：
#   P-SA-2a  mb1 的 `a_lath`（长轴跨度）出现**平台**，且平台期间母相仍存在（Vt 远小于盒）
#   P-SA-2b  mb1 的 `nf2`/`f2_area` 从 0 **单调增**（两块确实接触上了）
#   P-SA-2c  负对照 mb1s 在**同一步数**内 `a_lath` 不出现平台（或平台出现在撞壁之后）
#   P-SA-2d  两臂的 `E_el_J` 趋势不同（弹性相互作用存在）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

COMMON="--arm dry --N 96 --dx-nm 125 --plate-L 1600 --plate-W 700 \
  --plate-T 635 --plate-t-physical 510 --gamma0 0.25 --beta-h 6.477 \
  --norm-smooth 0 --reinit-dt 1e-4 --steps 1500 --every 20 --snap-every 200 \
  --pair-every 20 --nthreads 4"

"$PY" -u _bk_exp.py $COMMON --laths 1,1,1,3,3,3 --multi-block --block-gap-nm 5000 \
  --tag mb1 --out _exp/_bk_mb > _w2_r31_mb1.log 2>&1 &
P1=$!
"$PY" -u _bk_exp.py $COMMON --laths 1,1,1 --multi-block --block-gap-nm 5000 \
  --tag mb1s --out _exp/_bk_mb > _w2_r31_mb1s.log 2>&1 &
P2=$!
echo "已启动：mb1 pid=$P1   mb1s pid=$P2"
wait $P1; echo "mb1  结束 rc=$?"
wait $P2; echo "mb1s 结束 rc=$?"
echo "=== R31 MB-1 DONE $(date '+%F %T') ==="
