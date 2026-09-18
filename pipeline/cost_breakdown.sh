#!/bin/bash
# 【关键测量】求解成本到底花在哪：晶粒的各向异性材料 vs 溶质 vs 其余
#
# 动机：用户的方案是"晶粒拓扑走传统求解器、晶界溶质走神经算子"。
#       若成本主要在**晶粒材料**上，那"把溶质交给算子"就省不了多少，
#       整个加速方案的收益需要重新论证。
#
# 全尺寸 430x150（生产配置）+ ASM（新定稿求解器）+ dt=1e-7 起步。
#
#   V0  完整基线
#   V1  L/kappa/gamma 换成简单形式（去掉 2a 的 O(n^2) 对项 + 2b 的对齐项）
#   V2  删掉溶质 c/w 及其核与材料
#   V3  V1 + V2
#
# 判据：比较**雅可比装配均值**与**总墙钟**。
#       溶质占比 = (V0 - V2) / V0
#       各向异性材料占比 = (V0 - V1) / V0
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/cost
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

# --- 生成基线 d.i（非 AD 版！见 ROADMAP 附录 A2）---
cp /root/work/bak/gen_aniso.py .
cp /root/work/bak/splice_aniso.py .
sed 's/\r$//' /mnt/f/speed_up/pipeline/stage1_meltpool_c.i > stage1_meltpool_c.i
sed 's/\r$//' /mnt/f/speed_up/pipeline/columnar_seeds.csv > columnar_seeds.csv
conda activate ml
python3 gen_aniso.py --op-num 8 --out aniso_block.i > gen.log 2>&1 || { echo "gen 失败"; tail -3 gen.log; exit 1; }
python3 splice_aniso.py >> gen.log 2>&1 || { echo "splice 失败"; tail -3 gen.log; exit 1; }
conda activate moose
[ -f stage1_meltpool_d.i ] || { echo "无 d.i"; exit 1; }
grep -c 'ADTimeDerivative\|ADGrainGrowth\|ADACInterface' stage1_meltpool_d.i | sed 's/^/  自检 AD 核数（应为0）: /'

python3 - <<'PY'
import re

base = open("stage1_meltpool_d.i", encoding="utf-8").read()

def common(s):
    s = re.sub(r"^    nx = .*$", "    nx = 430", s, flags=re.M)
    s = re.sub(r"^    ny = .*$", "    ny = 150", s, flags=re.M)
    s = re.sub(r"^  petsc_options_iname = .*$",
               "  petsc_options_iname = '-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap'", s, flags=re.M)
    s = re.sub(r"^  petsc_options_value = .*$", "  petsc_options_value = 'asm 31 preonly ilu 1'", s, flags=re.M)
    s = re.sub(r"^  nl_abs_tol = .*$", "  nl_abs_tol = 1e-9", s, flags=re.M)
    s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 20", s, flags=re.M)
    s = re.sub(r"^  end_time = .*$", "  end_time = 2.5e-7", s, flags=re.M)
    s = re.sub(r"^  dtmax = .*$", "  dtmax = 4e-6", s, flags=re.M)
    s = re.sub(r"^    dt = .*$", "    dt = 1e-7", s, flags=re.M)
    s = re.sub(r"\[Outputs\][\s\S]*$", "[Outputs]\n  csv = true\n  print_linear_residuals = false\n[]\n", s)
    return s

def drop_solute(s):
    """删掉溶质：变量 c/w、它们的 IC、核、材料、以及引用它们的后处理"""
    # 变量块
    for name in ("c", "w"):
        s = re.sub(rf"^  \[{name}\]\n(?:.*\n)*?  \[\]\n", "", s, flags=re.M)
    # IC 块
    for name in ("c_init", "w_init"):
        s = re.sub(rf"^  \[{name}\]\n(?:.*\n)*?  \[\]\n", "", s, flags=re.M)
    # 核块
    for name in ("w_dot", "coupled_res", "coupled_parsed"):
        s = re.sub(rf"^  \[{name}\]\n(?:.*\n)*?  \[\]\n", "", s, flags=re.M)
    # 材料块
    for name in ("ch_params", "free_energy"):
        s = re.sub(rf"^  \[{name}\]\n(?:.*\n)*?  \[\]\n", "", s, flags=re.M)
    # 引用 c/w 的后处理
    out, skip = [], 0
    lines = s.split("\n")
    i = 0
    while i < len(lines):
        if re.match(r"^  \[\w+\]$", lines[i]) and i + 1 < len(lines):
            blk = []
            j = i
            while j < len(lines) and not (j > i and lines[j].strip() == "[]"):
                blk.append(lines[j]); j += 1
            blk.append(lines[j])
            txt = "\n".join(blk)
            if re.search(r"variable = (c|w)\b", txt):
                i = j + 1; continue
            out.extend(blk); i = j + 1
        else:
            out.append(lines[i]); i += 1
    s = "\n".join(out)
    # c 可能残留在 coupled_variables 里
    s = re.sub(r"coupled_variables = '([^']*)\bc\b([^']*)'", lambda m: "coupled_variables = '" + (m.group(1)+m.group(2)).strip() + "'", s)
    return s

def simple_aniso(s):
    """把 2a 的 O(n^2) 对项与 2b 的对齐项换成简单形式"""
    # kappa_aniso -> 常数
    s = re.sub(r"(property_name = kappa_op\n(?:.*\n)*?    expression = )'[^']*'",
               r"\g<1>'1.8e-6'", s)
    # gamma_aniso -> 常数
    s = re.sub(r"(property_name = gamma_asymm\n(?:.*\n)*?    expression = )'[^']*'",
               r"\g<1>'1.5'", s)
    # L2a -> 各向同性 Arrhenius（去掉 O(n^2) 对项）
    s = re.sub(r"(property_name = L2a\n(?:.*\n)*?    expression = )'[^']*'",
               r"\g<1>'(4.0/3.0)*232*exp(-3.234/(8.617e-05*T))/4e-06'", s)
    # L2b -> 1（去掉 2b 的热梯度对齐）
    s = re.sub(r"(property_name = L2b\n(?:.*\n)*?    expression = )'[^']*'",
               r"\g<1>'1.0'", s)
    return s

VARIANTS = [("V0", lambda x: x),
            ("V1", simple_aniso),
            ("V2", drop_solute),
            ("V3", lambda x: drop_solute(simple_aniso(x)))]
import os
for tag, fn in VARIANTS:
    s = fn(common(base))
    os.makedirs(tag, exist_ok=True)
    open(f"{tag}/v.i", "w", encoding="utf-8").write(s)
    nv = len(re.findall(r"^  \[\w+\]$", s, flags=re.M))
    print(f"  {tag}: 已生成")
PY

for T in V0 V1 V2 V3; do cp columnar_seeds.csv "$T"/; done

echo
echo "=== 串行跑 4 个变体（排除互相争用）==="
for T in V0 V1 V2 V3; do
  echo "--- $T 开始 $(date +%H:%M:%S) ---"
  ( cd "$T" && setsid --wait "$MOOSE" -i v.i > run.log 2>&1; echo "$T rc=$?" >> "$D/rc.txt" )
done

echo
echo "================ 成本分解 ================"
printf "  %-5s %-8s %-12s %-14s %-12s %s\n" "变体" "rc" "墙钟(s)" "雅可比均值(s)" "牛顿迭代" "说明"
python3 - <<'PY'
import re, os
DESC = {"V0":"完整基线","V1":"去各向异性材料(2a+2b)","V2":"去溶质 c/w","V3":"去两者"}
rows = {}
for tag in ("V0","V1","V2","V3"):
    L = f"/root/work/cost/{tag}/run.log"
    if not os.path.exists(L): print(f"  {tag}: 无日志"); continue
    txt = re.sub(r"\x1b\[[0-9;]*m", "", open(L, errors="ignore").read())
    rc = "?"
    p = f"/root/work/cost/rc.txt"
    if os.path.exists(p):
        m = re.search(rf"{tag} rc=(\d+)", open(p).read())
        if m: rc = m.group(1)
    wall = re.findall(r"Finished Executing[^\]]*\]\s*\[\s*([0-9.]+) s\]", txt)
    wall = float(wall[-1]) if wall else None
    jac = [float(x) for x in re.findall(r"Computing Jacobian[^\[]*\[\s*([0-9.]+) s\]", txt)]
    nit = len(re.findall(r"Nonlinear \|R\|", txt))
    jm = sum(jac)/len(jac) if jac else None
    rows[tag] = (wall, jm, nit)
    print(f"  {tag:<5} {rc:<8} {('%.0f'%wall) if wall else '?':<12} {('%.1f'%jm) if jm else '?':<14} {nit:<12} {DESC[tag]}")
print()
if all(t in rows and rows[t][0] for t in ("V0","V1","V2","V3")):
    w0 = rows["V0"][0]
    print(f"  溶质占比        = (V0-V2)/V0 = {(w0-rows['V2'][0])/w0*100:.1f}%")
    print(f"  各向异性材料占比 = (V0-V1)/V0 = {(w0-rows['V1'][0])/w0*100:.1f}%")
    print(f"  两者之和占比     = (V0-V3)/V0 = {(w0-rows['V3'][0])/w0*100:.1f}%")
PY
