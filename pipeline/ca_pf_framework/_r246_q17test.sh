#!/bin/bash
# _r246_q17test.sh —— ★ **Q-17 的决定性小实验**：γ_F3 的极端对比下，轨迹是"连续分叉"还是"偶发分叉"？
#
# ## 假设（`§143.5`，【推理】）
# 界面位置被**重初始化 + 面片投影**"钉"在网格上 ⇒ 小于半胞的位移差被抹掉
# ⇒ 两条轨迹在多数步上**逐位重合**，只在累积差跨过一个胞时才显出区别。
#
# ## 设计（**极端对比度**，小几何，秒级）
# * 几何：N=32 / Δx=125 nm / **`--laths 1,1`**（一个块、2 根同变体 ⇒ 必有 F3）/ gap 0
# * **臂 H**：`--omega-mode ladder --omega-max-deg 5.0`
#   ⇒ M=2 ⇒ Δθ = 5° ⇒ **γ_F3 = γ_RS(5°) = 0.2771**（**1.108×γ₀，倒挂**）
# * **臂 C**：`--omega-mode perstep --omega-max-deg 0.05`
#   ⇒ Δθ = 0.05° ⇒ **γ_F3 = γ_RS(0.05°) ≈ 0.0095**（0.038×γ₀）
# * **⇒ 对比度约 29×**（比 `_r225` 的 1.815× 强 16 倍）
# * **`--every 1 --steps 30`** ⇒ **逐步**读出，看分叉是连续还是偶发
#
# ## 判据
# * **Q-1** 两臂的 `gamma_RS` 确实差 ~29×（前置检查，`_r241` 同款）。
# * **Q-2** 逐步数出：**有多少步的物理列逐位相同**、**多少步不同**。
# * **Q-3** 若**连续多步**逐步分叉（差异单调增长）⇒ **假设被否**
#   （说明界面没被钉住，那 `_r225` 的 8/9 重合需另找解释）。
# * **Q-4** 若**只有零星几步**分叉 ⇒ **假设得到支持**。
# * **Q-5** 负对照：**同一配置跑两次**（同 γ）⇒ 必须**逐步逐位相同**
#   （否则"差异"里混了非确定性，实验无效）。⚠ 这一条最关键。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

GEO="--arm dry --N 32 --dx-nm 125 --laths 1,1 --gap-nm 0 \
     --steps 30 --every 1 --snap-every 30 --pair-every 0 --nthreads 2 \
     --out _exp/_bk_q17"
rm -rf _exp/_bk_q17

echo "=== Q-17 小实验 $(date '+%F %T') ==="
echo "--- 臂 H（ladder 5.0 ⇒ γ_F3=0.2771）---"
$PY -u _bk_exp.py $GEO --omega-mode ladder --omega-max-deg 5.0 --tag qH \
    > _w2_r246_H.log 2>&1 &
PH=$!
echo "--- 臂 C（perstep 0.05 ⇒ γ_F3≈0.0095）---"
$PY -u _bk_exp.py $GEO --omega-mode perstep --omega-max-deg 0.05 --tag qC \
    > _w2_r246_C.log 2>&1 &
PC=$!
echo "--- 臂 H2（**负对照**：与 H 完全相同，跑第二次）---"
$PY -u _bk_exp.py $GEO --omega-mode ladder --omega-max-deg 5.0 --tag qH2 \
    > _w2_r246_H2.log 2>&1 &
PH2=$!
wait $PH; echo "  H  rc=$?"
wait $PC; echo "  C  rc=$?"
wait $PH2; echo "  H2 rc=$?"
echo "=== 跑完 $(date '+%F %T') ==="
