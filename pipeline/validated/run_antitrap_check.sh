#!/bin/bash
# =============================================================================
# 抗截留项合入生产链的冒烟测试（不改生产源，用临时目录）
# =============================================================================
# ## 为什么必须走这条链
#
# `stage1_meltpool_c.i` 只是**生成器的源**，不是最终输入：
#     stage1_meltpool_c.i
#       --(gen_aniso_nonad.py)-->      aniso_block.i
#       --(splice_aniso_nonad.py)-->   stage1_meltpool_d.i   ← **splice 会重写文件**
#       --(make_jacfix.py)-->          ACGrGrPoly → ACGrGrPolyJ
# ⇒ 加在 `_c` 上的东西**可能在 splice 阶段被静默吃掉**（本项目踩过）。
#
# ## 判据
#
#   1. 8 个 `AntitrappingCurrent` 核 + 1 个 `at_susc` 材料**存活到 `_d`**
#   2. 原有的 11 项合入（Phase 3 / AMR / 拖曳）**全部仍在**
#   3. `--check-input` 通过
#   4. **生产源 `stage1_meltpool_c.i` 逐字节不变**（本脚本只在临时目录操作）
#
# ⚠ 用户约束：只做 smoke test（只生成 + 语法检查，**不跑仿真**）。
#
# 用法： bash run_antitrap_check.sh
# =============================================================================
set -eo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
ROOT="${ROOT:-/root/work/at_check}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
TMO="${TMO:-1200}"

# 生产源的哈希（用于判据 4）
SRC_HASH_BEFORE=$(sha256sum "$REPO/stage1_meltpool_c.i" | cut -d' ' -f1)

rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

# --- ① 在临时目录里造出「打了抗截留补丁的 _c 源」---
python3 "$REPO/validated/make_antitrap_prod.py" \
    --src "$REPO/stage1_meltpool_c.i" --out "$ROOT/stage1_meltpool_c.i" \
    > "$ROOT/patch.log" 2>&1 || { echo "❌ 补丁生成失败"; tail -5 "$ROOT/patch.log"; exit 1; }
echo "① 抗截留补丁已生成到临时目录（生产源未动）"
tail -6 "$ROOT/patch.log" | sed 's/^/     /'

# --- ② 冻结生成器哈希校验（与生产脚本同一道闸）---
if ! HASHOUT=$( cd "$REPO/frozen" && sha256sum -c SHA256SUMS 2>&1 ); then
  echo "❌ frozen/ 哈希校验失败"; echo "$HASHOUT" | grep -v ': OK$'; exit 1
fi
echo "② 冻结生成器哈希校验通过"

cp "$REPO/frozen/gen_aniso_nonad.py"    .
cp "$REPO/frozen/splice_aniso_nonad.py" .
cp "$REPO/columnar_seeds.csv"           .

grep -qE "^[[:space:]]*constant_expressions = '0\.9 0\.036 0\.264" stage1_meltpool_c.i \
  || { echo "❌ 溶质参数校验失败"; exit 1; }
echo "③ 源输入参数校验通过"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate ml
python3 gen_aniso_nonad.py --op-num 8 --out aniso_block.i > gen.log 2>&1 \
  || { echo "❌ gen 失败"; tail -5 gen.log; exit 1; }
python3 splice_aniso_nonad.py >> gen.log 2>&1 \
  || { echo "❌ splice 失败"; tail -5 gen.log; exit 1; }
echo "④ 各向异性块生成 + splice 完成"

conda activate moose
python3 "$REPO/validated/make_jacfix.py" \
        --src stage1_meltpool_d.i --out stage1_meltpool_d.i.jac --diff >> gen.log 2>&1 \
  || { echo "❌ jacfix 失败"; tail -8 gen.log; exit 1; }
mv stage1_meltpool_d.i.jac stage1_meltpool_d.i
echo "⑤ 雅可比补全核已替换"

# --- ⑥ 存活检查 ---
echo
echo "⑥ 合入改动存活检查："
python3 - <<'PY'
import sys
t = open("stage1_meltpool_d.i", encoding="utf-8").read()
chk = [
    # --- 本轮新增：抗截留 ---
    ("抗截留：8 个核",          t.count("type = AntitrappingCurrent") == 8),
    ("抗截留：F_at 材料",       t.count("property_name = F_at") == 1),
    ("抗截留：8 处引用 F_at",   t.count("f_name = F_at") == 8),
    ("抗截留：晶界抑制项在",     "(1-h_gb)" in t),
    ("抗截留：h_gb 已声明",      "material_property_names = 'h_gb'" in t),
    ("抗截留：核作用在 w 上",    t.count("    variable = w\n") >= 8),
    # --- 原有 11 项（防回归）---
    ("分配项由 h_solid 驱动",   "A_part*c^2*min(1, 2*(gr0^2" in t),
    ("独立偏析项 Omega0",       "Omega0/wgb" in t),
    ("常量表含 Omega0/wgb",     "Omega0 wgb" in t),
    ("M 的分母 f_cc 已同步",    "/ (k_c + 2*A_part*min(1, 2*S_eta2))" in t),
    ("ACGrGrPolyJ 已替换",      "type = ACGrGrPolyJ" in t),
    ("无裸 ACGrGrPoly 残留",    "\n    type = ACGrGrPoly\n" not in t),
    ("AMR 已启用",              "[Adaptivity]" in t),
    ("AMR 指示量是节点型",       "variable = S_eta2_aux" in t and "family = LAGRANGE" in t),
    ("仍无 elementid",          "elementid" not in t),
    ("溶质拖曳项已补",           t.count("type = AllenCahn") == 16),
    ("拖曳项指向 f_loc",         t.count("f_name = f_loc") == 9),
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

# --- ⑦ 语法/参数检查 ---
echo
echo "⑦ --check-input（最多 ${TMO}s）："
timeout "$TMO" "$MOOSE" -i stage1_meltpool_d.i --check-input 2>&1 \
    | sed "s/\x1b\[[0-9;]*m//g" | tail -8 || echo "    ⚠ 超时或被中断（见上）"

# --- ⑧ 生产源未被改动 ---
echo
SRC_HASH_AFTER=$(sha256sum "$REPO/stage1_meltpool_c.i" | cut -d' ' -f1)
if [ "$SRC_HASH_BEFORE" = "$SRC_HASH_AFTER" ]; then
  echo "⑧ ✅ 生产源 stage1_meltpool_c.i 逐字节未变（本脚本只在临时目录操作）"
else
  echo "⑧ ❌ 生产源被改动了！before=$SRC_HASH_BEFORE after=$SRC_HASH_AFTER"
  exit 1
fi
