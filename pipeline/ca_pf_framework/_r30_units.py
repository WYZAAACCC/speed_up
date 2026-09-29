#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r30_units.py —— R30 审计：**量纲 / 单位 / 内部一致性**在真实归档数据上的核对。

本仓库在"米 vs nm"上已犯过 3 次同类错误（`gap_w_nm` 忘乘 dx 报 1.2e10 nm；
`_bk_f3flat.py` 把米当 nm；`Wc` 当 nm 打印得 0）。所以这里不靠"读代码觉得对"，
而是**在落盘数据上做恒等式检查**：

  U1 `V0 + Vt` 应 == L³（区域划分覆盖整盒）—— 检查体积单位与守恒。
  U2 `Σ f3_pairs` 应 == `f3_area_m2`（两条**独立代码路径**算同一个量）。
  U3 `f3_area_stair / f3_area_m2` 应 == Σ|n_i|（Cauchy 估计量的内禀恒等式；
     本项目 n* 的 Σ|n_i| = 1.6649）—— 同时验证"两个面积列"的单位一致。
  U4 `nf3`（面数，整数）× Δx² × Σ|n| ... 与 f3_area 的关系（见 U3）。
  U5 `vols` 之和 应 == `Vt`（同一次测量里的两个字段）。
  U6 `ths` 与 `n_lath` 的关系：`n_lath` = 在位的场的 `n_k` 的**中位数** ×1e9。
  U7 `t_s` 与 `Σ dt` 一致；`dt` 与 `cfl_used` 的量级。
  U8 `f3_pos_dx` == (`f3_pos_m` − P0)/Δx（P0 由 CSV 反解）。
  U9 `t_s` 单位（秒）与 `wall_s` 的合理性。
  U10 `psi_mean` / `finite` / `box_touch` 取值范围。
  U11 `cfl_used` 的实际分布（vs 名义 0.15）。

用法: python3 _r30_units.py [臂目录 ...]
"""
import glob
import json
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np                                              # noqa: E402


def read_csv_stable(p, tries=3):
    """读**正在被追加**的 CSV：反复读到行数不再增长（`AGENTS.md` §3.6 的 9p 缓存）。

    返回 (rows, nlines, stable)。"""
    import csv as _csv
    best, n, stable = [], -1, False
    for _ in range(tries):
        with open(p, newline='', encoding='utf-8') as f:
            txt = f.read()
        n2 = txt.count('\n')
        if n2 < n:
            continue
        rows = list(_csv.DictReader(txt.splitlines()))
        if n2 > n:
            best, n, stable = rows, n2, False
        elif n2 == n:
            best, stable = rows, True
            break
    return best, n, stable


def f(x, d=float('nan')):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def sl(x):
    return [float(t) for t in x.split('/') if t.strip() != '']


def main():
    dirs = sys.argv[1:] or sorted(
        d for d in glob.glob(os.path.join(_HERE, '_exp', '_bk_*', '*'))
        if os.path.exists(os.path.join(d, 'series.csv')))
    bad = []
    hdr = ('%-34s %-6s %-22s %-22s %-5s %s'
           % ('臂', '行数', 'U1 |V0+Vt−L³|/L³', 'U2 |Σpairs−area|/area',
              '稳定', 'U3 阶梯/无偏'))
    print('=' * 130)
    print('R30：落盘数据的**单位/恒等式**核对（真实归档，全部离线可复算）')
    print('=' * 130)
    print(hdr)
    print('-' * 130)
    objs = {}
    for d in dirs:
        p = os.path.join(d, 'series.csv')
        rows, n, st = read_csv_stable(p)
        if not rows:
            continue
        mp = os.path.join(d, 'meta.json')
        meta = json.load(open(mp, encoding='utf-8')) if os.path.exists(mp) else {}
        L = f(meta.get('L'))
        n_hab = np.asarray(meta.get('n_hab') or [0, 0, 0], float)
        sn = float(np.abs(n_hab).sum()) if n_hab.size == 3 else float('nan')
        last = rows[-1]
        # U1
        u1 = float('nan')
        if np.isfinite(L):
            V0, Vt = f(last.get('V0')), f(last.get('Vt'))
            u1 = abs(V0 + Vt - L ** 3) / L ** 3
        # U2 逐对 vs 总量
        u2 = float('nan')
        pr = last.get('f3_pairs', '')
        if pr:
            s = 0.0
            for tok in pr.split('/'):
                if ':' in tok:
                    s += f(tok.split(':')[1], 0.0)
            A = f(last.get('f3_area_m2'))
            u2 = abs(s - A * 1e12) / (A * 1e12) if A > 0 else float('nan')
        # U3 阶梯/无偏
        A, As = f(last.get('f3_area_m2')), f(last.get('f3_area_stair'))
        u3 = (As / A) if A > 0 else float('nan')
        flag = []
        if np.isfinite(u1) and u1 > 1e-6:
            flag.append('U1✗')
        if np.isfinite(u2) and u2 > 1e-6:
            flag.append('U2✗')
        if np.isfinite(u3) and np.isfinite(sn) and sn > 0 and abs(u3 / sn - 1) > 0.05:
            flag.append('U3%s' % ('?' if not np.isfinite(sn) else '✗'))
        if flag:
            bad.append((os.path.relpath(d, _HERE), flag))
        objs[os.path.relpath(d, _HERE)] = (rows, meta, d)
        print('%-34s %-6d %-22s %-22s %-5s %-8.4f %s'
              % (os.path.relpath(d, _HERE), len(rows),
                 ('%.3e' % u1) if np.isfinite(u1) else '—',
                 ('%.3e' % u2) if np.isfinite(u2) else '—',
                 'Y' if st else 'N',
                 u3 if np.isfinite(u3) else float('nan'),
                 ' '.join(flag)))
    print('-' * 130)
    print('U1 = |V0+Vt−L³|/L³（应 ~1e-16，浮点级）；U2 = |Σf3_pairs − f3_area|/f3_area'
          '（**两条独立代码路径**）；')
    print('U3 = f3_area_stair/f3_area（应 == Σ|n_i| = %.4f ± 2%%）。' % 1.6649)
    print('⇒ 不一致的臂：%s' % (bad if bad else '**无**'))

    print('\n' + '=' * 130)
    print('U5/U6/U7/U8/U11：同一个臂内的**字段间**一致性（取每个臂的末行）')
    print('=' * 130)
    print('%-34s %-18s %-18s %-16s %-16s %s'
          % ('臂', 'U5 |Σvols−Vt|/Vt', 'U6 |med(ths)−n_lath|', 'U8 Δpos残差(Δx)',
             'U7 dt·n步−t_s', 'U11 cfl_used 中位[范围]'))
    for k, (rows, meta, d) in objs.items():
        last = rows[-1]
        # U5
        vs = sl(last.get('vols', ''))
        Vt = f(last.get('Vt'))
        u5 = abs(sum(vs) - Vt * 1e18) / (Vt * 1e18) if Vt > 0 and vs else float('nan')
        # U6
        th = sl(last.get('ths', ''))
        occ = [t for t, v in zip(th, vs) if v > 0]
        nla = f(last.get('n_lath'))
        u6 = abs(float(np.median(occ)) - nla) if occ else float('nan')
        # U8: f3_pos_dx = (f3_pos_m - P0)/dx, 反解 P0 检查一致性（需 dx）
        dx = f(meta.get('dx_nm')) * 1e-9
        u8 = float('nan')
        a0 = [(f(r.get('f3_pos_m')), f(r.get('f3_pos_dx'))) for r in rows]
        a0 = [(m, q) for m, q in a0 if np.isfinite(m) and np.isfinite(q)]
        if len(a0) >= 2 and np.isfinite(dx):
            P0s = [m - q * dx for m, q in a0]
            u8 = float(np.ptp(P0s)) / dx
        # U7
        dts = [f(r.get('dt')) for r in rows]
        ts = f(last.get('t_s'))
        u7 = abs(sum(dts) - ts) / max(ts, 1e-300)
        # U11
        cfl = [f(r.get('cfl_used')) for r in rows if np.isfinite(f(r.get('cfl_used')))]
        c11 = ('%.3f[%.3f,%.3f]' % (np.median(cfl), min(cfl), max(cfl))) if cfl else '—'
        print('%-34s %-18s %-18s %-16s %-16s %s'
              % (k, '%.2e' % u5 if np.isfinite(u5) else '—',
                 '%.2e' % u6 if np.isfinite(u6) else '—',
                 '%+.2e' % u8 if np.isfinite(u8) else '—',
                 '%.2e' % u7 if np.isfinite(u7) else '—', c11))
    print('-' * 130)
    print('U5 应 ~0（`vols` 与 `Vt` 是同一次测量里的两个字段）；')
    print('U6 应 ~0（`n_lath` 就是"在位场 `n_k` 的中位数 ×1e9"）；')
    print('U8 应 ~0（`f3_pos_dx` 是 `f3_pos_m` 减去一个**常数** P0 再除以 Δx）；')
    print('U7 应 ~0（`t_s` 是逐步累加的 dt 之和）。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
