#!/bin/bash
# _r51_b62.sh —— R51 **方案 B**：分辨率合规的"两块相互影响"盒子（用户条件 1+2+3+4）
#
# ## 设计依据
# * `R30_AUDIT_LEDGER.md` **§33**：要复现板条各向异性必须 **`t_phys/Δx ≳ 8`**
#   ⇒ `t_phys = 510 nm` ⇒ **Δx ≤ 63 nm**。本臂取 **Δx = 62.5 nm**（`t/Δx = 10.16`）。
# * `BLOCK_SELFAC.md` **§7.2e**：`eng_mb2` 的 **12 层堆叠跨度 7.62 µm**
#   **装不进** 6 µm 盒（引擎实测余量 −0.81 µm）⇒ 同 N 下只能放 **6 层**。
# * `BLOCK_SELFAC.md` **§7.2c** 实测标度律：`N=96 / nreg=7` ⇒ **≈3.5 秒/步、≈1.1 GB**
#   ⇒ 900 步 ≈ **0.9 h**（可与其他臂并行）。
#
# ## 与 `dry_mb1L` 的差别（**只差分辨率与盒**）
#   dry_mb1L : N=96 / Δx=125 nm / 盒 12 µm / `--block-gap-nm 5000`
#   b62      : N=96 / Δx=62.5 nm / 盒 6 µm / `--block-gap-nm 1800`
# ⚠ **记账**：gap 也必须缩小（同 N 下盒减半）⇒ 这是"Δx + 盒 + 间距"的混合对照。
#   可接受的理由：本臂回答的是**"在分辨率合规的盒子里，两块能不能互相影响"**，
#   不是"复现 mb1L 的读数"。
#
# ## 满足的四条
#   1 能解析板条：`t/Δx = 10.16`（§33 判据 ≥10）✅
#   2 板条堆成块：每块 3 层同类板条沿 n* 堆叠（`--laths 1,1,1` / `3,3,3`）✅
#   3 多块互相影响：两块（变体 1 与 3）分开摆放、间距 1800 nm（在弹性相互作用范围内）✅
#   4 本机可行：≈1.1 GB / ≈3.5 秒/步 / 900 步 ≈0.9 h ✅
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

MODE="${1:-smoke}"
case "$MODE" in
  smoke) STEPS=120 ;;
  full)  STEPS=900 ;;
  *) echo "用法: $0 [smoke|full]"; exit 2 ;;
esac

echo "=== R51 b62 模式=$MODE steps=$STEPS  $(date '+%F %T')"
"$PY" -u _bk_exp.py --arm dry --N 96 --dx-nm 62.5 \
  --laths 1,1,1,3,3,3 --multi-block --block-gap-nm 1800 \
  --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps "$STEPS" --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
  --tag b62 --out _exp/_bk_mb > "_w2_r51_b62_${MODE}.log" 2>&1
rc=$?
echo "=== R51 b62 rc=$rc  $(date '+%F %T')"
exit $rc
