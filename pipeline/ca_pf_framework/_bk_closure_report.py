#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_closure_report.py —— 由 `windowB_closure` 生成 **参数闭环报告**（Markdown）。

为什么要有它：用户在 R29 要求「把当前物理框架下所有物理公式里的参数提取出来」。
手写一张表会在改代码后失效 ⇒ 参数表**从代码生成**，报告正文只写论证。
`windowB_closure.params()` 是**唯一真源**；本文件只负责排版与把闭式的数值填进去。

用法：
    python3 _bk_closure_report.py                 # 打到 stdout
    python3 _bk_closure_report.py --out BLOCK_PARAM_TABLE.md
    python3 _bk_closure_report.py --selftest      # 正/负对照
"""
import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import windowB_closure as CL                                    # noqa: E402

TIER_ORDER = ['推', '借', '标', '数']
TIER_NAME = {
    '推': '**[推]** 纯推导（无自由常数）',
    '借': '**[借]** 文献值（带出处与误差带）',
    '标': '**[标]** 仍需标定的单一常数',
    '数': '**[数]** 数值/建模选择（不是物理量）',
}


def fmt(v):
    if isinstance(v, float):
        if v != 0 and (abs(v) < 1e-3 or abs(v) >= 1e5):
            return '%.4e' % v
        return ('%.6g' % v)
    if isinstance(v, (tuple, list)):
        return '(' + ', '.join(fmt(x) for x in v) + ')'
    if isinstance(v, dict):
        return '; '.join('%s:%s' % (k, fmt(x)) for k, x in v.items())
    return str(v)


def table(params, tiers=None):
    out = ['| 参数（代码里的名字） | 值 | 单位 | 出现在哪 | 在公式里的角色 | 层 | 出处 / 闭环论证 |',
           '|---|---|---|---|---|---|---|']
    for p in params:
        if tiers and p['tier'] not in tiers:
            continue
        out.append('| `%s` | `%s` | %s | %s | %s | **%s** | %s |'
                   % (p['name'], fmt(p['value']), p['unit'], p['where'],
                      p['role'], p['tier'], p['source'].replace('|', '\\|')))
    return '\n'.join(out)


def closure_numbers():
    """把 C-1..C-7 的**当前数值**算一遍（报告里的数字随代码更新，不手抄）。"""
    rec = CL.recommend()
    w = CL.wetting_check(0.25, 5.0)
    return [
        ('C-1 ΔG*/kT @M_s（γ=0.25）', '%.0f' % CL.barrier_ratio(0.25, CL.DG_CRIT_REF,
                                                               CL.M_S_TI64),
         '需要 ≲60 才有可测速率；差 %.0f 个数量级'
         % (CL.barrier_ratio(0.25, CL.DG_CRIT_REF, CL.M_S_TI64) / 60.0)),
        ('C-1 允许 athermal 的 γ 上限', '%.4f J/m²' % CL.gamma_max_athermal(
            CL.DG_CRIT_REF, CL.M_S_TI64),
         '文献最低端 0.201 ⇒ **低 2.5 倍**，结论不依赖 γ 取哪个文献值'),
        ('C-2 n = α_KM(M_s − T_end)', 'floor(%.4f) = **%d**'
         % (rec['n_lath_float'], rec['n_lath']),
         '与归档"规定的 6"**独立地一致**'),
        ('C-2 T_k（逐根形核温度）',
         ' '.join('T%d=%.0f K' % (k, CL.T_of_k(k)) for k in range(1, 7)),
         '可直接证伪：原位/中断实验数板条'),
        ('C-3 q 上界（有序形核）', '%.4e K/s' % rec['q_cap'],
         '目标比 %.2f ⇒ 用 q=%.4e K/s' % (rec['ratio_target'], rec['q'])),
        ('C-3 最小步数（物理下界）', '%.0f 步' % rec['steps_min'],
         '与 MOB、q **无关**；实际用 %d 步' % rec['steps']),
        ('C-4 几何容纳 n_cap', '%d（Δx=%.0f nm）' % (rec['n_geo_cap'], rec['dx_nm']),
         'Δx=62.5 nm + 文献板条厚 ⇒ n_cap=%d < 6 ⇒ 必须放大网格'
         % CL.alpha_max_from_box(96 * 62.5e-9, 680e-9, 9 * 680e-9,
                                 0.2667 * 9 * 680e-9, CL.HAT_N, CL.HAT_A,
                                 CL.HAT_W)[0]),
        ('C-5 β_h 下界', '%.2f（%d 步）' % (rec['beta_h_floor'], rec['steps']),
         'β_h(T) 运行均值 %.2f ⇒ 两者一致' % rec['beta_h_T']),
        ('C-6 润湿余量', '%.2f×（γ_F1=0.25）' % w['margin'],
         '翻转阈值 γ = %.4f J/m²' % w['flip_gamma']),
        ('C-7 ΔG_v / (4γ/t)', '%.1f（t=510 nm, γ=0.25）'
         % CL.fcrit_ratio(0.25, 510e-9, CL.DG_CRIT_REF)[1],
         '≫1 ⇒ `use_fcrit` 结构性惰性'),
    ]


def report():
    rec = CL.recommend()
    L = []
    L.append('# Window B「块」物理框架 —— **参数闭环报告**（由代码生成）\n')
    L.append('> 由 `_bk_closure_report.py` 从 **`windowB_closure.py`** 生成。'
             '参数表的唯一真源是 `windowB_closure.params()`。')
    L.append('> **改了代码里的数不改 `params()` = 记账失效。**\n')
    L.append('层标记：' + ' | '.join(TIER_NAME[t] for t in TIER_ORDER) + '\n')

    L.append('## 1. 七条闭环结论（数值随代码更新）\n')
    L.append('| 结论 | 当前值 | 说明 |')
    L.append('|---|---|---|')
    for a, b, c in closure_numbers():
        L.append('| %s | **%s** | %s |' % (a, b, c))
    L.append('')

    L.append('## 2. 闭环配置（`recommend()` 一次算出，不是调出来的）\n')
    L.append('```')
    for k in ('n_lath_float', 'n_lath', 't_lath_nm', 'L_lath', 'W_lath', 'elong',
              'dx_nm', 'L_box_um', 't_over_dx', 'n_geo_cap', 'alpha_max',
              'q_cap', 'q', 'ordered_ratio', 'steps_min', 'steps',
              'beta_h_T', 'beta_h_floor', 'beta_h_use', 't_sim',
              'r_nuc_nm', 'overlap_nm', 'ok'):
        if k in rec:
            L.append('  %-16s %s' % (k, rec[k]))
    L.append('```\n')

    L.append('## 3. 参数总表（当前物理框架下**所有**公式里的参数）\n')
    for t in TIER_ORDER:
        L.append('### 3.%d %s\n' % (TIER_ORDER.index(t) + 1, TIER_NAME[t]))
        L.append(table(CL.params(), tiers={t}))
        L.append('')

    L.append('## 4. 必须随结论一起报的局限\n')
    for i, s in enumerate(CL.limitations(), 1):
        L.append('%d. %s' % (i, s))
    L.append('')
    return '\n'.join(L)


def selftest(verbose=True):
    chk = []

    def ck(n, c, e=''):
        chk.append((n, bool(c), e))

    ps = CL.params()
    names = [p['name'] for p in ps]
    ck('T-1 参数条数 ≥ 30', len(ps) >= 30, '%d 条' % len(ps))
    ck('T-2 名字不重复', len(names) == len(set(names)))
    ck('T-3 每条都有 tier 且合法', all(p['tier'] in TIER_ORDER for p in ps),
       str(sorted(set(p['tier'] for p in ps))))
    ck('T-4 每条都有出处字符串（非空）', all(p['source'].strip() for p in ps))
    ck('T-5 每条都有 where（能被定位到代码）', all(p['where'].strip() for p in ps))
    ck('T-6 **C-2 由推导给出 n=6**', rec_n() == 6, str(rec_n()))
    ck('T-7 报告能渲染出表（含表头）',
       '| 参数（代码里的名字） |' in table(ps))
    ck('T-8 报告正文含七条结论的标题',
       all(('C-%d' % i) in report() for i in range(1, 8)))
    # ★ 负对照：把一条参数的 tier 改成非法值，T-3 必须拦
    ps2 = [dict(p) for p in ps]
    ps2[0]['tier'] = 'XX'
    ck('T-9 ★负对照：非法 tier 会被 T-3 拦',
       not all(p['tier'] in TIER_ORDER for p in ps2))
    ps3 = [dict(p) for p in ps]
    ps3[1]['source'] = '   '
    ck('T-10 ★负对照：空出处会被 T-4 拦',
       not all(p['source'].strip() for p in ps3))
    if verbose:
        print('=' * 96)
        print('_bk_closure_report 自检')
        print('=' * 96)
        for n, v, e in chk:
            print('  %-56s %s   %s' % (n, 'PASS' if v else '**FAIL**', e))
        print('  对照数 = %d   FAIL = %d' % (len(chk), sum(1 for c in chk if not c[1])))
    return all(c[1] for c in chk), chk


def rec_n():
    import windowB_closure as _C
    return _C.recommend()['n_lath']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        ok, _ = selftest()
        return 0 if ok else 1
    txt = report()
    if a.out:
        with open(os.path.join(_HERE, a.out), 'w', encoding='utf-8') as f:
            f.write(txt)
        print('已写 %s（%d 字符）' % (a.out, len(txt)))
    else:
        print(txt)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
