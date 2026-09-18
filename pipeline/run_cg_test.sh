#!/bin/bash
# 最小判据实验：竞争生长机制是否真的在起作用 + 收敛性/雅可比正确性。
#
# 三个判据：
#   1. 雅可比正确性：||J-Jfd||_F/||J||_F 应达 ~1e-8（AD 核 + AD 材料）
#   2. 收敛性：Newton 应二次收敛（残差每步降 1-2 个数量级），而非线性爬行
#   3. 竞争生长：gr0（theta=0，与梯度对齐）在凝固区中的面积分数应
#      **单调上升超过 50%**；A_ani=0 时无择优作为对照
#
# 域 40x40 网格=1600 单元、2 个序参量 -> 很小很快。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/cg
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /mnt/f/speed_up/pipeline/test_cg.i ./base.i

python3 - <<'PY'
import re
base = open("base.i", encoding="utf-8").read()

# T1: A_ani=0.7（测试）+ 雅可比自检（只跑很短，够拿到 J 即止）
t1 = re.sub(r"^  end_time = .*$", "  end_time = 4e-6", base, flags=re.M)
t1 = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 8", t1, flags=re.M)
t1 = re.sub(r"^  petsc_options_iname = .*$",
            "  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type -snes_test_jacobian'",
            t1, flags=re.M)
t1 = re.sub(r"^  petsc_options_value = .*$", "  petsc_options_value = 'lu mumps 1'", t1, flags=re.M)
t1 = t1.replace("file_base = cg", "file_base = cgJ")
open("T1_jac.i", "w", encoding="utf-8").write(t1)

# T2: A_ani=0.7，跑全程（竞争生长测试）
t2 = base.replace("file_base = cg", "file_base = cgA7")
open("T2_ani07.i", "w", encoding="utf-8").write(t2)

# T3: A_ani=0 对照
t3 = base.replace("1+0.7*(2*(gr0^2/(gr0^2+gr1^2+1e-3))-1)", "1+0.0*(2*(gr0^2/(gr0^2+gr1^2+1e-3))-1)")
assert t3 != base, "A_ani=0 替换失败"
t3 = t3.replace("file_base = cg", "file_base = cgA0")
open("T3_ani00.i", "w", encoding="utf-8").write(t3)

print("T1_jac.i（雅可比自检, 4e-6）  T2_ani07.i（竞争生长, 全程）  T3_ani00.i（对照）")
PY

mkdir -p T1 T2 T3
cp T1_jac.i T1/ ; cp T2_ani07.i T2/ ; cp T3_ani00.i T3/

echo "=== 并行跑 T1 / T2 / T3 ==="
( cd T1 && setsid --wait "$MOOSE" -i T1_jac.i > run.log 2>&1; echo "T1 rc=$?" ) & P1=$!
( cd T2 && setsid --wait "$MOOSE" -i T2_ani07.i > run.log 2>&1; echo "T2 rc=$?" ) & P2=$!
( cd T3 && setsid --wait "$MOOSE" -i T3_ani00.i > run.log 2>&1; echo "T3 rc=$?" ) & P3=$!
wait $P1 $P2 $P3 2>/dev/null

echo
echo "############ 判据 1：雅可比正确性 ############"
grep -a "J - Jfd" /root/work/cg/T1/run.log | head -4 | sed 's/^/  /'
grep -a -m3 -E '\*\*\* ERROR|Aborting' /root/work/cg/T1/run.log | sed 's/^/  /'

echo
echo "############ 判据 2：Newton 收敛形态 ############"
echo "--- T1 (MUMPS 直接解, 应二次收敛) ---"
grep -a "Nonlinear |R|" /root/work/cg/T1/run.log | sed 's/\x1b\[[0-9;]*m//g' | head -8 | sed 's/^/  /'

echo
echo "############ 判据 3：竞争生长（gr0 面积分数）############"
for t in T2 T3; do
  echo "--- $t ---"
  grep -a -c "Solve Converged" /root/work/cg/$t/run.log | sed 's/^/  收敛步=/'
  python3 - "$t" <<'PY'
import csv, sys
t = sys.argv[1]
try:
    rows = list(csv.DictReader(open(f"/root/work/cg/{t}/{t[0:0]}{'cgA7' if t=='T2' else 'cgA0'}_out.csv")))
except Exception as e:
    print(f"  读 CSV 失败: {e}"); raise SystemExit
print(f"  {'time':>10} {'gr0':>10} {'gr1':>10} {'gr0 占比':>9}")
for r in rows[::max(1, len(rows)//8)] + [rows[-1]]:
    try:
        a, b = float(r['gr0_total']), float(r['gr1_total'])
        f = a/(a+b) if (a+b) > 0 else float('nan')
        print(f"  {float(r['time']):10.3e} {a:10.4e} {b:10.4e} {f:9.4f}")
    except Exception:
        pass
PY
done
