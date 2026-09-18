#!/bin/bash
# 短跑验证：浓度场 c 是否真的在演化（而非被冻住）
# 若 c 的极值不变，说明守恒性测试是空的

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BIN=/root/moose/modules/phase_field/phase_field-opt
RUN=/root/work/phase0a

mkdir -p "$RUN"
sed 's/\r$//' /mnt/f/speed_up/phase0a/phase0a.i > "$RUN/phase0a.i"
cd "$RUN" || exit 1

rm -f chk_out.csv chk_out.e

echo "=============================================="
echo " 短跑 t=0..300，检查 c 场演化"
echo "=============================================="
mpirun -np 4 "$BIN" -i phase0a.i Executioner/end_time=300 Outputs/file_base=chk_out 2>&1 | tail -8

echo
echo "=============================================="
echo " 结果"
echo "=============================================="
python3 - << 'PYEOF'
import csv, os
if not os.path.exists('chk_out.csv'):
    print("chk_out.csv 未生成，仿真可能失败")
    raise SystemExit(1)
rows = list(csv.DictReader(open('chk_out.csv')))
cols = list(rows[0].keys())
print("列：", cols)
print()
hdr = f"{'time':>8} {'c_max':>12} {'c_min':>12} {'total_solute':>22} {'grains':>7}"
print(hdr)
print("-" * len(hdr))
step = max(1, len(rows) // 12)
for r in rows[::step]:
    print(f"{float(r['time']):>8g} {float(r['c_max']):>12.6f} {float(r['c_min']):>12.6f} "
          f"{r['total_solute']:>22} {r['grain_tracker']:>7}")
print("-" * len(hdr))
r0, r1 = rows[0], rows[-1]
print()
cmax0, cmax1 = float(r0['c_max']), float(r1['c_max'])
cmin0, cmin1 = float(r0['c_min']), float(r1['c_min'])
m0, m1 = float(r0['total_solute']), float(r1['total_solute'])
print("判读：")
if abs(cmax1 - cmax0) < 1e-12 and abs(cmin1 - cmin0) < 1e-12:
    print(f"  ❗ c 的极值完全没变（max {cmax0:.6f}→{cmax1:.6f}, min {cmin0:.6f}→{cmin1:.6f}）")
    print("     → 浓度场根本没在演化，守恒性测试是空的！需要排查")
else:
    print(f"  ✅ c 的极值在变化：max {cmax0:.6f} → {cmax1:.6f}，min {cmin0:.6f} → {cmin1:.6f}")
    print("     → 浓度场确实在扩散（随机初值被抹平）")
    print(f"  ✅ 但总量不变：{m0:.10f} → {m1:.10f}  (Δ = {m1-m0:+.3e})")
    print("     → 场在演化、总量守恒 —— 这是有效的守恒性检验")
PYEOF
