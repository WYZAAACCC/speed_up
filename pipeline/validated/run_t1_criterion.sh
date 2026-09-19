#!/bin/bash
# =============================================================================
# T1 判据的**决定性正对照**：删掉一个**大项**，残差必须逐位不变
# =============================================================================
# 起因：早先的结论是「`-snes_test_jacobian` 的比值测的是残差数值条件，
#   对雅可比完备性不敏感」，证据是**五种结构不同的雅可比给出逐位相同的比值**。
#
# ⚠ 但那个证据有**致命的漏洞**：如果该比值是被 **FD 舍入误差**主导的
#   （病态缩放的方程组里很常见），那么它**本来就应该**对雅可比结构不敏感 ——
#   舍入误差取决于缩放与残差量级，与哪些项被删无关。
#   早先的正对照只删了 ~5e-7 的**相对小项**，量级远在舍入噪声之下
#   ⇒ 那个对照**没有排他性**，结论因此不可靠。
#
# 本实验的设计（消除上述漏洞）：
#   * **同一个二进制**（gb_jac-opt），只差输入里一行 `jac_mode`
#   * `full` = 生产用的完整雅可比
#   * `off`  = **故意**让 computeQpOffDiagJacobian 直接返回 0
#             ⇒ 整个 η–η 非对角块被删掉（量级最大的块之一）
#   * `computeQpResidual` **未被触碰** ⇒ 残差必须逐位相同（第 1 步验证）
#
# ⚠ **两个算例必须放在同一个目录里跑**：MOOSE 的 JIT 缓存在 CWD 的 `.jitcache`，
#   两个算例的 parsed 表达式完全相同 ⇒ 共用缓存后**只有第一次要付编译代价**。
#   实测分开跑要付 4 次（每次 5–15 分钟、且全程 I/O 等待），合起来只需 1 次。
#
# 判读：
#   比值显著上升  ⇒ 该判据**对完备性敏感**，早先的结论错，T1 的 1e-5 判据可用
#   比值一位不变  ⇒ 早先的结论成立，判据确实无效，必须换判据
#
# 用法： bash run_t1_criterion.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BASE="${BASE:-/root/work/prod_merged}"
SRCI="${SRCI:-N.i}"
ROOT="${ROOT:-/root/work/t1crit}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
# ⚠ **网格覆盖必须走嵌套路径 `Mesh/gen/nx`**：生产输入的 Mesh 是
#   `[Mesh][gen] type=GeneratedMeshGenerator`，写 `Mesh/nx` 会被 MOOSE 判成
#   **未使用参数**并直接 abort（实测踩过：`unused parameter 'Mesh/nx'`）。
#   生产网格是 430×150，直接用太贵；这里缩到 108×38（长宽比 2.84 ≈ 生产的 2.87）。
NX="${NX:-108}"; NY="${NY:-38}"
TMO="${TMO:-3600}"

[ -x "$MOOSE" ] || { echo "错误：$MOOSE 不存在" >&2; exit 1; }

rm -rf "$ROOT"; mkdir -p "$ROOT/run"; cd "$ROOT/run"

# 预置 JIT 缓存（若之前跑过一轮，把已编好的缓存接上，省掉最贵的一次 LLVM 编译）。
# ⚠ 缓存按 CWD 找 `.jitcache`；两个算例的 parsed 表达式完全相同 ⇒ 可共用。
SEED="${SEED:-/root/work/jitcache_seed}"
if [ -d "$SEED" ]; then
  cp -r "$SEED" .jitcache
  echo "  已预置 JIT 缓存：$(ls .jitcache | wc -l) 项"
fi

cp "$BASE/$SRCI" case_full.i
for f in columnar_seeds.csv aniso_block.i; do
  [ -f "$BASE/$f" ] && cp "$BASE/$f" . || true
done

python3 - "$ROOT" <<'PY'
import re, sys, os
root = sys.argv[1]
src = os.path.join(root, "run", "case_full.i")
t = open(src, encoding="utf-8").read()
pat = re.compile(r"(type\s*=\s*ACGrGrPolyJ\b)")
n = len(pat.findall(t))
assert n > 0, "没找到 ACGrGrPolyJ —— 这个输入不是补全版"
t2, k = pat.subn(r"\1\n    jac_mode = off", t)
assert k == n, f"替换数不符：{k} != {n}"
open(os.path.join(root, "run", "case_off.i"), "w", encoding="utf-8").write(t2)
print(f"  off 档：给 {k} 个 ACGrGrPolyJ 加了 jac_mode = off")
PY

COMMON=("Mesh/gen/nx=$NX" "Mesh/gen/ny=$NY" Executioner/end_time=1e-6 Outputs/exodus=false)

# --- 1. 先验证**残差逐位相同**（没有这一步，整个对照无效） --------------------
echo
echo "=== 第 1 步：残差同一性验证（2 个时间步，不开 -snes_test_jacobian）==="
for d in full off; do
  S=$(date +%s)
  timeout 1800 "$MOOSE" -i "case_$d.i" "${COMMON[@]}" \
      "Outputs/file_base=ident_$d" > "ident_$d.log" 2>&1 || true
  echo "  $d: $(( $(date +%s) - S )) s"
done

python3 - "$ROOT" <<'PY'
import os, sys
root = sys.argv[1]
def load(d):
    f = os.path.join(root, "run", f"ident_{d}.csv")
    return open(f, encoding="utf-8", errors="replace").read() if os.path.exists(f) else None
a, b = load("full"), load("off")
if a is None or b is None:
    print("  ⚠ 有档没产生 ident csv")
    for d in ("full", "off"):
        f = os.path.join(root, "run", f"ident_{d}.log")
        if os.path.exists(f):
            ls = [l for l in open(f, errors="replace").read().splitlines()
                  if "ERROR" in l or "Time Step" in l][-3:]
            print(f"    {d}: {ls}")
else:
    same = (a == b)
    print("  ✅ CSV 逐字节相同 —— 残差确实没被动过，对照有效" if same else
          "  ❌ CSV **不同** —— 残差被动过，对照无效！")
    print(f"     （full {len(a)} 字节 / off {len(b)} 字节）")
PY

# --- 2. 雅可比有限差分（用 MOOSE 自己 PetscJacobianTester 的快速设置） --------
#   -snes_type ksponly -ksp_type preonly -pc_type none -snes_convergence_test skip
#   ⇒ 不做非线性迭代、不预条件，只在**初始态装配一次**就做 FD 比对。
echo
echo "=== 第 2 步：-snes_test_jacobian 对照（快速求解器设置）==="
for d in full off; do
  S=$(date +%s)
  timeout "$TMO" "$MOOSE" -i "case_$d.i" "${COMMON[@]}" \
      -snes_force_iteration -snes_type ksponly -ksp_type preonly -pc_type none \
      -snes_convergence_test skip \
      -snes_test_jacobian 1e-3 -snes_test_jacobian_view \
      > "jac_$d.log" 2>&1 || true
  echo "  $d: $(( $(date +%s) - S )) s"
done

echo
echo "=== 结果 ==="
python3 - "$ROOT" <<'PY'
import os, re, sys
root = sys.argv[1]
pat = re.compile(
    r"\|\|J - Jfd\|\|_F/\|\|J\|\|_F\s?=?\s?(\S+?),\s*"
    r"\|\|J - Jfd\|\|_F\s?=?\s?(\S+)")
print("  %-6s %-26s %-24s %s" % ("档", "比值 ||J-Jfd||/||J||", "绝对 ||J-Jfd||", "有差异的行"))
print("  " + "-" * 76)
rows = {}
for d in ("full", "off"):
    f = os.path.join(root, "run", f"jac_{d}.log")
    if not os.path.exists(f):
        print("  %-6s 没有日志" % d); continue
    txt = open(f, encoding="utf-8", errors="replace").read()
    ms = pat.findall(txt)
    nrow = len(re.findall(r"^row \d+:", txt, re.M))
    if not ms:
        print("  %-6s 没解析到比值（%d 行）" % (d, txt.count("\n")))
        for l in txt.splitlines():
            if "Jfd" in l or "ERROR" in l:
                print("      | " + l.strip()[:110])
        continue
    r, a = ms[0]
    rows[d] = (r, a, nrow)
    print("  %-6s %-26s %-24s %d" % (d, r, a, nrow))

if "full" in rows and "off" in rows:
    rf, ra, _ = rows["full"]; ro, oa, _ = rows["off"]
    print()
    print("  判读：")
    if rf == ro:
        print("    **一位不变** ⇒ 该判据对「删掉整个 η–η 非对角块」不敏感")
        print("    ⇒ 早先的结论成立：这个比值不是有效的完备性判据，必须换")
    else:
        print(f"    比值 **动了**：{rf} -> {ro}")
        print("    ⇒ 该判据确实能测出缺项；早先的结论是被 FD 舍入噪声蒙蔽")
PY
