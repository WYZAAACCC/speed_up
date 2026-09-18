#!/usr/bin/env python3
"""
核验 extract.py 产出的第二档数据是否真的对、真的全。

用法： python3 check_tier2_data.py <dataset_dir>

检查项（每一条都可能静默出错，所以都要显式验）：
  1. 取向反解：逐晶粒从取向场反解出的 theta 是否复原 gen_aniso 生成的 θ 表
     —— 这是"取向真的被正确记录"的唯一证据
  2. dtheta 是否与 theta 自洽（dtheta = 四重折叠的 |θi-θj|）
  3. 是否有 dtheta == 0 的晶面（说明共用序参量的晶粒相邻了，模型前提被破坏）
  4. align_i/align_j 是否与 grad + theta 自洽（独立重算一遍）
  5. T_avg 是否覆盖了足够宽的温度范围（温度不参与的话，加它就没意义）
  6. 溶质守恒（沿用 conservation.csv）
"""

import csv
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_aniso import build_orientations          # θ 表的单一来源
from extract import align4_deg, misorientation_deg

FAIL = []


def check(name, ok, detail=""):
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def fnum(d, k):
    try:
        return float(d[k])
    except (KeyError, TypeError, ValueError):
        return float("nan")


def main():
    ds = sys.argv[1] if len(sys.argv) > 1 else "."
    grains = read(os.path.join(ds, "grains.csv"))
    faces = read(os.path.join(ds, "faces.csv"))
    if not grains or not faces:
        sys.exit("数据集为空")

    th_expect = build_orientations(8)
    print(f"gen_aniso 生成的 θ 表（{len(th_expect)} 个）: "
          f"{[round(t, 3) for t in th_expect]}")

    # ---- 1. 取向反解 ----
    print("\n1. 取向反解（逐晶粒从取向场反解 theta）")
    seen = {}
    for g in grains:
        v = fnum(g, "theta_deg")
        if math.isfinite(v):
            seen[round(v, 2)] = seen.get(round(v, 2), 0) + 1
    print(f"     反解出的 theta 取值: {sorted(seen)}")
    check("theta 列不是 NaN", bool(seen))
    if seen:
        # 每个反解值都应落在 θ 表附近（容差 0.5 度，允许数值/界面混合误差）
        bad = [v for v in seen
               if min(abs(v - t) for t in th_expect) > 0.5]
        check("每个反解 theta 都对应 θ 表里的一个取向", not bad,
              f"偏离者 {bad}" if bad else f"{len(seen)} 个互异值")
        check("反解出的互异取向数 == op_num (8)", len(seen) == 8,
              f"实测 {len(seen)}（op_num=8，故 11 个晶粒只有 8 个互异取向）")

    # ---- 2/3. dtheta ----
    print("\n2. dtheta 与 theta 自洽 + 无零取向差晶面")
    th_by_grain = {}
    for g in grains:
        th_by_grain.setdefault(int(g["grain_id"]), {})[float(g["time"])] = fnum(g, "theta_deg")
    worst, n0, nchk = 0.0, 0, 0
    for r in faces:
        d = fnum(r, "dtheta_deg")
        if not math.isfinite(d):
            continue
        if d == 0.0:
            n0 += 1
        t = float(r["time"])
        ta = th_by_grain.get(int(r["grain_i"]), {}).get(t, float("nan"))
        tb = th_by_grain.get(int(r["grain_j"]), {}).get(t, float("nan"))
        want = misorientation_deg(ta, tb)
        if math.isfinite(want):
            worst = max(worst, abs(d - want))
            nchk += 1
    check(f"dtheta 与两侧晶粒 theta 自洽（核了 {nchk} 条）", worst < 0.5,
          f"最大差 {worst:.3f} 度")
    check("没有 dtheta == 0 的真实晶面（模型前提未被破坏）", n0 == 0,
          f"{n0} 条" if n0 else "")

    # ---- 4. align 自洽 ----
    print("\n3. align 与 (theta, grad) 自洽（独立重算）")
    worst_i, worst_j, nchk = 0.0, 0.0, 0
    for r in faces:
        gx, gy = fnum(r, "grad_x"), fnum(r, "grad_y")
        ai, aj = fnum(r, "align_i"), fnum(r, "align_j")
        t = float(r["time"])
        ta = th_by_grain.get(int(r["grain_i"]), {}).get(t, float("nan"))
        tb = th_by_grain.get(int(r["grain_j"]), {}).get(t, float("nan"))
        if not (math.isfinite(gx) and math.isfinite(ai) and math.isfinite(ta)):
            continue
        worst_i = max(worst_i, abs(ai - align4_deg(ta, gx, gy)))
        if math.isfinite(tb) and math.isfinite(aj):
            worst_j = max(worst_j, abs(aj - align4_deg(tb, gx, gy)))
        nchk += 1
    check(f"align_i 自洽（核了 {nchk} 条）", worst_i < 1e-6, f"最大差 {worst_i:.3e}")
    check("align_j 自洽", worst_j < 1e-6, f"最大差 {worst_j:.3e}")
    check("align 取值在 [0,1]",
          all(0.0 <= fnum(r, "align_i") <= 1.0 for r in faces
              if math.isfinite(fnum(r, "align_i"))))

    # ---- 5. 温度范围 ----
    print("\n4. 温度覆盖范围（决定「加温度」是否有意义）")
    Tg = [fnum(g, "T_avg") for g in grains]
    Tf = [fnum(r, "T_avg") for r in faces]
    Tg = [v for v in Tg if math.isfinite(v)]
    Tf = [v for v in Tf if math.isfinite(v)]
    if Tg and Tf:
        allT = Tg + Tf
        # 迁移率 L ∝ exp(-Q/kbT)，Q=3.234 eV：看跨度值多少个数量级
        kb, Q = 8.617e-5, 3.234
        span = math.exp(-Q / (kb * max(allT))) / math.exp(-Q / (kb * min(allT)))
        check("温度跨度足够大（否则加温度没意义）", span > 1e6,
              f"T ∈ [{min(allT):.0f}, {max(allT):.0f}] K -> "
              f"L 跨度 {span:.3g} 倍")

    # ---- 6. 守恒 ----
    print("\n5. 溶质守恒")
    cons = read(os.path.join(ds, "conservation.csv"))
    if cons:
        tot = [fnum(c, "total_all") for c in cons]
        tot = [v for v in tot if math.isfinite(v)]
        if tot:
            drift = abs(tot[-1] - tot[0]) / max(abs(tot[0]), 1e-30)
            check("溶质总量相对漂移 < 1e-10", drift < 1e-10, f"{drift:.3e}")

    print()
    if FAIL:
        print(f"失败 {len(FAIL)} 项：{FAIL}")
        sys.exit(1)
    print("第二档数据核验全部通过")


if __name__ == "__main__":
    main()
