#!/bin/bash
# =============================================================================
# T9（六边形周期胞版）：三晶粒静态三叉晶界的 120° 力平衡
# =============================================================================
# 审计判据：「三叉角误差 ≤ 5°；无伪第三相增长」
#
# ## 为什么必须换域
#
# 120° 是 Herring 力平衡在三条等晶界能下的结论 —— 一条**纯几何**、
# 与迁移率无关的约束。但它要求域与网格**与 3 重对称兼容**。
#
# 旧算例用**有界方形域**：4 重对称，与 3 重不兼容 ⇒ 体系必然破掉 3 重，
# 落到一个由域/网格 4 重对称决定的平衡态。实测三档（域放大 23×、dx 减半）
# 都收敛到 ~103/106/150°，**与 120° 差 20~30°** —— 那是构型的病，不是模型的病。
#
# 正六边形有 6 重对称（含 3 重）⇒ 才可能与 120° 自洽。
#
# ## 几何：为什么「等边三角形种子」给出恰好 120°
#
# 三点 Voronoi 的三条边是三角形三边的**垂直平分线**，交于**外心**。
# 外心发出的三条射线之间的夹角 = 180° − 对应内角。
# 等边三角形内角 60° ⇒ **三个夹角恰好 120/120/120** ✓
#
# ⚠ 但要**相对网格旋转一个角度**（这里用 17°）：旋转 0° 时晶界与网格轴平行，
#   数值各向异性被对称性掩盖、就测不出来了。
#
# 用法： bash run_t9_hex.sh
#   TRI=eq41 N=60 R=5e-6 bash run_t9_hex.sh     # 换旋转角/网格
# =============================================================================
set -eo pipefail

# ⚠ 必须激活 conda（MOOSE 的 libMesh/PETSc/WASP 来自 conda 的 moose-dev；
#   ParsedMaterial 的 LLVM JIT 要 mpicxx）。不用 `set -u` —— conda 的
#   activate 会引用未定义的 $CONDA_BUILD。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-/mnt/f/speedup_work/t9hex}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
TRI="${TRI:-eq17}"
N="${N:-40}"
R="${R:-5e-6}"
T_END="${T_END:-1.0e-3}"
SEED_SCALE="${SEED_SCALE:-0.3}"     # 六边形外接圆半径 5 µm ⇒ 种子缩到 2.7 µm 才在域内

rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

echo "=== 1. 生成六边形网格 ==="
python3 "$HERE/make_hex_mesh.py" --out hex.msh --n "$N" --r "$R"

echo
echo "=== 2. 生成 T9 算例（等边三角形种子，旋转 $TRI）==="
python3 "$HERE/make_t9.py" --out t9hex.i --tri "$TRI" \
        --hex-mesh 1 --seed-scale "$SEED_SCALE" \
        --t-end "$T_END" --seeds-out seeds3.csv

echo
echo "=== 3. 跑 ==="
timeout 3600 "$MOOSE" -i t9hex.i > run.log 2>&1 || true
echo "  rc=$?   末步：$(grep -a '^Time Step' run.log | tail -1)"

echo
echo "=== 4. 量三叉角 ==="
python3 "$HERE/analyze_t9.py" t9hex_exo.e

echo
echo "产物：$ROOT/（hex.msh / t9hex.i / t9hex_exo.e / run.log）"
