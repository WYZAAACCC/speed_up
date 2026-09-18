#!/bin/bash
# 测试含偏析的 2D 算例
# 关键问题：晶界富集到底有没有建立起来？

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BIN=/root/moose/modules/phase_field/phase_field-opt
RUN=/root/work/phase2seg
SRC=/mnt/f/speed_up/pipeline
NP=8

mkdir -p "$RUN"
sed 's/\r$//' "$SRC/phase2_2d_seg.i" > "$RUN/phase2_2d_seg.i"
cd "$RUN" || exit 1

echo "=============================================="
echo " 1. 语法检查"
echo "=============================================="
"$BIN" -i phase2_2d_seg.i --check-input 2>&1 | tail -12
if [ "${PIPESTATUS[0]}" -ne 0 ]; then echo "语法检查失败"; exit 1; fi

echo
echo "=============================================="
echo " 2. 短跑 end_time=200，看偏析是否建立"
echo "=============================================="
rm -f phase2_2d_seg*.e phase2_2d_seg_out.csv

START=$(date +%s)
mpirun -np $NP "$BIN" -i phase2_2d_seg.i Executioner/end_time=200 2>&1 | tail -8
RC=${PIPESTATUS[0]}
END=$(date +%s)
echo "退出码 $RC，耗时 $((END-START)) 秒"

if [ ! -f phase2_2d_seg_out.csv ]; then
    echo "CSV 未生成，仿真失败"
    exit 1
fi

echo
echo "=============================================="
echo " 3. 检查偏析是否建立（关键）"
echo "=============================================="
python3 << 'PYEOF'
import numpy as np
from netCDF4 import Dataset

ds = Dataset("phase2_2d_seg_out.e", "r")

def slots(key):
    out = []
    for row in ds.variables[key][:]:
        try: s = b"".join(row).decode("utf-8", "replace")
        except Exception: s = str(row)
        out.append(s.replace("\x00", "").strip())
    return out

en = slots("name_elem_var")
print("元素变量:", en)

def get(name):
    i = en.index(name) + 1
    return np.asarray(ds.variables[f"vals_elem_var{i}eb1"][:], dtype=float)

gb = get("gb_indicator")      # Ση²：体相≈1，晶界≈0.5
t = np.asarray(ds.variables["time_whole"][:], dtype=float)

# c 是节点量，平均到单元
nn = slots("name_nod_var")
ci = nn.index("c") + 1
c_node = np.asarray(ds.variables[f"vals_nod_var{ci}"][:], dtype=float)
conn = np.asarray(ds.variables["connect1"][:], dtype=np.int64) - 1

print()
print(f"{'time':>8} {'c(体相)':>12} {'c(晶界)':>12} {'富集比':>10} {'GB占比':>8}")
print("-" * 56)

idx = [0, len(t)//4, len(t)//2, 3*len(t)//4, len(t)-1]
for it in sorted(set(idx)):
    c_e = c_node[it][conn].mean(axis=1)
    g = gb[it]
    bulk = g > 0.98          # 体相：只有一个序参量占主导
    face = g < 0.85          # 晶界：至少两个序参量显著
    if bulk.sum() == 0 or face.sum() == 0:
        print(f"{t[it]:>8.0f}   (体相或晶界单元数为 0，检查阈值)")
        continue
    cb, cf = c_e[bulk].mean(), c_e[face].mean()
    print(f"{t[it]:>8.0f} {cb:>12.6f} {cf:>12.6f} {cf/cb:>10.3f} "
          f"{face.sum()/len(g)*100:>7.1f}%")

ds.close()
PYEOF
