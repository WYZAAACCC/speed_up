#!/bin/bash
# 多分散种子的含偏析算例：目标是在低成本区间内产生拓扑事件

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BIN=/root/moose/modules/phase_field/phase_field-opt
RUN=/root/work/phase2seg
SRC=/mnt/f/speed_up/pipeline
NP=8

mkdir -p "$RUN"
cd "$RUN" || exit 1

# 同步输入与脚本
sed 's/\r$//' "$SRC/phase2_2d_seg.i" > phase2_2d_seg.i
sed 's/\r$//' "$SRC/gen_seeds.py"    > gen_seeds.py
sed 's/\r$//' "$SRC/check_seg.py"    > check_seg.py

echo "=== 生成多分散种子 ==="
python3 gen_seeds.py seeds_poly.txt

echo
echo "=== 语法检查 ==="
"$BIN" -i phase2_2d_seg.i --check-input 2>&1 | tail -8
if [ "${PIPESTATUS[0]}" -ne 0 ]; then echo "语法检查失败"; exit 1; fi

echo
echo "=== 运行 end_time=400 ==="
rm -f phase2_2d_seg.e phase2_2d_seg_out.csv
START=$(date +%s)
mpirun -np $NP "$BIN" -i phase2_2d_seg.i Executioner/end_time=400 2>&1 | tail -8
RC=${PIPESTATUS[0]}
END=$(date +%s)
echo "退出码 $RC，耗时 $((END-START)) 秒"

if [ ! -f phase2_2d_seg_out.csv ]; then echo "CSV 未生成"; exit 1; fi

echo
echo "=== 晶粒数演化（看有没有消失事件）==="
python3 - << 'PYEOF'
import csv
rows = list(csv.DictReader(open("phase2_2d_seg_out.csv")))
print(f"{'time':>8} {'grains':>7} {'dt':>6}  total_solute")
prev = None
events = 0
for r in rows:
    g = float(r["grain_tracker"])
    if prev is not None and g < prev:
        print(f"{float(r['time']):>8.1f} {g:>7.0f} {float(r['dt']):>6.2f}   ← 晶粒消失 {prev:.0f}→{g:.0f}")
        events += 1
    prev = g
print()
print(f"总步数 {len(rows)}，拓扑事件 {events} 次")
print(f"末行: {rows[-1]}")
PYEOF

echo
echo "=== 偏析检查 ==="
python3 check_seg.py phase2_2d_seg.e 2>&1 | tail -20
