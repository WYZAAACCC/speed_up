#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_athermal.py —— 核验 **athermal 形核律**（R29 闭环）实际跑出来的行为。

它回答三个问题（每个都有预登记判据）：

| 判据 | 问题 | 数据来源 |
|---|---|---|
| **A-1** | 跑出来的板条数 == `floor(α_KM·(M_s − T_end))`？ | `closure.json` + `nuc_dbg.json` |
| **A-2** | 形核事件数 == n_law − 1（第 1 片是预摆的）？ | `nuc_dbg.json.T_events` |
| **A-3** | **每次事件的温度**是否落在 `T_k = M_s − k/α_KM` 的一个时钟步内？ | `T_events` |
| **A-4** | 实现出来的有序比 `Δt_grow/Δt_nuc` 是否 ≤1（= 顺序形核，不是 burst）？ | `T_events` 的 `df` |
| **A-5** | 末态块是完整的（`nslab_n == M` 且 `nf3_col == M−1` 且 `runs` 有 M 个不同场）？ | `series.csv` |
| **A-6** | 有没有撞盒壁 / 出现非有限值？ | `series.csv` |
| **A-7** | 时钟真的走完了 `M_s → T_end`（`t_sim ≥ (M_s−T_end)/q`）？ | `series.csv` + `closure.json` |

⚠ 方法学（本项目的硬规矩）：`--selftest` 里有**正/负对照**。
  负对照是**人为把一个事件温度改歪**，确认 A-3 真的会 FAIL —— 只验证
  "正常情况能过"等于没验证（AGENTS.md §3.4）。

用法：
    python3 _bk_athermal.py --root _exp/_bk_closed --tag cl1
    python3 _bk_athermal.py --selftest
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import numpy as np                                              # noqa: E402
import windowB_closure as CL                                    # noqa: E402


# ---------------------------------------------------------------------------
def load(tag, root):
    d = os.path.join(_HERE, root, tag)
    out = {}
    for name in ('closure.json', 'nuc_dbg.json', 'meta.json'):
        p = os.path.join(d, name)
        out[name.split('.')[0]] = (json.load(open(p, encoding='utf-8'))
                                   if os.path.exists(p) else None)
    p = os.path.join(d, 'series.csv')
    if os.path.exists(p):
        import csv
        out['series'] = list(csv.DictReader(open(p)))
    else:
        out['series'] = None
    out['dir'] = d
    return out


def fnum(row, k, default=float('nan')):
    try:
        return float(row[k])
    except (KeyError, TypeError, ValueError):
        return default


def judge(tag, root, verbose=True):
    D = load(tag, root)
    ck = []
    cl, nd, se = D['closure'], D['nuc_dbg'], D['series']
    if cl is None or nd is None or not se:
        print('✗ %s/%s 缺 closure.json / nuc_dbg.json / series.csv' % (root, tag))
        return False, []
    alpha = float(cl['alpha_KM'])
    Ms, T0, DS = float(cl['Ms']), float(cl['T0']), float(cl['DS'])
    q = cl.get('q')
    n_law = int(np.floor(CL.alpha_km_n_lath(float(cl['T_end']), alpha) + 1e-12))
    M = int((D['meta'] or {}).get('nv', 0)) or int(cl.get('n_law', n_law))
    L_lath = float(cl['geometry']['plate_L_nm']) * 1e-9
    MOB = 1.0e-9                                    # 见 `T16_verify_rve.MOB`

    # ---- A-1：导出板条数 ------------------------------------------------
    ck.append(('A-1 导出板条数 n_law == floor(α_KM·(M_s−T_end)) == nv',
               (abs(float(cl['n_law_float']) - CL.alpha_km_n_lath(float(cl['T_end']), alpha))
                < 1e-9) and (int(cl['n_law']) == n_law) and (n_law == M),
               'n_law_float=%.4f n_law=%d nv(M)=%d' % (cl['n_law_float'],
                                                       int(cl['n_law']), M)))

    ev = nd.get('T_events') or []
    n_ev = len(ev)
    # ---- A-2：事件数 -----------------------------------------------------
    ck.append(('A-2 形核事件数 == n_law − 1（第 1 片是 t=0 预摆）',
               n_ev == n_law - 1, '事件数=%d，应为 %d' % (n_ev, n_law - 1)))

    # ---- A-3：事件温度 == T_k（时钟步内） --------------------------------
    #   ★ 口径必须**双边**：事件在"第一步 T ≤ T_k"处触发 ⇒ 允许的超调是
    #     `q·dt`（实测最大 ≈0.22 K），而**测早了**同样是违反律（例如事件次序错乱）。
    #     第一版只查 `T_k − T_event > 0` 一侧 ⇒ 把"第 2 个事件发生在 T_1"
    #     这种明显违反判成 PASS（`--selftest` 的 N-3 抓到）。
    worst = 0.0
    rows = []
    TOL_K = 1.0
    for i, e in enumerate(ev, start=1):
        Tk = CL.T_of_k(i, alpha)
        dev = abs(float(e['T']) - Tk)
        worst = max(worst, dev)
        rows.append('k=%d T=%.2f T_k=%.2f |Δ|=%.2f K' % (i, e['T'], Tk, dev))
    ok3 = bool(ev) and (worst < TOL_K)
    ck.append(('A-3 每次事件的温度落在 T_k 的 %g K 内（**双边**）' % TOL_K,
               ok3, '；'.join(rows) if rows else '无事件'))

    # ---- A-4：实现出来的有序比 ------------------------------------------
    rs = []
    for e in ev:
        df = float(e['df'])
        v = MOB * df
        t_grow = L_lath / v
        t_nuc = 1.0 / (alpha * float(q))
        rs.append(t_grow / t_nuc)
    worst_r = max(rs) if rs else float('nan')
    ck.append(('A-4 实现的有序比 Δt_grow/Δt_nuc ≤ 1（顺序形核）',
               bool(rs) and worst_r <= 1.0,
               '逐次=%s（最差 %.3f）' % ('/'.join('%.3f' % x for x in rs), worst_r)))

    # ---- A-5：块完整 -----------------------------------------------------
    last = se[-1]
    nslab = int(fnum(last, 'nslab_n', -1))
    nf3 = int(fnum(last, 'nf3_col', -1))
    nrun = len(set(int(x) for x in last.get('runs', '').split('/') if x))
    ck.append(('A-5 末态块完整：nslab_n == M 且 nf3_col == M−1 且 runs 有 M 个场',
               (nslab == M) and (nf3 == M - 1) and (nrun == M),
               'nslab_n=%d nf3_col=%d runs=%s（不同场 %d）'
               % (nslab, nf3, last.get('runs'), nrun)))

    # ---- A-6：数值健康 ---------------------------------------------------
    touch = int(fnum(last, 'box_touch', -1))
    fin = int(fnum(last, 'finite', 0))
    ck.append(('A-6 没撞盒壁（box_touch==0）且 phi 有限',
               (touch == 0) and (fin == 1), 'box_touch=%d finite=%d' % (touch, fin)))

    # ---- A-7：时钟走完 ---------------------------------------------------
    t_end_sim = float(fnum(last, 't_s'))
    # `T_start` 的读法要**显式可诊断**：`closure.json` 里没有就按 `T_1` 算，并打印出来。
    # （本项目在"读数口径"上栽过四次 ⇒ 不允许静默取默认值。）
    if cl.get('T_start') is not None:
        T_start, tsrc = float(cl['T_start']), 'closure.json'
    else:
        T_start, tsrc = CL.T_start_of_clock(alpha), '⚠ 现场按 T_1 算（closure.json 无 T_start）'
    need = (T_start - float(cl['T_end'])) / float(q)
    ck.append(('A-7 时钟走完 T_start(T_1) → T_end（t_sim ≥ ΔT/q）',
               t_end_sim >= need * 0.999,
               't_sim=%.4e 需要≥%.4e（比 %.3f）[T_start=%.2f K 来自 %s]'
               % (t_end_sim, need, t_end_sim / need, T_start, tsrc)))

    # ---- A-8：总体积与几何预期一致 ---------------------------------------
    #   `Vt` 应 ≈ n·L·W·t_physical（每片都长到**物理**尺寸）。
    #   ⚠ 必须用 `T_physical` 而**不是**播种厚：播种厚里含"预补的被咬量"。
    geo_nm = float(cl['geometry'].get('plate_T_physical_nm')
                   or cl['geometry']['plate_T_nm'])
    geo = (M * float(cl['geometry']['plate_L_nm'])
           * float(cl['geometry']['plate_W_nm']) * geo_nm) * 1e-9   # nm³ → µm³
    Vt = float(fnum(last, 'Vt'))
    ck.append(('A-8 总体积 ≈ n·L·W·t（±25%）', abs(Vt / geo - 1.0) <= 0.25,
               'Vt=%.4f µm³  几何=%.4f µm³  比=%.3f' % (Vt, geo, Vt / geo)))

    if verbose:
        print('=' * 104)
        print('athermal 形核律核验 —— %s（%s）' % (tag, D['dir']))
        print('  α_KM=%.4e /K  M_s=%.0f K  T_end=%.0f K  q=%s K/s  n_law=%d  M=%d'
              % (alpha, Ms, float(cl['T_end']),
                 ('%.4e' % q) if q else 'n/a', n_law, M))
        print('=' * 104)
        for t, ok, det in ck:
            print('   %-62s %s  %s' % (t, 'PASS' if ok else '**FAIL**', det))
        nf = sum(1 for c in ck if not c[1])
        print('-' * 104)
        print('   A-1..A-7  FAIL = %d / %d' % (nf, len(ck)))
    return all(c[1] for c in ck), ck


# ---------------------------------------------------------------------------
def selftest(verbose=True):
    """正/负对照：把 `judge` 的核心算式喂**人造数据**，确认它真的会拦。"""
    chk = []

    def ck(name, cond, extra=''):
        chk.append((name, bool(cond), extra))

    alpha, Ms = 0.011, 873.0

    def _mk(offset_k=0.0):
        out = []
        for k in range(1, 6):
            out.append(dict(step=100 * k, t=1e-5 * k,
                            T=CL.T_of_k(k, alpha) - offset_k,
                            df=4.147e5 * (1145.0 - (CL.T_of_k(k, alpha) - offset_k))))
        return out

    def _worst_dev(ev, tol=1.0):
        """与 `judge` 的 A-3 **同一算式**（双边 |Δ|）。"""
        w = 0.0
        for i, e in enumerate(ev, start=1):
            w = max(w, abs(float(e['T']) - CL.T_of_k(i, alpha)))
        return w

    w_ok = _worst_dev(_mk(0.4))
    ck('N-1 正对照：正常事件序列的 |ΔT| = 0.4 K < 1 K', w_ok < 1.0, '%.2f' % w_ok)
    w_bad = _worst_dev(_mk(40.0))
    ck('N-2 ★负对照：事件温度整体压低 40 K ⇒ |ΔT| = 40 K ⇒ **必须被拦**',
       not (w_bad < 1.0), '%.2f' % w_bad)
    ev_bad = _mk(0.4)
    ev_bad[1]['T'] = CL.T_of_k(1, alpha) - 0.4      # 第 2 个事件给成 T_1
    ck('N-3 ★负对照：把第 2 个事件的温度写成 T_1（次序错乱）⇒ **必须被拦**',
       not (_worst_dev(ev_bad) < 1.0), '%.2f' % _worst_dev(ev_bad))
    ev_swap = _mk(0.4)
    ev_swap[0], ev_swap[1] = ev_swap[1], ev_swap[0]  # 交换前两个事件
    ck('N-3b ★负对照：交换前两个事件的**次序** ⇒ **必须被拦**',
       not (_worst_dev(ev_swap) < 1.0), '%.2f' % _worst_dev(ev_swap))
    # 有序比：人造一个"太快"的冷速
    def _ratio(df, q):
        return (4.59e-6 / (1e-9 * df)) / (1.0 / (alpha * q))
    ck('N-4 正对照：q=1.787e6、df=DS(873K) ⇒ 有序比 ≤1',
       _ratio(4.147e5 * (1145 - 873), 1.787e6) <= 1.0,
       '%.3f' % _ratio(4.147e5 * (1145 - 873), 1.787e6))
    ck('N-5 ★负对照：q 放大 10× ⇒ 有序比 >1 ⇒ **必须被拦**',
       _ratio(4.147e5 * (1145 - 873), 1.787e7) > 1.0,
       '%.3f' % _ratio(4.147e5 * (1145 - 272), 1.787e7))

    if verbose:
        print('=' * 104)
        print('_bk_athermal 自检（正/负对照）')
        print('=' * 104)
        for n, v, e in chk:
            print('  %-58s %s   %s' % (n, 'PASS' if v else '**FAIL**', e))
        nf = sum(1 for c in chk if not c[1])
        print('  对照数 = %d   FAIL = %d' % (len(chk), nf))
    return all(c[1] for c in chk), chk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='_exp/_bk_closed')
    ap.add_argument('--tag', default='cl1')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        ok, _ = selftest()
        return 0 if ok else 1
    ok, _ = judge(a.tag, a.root)
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
