#!/usr/bin/env python3
"""R49: 用**同族算例**的直测统计量，重算"朴素预言" —— 判 R48 的 5.8× 残差是不是口径问题。

输入全部落在同一条臂 `dry_r49dg`（N=48, Δx=125 nm, 2 根板条, 1600×700 nm 板,
200 步）上 —— 即 **面速率与驱动统计量同算例**，这是 R48 缺的那一步。
⚠ 仍然不是 `mb1s` 本身（mb1s 是 3 根板条/N=96）⇒ 结论标记为【待 mb1s62 v3 确认】。
"""
import csv
import os
import sys

D = '_exp/_bk_mb/dry_r49dg'
DX = 125e-9
MOB = None  # 从 meta 读
B_H, B_W = 6.477, 2.3


def mobility(n_dot_nstar_sq, n_dot_w_sq):
    return pow(2.718281828459045, -B_H * n_dot_nstar_sq - B_W * n_dot_w_sq)


def main():
    import json
    m = json.load(open(os.path.join(D, 'meta.json')))
    dx_nm = m['dx_nm']
    rows = list(csv.DictReader(open(os.path.join(D, 'series.csv'))))
    # 取最后一行的 ΔG_max（引擎逐步写在 CSV 的 dG_max_Jm3）
    r = rows[-1]

    def g(k):
        try:
            return float(r[k])
        except (KeyError, ValueError, TypeError):
            return float('nan')

    dgmax = g('dG_max_Jm3')
    print('算例参数: N=%s dx=%.1f nm 板=%.0f×%.0f nm  末行 step=%s'
          % (m.get('N'), dx_nm, m['plate']['L'], m['plate']['W'], r['step']))
    print('ΔG_max = %.4e J/m³' % dgmax)
    print()
    # 面的"标称法向" → M/M0
    #   tip  法向 ≈ a(长轴)；a·n* = -0.127（R30 实测）⇒ (a·n*)² = 0.0161, a·w = 0
    #   side 法向 ≈ w；w·n* = 0, w·w = 1
    #   wide 法向 ≈ n*；n*·n* = 1, n*·w = 0
    FACE = {
        'tip':  ('a', 0.127 ** 2, 0.0),
        'side': ('w', 0.0, 1.0),
        'wide': ('n*', 1.0, 0.0),
    }
    v_cfl = 0.15 * dx_nm                      # nm/step（CFL 上限，最快胞）
    print('CFL 上限 = 0.15Δx = %.2f nm/step' % v_cfl)
    print()
    print('%-6s %-6s %-9s %-13s %-13s %-13s %-11s %s'
          % ('面', 'M/M0', 'v_naive', 'dG中位', 'dG_p90', 'dG_max',
             '中位→v', 'p90→v / max→v'))
    for tag, (nn, c2n, c2w) in FACE.items():
        mm = mobility(c2n, c2w)
        vmax = v_cfl * mm
        med, p90, mx = g('dG_%s' % tag), g('dG_%s_p90' % tag), g('dG_%s_max' % tag)
        def pred(x):
            return vmax * (x / dgmax) if dgmax == dgmax and x == x else float('nan')
        print('%-6s %-6.3f %-9.2f %-13.4e %-13.4e %-13.4e %-11.2f %.2f / %.2f'
              % (tag, mm, vmax, med, p90, mx, pred(med), pred(p90), pred(mx)))
    print()
    print('实验测得的金标准面速率（`mb1s`，Δx=125，3 根板条）:')
    print('  tip +0.25   side +0.37   wide -0.06  nm/step')
    return 0


if __name__ == '__main__':
    sys.exit(main())
