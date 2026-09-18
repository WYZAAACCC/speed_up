#!/bin/bash
# =============================================================================
# 阶段 1.0：验证数据可得性
#
# 目的：确认 MOOSE 的 Exodus 输出里真的有构建晶粒图所需的三个变量：
#         unique_grains（元素级晶粒 ID）
#         c            （溶质浓度场）
#         bnds         （晶界指示函数）
#       这一步不通过，后面的提取管线、算子训练全部免谈。
# =============================================================================

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

echo "=============================================="
echo " 1. 安装 netcdf4（Exodus 是 NetCDF-3 格式，h5py 读不了）"
echo "=============================================="
if python3 -c "import netCDF4" 2>/dev/null; then
    echo "  netCDF4 已存在，跳过"
else
    conda install -n moose -y -c conda-forge netcdf4 2>&1 | tail -8
fi

echo
echo "=============================================="
echo " 2. 列出 Exodus 里的所有变量"
echo "=============================================="
python3 << 'PYEOF'
from netCDF4 import Dataset

p = "/root/work/phase0a/phase0a_out.e"
ds = Dataset(p, "r")

def decode(arr):
    out = []
    for row in arr:
        try:
            out.append(b"".join(row).decode("utf-8").strip())
        except Exception:
            out.append(str(row))
    return out

print(f"文件: {p}")
print(f"时间步数: {len(ds.dimensions.get('time_step', []))}")
print()

elem_names = decode(ds.variables["name_elem_var"][:]) if "name_elem_var" in ds.variables else []
nod_names  = decode(ds.variables["name_nod_var"][:])  if "name_nod_var"  in ds.variables else []

print(f"=== 元素变量 ({len(elem_names)}) ===")
for i, n in enumerate(elem_names, 1):
    print(f"  [{i}] {n}")

print()
print(f"=== 节点变量 ({len(nod_names)}) ===")
for i, n in enumerate(nod_names, 1):
    print(f"  [{i}] {n}")

print()
print("=" * 50)
print("关键变量检查")
print("=" * 50)
need = ["unique_grains", "c", "bnds"]
allnames = elem_names + nod_names
for v in need:
    hit = [n for n in allnames if n == v]
    if hit:
        # 找出它在哪个槽位
        where = "elem" if v in elem_names else "nod"
        idx = (elem_names if where == "elem" else nod_names).index(v) + 1
        print(f"  ✅ {v:16s} 存在（{where}, 第 {idx} 个）")
    else:
        print(f"  ❌ {v:16s} 缺失！需要调整 MOOSE 输出设置")

ds.close()
PYEOF
