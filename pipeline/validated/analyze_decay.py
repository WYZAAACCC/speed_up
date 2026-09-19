#!/usr/bin/env python3
# =============================================================================
# T12 分析器：从扰动衰减的 CSV 里拟合出有效扩散系数
# =============================================================================
# 读 <dir>/case_out.csv 的 c_max/c_min，算振幅 A(t) = (c_max − c_min)/2，
# 对 ln A(t) 做线性拟合得到 rate，反解
#       D_measured = rate / (k² (1 + κ_c k² / f''))
# 并与该状态的目标值（D_L / D_S / D_GB）比较。
#
# ⚠ 拟合只取**早期段**（振幅降到初值 1/e 之前）：
#   扰动一大就不再是线性区，而且 c 偏离平衡后 f'' 也不再是常数。
#
# 用法：
#   python3 analyze_decay.py <状态>=<目录> [...]      # 例如 gb=/path/to/gb
#   python3 analyze_decay.py <目录>                   # 单个，目录名末尾当状态
# =============================================================================

import csv
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

K_C, A_PART, C0 = 0.9, 0.264, 0.036
STATE_S = {"liquid": 0.0, "grain": 1.0, "gb": 0.5}
STATE_D = {"liquid": "D_L", "grain": "D_S", "gb": "D_GB"}


def read_case(txt):
    """从 case.i 里读 kappa_c、eta0、eta1、xmax、D_L/D_S/D_GB。
    ⚠ kappa_c 必须**从输入里读**，不能硬编码 —— 改过一版就是硬编码 1e-14，
      结果扫 kappa_c 时所有档都套用了同一个修正因子，把结论带偏。"""
    import re
    kc = 1.0e-14
    m = re.search(r"prop_values\s*=\s*'(\S+)'", txt)
    if m:
        kc = float(m.group(1))
    e0 = e1 = None
    m = re.search(r"\[eta0\]\s*\n\s*initial_condition\s*=\s*(\S+)", txt)
    if m:
        e0 = float(m.group(1))
    m = re.search(r"\[eta1\]\s*\n\s*initial_condition\s*=\s*(\S+)", txt)
    if m:
        e1 = float(m.group(1))
    ldom = 4.0e-6
    m = re.search(r"xmax\s*=\s*(\S+)", txt)
    if m:
        ldom = float(m.group(1))
    dl = ds = dgb = None
    m = re.search(r"constant_expressions\s*=\s*'(\S+)\s+(\S+)\s+(\S+)'", txt)
    if m:
        dl, ds, dgb = (float(m.group(i)) for i in (1, 2, 3))
    return kc, e0, e1, ldom, dl, ds, dgb


def fit_decay(path):
    """返回 (D_measured, rate, R², 用的点数, S, kc, 目标值)"""
    rows = list(csv.DictReader(open(path)))
    pts = []
    for r in rows:
        try:
            t = float(r["time"])
            cmax = float(r["c_max"])
            cmin = float(r["c_min"])
        except (KeyError, ValueError):
            continue
        a = (cmax - cmin) / 2.0
        if a > 0:
            pts.append((t, a))
    if len(pts) < 5:
        return None

    a0 = pts[0][1]
    use = [(t, a) for t, a in pts if a >= a0 / math.e]
    if len(use) < 4:
        use = pts[:max(4, len(pts) // 3)]

    xs = [t for t, _ in use]
    ys = [math.log(a) for _, a in use]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0:
        return None
    slope = sxy / sxx
    inter = my - slope * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (inter + slope * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    rate = -slope

    ii = os.path.join(os.path.dirname(path), "case.i")
    if not os.path.exists(ii):
        return None
    kc, e0, e1, ldom, dl, ds, dgb = read_case(open(ii, encoding="utf-8",
                                                    errors="replace").read())
    e0 = e0 if e0 is not None else 1.0
    e1 = e1 if e1 is not None else 0.0
    S = e0 ** 2 + e1 ** 2
    fpp = K_C + 2.0 * A_PART * S
    k = math.pi / ldom
    D = rate / (k ** 2 * (1.0 + kc * k ** 2 / fpp))
    if abs(S) < 1e-12:
        tgt = dl
    elif abs(S - 1.0) < 1e-12:
        tgt = ds
    elif abs(S - 0.5) < 1e-9:
        tgt = dgb
    else:
        tgt = None
    return D, rate, r2, len(use), S, kc, tgt


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    pairs = []
    for a in args:
        if "=" in a:
            tag, d = a.split("=", 1)
        else:
            d = a
            tag = os.path.basename(os.path.normpath(d))
        pairs.append((tag, d))

    print("T12：小扰动衰减 -> 有效扩散系数")
    print()
    print("  %-9s %8s %14s %14s %10s %8s %6s" %
          ("标签", "kappa_c", "D 实测 (m²/s)", "D 目标 (m²/s)", "相对偏差", "R²", "点数"))
    print("  " + "-" * 78)
    ok = True
    for tag, d in pairs:
        p = os.path.join(d, "case_out.csv")
        if not os.path.exists(p):
            print("  %-9s  %s 没有 case_out.csv" % (tag, d))
            continue
        res = fit_decay(p)
        if res is None:
            print("  %-9s  拟合失败" % tag)
            ok = False
            continue
        D, _rate, r2, n, S, kc, tgt = res
        if tgt:
            rel = (D - tgt) / tgt
            good = abs(rel) <= 0.10
            ok &= good
            print("  %-9s %8.2g %14.6e %14.6e %9.2f%% %8.5f %6d%s" %
                  (tag, kc, D, tgt, rel * 100, r2, n,
                   "" if good else "  <- 超 10%"))
        else:
            print("  %-9s %8.2g %14.6e %14s %10s %8.5f %6d" %
                  (tag, kc, D, "?", "?", r2, n))
    print()
    if ok:
        print("  ⇒ 全部在 10% 以内")
    else:
        print("  ⚠ 有状态超出 10% —— 见上表")


if __name__ == "__main__":
    main()
