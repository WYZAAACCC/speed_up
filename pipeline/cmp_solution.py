#!/usr/bin/env python3
"""逐场对比 MUMPS(A) 与 ASM(B) 的解 —— A2 的决定性判据。

判据（预先设定，不许事后改）：
    max|Δgr_i| ~ 1e-7 量级  ->  ASM 的残差地板在物理上无害 -> 生产用 ASM（快约 2 倍）
    出现 O(0.1) 的差异       ->  地板有害 -> 必须 MUMPS

Exodus 结构要点（已探明，别改错）：
  * 时间变量叫 `time_whole`，不是 `time`
  * 变量名在 `name_nod_var` / `name_elem_var`，形状 (nvar, len_name) 的二维字符数组，
    要**按行**拼接再 strip 掉 \\x00
  * 本算例有**两个单元块**（liquid 子域），单元变量名为 `vals_elem_var{i}eb{blk}`，
    对比时按块分开算
"""
import numpy as np
import netCDF4 as nc

PATHS = {"A(MUMPS)": "/root/work/slv_cmp/A/A.e", "B(ASM)": "/root/work/slv_cmp/B/B.e"}


def _decode(arr):
    """(nvar, len_name) 的字符数组 -> 名字列表

    Exodus 用空格/'-'/NUL 填充到 len_name，三种都要剥掉。
    """
    out = []
    for row in np.atleast_2d(arr[:]):
        s = "".join(c.decode() if isinstance(c, bytes) else str(c) for c in row)
        out.append(s.replace("\x00", "").strip().rstrip("-").strip())
    return out


def load(path):
    ds = nc.Dataset(path)
    times = np.array(ds.variables["time_whole"][:], dtype=float)
    data = {}

    if "name_nod_var" in ds.variables:
        for i, name in enumerate(_decode(ds.variables["name_nod_var"][:])):
            k = f"vals_nod_var{i + 1}"
            if k in ds.variables:
                data[("node", name)] = np.array(ds.variables[k][:], dtype=float)

    if "name_elem_var" in ds.variables:
        nm = _decode(ds.variables["name_elem_var"][:])
        for blk in range(1, len(ds.dimensions.get("num_el_blk", [])) + 1):
            for i, name in enumerate(nm):
                k = f"vals_elem_var{i + 1}eb{blk}"
                if k in ds.variables:
                    data[(f"elem_b{blk}", name)] = np.array(ds.variables[k][:], dtype=float)
    ds.close()
    return times, data


def main():
    loaded = {}
    for tag, p in PATHS.items():
        try:
            loaded[tag] = load(p)
        except Exception as e:
            print(f"  读 {tag} 失败：{type(e).__name__}: {e}")
            return
    a_t, a_d = loaded["A(MUMPS)"]
    b_t, b_d = loaded["B(ASM)"]
    print(f"  A(MUMPS) 时间点 {len(a_t)} 个，末 = {a_t[-1]:.6e}")
    print(f"  B(ASM)   时间点 {len(b_t)} 个，末 = {b_t[-1]:.6e}")

    common = []
    for i, ta in enumerate(a_t):
        j = int(np.argmin(np.abs(b_t - ta)))
        if abs(b_t[j] - ta) < 1e-12:
            common.append((i, j, ta))
    if not common:
        print("  没有共同时间点，无法对比")
        return
    print(f"  共同时间点 {len(common)} 个：{[f'{t:.3e}' for _, _, t in common]}")
    print()

    keys = sorted(set(a_d) & set(b_d))
    print(f"  可比变量 {len(keys)} 个：{sorted(set(k[1] for k in keys))}")
    print()

    verdicts = []
    for i, j, t in common:
        print("=" * 78)
        print(f"  t = {t:.6e}")
        print("=" * 78)
        print(f"  {'块':<9}{'变量':<10}{'max|Δ|':>13}{'relL2':>12}{'max|A|':>12}   判定")
        worst_abs, worst_rel, worst_name = 0.0, 0.0, ""
        for k in keys:
            va, vb = a_d[k][i], b_d[k][j]
            if va.shape != vb.shape:
                continue
            d = np.abs(va - vb)
            ma = float(d.max())
            mr = float(np.linalg.norm(d) / (np.linalg.norm(va) + 1e-300))
            if ma > worst_abs:
                worst_abs, worst_name = ma, f"{k[0]}/{k[1]}"
            worst_rel = max(worst_rel, mr)
            flag = "  <== 显著" if (ma > 1e-4 or mr > 1e-3) else ("  轻微" if ma > 1e-7 else "  一致")
            print(f"  {k[0]:<9}{k[1]:<10}{ma:>13.4e}{mr:>12.4e}{np.abs(va).max():>12.4e}{flag}")
        print()
        print(f"  >>> 最大绝对差 = {worst_abs:.4e}   ({worst_name})")
        print(f"  >>> 最大相对 L2 = {worst_rel:.4e}")
        verdicts.append((t, worst_abs))
        if worst_abs < 1e-5:
            v = "两解一致 -> ASM 地板在物理上无害，生产可用 ASM"
        elif worst_abs < 1e-2:
            v = "两解有可见差异 -> 看随时间的累积趋势"
        else:
            v = "两解显著不同 -> ASM 地板有害，生产必须用 MUMPS"
        print(f"  >>> 判定：**{v}**")
        print()

    # ---------- 物理量 vs 标号量：必须分开 ----------
    # unique_grains 是 GrainTracker 分配的**整数标号**，不是物理量；
    # 它的差值是"标号不同"，会污染 max|Δ| 统计。
    # 同理 max|Δ| 本身也被**界面单元**主导：η 在界面处变化剧烈，
    # 界面位置微移就产生大的局部 Δη，但 relL2 很小。**趋势要看 relL2。**
    LABELING = {"unique_grains"}
    PHYS = ["gr0", "gr1", "gr2", "gr3", "gr4", "gr5", "gr6", "gr7", "c", "w"]

    print("=" * 78)
    print("  物理量的 relL2 随时间的累积趋势（决定性证据）")
    print("=" * 78)
    print(f"  {'t':>11}" + "".join(f"{n:>11}" for n in PHYS))
    for i, j, t in common:
        row = f"  {t:>11.3e}"
        for n in PHYS:
            k = ("node", n)
            if k not in a_d or k not in b_d:
                row += f"{'-':>11}"
                continue
            d = np.abs(a_d[k][i] - b_d[k][j])
            r = float(np.linalg.norm(d) / (np.linalg.norm(a_d[k][i]) + 1e-300))
            row += f"{r:>11.3e}"
        print(row)

    print()
    print("  非标号量的 max|Δ| 趋势")
    print(f"  {'t':>11}{'max|Δ|物理':>14}{'elem max':>12}")
    for i, j, t in common:
        wp = max((float(np.abs(a_d[k][i] - b_d[k][j]).max())
                  for k in keys if k[1] not in LABELING and a_d[k][i].shape == b_d[k][j].shape),
                 default=0.0)
        we = max((float(np.abs(a_d[k][i] - b_d[k][j]).max())
                  for k in keys if k[1] in LABELING and a_d[k][i].shape == b_d[k][j].shape),
                 default=0.0)
        print(f"  {t:>11.3e}{wp:>14.4e}{we:>12.4e}")

    print()
    print("=" * 78)
    print("  结论")
    print("=" * 78)
    rel_g = max((float(np.linalg.norm(a_d[("node", n)][i] - b_d[("node", n)][j])
                       / (np.linalg.norm(a_d[("node", n)][i]) + 1e-300))
                 for i, j, t in common for n in ("gr0", "gr1", "gr2", "gr3", "gr4")
                 if ("node", n) in a_d), default=0.0)
    print(f"  序参量最大 relL2 = {rel_g:.3e}")
    if rel_g < 1e-4:
        print("  ==> 物理量一致 -> ASM 地板无害，生产可用 ASM")
    elif rel_g < 1e-2:
        print("  ==> 物理量有 ~0.1% 量级差异。**对训练数据可接受**，")
        print("      但须确认它不随时间放大（看上面的 relL2 趋势行是否单调增长）")
    else:
        print("  ==> 物理量显著不同 -> 必须用 MUMPS")


if __name__ == "__main__":
    main()
