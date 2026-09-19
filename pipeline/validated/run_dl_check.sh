#!/bin/bash
# =============================================================================
# 缺口 #3 修复第 3 条（`D_L` 子网格闭合）的验收
# =============================================================================
# ## 修的是什么
#
# 生产工作点上溶质边界层 `δ_c = D_L/V = 4.2 nm`，比 `dx = 1 µm` 小 238 倍
# ⇒ 网格不可解析 ⇒ 那层被摊到 ~dx 宽 ⇒ 实测 `k_eff = 0.999015`
#   vs 物理 0.6549 ⇒ **界面排出的溶质被低估 350 倍 ⇒ 微偏析被低估 350 倍**。
#
# 取 `D_L ≥ 2·V_scan·dx = 1.2e-6`（`δ_c = 2 µm`、`ξ/δ_c = 1`，正是抗截留项
# 残差最小的那一档）。**精确关系 `c_max − c0 = 2A·c0/k_c` 与 `D_L` 无关**
# ⇒ 放大只是把亚网格的那层变成可解析的，不引入新近似。
#
# ## 判据
#
#   ① **T6 仍然通过**：`D = M·∂²f/∂c²` 在三态逐点等于输入定义；
#      **且 `D_S`/`D_GB` 必须逐位不变**（这是「不影响 `s·δ·D_GB` 可观测量」的依据）
#   ② **生产链走通 + 短冒烟不崩**
#   ③ **代价必须记账**：`M` 大 476 倍会压自适应步长 ⇒ 实测墙钟倍数
#
# ⚠ 用户约束：只做 smoke test（缩小网格、极短时间）。
#
# 用法： bash run_dl_check.sh
# =============================================================================
set -eo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
ROOT="${ROOT:-/root/work/dlchk}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
DL="${DL:-1.2e-6}"
DS=4e-13; DGB=4e-10
NX="${NX:-86}"; NY="${NY:-30}"
END="${END:-2e-6}"
TMO="${TMO:-420}"

rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

echo "=== ① 生成候选源 + 走生产链 ==="
python3 "$HERE/make_dl_prod.py" --src "$REPO/stage1_meltpool_c.i" \
        --out "$ROOT/stage1_meltpool_c.i" --dl "$DL" 2>&1 | tail -8 | sed 's/^/    /'
cp "$REPO/frozen/gen_aniso_nonad.py" "$REPO/frozen/splice_aniso_nonad.py" .
cp "$REPO/columnar_seeds.csv" .

source /root/miniconda3/etc/profile.d/conda.sh
conda activate ml
python3 gen_aniso_nonad.py --op-num 8 --out aniso_block.i > gen.log 2>&1 \
  || { echo "❌ gen 失败"; tail -5 gen.log; exit 1; }
python3 splice_aniso_nonad.py >> gen.log 2>&1 \
  || { echo "❌ splice 失败"; tail -5 gen.log; exit 1; }
conda activate moose
python3 "$HERE/make_jacfix.py"  --src stage1_meltpool_d.i --out d.jac --diff >> gen.log 2>&1 \
  || { echo "❌ jacfix 失败"; tail -5 gen.log; exit 1; }
mv d.jac stage1_meltpool_d.i
python3 "$HERE/make_jacchain.py" --src stage1_meltpool_d.i --out d.jc >> gen.log 2>&1 \
  || { echo "❌ jacchain 失败"; tail -8 gen.log; exit 1; }
mv d.jc stage1_meltpool_d.i
DL_ACT=$(grep -oE "constant_expressions = '(1\.2e-06|2\.52e-09)" stage1_meltpool_d.i | grep -oE "(1\.2e-06|2\.52e-09)" | head -1)
echo "    链走通；[solute_mobility] 的 D_L = ${DL_ACT:-未识别}"

echo
echo "=== ② T6：分层关系 + D_S/D_GB 是否逐位不变 ==="
python3 "$HERE/check_D_layering.py" "$ROOT/stage1_meltpool_c.i" \
        --dl "$DL" --ds "$DS" --dgb "$DGB" 2>&1 | grep -E "OK |T6|⇒" | sed 's/^/    /'

echo
echo "=== ③ 生产链输出跑短冒烟 ==="
S=$(date +%s); RC=0
timeout "$TMO" "$MOOSE" -i stage1_meltpool_d.i Mesh/gen/nx=$NX Mesh/gen/ny=$NY \
    Executioner/end_time=1e-12 > smoke.log 2>&1 || RC=$?
sed "s/\x1b\[[0-9;]*m//g" smoke.log | grep -A3 "os_mean" | tail -3 | sed 's/^/    /'
echo "    rc=$RC  墙钟 $(( $(date +%s) - S ))s"

echo
echo "=== ④ 代价（A/B，同网格同 end_time，跑真实时间推进）==="
A="$ROOT/base_d.i"
cp "$ROOT/stage1_meltpool_d.i" A.i
python3 - A.i <<'PY'
import re, sys
p = "A.i"
t = open(p, encoding="utf-8").read()
t2, n = re.subn(r"constant_expressions = '1\.2e-06", "constant_expressions = '2.52e-09", t)
assert n == 1, f"还原 D_L 匹配 {n} 处"
open(p, "w", encoding="utf-8", newline="").write(t2)
PY
for tag in A:2.52e-09 B:1.2e-06; do
  n=${tag%%:*}; v=${tag##*:}
  cp "$ROOT/stage1_meltpool_d.i" "cmp_$n.i"
  python3 - "cmp_$n.i" "$v" <<'PY'
import re, sys
p, v = sys.argv[1], sys.argv[2]
t = open(p, encoding="utf-8").read()
t2, n = re.subn(r"constant_expressions = '(1\.2e-06|2\.52e-09)", f"constant_expressions = '{v}", t)
assert n == 1, f"D_L 替换匹配 {n} 处"
open(p, "w", encoding="utf-8", newline="").write(t2)
PY
  S=$(date +%s)
  timeout "$TMO" "$MOOSE" -i "cmp_$n.i" Mesh/gen/nx=$NX Mesh/gen/ny=$NY \
      Executioner/end_time=$END > "cmp_$n.log" 2>&1 || true
  T=$(( $(date +%s) - S ))
  ST=$(sed "s/\x1b\[[0-9;]*m//g" "cmp_$n.log" | grep -c "^Time Step" || true)
  DT=$(sed "s/\x1b\[[0-9;]*m//g" "cmp_$n.log" | grep -oE "dt = [0-9.e+-]+" | tail -1)
  echo "    D_L=$v  步数=$ST  末步 $DT  墙钟 ${T}s"
done
echo
echo "    ⇒ 放大 D_L 会压小自适应步长，**代价不是 1×**。生产上按实测算总账。"
