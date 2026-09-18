#!/usr/bin/env python3
"""
验证浓度场 c 真的在演化（而不是被冻住），否则守恒性测试是空的。

要看的是：
  - c 的空间分布随时间有没有变（随机初值应该被扩散抹平）
  - 但总量始终不变

读 Exodus 输出，比较首末时刻 c 的统计量。
"""
import sys
import numpy as np

try:
    from netCDF4 import Dataset
except ImportError:
    sys.exit("需要 netCDF4：conda install -c conda-forge netcdf4")

path = sys.argv[1] if len(sys.argv) > 1 else "phase0a_out.e"

with Dataset(path) as ds:
    # Exodus 的时间步
    tv = ds.variables["time_whole"][:]
    nsteps = len(tv)
    print(f"Exodus 文件：{path}")
    print(f"时间步数：{nsteps}，t = {tv[0]:g} → {tv[-1]:g}")
    print()

    # 找 c 变量（可能是 vals_elem_var / vals_nod_var）
    names = list(ds.variables.keys())
    cvar = None
    for cand in ("vals_elem_var1eb1", "vals_nod_var1", "vals_elem_var1e1"):
        if cand in names:
            cvar = cand
            break

    # 更稳妥：按名字里带 c 的找；必要时列出所有 vals_*
    if cvar is None:
        vals = [n for n in names if n.startswith("vals_")]
        print("未能自动定位 c 变量，所有候选：")
        for v in vals[:20]:
            print("   ", v, ds.variables[v].shape)
        # 尝试第一个
        cvar = vals[0] if vals else None

    if cvar is None:
        sys.exit("找不到变量数据")

    print(f"使用变量：{cvar}，形状 {ds.variables[cvar].shape}")
    print()

    data = ds.variables[cvar][:]
    # Exodus 里通常是 (time, elem)
    if data.ndim == 1:
        data = data.reshape(1, -1)

    def stats(row):
        r = np.asarray(row, dtype=float)
        r = r[np.isfinite(r)]
        return r.min(), r.max(), r.mean(), r.std()

    print("=" * 74)
    print("浓度场 c 的空间分布演化")
    print("=" * 74)
    print(f"{'时间':>10} {'min':>12} {'max':>12} {'mean':>16} {'std':>12}")
    print("-" * 74)

    idx = [0, len(data) // 4, len(data) // 2, 3 * len(data) // 4, len(data) - 1]
    for i in sorted(set(idx)):
        mn, mx, mean, sd = stats(data[i])
        print(f"{tv[i]:>10g} {mn:>12.6f} {mx:>12.6f} {mean:>16.10f} {sd:>12.6f}")

    print("-" * 74)

    mn0, mx0, mean0, sd0 = stats(data[0])
    mn1, mx1, mean1, sd1 = stats(data[-1])

    print()
    print("=" * 74)
    print("判读")
    print("=" * 74)
    if abs(sd1 - sd0) < 1e-12:
        print("  ❗ 标准差几乎没变 —— c 可能根本没在扩散，守恒性测试是空的！")
    else:
        print(f"  ✅ c 的标准差从 {sd0:.6f} 降到 {sd1:.6f}（随机初值被扩散抹平）")
        print("     → 浓度场确实在演化")
    if abs(mean1 - mean0) / abs(mean0) < 1e-14:
        print(f"  ✅ 但均值完全不变（{mean0:.10f} → {mean1:.10f}）")
        print("     → 总量守恒，且场的分布确实在变 —— 这才是有效的守恒性检验")
    else:
        print(f"  ⚠️  均值变了 {mean0:.10f} → {mean1:.10f}")
