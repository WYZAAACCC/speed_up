#!/bin/bash
# =============================================================================
# T1 第 2 步补跑：`-snes_test_jacobian` 的比值对照（full vs off）
# =============================================================================
# 为什么不重跑整个 run_t1_criterion.sh：
#   第 1 步（残差同一性）已经跑完并通过（差异 1.6e-13 ≪ 容差 1e-8，
#   见 validated/SALVAGED_2026-09-19.md），算例与 **JIT 缓存都是热的**。
#   重跑整个脚本会 `rm -rf` 掉这些，白付一次编译代价。
#
# 第 2 步用的是 MOOSE 自己 `PetscJacobianTester` 的**快速求解器设置**：
#   -snes_type ksponly -ksp_type preonly -pc_type none -snes_convergence_test skip
#   ⇒ 不做非线性迭代、不预条件，只在**初始态装配一次**就做 FD 比对。
#   （参考 /root/moose/python/TestHarness/testers/PetscJacobianTester.py）
#
# 判读：`off` 档（删掉整个 η–η 非对角块）的比值若与 `full` 档**逐位相同**，
#   说明该比值对雅可比完备性不敏感 ⇒ T1 判据必须换。
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

RUN="${RUN:-/root/work/t1crit/run}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
# ⚠ **网格必须小**。实测 108×38（4.1k 单元 / 4.2 万自由度 / 10 变量）上
#   着色有限差分**跑 8.6 分钟还没出结果**（`timeout 2400` 都可能不够）。
#   而**缺项是结构性的、与网格无关**（见 T1_CRITERION.md），所以小网格给出同样的答案。
NX="${NX:-27}"; NY="${NY:-10}"
TMO="${TMO:-1800}"

cd "$RUN"
[ -f case_full.i ] && [ -f case_off.i ] || { echo "错误：$RUN 里没有 case_full.i / case_off.i" >&2; exit 1; }

# --- zero 档：从 case_full.i 派生，把 jac_mode 全改成 zero_all ----------------
# ⚠ `zero_all` 才是**量级级**的正对照：`off` 删的 η–η 非对角项是 η_i·η_j 型的，
#   **只在晶界单元非零**，实测 `||J||_F` 只变 −0.003% ⇒ 没有排他性。
#   `zero_all` 连**每个单元都有的对角贡献**一起删。
python3 - "$RUN" <<'PY'
import os, re, sys
run = sys.argv[1]
src = os.path.join(run, "case_full.i")
t = open(src, encoding="utf-8").read()
t2, n = re.subn(r"(type\s*=\s*ACGrGrPolyJ\b)", r"\1\n    jac_mode = zero_all", t)
assert n > 0, "没找到 ACGrGrPolyJ"
open(os.path.join(run, "case_zero.i"), "w", encoding="utf-8").write(t2)
print(f"  生成 case_zero.i：给 {n} 个 ACGrGrPolyJ 加了 jac_mode = zero_all")
PY

COMMON=("Mesh/gen/nx=$NX" "Mesh/gen/ny=$NY" Executioner/end_time=1.5e-7 Outputs/exodus=false)
# ⚠ **必须加 `-snes_max_it 1`**：`-snes_convergence_test skip` 会让 SNES **永不收敛**，
#   于是它会在**每一次非线性迭代都重做一遍 FD 比对**，一路做到 `nl_max_its`
#   ——实测跑了 4 分钟还在第一次打印之前。MOOSE 自己的 `PetscJacobianTester`
#   只用在小算例上，所以没暴露这个坑。
FAST=(-snes_force_iteration -snes_type ksponly -ksp_type preonly -pc_type none
      -snes_convergence_test skip -snes_max_it 1)

for d in full off zero; do
  S=$(date +%s)
  timeout "$TMO" "$MOOSE" -i "case_$d.i" "${COMMON[@]}" "${FAST[@]}" \
      -snes_test_jacobian -snes_test_jacobian_view \
      > "jac2_$d.log" 2>&1 || true
  echo "  $d: $(( $(date +%s) - S )) s"
done

echo
echo "=== 结果 ==="
python3 - "$RUN" <<'PY'
import os, re, sys
run = sys.argv[1]
pat = re.compile(r"\|\|J - Jfd\|\|_F/\|\|J\|\|_F\s?=?\s?(\S+?),\s*"
                 r"\|\|J - Jfd\|\|_F\s?=?\s?(\S+)")
print("  %-6s %-26s %-22s %s" % ("档", "比值 ||J-Jfd||/||J||", "绝对 ||J-Jfd||", "差异行数"))
print("  " + "-" * 74)
rows = {}
for d in ("full", "off", "zero"):
    f = os.path.join(run, f"jac2_{d}.log")
    if not os.path.exists(f):
        print("  %-6s 没有日志" % d); continue
    txt = open(f, encoding="utf-8", errors="replace").read()
    ms = pat.findall(txt)
    nrow = len(re.findall(r"^row \d+:", txt, re.M))
    if not ms:
        print("  %-6s 没解析到比值（%d 行）" % (d, txt.count("\n")))
        continue
    r, a = ms[0]
    rows[d] = (r, a, nrow)
    print("  %-6s %-26s %-22s %d" % (d, r, a, nrow))

print()
if "full" in rows:
    rf, ra, nf = rows["full"]
    print("  判读（⚠ 不能只看「相不相等」——「不相等」不是判据）：")
    print(f"    基准 full：比值={rf}  绝对差={ra}  差异行数={nf}")
    print()
    for d in ("off", "zero"):
        if d not in rows:
            print(f"    {d}: 没有数据"); continue
        rd, ad, nd = rows[d]
        note = ("删掉 η–η 非对角块（**只在晶界单元非零**）" if d == "off"
                else "**连对角贡献一起删**（每个单元都非零 = 量级级）")
        try:
            rr = float(rd) / float(rf); rn = float(nd) / float(nf) if nf else float("nan")
            print(f"    {d}（{note}）：比值×{rr:.3f}   差异行数×{rn:.2f}")
        except Exception:
            print(f"    {d}: 解析失败")
    print()
    if "zero" in rows:
        try:
            rz = float(rows["zero"][0]) / float(rf)
            if rz >= 2.0:
                print(f"    ⇒ `zero_all` 让比值上升 {rz:.1f}× ⇒ 判据**对缺项敏感**，可用作验收")
                print("      （那早先『五种雅可比给出同一比值』就要另找解释）")
            else:
                print(f"    ⇒ 连**量级级**的删除（`zero_all`）都只让比值动 {(rz-1)*100:.1f}%")
                print("    ⇒ **该比值在本算例上确实不是有效的完备性判据**（结论坐实）")
        except Exception:
            pass
    try:
        rnz = float(rows["zero"][2]) / float(nf) if nf else float("nan")
        if rnz >= 2.0:
            print(f"    ⭐ **差异行数**上升 {rnz:.1f}× —— 比比值敏感得多，")
            print("       印证 L3『结构性缺项计数』的方向是对的")
    except Exception:
        pass
else:
    print("  数据不全，看上面的日志")
PY
