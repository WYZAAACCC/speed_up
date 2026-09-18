#!/usr/bin/env python3
"""三路对比，解开"求解器差异"与"容差差异"。

    A = MUMPS + nl_abs_tol=1e-9
    B = ASM   + nl_abs_tol=1e-6
    C = MUMPS + nl_abs_tol=1e-6      <- 关键对照：与 B 同容差、与 A 同求解器

判据（预先设定）：
    C ≈ A  且  C ≠ B   -> 差异来自**求解器**（ASM 线性解不准）-> 生产必须 MUMPS
    C ≈ B  且  C ≠ A   -> 差异来自**容差**（1e-6 不够）-> 收紧容差即可，ASM 仍可用
    C 与 A、B 都不同    -> 系统对精度**敏感依赖**（混沌式放大），是科学问题

只报物理量的 relL2（max|Δ| 被界面单元主导，unique_grains 是整数标号，都不用）。
"""
import numpy as np
import netCDF4 as nc

RUNS = {
    "A": ("MUMPS+1e-9", "/root/work/slv_cmp/A/A.e"),
    "B": ("ASM+1e-6",   "/root/work/slv_cmp/B/B.e"),
    "C": ("MUMPS+1e-6", "/root/work/slv_cmp/C/C.e"),
    "D": ("ASM+1e-9",   "/root/work/slv_cmp/D/D.e"),
}
PHYS = ["gr0", "gr1", "gr2", "gr3", "gr4", "c", "w"]


def _decode(arr):
    out = []
    for row in np.atleast_2d(arr[:]):
        s = "".join(c.decode() if isinstance(c, bytes) else str(c) for c in row)
        out.append(s.replace("\x00", "").strip().rstrip("-").strip())
    return out


def load(path):
    ds = nc.Dataset(path)
    t = np.array(ds.variables["time_whole"][:], dtype=float)
    d = {}
    if "name_nod_var" in ds.variables:
        for i, name in enumerate(_decode(ds.variables["name_nod_var"][:])):
            k = f"vals_nod_var{i + 1}"
            if k in ds.variables:
                d[name] = np.array(ds.variables[k][:], dtype=float)
    ds.close()
    return t, d


def rel(a, b):
    return float(np.linalg.norm(a - b) / (np.linalg.norm(a) + 1e-300))


def main():
    data = {}
    for tag, (label, p) in RUNS.items():
        try:
            data[tag] = load(p)
        except Exception as e:
            print(f"  {tag} ({label}) 读取失败：{type(e).__name__}: {e}")
    if len(data) < 2:
        print("  可用数据不足")
        return

    for tag, (label, p) in RUNS.items():
        if tag in data:
            t, _ = data[tag]
            print(f"  {tag} = {label:<12} 时间点 {len(t):>3} 个，末 = {t[-1]:.4e}")
    print()

    # 三者的共同时间点
    sets = [set(np.round(data[tag][0], 15)) for tag in data]
    common = sorted(set.intersection(*sets))
    print(f"  三者共同时间点 {len(common)} 个，最晚 = {common[-1]:.4e}")
    print()

    idx = {tag: {round(v, 15): i for i, v in enumerate(data[tag][0])} for tag in data}

    # A-C: 同求解器换容差 | C-B: 同容差(1e-6)换求解器 | A-D: 同容差(1e-9)换求解器
    for x, y in (("A", "C"), ("C", "B"), ("A", "D"), ("A", "B")):
        if x not in data or y not in data:
            continue
        print("=" * 80)
        print(f"  {x}({RUNS[x][0]})  vs  {y}({RUNS[y][0]})")
        print("=" * 80)
        print(f"  {'t':>11}" + "".join(f"{n:>11}" for n in PHYS))
        for tv in common:
            i, j = idx[x][tv], idx[y][tv]
            row = f"  {tv:>11.3e}"
            for n in PHYS:
                if n in data[x][1] and n in data[y][1]:
                    row += f"{rel(data[x][1][n][i], data[y][1][n][j]):>11.3e}"
                else:
                    row += f"{'-':>11}"
            print(row)
        print()

    print("=" * 80)
    print("  判定")
    print("=" * 80)
    if all(t in data for t in "ABC") and common:
        tv = common[-1]
        ac = rel(data["A"][1]["gr0"][idx["A"][tv]], data["C"][1]["gr0"][idx["C"][tv]])
        cb = rel(data["C"][1]["gr0"][idx["C"][tv]], data["B"][1]["gr0"][idx["B"][tv]])
        ab = rel(data["A"][1]["gr0"][idx["A"][tv]], data["B"][1]["gr0"][idx["B"][tv]])
        print(f"  在 t={tv:.3e} 时 gr0 的 relL2：")
        print(f"    A vs C (同求解器，差容差) = {ac:.3e}")
        print(f"    C vs B (同容差，差求解器) = {cb:.3e}")
        print(f"    A vs B (都不同)           = {ab:.3e}")
        print()
        if ac < cb / 10:
            print("  ==> **差异来自求解器**：同求解器下换容差不影响，换求解器就分岔")
            print("      -> ASM 的线性解不准，生产必须用 MUMPS")
        elif cb < ac / 10:
            print("  ==> **差异来自容差**：同容差下换求解器不影响，换容差就分岔")
            print("      -> 收紧容差即可，ASM 仍可用（若 ASM 能收敛到更紧的容差）")
        else:
            print("  ==> **两者都贡献**，或系统对精度敏感依赖")
            print("      -> 需在全尺寸网格上复测（A7），并检查是否界面欠分辨所致")


if __name__ == "__main__":
    main()
