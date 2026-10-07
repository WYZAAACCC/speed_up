#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r579_report.py --- 把 4 个**并行**跑出来的内存清单 JSON 汇总成 goal §(5) 的报告。

判据与 `_r579_mem160.py` 的 docstring 一致：M1（soft 触发）/ M2（清单自洽）/
M3（`a_f64 ∈ [15.5, 16.5]`）/ M4（f32 恰好 −4.000 B/胞）/ M5（C5 判定）。
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
N = int(os.environ.get('R579_N', '160'))
BUDGET_MB = float(os.environ.get('R579_BUDGET_MB', str(22 * 1024)))
PLATE_L_NM = float(os.environ.get('R579_PLATE_L', '2400'))
PLATE_W_NM = float(os.environ.get('R579_PLATE_W', '640'))
PLATE_T_NM = float(os.environ.get('R579_PLATE_T', '250'))
FILL = float(os.environ.get('R579_FILL', '0.30'))
BOX_UM = float(os.environ.get('R579_BOX_UM', '10'))
OUT = os.environ.get('R579_OUT', '_w2_r579_mem160.log')


def load(prec, nv, pf_phi='materialized'):
    # ⚠ 兼容：`pf_phi` 后缀是在加 `onfly` 时**后加**的 ⇒ 早先那 4 个构型的文件名里没有它。
    for p in (os.path.join(HERE, '_w2_r579_one_%s_nv%d_%s.json' % (prec, nv, pf_phi)),
              os.path.join(HERE, '_w2_r579_one_%s_nv%d.json' % (prec, nv))):
        if os.path.exists(p) and (pf_phi == 'materialized' or '_onfly' in p):
            with open(p, encoding='utf-8') as fh:
                return json.load(fh)
    return None


def main():
    L = []
    A = L.append
    A('=' * 104)
    A('R579 — N=%d 的**实测**内存定律 + `a` 的逐项构成（4 个构型**并行**测）' % N)
    A('=' * 104)
    A('  宿主：python %s  numpy %s   dx=%.4f µm  预算 %.0f MB'
      % (sys.version.split()[0], np.__version__,
         float(os.environ.get('R579_DX', '0.0625')), BUDGET_MB))
    N3 = N ** 3
    CELL = N3 / 2.0 ** 20

    res = {}
    for prec in ('f64', 'f32'):
        for nv in (4, 8):
            d = load(prec, nv)
            if d is None:
                A('  ⚠ 缺 %s/nv=%d 的清单 JSON ⇒ 该构型没跑成功' % (prec, nv))
                continue
            res[(prec, nv)] = d
            A('')
            A('  ── prec=%-3s nv=%d ──（pid 独立进程）' % (prec, nv))
            A('    `pf.phi.dtype`：soft 前 **%s** → soft 后 **%s**   %s'
              % (d['d0'], d['d1'], '✅ M1 PASS' if d['d1'] == 'float64' else '❌ M1 FAIL'))
            A('    数组总计 = **%.1f MB**（= %.3f B/胞 全盒摊）'
              % (d['total'] / 2**20, d['total'] / N3))
            A('    逐项清单（前 10）：')
            for p, sh, dt_, nb in d['rows'][:10]:
                A('      %-36s %-22s %-9s %9.2f MB'
                  % (p[:36], str(sh)[:22], dt_, nb / 2**20))

    if len(res) < 4:
        A('')
        A('  ❌ 构型不全（%d/4）⇒ 无法拟合 `a`/`c`，本报告作废' % len(res))
        out = '\n'.join(L)
        print(out)
        with open(os.path.join(HERE, OUT), 'w', encoding='utf-8') as fh:
            fh.write(out + '\n')
        return 1

    # M2 清单自洽
    A('')
    A('  ── M2 清单自洽（清单求和 vs 总计，同一次构造）──')
    ok2 = True
    for k, d in res.items():
        s = sum(r[3] for r in d['rows'])
        ok2 = ok2 and (s == d['total'])
        A('    %-10s 求和 %d vs 总计 %d ⇒ %s'
          % (str(k), s, d['total'], '✅' if s == d['total'] else '❌'))

    # M3 / M4
    A('')
    A('  ── M3/M4：a 与 f32 差 ──')
    aa = {}
    for prec in ('f64', 'f32'):
        m4 = res[(prec, 4)]['total']            # 字节
        m8 = res[(prec, 8)]['total']            # 字节
        a = (m8 - m4) / (4.0 * N3)              # B/胞（每增加一个 nv）
        # ★★ 单位自查（v1 在这里写错、被自己的量纲检查发现）：
        #   `c` 必须是 **B/胞** ⇒ 分子分母都是"胞"。
        #   v1 写成 `(m4 - 4*a*N3) / (N3/2**20)` ⇒ 得到"B·2²⁰/胞"，化成 MB 时再乘
        #   `N3/2**20` ⇒ 结果放大 2²⁰ 倍（报出 `fix = 1.4e9 MB`、`nv_max = 0`）。
        c = (m4 - 4.0 * a * N3) / N3            # B/胞（固定项）
        aa[prec] = (a, c, (m8 - m4) / 2**20)
        A('    %-3s：ΔM(nv 4→8) = %.1f MB ⇒ **a = %.5f B/胞**   c = %.2f B/胞'
          % (prec, (m8 - m4) / 2**20, a, c))
    ok3 = 15.5 <= aa['f64'][0] <= 16.5
    A('    M3（a_f64 ∈ [15.5, 16.5]）：%s'
      % ('✅ PASS' if ok3 else '❌ FAIL ⇒ 还有随 nv 增长的项没被识别'))
    d32 = aa['f64'][0] - aa['f32'][0]
    ok4 = abs(d32 - 4.0) < 1e-6
    A('    M4（f32 让 a 减少 **恰好 4.000**）：实测 %.6f ⇒ %s'
      % (d32, '✅ PASS' if ok4 else '❌ FAIL ⇒ 清单口径有问题'))

    # M5 C5 判定
    A('')
    A('  ── M5：N=%d 在 %.0f MB 预算下的 nv_max（**实测 a/c，无外推**）──'
      % (N, BUDGET_MB))
    V_LATH = (PLATE_L_NM * 1e-3) * (PLATE_W_NM * 1e-3) * (PLATE_T_NM * 1e-3)
    need = FILL * BOX_UM ** 3 / V_LATH
    A('    几何（`_bk_exp.py` 当前默认）：板条 %.0f×%.0f×%.0f nm ⇒ V_lath = **%.4f µm³**'
      % (PLATE_L_NM, PLATE_W_NM, PLATE_T_NM, V_LATH))
    A('    填满 %.0f%% 的 %.0f µm 盒 = %.1f µm³ ⇒ **需要 nv ≈ %.0f 根**'
      % (100 * FILL, BOX_UM, FILL * BOX_UM ** 3, need))
    A('')
    A('    %-6s %-11s %-11s %-11s %-10s %-10s %s'
      % ('prec', 'a(B/胞)', '每nv(MB)', '固定(MB)', 'nv_max', '可达分数', 'vs 需求'))
    mat = {}
    for prec in ('f64', 'f32'):
        a, c, _ = aa[prec]
        per = a * CELL
        fix = c * CELL
        nv_max = max(int((BUDGET_MB - fix) / per), 0)
        mat[prec] = nv_max
        pct = 100.0 * nv_max * V_LATH / BOX_UM ** 3
        flag = '✅ 够' if nv_max >= need else '❌ 不够（差 %.2f×）' % (need / max(nv_max, 1))
        A('    %-6s %-11.5f %-11.2f %-11.1f %-10d %.1f%%     %s'
          % (prec, a, per, fix, nv_max, pct, flag))
    A('')
    A('  ── 与归档结论对账（**本轮要复核的东西**）──')
    for nm, a_ass in (('R550（a=9.009，**未触发 soft**）', 9.009),
                      ('R553（a=5.009，f32 + 未触发 soft）', 5.009)):
        nvo = max(int((BUDGET_MB - 311.8 * CELL) / (a_ass * CELL)), 0)
        A('    %-34s ⇒ nv_max ≈ %4d，转变分数 %.1f%%'
          % (nm, nvo, 100.0 * nvo * V_LATH / BOX_UM ** 3))
    A('    ⚠ 上面两行是**外推**（N=64 拟合 → N=160）；本报告上面那两行是 **N=160 实测**。')

    # a 的构成
    A('')
    A('  ── `a` 的逐项构成（f64/nv=8 的清单，按"是否随 nv 增长"分组）──')
    rows = res[('f64', 8)]['rows']
    A('    随 nv 增长的（`shape[0] == nreg == %d`）：' % (8 + 1))
    for p, sh, dt_, nb in rows:
        if sh and sh[0] == 8 + 1:
            A('      %-40s %-20s %-9s %9.2f MB  ⇒ 该数组共 %.3f B/胞，其中每 nv 行 %.3f'
              % (p[:40], str(sh)[:20], dt_, nb / 2**20, nb / N3,
                 (nb / N3) / (8 + 1)))
    A('    固定项里最大的 6 个（**进 c，不进 a**）：')
    _c = 0
    for p, sh, dt_, nb in rows:
        if sh and sh[0] != 9:
            A('      %-40s %-20s %-9s %9.2f MB' % (p[:40], str(sh)[:20], dt_, nb / 2**20))
            _c += 1
            if _c >= 6:
                break

    npass = sum([ok2, ok3, ok4])
    # ---------- ★ onfly 的**直接实测**（不许用 "16−7" 推）----------
    on = {}
    for prec in ('f64', 'f32'):
        for nv in (4, 8):
            d = load(prec, nv, 'onfly')
            if d:
                on[(prec, nv)] = d
    if len(on) == 4:
        A('')
        A('  ══ `--pf-phi onfly`（软指示场不物化）的**直接实测** ══')
        A('    %-6s %-12s %-12s %-12s %-10s %s'
          % ('prec', 'a 物化', 'a onfly', '实测差', 'nv_max', 'vs 需求'))
        for prec in ('f64', 'f32'):
            m4o = on[(prec, 4)]['total']
            m8o = on[(prec, 8)]['total']
            a_o = (m8o - m4o) / (4.0 * N3)
            c_o = (m4o - 4.0 * a_o * N3) / N3
            a_m, c_m, _ = aa[prec]
            per = a_o * CELL
            fix = c_o * CELL
            nvm = max(int((BUDGET_MB - fix) / per), 0)
            on[(prec, 'a')] = a_o
            on[(prec, 'nvmax')] = nvm
            A('    %-6s %-12.5f %-12.5f %-12.5f %-10d %s'
              % (prec, a_m, a_o, a_m - a_o, nvm,
                 '✅ 够' if nvm >= need else '❌ 差 %.2f×' % (need / max(nvm, 1))))
        A('')
        A('    ★ C5 判定（N=160 **实测** a，**无外推**；需要 nv ≈ %.0f）' % need)
        A('      · 物化 + f64        ：nv_max = %d' % mat['f64'])
        A('      · onfly + f64       ：nv_max = %d' % on[('f64', 'nvmax')])
        A('      · 物化 + f32        ：nv_max = %d' % mat['f32'])
        A('      · **onfly + f32**   ：nv_max = %d  ⇒ %s'
          % (on[('f32', 'nvmax')],
             '✅ **可达 C5**' if on[('f32', 'nvmax')] >= need else '❌ 仍不够'))

    A('')
    A('  ★ 汇总：M2=%s  M3=%s  M4=%s  （%d/3）'
      % ('PASS' if ok2 else 'FAIL', 'PASS' if ok3 else 'FAIL',
         'PASS' if ok4 else 'FAIL', npass))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, OUT), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
    return 0 if npass == 3 else 1


if __name__ == '__main__':
    sys.exit(main())
