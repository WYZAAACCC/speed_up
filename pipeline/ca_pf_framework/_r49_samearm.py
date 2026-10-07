#!/usr/bin/env python3
"""_r49_samearm.py —— **在同一个算例上**把"面速率"与"三个候选驱动预言"对账。

## 为什么需要它（R30_AUDIT_LEDGER §22）
P1-25 的"端面慢 44×"整族说法，是在**不同算例、不同口径**之间比较得出的：
`dG_tip` 取自 `dry_r45sm`（N=48、单块、step 4），速率取自 `mb1s`（N=96、两块）。
本轮把 `dG_*` 的 p90/max 与 `<M(n)·dG>_面 · dt` 都接进 CSV 之后，
**终于可以在一条臂上同时拿到三样东西**，从而把口径一次定死。

## ★★★ 口径（**必须写死，否则又会算错**）
`*_sep_nm` 是**面间距** = 两簇对立面**中位位置之差**（`_bk_measure.face_separations`）
⇒ 一根板条的两张对面**同时**外移 ⇒
        `d(sep)/dt = 2 × v_面`
⇒ 与 `v_*_nabs`（**单个**面的局部法向速度）比较时，**必须把 sep 的斜率除以 2**。
⚠ 本条是 R49 自查出来的：第一版对账（§22 初稿）**漏了这个 2 倍**，
   把"差 15 倍"写成了"差 7.6 倍"。**两处都已更正。**

用法：  python _r49_samearm.py <臂目录> [起始步] [结束步]
"""
import csv
import os
import sys

import numpy as np


def load(d, lo=None, hi=None):
    rows = list(csv.DictReader(open(os.path.join(d, 'series.csv'))))
    out = []
    for r in rows:
        try:
            st = int(r['step'])
        except (KeyError, ValueError):
            continue
        if lo is not None and st < lo:
            continue
        if hi is not None and st > hi:
            continue
        out.append(r)
    return out


def fnum(r, k):
    try:
        v = float(r.get(k, ''))
        return v if np.isfinite(v) else np.nan
    except (TypeError, ValueError):
        return np.nan


def slope(rows, col):
    x = np.array([int(r['step']) for r in rows], float)
    y = np.array([fnum(r, col) for r in rows], float)
    m = np.isfinite(y)
    if m.sum() < 3:
        return np.nan, np.nan, 0
    sl = float(np.polyfit(x[m], y[m], 1)[0])
    # R² 作粗守卫
    yh = np.polyval(np.polyfit(x[m], y[m], 1), x[m])
    ss = ((y[m] - y[m].mean()) ** 2).sum()
    r2 = 1.0 - ((y[m] - yh) ** 2).sum() / ss if ss > 0 else np.nan
    return sl, r2, int(m.sum())


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    d = sys.argv[1]
    lo = int(sys.argv[2]) if len(sys.argv) > 2 else None
    hi = int(sys.argv[3]) if len(sys.argv) > 3 else None
    rows = load(d, lo, hi)
    if len(rows) < 3:
        raise SystemExit('行数不足（%d）' % len(rows))
    print('=' * 96)
    print('臂 %s   窗口 step %s..%s   行数 %d'
          % (d, rows[0]['step'], rows[-1]['step'], len(rows)))
    dx = None
    for r in rows:
        if fnum(r, 'dt') == fnum(r, 'dt'):
            pass
    print()
    print('### 一、面速率（金标准：面间距斜率 ÷ 2 = **单个面的推进速率**）')
    print('  %-6s %-15s %-9s %-7s %-13s %s'
          % ('面族', 'd(sep)/dstep', 'R²', 'n', '÷2 = v_面', '单位'))
    vface = {}
    for tag in ('tip', 'side', 'wide'):
        sl, r2, n = slope(rows, '%s_sep_nm' % tag)
        if not np.isfinite(sl):
            print('  %-6s %-15s %-9s %-7s %-13s %s'
                  % (tag, '(列缺失/点不足)', '-', n, '-', ''))
            continue
        vface[tag] = sl / 2.0
        print('  %-6s %+-15.5f %-9.3f %-7d %+-13.5f nm/步'
              % (tag, sl, r2, n, sl / 2.0))
    print()
    print('### 二、直测的面速度预言 `<M(n)·dG>_面 · dt`（同一条臂！）')
    print('  %-6s %-13s %-13s %s' % ('面族', 'signed', '|v|', '末行取值'))
    for tag in ('tip', 'side'):
        sg = fnum(rows[-1], 'v_%s_nsgn' % tag)
        ab = fnum(rows[-1], 'v_%s_nabs' % tag)
        print('  %-6s %+-13.5f %-13.5f step=%s' % (tag, sg, ab, rows[-1]['step']))
    abw = fnum(rows[-1], 'v_wide_nabs')
    print('  %-6s %-13s %-13.5f step=%s' % ('wide', '-', abw, rows[-1]['step']))
    print()
    print('### 三、对账（**同算例、同口径、同窗口**）')
    dgm = fnum(rows[-1], 'dG_max_Jm3')
    dt = fnum(rows[-1], 'dt')
    print('  ΔG_max = %.4e J/m³   dt = %.4e s' % (dgm, dt))
    print()
    # ★★★ R50 修（**这一版才是良定义的比较**）：
    #   原来拿 **瞬时预言** `v_*_nabs`（那一刻的量）去比 **窗口平均的位移速率**
    #   （`d(sep)/dt` 的斜率）⇒ **口径不对等**，而且实测斜率**随窗口剧烈漂移**
    #   （tip 0.27–0.48；side 甚至换号：+0.237 → −0.099 → 0.000）。
    #   良定义的判据是**累积量对齐**：
    #        Δsep(窗口)/2      vs      Σ v_面(t)·Δstep
    #   （`v_*_nabs` 已是 nm/步 ⇒ 乘以该行与下一行的步数差即可积分）。
    print('  **累积对账**（这一版才是良定义的）：')
    print('  %-6s %-14s %-14s %-10s %s'
          % ('面族', 'Δsep/2 (nm)', 'Σ v·Δstep (nm)', '比值', '逐行'))
    for tag in ('tip', 'side', 'wide'):
        col = '%s_sep_nm' % tag
        vcol = 'v_%s_nabs' % tag
        ys = [fnum(r, col) for r in rows]
        vs = [fnum(r, vcol) for r in rows]
        xs = [int(r['step']) for r in rows]
        # ⚠ 第 0 步（以及形核前）**没有面** ⇒ `*_sep_nm` 为空
        #   ⇒ 必须**先裁掉两端的非有限值**，否则整段报"sep 列缺失"
        #   （第一版就是这样，0–1500 窗口全废）。与 `vs` 的处理同源。
        _good = [i for i in range(len(rows)) if np.isfinite(ys[i])]
        if len(_good) < 3:
            print('  %-6s %s' % (tag, '(sep 列有效点 < 3)'))
            continue
        i0, i1 = _good[0], _good[-1]
        dsep = (ys[i1] - ys[i0]) / 2.0
        integ = 0.0
        ok = False
        for i in range(i0, i1):
            if not (np.isfinite(vs[i]) and np.isfinite(vs[i + 1])):
                continue
            integ += 0.5 * (vs[i] + vs[i + 1]) * (xs[i + 1] - xs[i])
            ok = True
        if not ok:
            print('  %-6s %-14.3f %-14s %-10s %s' % (tag, dsep, '(v 列缺失)', '-', ''))
            continue
        ratio = (integ / dsep) if dsep not in (0.0,) else float('nan')
        mark = '✅' if (np.isfinite(ratio) and 0.5 <= ratio <= 2.0) else \
               ('≈0 双方都≈0' if abs(dsep) < 1e-9 and abs(integ) < 1e-9 else '⚠')
        print('  %-6s %+-14.3f %-14.3f %-10.3f %s  (step %d→%d)'
              % (tag, dsep, integ, ratio, mark, xs[i0], xs[i1]))
    print()
    print('  ⚠ 为什么不用"斜率比"：实测斜率**随窗口漂移**（tip 0.27–0.48 nm/步；')
    print('     side 甚至换号 +0.237 → −0.099 → 0.000）⇒ 斜率不是稳态量。')
    print('  ★ 判据：累积比值落在 [0.5, 2] ⇒ 面运动被局部驱动解释，**不需要**新通道。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
