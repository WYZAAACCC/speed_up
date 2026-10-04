#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_fillcalc.py --- 填满一个盒子需要多少根成熟马氏体板条？

## 两种板条几何（**必须分开算，它们差 1.5 倍**）
* **G1 = `_t5_short.py` 启动器实际传的**：`--plate-L 1000 --plate-W 500 --plate-T 510` nm
  ⇒ `V = 1.000×0.500×0.510 µm³ = **0.2550 µm³**`
  （本项目此前一直用的"单根成熟板条体积"就是它；交叉核对：N=80 盒 125 µm³ 的 30% = 37.5 µm³
   ⇒ 37.5/0.255 = **147 根**，与项目先前记录的 147 一致 ✓）
* **G2 = `_bk_exp.py` 的 argparse 默认**：2400×640×250 nm ⇒ `V = **0.3840 µm³**`
  （`_r579_report.py` 打印的"当前默认"就是它，它自己的结论是
   "填满 30% 的 10 µm 盒 = 300.0 µm³ ⇒ 需要 nv ≈ **781 根**" —— 本脚本核对这一条）

## 同时给出三个约束（缺一个就会答错）
1. **体积约束**：`N_lath = f · L³ / V_lath`
2. **几何约束**（面内足迹）：`B_max = L² / A_f`（每块占满一个足迹）
3. **内存约束**：本项目**一场一根板条** ⇒ 需要 `nv ≥ N_lath`，
   而 N=160 实测 `nv_max = 270`（f64 物化）/ `≈870`（f32 onfly）
"""
WSL = 1.0  # µm

GEOM = {
    'G1 启动器传值 1000×500×510 nm': (1.000, 0.500, 0.510),
    'G2 引擎默认   2400×640×250 nm': (2.400, 0.640, 0.250),
}
FRACS = (0.30, 0.50, 1.00)
BOXES = (5.0, 10.0, 6.25, 16.0)

# N=160 实测（R598）：22 GB 预算
NV_MAX = {'f64 物化(生产档)': 270, 'f32 onfly': 870}


def main():
    print("=" * 104)
    print("填满一个盒子需要多少根成熟马氏体板条？")
    print("=" * 104)
    for gname, (L, W, T) in GEOM.items():
        vl = L * W * T
        af = L * W
        print()
        print("── %s ──  V_lath = %.4f µm³ ；面内足迹 A_f = %.3f µm²" % (gname, vl, af))
        hdr = "  %-9s %-11s" % ("盒边长", "盒体积")
        for f in FRACS:
            hdr += "%12s" % ("%d%% 需根数" % round(f * 100))
        hdr += "%13s" % "B_max(几何)"
        print(hdr)
        for lb in BOXES:
            v = lb ** 3
            row = "  %-9s %-11s" % ("%.2f µm" % lb, "%.0f µm³" % v)
            for f in FRACS:
                row += "%12d" % round(f * v / vl)
            row += "%13d" % int(lb * lb / af)
            print(row)
        print("      ⇒ 每块装 `n(T_end)=23` 根时，要填满 30%% 需要 **B = %d 块**"
              % round(0.30 * 10.0 ** 3 / vl / 23))

    print()
    print("═" * 104)
    print("★ 与「本项目当前配置」的对照（10 µm 盒、V = 1000 µm³、G1 几何）")
    print("═" * 104)
    vl = GEOM['G1 启动器传值 1000×500×510 nm'][0] * \
        GEOM['G1 启动器传值 1000×500×510 nm'][1] * \
        GEOM['G1 启动器传值 1000×500×510 nm'][2]
    v = 10.0 ** 3
    demand = 3 * 23          # --B 3 × n(T_end)=23
    print("  C-2 / KM 律的需求：`--B 3` × `n(T_end) 23` = **%d 根**" % demand)
    print("      ⇒ 占 10 µm 盒的 **%.2f%%**" % (100 * demand * vl / v))
    print("      ⇒ 占  5 µm 盒的 **%.2f%%**" % (100 * demand * vl / 5.0 ** 3))
    for f in FRACS:
        need = round(f * v / vl)
        print("  要填满 %3d%% ⇒ **%4d 根**，即需求量的 **%.1f 倍**；"
              "需 `--B = %d` 块（每块 23 根）"
              % (round(f * 100), need, need / demand, round(need / 23)))
    print()
    print("  ★★ 内存约束（本项目**一场一根板条** ⇒ 需 `nv ≥ 根数`；N=160 实测上限）：")
    for k, mx in NV_MAX.items():
        print("     %-18s nv_max = %4d ⇒ 最多只能填 **%.1f%%**（10 µm 盒）"
              % (k, mx, 100 * mx * vl / v))


if __name__ == "__main__":
    main()
