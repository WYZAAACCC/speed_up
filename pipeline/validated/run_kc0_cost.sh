#!/bin/bash
# =============================================================================
# κ_c = 0 / 去掉 w 的代价核算（回答用户问题 4）
# =============================================================================
# 审计的建议原文：「如果 κ_c = 0 可稳定工作，优先将溶质方程改为守恒二阶扩散形式，
#                   减少四阶刚性和一个变量 w」
#
# 但**生产输入的 κ_c 早就是 1e-14 了**（2026-09-18 Gate 1 修正，
# 1.125e-11 → 1e-14），而 T5 实测 1e-14 之后 k_eff 已收敛（变化 <1e-5）。
# ⇒ 「1e-14 → 0」本身不带来任何可观测量变化，**唯一可能的收益是去掉 w**。
#
# 而去掉 w 有两条路，各有一个坑：
#
#   路 A：用 MOOSE 的 CahnHilliard 核（`∂c/∂t = ∇·(M∇f_c)`）。
#         ✅ 正确 —— 源码核对过（CahnHilliardBase.h:131-152）：
#            它算的是 ∇f_c = Σ_i (∂²f/∂c∂x_i)·∇x_i，**含 f_{cη}∇η 交叉项**，
#            而那正是产生分凝（T4）的项。
#         ❌ 代价：它的 initialSetup 要求 **三阶导**（f_ccc、f_ccη、f_cηη），
#            而现用的 SplitCH 分离形式**只要二阶导**。
#            本项目已反复踩过 DerivativeParsedMaterial 符号求导的坑
#            （L2b 链、JIT 爆炸）⇒ **三阶导的代价可能吃掉省下的那个变量。**
#
#   路 B：自己写成 ∇·(D_eff ∇c)（因为模型里 M = D_eff/f_cc，看起来刚好约掉）。
#         ❌ **错**。∇f_c = f_cc∇c + Σ f_{cη_i}∇η_i，写成 D_eff∇c 等于
#            把第二项整个丢掉 ⇒ 分凝消失、T4 必挂。**不要走这条。**
#
# 本脚本做**三个同源算例**（一次只改一个因素）：
#   base  : κ_c = 1e-14、derivative_order = 2   ← 生产现状
#   kc0   : κ_c = 0、    derivative_order = 2   ← 隔离「κ_c 本身」的代价/收益
#   do3   : κ_c = 1e-14、derivative_order = 3   ← 隔离「三阶导」的代价
#
# ⚠ **三个算例必须放在同一个目录里**：MOOSE 的 JIT 是**把每条 parsed 表达式
#   当独立 C++ 源文件、调 mpicxx 现场编译成 .so**（实测 WCHAN=do_wait、
#   子进程是 mpicxx），一次 setup 要几分钟。共用 CWD 的 `.jitcache` 后才只付一次。
#   ⚠ 但 `do3` 改了 derivative_order ⇒ 表达式不同 ⇒ 它自己的缓存键不同，
#     仍然要重编。这是**结论本身的一部分**（三阶导贵在哪），别把它当噪声。
#
# 判读：
#   kc0 ≈ base  ⇒ κ_c 这一项本来就不花钱（预期，符合 T5）
#   do3 >> base ⇒ 三阶导代价大 ⇒ 审计的「去掉 w」得不偿失
#   do3 ≈ base  ⇒ 值得真去把 w 删掉再量一次
#
# 用法： bash run_kc0_cost.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BASE="${BASE:-/root/work/prod_merged}"
SRCI="${SRCI:-N.i}"
ROOT="${ROOT:-/root/work/kc0cost}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
NX="${NX:-32}"; NY="${NY:-16}"
END="${END:-2e-6}"
TMO="${TMO:-3600}"
SEED="${SEED:-/root/work/jitcache_seed}"

rm -rf "$ROOT"; mkdir -p "$ROOT/run"; cd "$ROOT/run"
[ -d "$SEED" ] && { cp -r "$SEED" .jitcache; echo "  已预置 JIT 缓存：$(ls .jitcache | wc -l) 项"; }

cp "$BASE/$SRCI" case_base.i
for f in columnar_seeds.csv aniso_block.i; do
  [ -f "$BASE/$f" ] && cp "$BASE/$f" . || true
done

python3 - "$ROOT" <<'PY'
import re, sys, os
run = os.path.join(sys.argv[1], "run")
base = open(os.path.join(run, "case_base.i"), encoding="utf-8").read()

# kc0：把 ch_kappa 的 prop_values 改成 0
t2, n2 = re.subn(r"(prop_names\s*=\s*'kappa_c'\s*\n\s*prop_values\s*=\s*)'[^']*'",
                 r"\g<1>'0'", base)
assert n2 > 0, "kc0: 没匹配到 ch_kappa"
open(os.path.join(run, "case_kc0.i"), "w", encoding="utf-8").write(t2)
print(f"  kc0 : kappa_c -> 0 （{n2} 处）")

# do3：把**溶质自由能那一块**的 derivative_order 2 -> 3
# ⚠ 两个坑叠在一起（本轮都踩了）：
#   ① 生产输入里这一块叫 `[free_energy]`（property_name = f_loc），**不叫** `[f_loc]`；
#   ② `[free_energy]` 这个字符串在**注释**里也出现过（"…见 [free_energy] 的…"）。
#      只写 `[ \t]*\[free_energy\]` 而**不加行首锚定**，`[ \t]*` 会匹配到注释里
#      括号后面的那个空格 ⇒ **匹配到注释**，看起来像"块里没有 f_loc"。
#      ⇒ 必须用 `^[ \t]*\[free_energy\]` 配 re.M。
m = re.search(r"(^[ \t]*\[free_energy\](?:.*?))\n[ \t]*\[\]", base, re.S | re.M)
assert m, "do3: 找不到 [free_energy] 块"
assert "property_name = f_loc" in m.group(1), "do3: [free_energy] 里不是 f_loc"
blk, k = re.subn(r"derivative_order\s*=\s*2", "derivative_order = 3", m.group(1))
assert k > 0, "do3: 该块里没有 derivative_order = 2"
t3 = base[:m.start(1)] + blk + base[m.end(1):]
open(os.path.join(run, "case_do3.i"), "w", encoding="utf-8").write(t3)
print(f"  do3 : f_loc（[free_energy] 块）derivative_order 2 -> 3 （{k} 处）")
PY

COMMON=("Mesh/gen/nx=$NX" "Mesh/gen/ny=$NY" "Executioner/end_time=$END" Outputs/exodus=false)

echo
echo "=== 跑三个算例（网格 ${NX}x${NY}，end_time=${END} s）==="
for d in base kc0 do3; do
  S=$(date +%s)
  timeout "$TMO" "$MOOSE" -i "case_$d.i" "${COMMON[@]}" \
      "Outputs/file_base=out_$d" --timing > "run_$d.log" 2>&1 || true
  echo "  $d: $(( $(date +%s) - S )) s"
done

echo
echo "=== 结果 ==="
python3 - "$ROOT" <<'PY'
import os, re, sys
run = os.path.join(sys.argv[1], "run")

def stats(d):
    f = os.path.join(run, f"run_{d}.log")
    if not os.path.exists(f):
        return None
    t = open(f, encoding="utf-8", errors="replace").read()
    s = {}
    m = re.search(r"Number of DoFs\s*:?\s*(\d+)", t)
    s["dof"] = m.group(1) if m else "?"
    s["steps"] = len(re.findall(r"^Time Step \d+", t, re.M))
    s["nl"] = len(re.findall(r"Nonlinear \|R\|", t))
    # MOOSE 的线性迭代打印形如 "Linear |R| = ..." 后跟迭代数；这里数 "      N linear iterations"
    s["lin"] = sum(int(x) for x in re.findall(r"(\d+)\s+linear iterations", t))
    ts = re.findall(r"time=([0-9.eE+-]+)", t)
    s["tend"] = ts[-1] if ts else "?"
    s["err"] = "有 ERROR" if "*** ERROR ***" in t else "ok"
    s["setup"] = "?"  # JIT 时间见 --timing 输出
    return s

hdr = "%-6s %-9s %-7s %-9s %-11s %-11s %s"
print("  " + hdr % ("档", "DoFs", "步数", "NL 迭代", "线性迭代", "末态 t", "状态"))
print("  " + "-" * 72)
res = {}
for d in ("base", "kc0", "do3"):
    s = stats(d)
    if s is None:
        print("  %-6s 没有日志（生成或运行失败）" % d); continue
    res[d] = s
    print("  " + hdr % (d, s["dof"], s["steps"], s["nl"], s["lin"], s["tend"], s["err"]))

print()
print("  判读：")
if "base" in res:
    b = res["base"]
    for d, note in (("kc0", "κ_c 本身"), ("do3", "三阶导")):
        if d not in res: continue
        x = res[d]
        # 用「每单位模拟时间的线性迭代」做归一，避免步数不同误导
        try:
            nb = b["lin"] / float(b["tend"]); nx_ = x["lin"] / float(x["tend"])
            print(f"    {note}: 线性迭代/模拟时间  base={nb:.3g}  {d}={nx_:.3g}"
                  f"  ({nx_/nb:.2f}×)")
        except Exception:
            print(f"    {note}: 数据不全，看上面表格")
PY
