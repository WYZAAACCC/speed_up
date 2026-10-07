#!/bin/bash
# _r49_dx62c.sh —— R49：Δx=62.5 nm 的对照臂，**最终版**
#
# ## 为什么跑了两遍才定（记账，避免以后重复踩）
# 第 1 版（`_r47_dx62.sh`）：`--every 40 --snap-every 250`，旧代码把快照块放在
#   `--every` 门里 ⇒ 实际快照间隔 **lcm(40,250)=1000**，1500 步只会有 3 个快照
#   ⇒ 分不开初始瞬态、没有误差棒。**在 360 步处杀掉**（R30_AUDIT_LEDGER §20）。
# 第 2 版（`_r49_dx62b.sh`）：快照门已修（`--snap-every 40`），但它起在
#   `ed_by_face` **扩展出 p90/max 之前**（Python 模块在进程启动时读入）
#   ⇒ 这条臂**不会有** `dG_tip_p90/dG_tip_max` 列，而这两列正是 R48 点名
#   要的受控检验量。**在 240 步处杀掉**（§22）。
# 第 3 版（本文件）：两者都带上。
#
# ## 这条臂要同时回答三件事（**一次跑，三个判据**）
#   R-1  `tip/side/wide` 三个面族的速率**量级**与 mb1s（Δx=125）同阶
#   R-2  `t/Δx` 从 5.08 → 10.16，几何解析更好；速率若显著变化 ⇒ 记账
#   R-3  `wide` 是否仍为负（退湿/变薄）
#   **R-4（R48 遗留的受控检验，本版新增）**：在**同一个算例**上，
#        面位置速率 与 `dG_tip` 的 **中位 / p90 / max** 三个统计量哪个对得上
#        —— 判"中位数不预测面运动（R46b）"到底是口径没定对，还是机理另有其因。
#        ⚠ R48 的 68× 对账之所以只能给量级，就是因为 `dG_tip` 取自 `dry_r45sm`
#        而速率取自 `mb1s`，**不是同一个算例**。这一版把它做在同一个算例上。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

rm -rf _exp/_bk_mb/dry_mb1s62          # 清掉口径不同的前两版产物

"$PY" -u _bk_exp.py --arm dry --N 96 --dx-nm 62.5 \
  --laths 1,1,1 --multi-block --block-gap-nm 0 \
  --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps 1500 --every 40 --snap-every 40 --pair-every 40 --nthreads 3 \
  --tag mb1s62 --out _exp/_bk_mb > _w2_r49_mb1s62c.log 2>&1
echo "=== R49 mb1s62(v3) DONE rc=$? $(date '+%F %T') ==="
