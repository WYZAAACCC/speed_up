#!/bin/bash
# _r248_projtest.sh —— ★ **统一假设检验**：`--facet-proj` 是否**压制了界面能效应**？
#
# ## 假设（由 `_r246`/`_r247` 逼出来）
# `_r246` 实测：**无** `--facet-proj` 时，γ_F3 改 **31.3×** ⇒ **29/31 步都分叉**（94%），
#   差异**单调增长** ⇒ **界面能确实进动力学**（`§138.3` 的推论得到支持）。
# 而 `_r225` 实测：**有** `--facet-proj 10` 时，γ_F3 改 1.815× ⇒ **只有 step 80 不同**。
#
# **⇒ 假设 H-1**：**`--facet-proj` 每步把 φ 场"投影/重写"，
#    而这一步与 `γ_F3` 无关 ⇒ 把 γ 引起的差异**抹掉**。**
#
# ## 若 H-1 成立，它统一解释本会话**一整串"量不到"**
# * `§99`/P1-42：投影把 `f3_area` 从 4.108 抹成 **0.000000**
# * `§142.1`：F3 占比从 t=0 的 11.8% 塌到 step 80 的 **0.9%**
# * `§132.5`：`ncmp` 的取向择优（把 `stk` 改 3 倍）量不到
# * `§135.2`：R165（F2 的 γ 改 9.3 倍）只有 **0.03%** 效应
# * `§143.5`/Q-17：`_r225` 只有 step 80 分叉
# ⇒ **而归档的"自协调"臂几乎全都带 `--facet-proj 10`！**
#
# ## 设计（**只加一个变量**：`--facet-proj 10`）
# 与 `_r246` 完全相同的几何与两臂（γ_F3 对比 ~31×），**唯一差别**是加 `--facet-proj 10`；
# 并保留**负对照**（同配置跑两次）。
#
# ## 判据（**先写死**）
# * **P-1** 负对照 `qHp` vs `qH2p`：必须**逐步逐位相同**。
# * **P-2** ★ **核心**：`qHp` vs `qCp` 的**分叉步数占比**。
#   - 若 **≈ 94%**（与无投影时相同）⇒ **H-1 被否**（投影不压制界面能效应）；
#   - 若 **显著下降**（例如 < 30%）⇒ **H-1 得到支持** —— 那是一条**重大发现**。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

# 与 `_r246` 逐字相同，**只多 `--facet-proj 10`**
GEO="--arm dry --N 32 --dx-nm 125 --laths 1,1 --gap-nm 0 --facet-proj 10 \
     --steps 30 --every 1 --snap-every 30 --pair-every 0 --nthreads 2 \
     --out _exp/_bk_q18"
rm -rf _exp/_bk_q18

echo "=== H-1 检验（加 --facet-proj 10）$(date '+%F %T') ==="
$PY -u _bk_exp.py $GEO --omega-mode ladder  --omega-max-deg 5.0  --tag qHp  > _w2_r248_Hp.log 2>&1 &
A=$!
$PY -u _bk_exp.py $GEO --omega-mode perstep --omega-max-deg 0.05 --tag qCp  > _w2_r248_Cp.log 2>&1 &
B=$!
$PY -u _bk_exp.py $GEO --omega-mode ladder  --omega-max-deg 5.0  --tag qH2p > _w2_r248_H2p.log 2>&1 &
C=$!
wait $A; echo "  qHp  rc=$?"
wait $B; echo "  qCp  rc=$?"
wait $C; echo "  qH2p rc=$?"
echo "=== 跑完 $(date '+%F %T') ==="
for f in _w2_r248_Hp.log _w2_r248_Cp.log _w2_r248_H2p.log; do
  printf '  %-22s Traceback=%s\n' "$f" "$(grep -c Traceback "$f" || true)"
done
