#!/bin/bash
# =============================================================================
# 生产链冒烟测试：从**当前**的 stage1_meltpool_c.i 生成生产输入并做 --check-input
# =============================================================================
# 为什么需要它：`stage1_meltpool_c.i` 是**生成器的源**，不是最终输入。
# 生产链是：
#     stage1_meltpool_c.i
#       --(frozen/gen_aniso_nonad.py)--> aniso_block.i      [2a+2b 各向异性块]
#       --(frozen/splice_aniso_nonad.py)--> stage1_meltpool_d.i
#       --(validated/make_jacfix.py)-->   ACGrGrPoly -> ACGrGrPolyJ
#       --(run_nonad_prod.sh 后续)-->     改输出名等 -> N.i
#
# 所以改完 `stage1_meltpool_c.i` 后，**必须重走这条链并让它解析通过**，
# 否则合入的改动可能在生成阶段就被静默吃掉（本项目踩过：splice 会重写文件头）。
#
# 本脚本**只生成 + `--check-input`，不跑仿真**（用户约束：只做 smoke test）。
#
# 用法： bash smoke_prod_chain.sh
# =============================================================================
set -eo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
ROOT="${ROOT:-/root/work/smokechain}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"

rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

# --- 哈希校验：冻结生成器必须与登记值一致（与生产脚本同一道闸）---
if ! HASHOUT=$( cd "$REPO/frozen" && sha256sum -c SHA256SUMS 2>&1 ); then
  echo "错误：frozen/ 哈希校验失败"; echo "$HASHOUT" | grep -v ': OK$'; exit 1
fi
echo "① 冻结生成器哈希校验通过"

cp "$REPO/frozen/gen_aniso_nonad.py"    .
cp "$REPO/frozen/splice_aniso_nonad.py" .
cp "$REPO/stage1_meltpool_c.i"          .
cp "$REPO/columnar_seeds.csv"           .

# --- 源输入自检（与生产脚本同一道闸）---
# ⚠ 前缀匹配，不要求闭合引号 —— 合入 Phase 3 后常量表多了 Omega0/wgb。
grep -qE "^[[:space:]]*constant_expressions = '0\.9 0\.036 0\.264" stage1_meltpool_c.i \
  || { echo "错误：溶质参数不是 Ti64 真实值"; exit 1; }
echo "② 源输入参数校验通过"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate ml
python3 gen_aniso_nonad.py --op-num 8 --out aniso_block.i > gen.log 2>&1 \
  || { echo "错误：gen 失败"; tail -5 gen.log; exit 1; }
python3 splice_aniso_nonad.py >> gen.log 2>&1 \
  || { echo "错误：splice 失败"; tail -5 gen.log; exit 1; }
echo "③ 各向异性块生成 + splice 完成"

conda activate moose
python3 "$REPO/validated/make_jacfix.py" \
        --src stage1_meltpool_d.i --out stage1_meltpool_d.i.jac --diff >> gen.log 2>&1 \
  || { echo "错误：jacfix 失败"; tail -8 gen.log; exit 1; }
mv stage1_meltpool_d.i.jac stage1_meltpool_d.i
echo "④ 雅可比补全核已替换"

# --- ⑤ 合入的改动**还在不在**（这是本脚本最要紧的一步）---
echo
echo "⑤ 合入改动存活检查："
python3 - <<'PY'
import sys
t = open("stage1_meltpool_d.i", encoding="utf-8").read()
chk = [
    ("分配项由 h_solid 驱动", "A_part*c^2*min(1, 2*(gr0^2" in t),
    ("独立偏析项 Omega0",     "Omega0/wgb" in t),
    ("常量表含 Omega0/wgb",   "Omega0 wgb" in t),
    ("M 的分母 f_cc 已同步",  "/ (k_c + 2*A_part*min(1, 2*S_eta2))" in t),
    ("ACGrGrPolyJ 已替换",    "type = ACGrGrPolyJ" in t),
    ("无裸 ACGrGrPoly 残留",  "\n    type = ACGrGrPoly\n" not in t),
    ("AMR 已启用",            "[Adaptivity]" in t),
    ("AMR 指示量是节点型",     "variable = S_eta2_aux" in t
                              and "family = LAGRANGE" in t),
    ("仍无 elementid",        "elementid" not in t),
    # 拖曳项：8 个 AllenCahn(f_loc)；`f_name = f_loc` 会数到 9（多一个是 SplitCHParsed）
    ("溶质拖曳项已补",         t.count("type = AllenCahn") == 16),
    ("拖曳项指向 f_loc",       t.count("f_name = f_loc") == 9),
]
ok = True
for name, good in chk:
    print(f"    {'✅' if good else '❌'} {name}")
    ok &= good
if not ok:
    print("\n  ❌ 有改动在生成链上丢失了 —— 合入没真正生效")
    sys.exit(1)
print("    全部通过")
PY

# --- ⑥ 语法检查 ---
echo
echo "⑥ --check-input："
timeout 900 "$MOOSE" -i stage1_meltpool_d.i --check-input 2>&1 \
    | sed "s/\x1b\[[0-9;]*m//g" | tail -8
