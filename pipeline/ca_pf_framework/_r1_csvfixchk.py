#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_csvfixchk.py --- 对 `series.csv` 记账列的修复做**正/负对照**。

`AGENTS.md §3.4`：写守卫/修复后必须**反向测一次**，只验证"正常情况能过"等于没验证。

这里做三件事：
  P-1 静态检查：`_r1_exp.py` 里是否还存在"用 `mm` 覆盖全部 `COLS`"的写法。
  P-2 负对照：直接复现**旧写法**，确认它确实产生空 `step`（证明 bug 真实存在）。
  P-3 正对照：复现**新写法**，确认 `step`/`t_s`/`dG_max` 等记账量被保住、
      且测量量仍然被写入。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '_r1_exp.py')
COLS = ['step', 't_s', 'dt', 'ncell', 'V', 'L', 'W', 'T', 'Lb', 'Wb', 'Tb',
        'L_cal', 'W_cal', 'T_cal', 'LW_cal', 'LT_cal', 'WT_cal',
        'LWo', 'LTo', 'WTo', 'LW', 'LT', 'WT', 'LW_pm', 'LT_pm',
        'LA', 'WA', 'TA', 'LWA', 'LTA', 'WTA', 'fill_A', 'A_tot', 'A_a', 'A_w', 'A_n',
        'fill', 'fill_n', 'ang_a_deg', 'sv0', 'sv1', 'sv2',
        'ncomp', 'frac_big', 'L_big', 'nif', 'gmed', 'f_a', 'f_w', 'f_n',
        'nc', 'Lc', 'Wc', 'Tc', 'LWc', 'LTc', 'align_deg', 'big_frac', 'gap_w_nm',
        'nsig', 'debris',
        'ded_a', 'ded_w', 'ded_n', 'ded_all', 'ed_par_mean',
        'box_touch', 'band_bad', 'ok', 'dG_max', 'nreinit', 'nskip', 'regflip',
        'adv_wall', 'reinit_wall', 'reinit_pairs']

txt = open(SRC).read()
# ⚠ P-1 第一版把**注释里引用的旧代码**也算成了"仍存在旧写法"，报了 1 处假阳性。
#   ⇒ 先剥掉注释行再匹配（`AGENTS.md §3.3`：工具没给出预期结果时先怀疑自己的检查）。
code = '\n'.join(l for l in txt.splitlines() if not l.lstrip().startswith('#'))
print('=' * 88)
print('P-1 静态检查 `_r1_exp.py`（**已剥离注释行**）：')
bad = re.findall(r'row\.update\(\{k: mm\.get\(k, float\(.nan.\)\) for k in COLS\}\)',
                 code)
print('   仍存在旧写法 `row.update({k: mm.get(k,nan) for k in COLS})` ：%d 处  ⇒ %s'
      % (len(bad), '⛔ 未修复' if bad else '✅ 已移除'))
new = re.findall(r'if k in COLS and k not in row:', code)
print('   新写法 `if k in COLS and k not in row:` ：%d 处  ⇒ %s'
      % (len(new), '✅ 已就位' if new else '⛔ 缺失'))
print('   `every=a.every` 是否写入 meta ：%s'
      % ('✅' if 'every=a.every' in code else '⛔'))

# ---- 复现两种写法 ----
def mk_mm():
    """模拟 `measure()` 的返回：只有测量量，没有记账量。"""
    return dict(ncell=1234, V=1.5e-18, L=2e-6, W=8e-7, T=3.2e-7,
                Lb=2.1e-6, Wb=8.2e-7, Tb=3.3e-7,
                L_cal=2.05e-6, W_cal=8.1e-7, T_cal=3.25e-7,
                LW_cal=2.53, LT_cal=6.31, WT_cal=2.49,
                box_touch=0, band_bad=0, ok=1)


def mk_row():
    return dict(step=240, t_s=1.5e-7, dt=5.0e-11, dG_max=1e7, nreinit=3,
                nskip=1, regflip=0, adv_wall=12.5, reinit_wall=0.42,
                reinit_pairs=0)


def old_way():
    row = mk_row(); mm = mk_mm()
    row.update({k: mm.get(k, float('nan')) for k in COLS})
    for k in COLS:
        row.setdefault(k, float('nan'))
    return row


def new_way():
    row = mk_row(); mm = mk_mm()
    for k, v in mm.items():
        if k in COLS and k not in row:
            row[k] = v
    for k in COLS:
        row.setdefault(k, float('nan'))
    return row


def nan(v):
    return isinstance(v, float) and v != v


BOOK = ['step', 't_s', 'dt', 'dG_max', 'nreinit', 'nskip', 'regflip',
        'adv_wall', 'reinit_wall', 'reinit_pairs']
MEAS = ['ncell', 'L_cal', 'W_cal', 'T_cal', 'LW_cal', 'ok']

print('\nP-2 负对照（旧写法）：')
o = old_way()
lost = [k for k in BOOK if nan(o[k])]
print('   记账量丢失：%d/%d  %s' % (len(lost), len(BOOK), lost))
print('   测量量保住：%d/%d' % (sum(not nan(o[k]) for k in MEAS), len(MEAS)))
print('   ⇒ %s' % ('✅ 复现了 bug（`step` 等全变 NaN）' if len(lost) == len(BOOK)
                   else '⚠ 未复现，负对照无效'))

print('\nP-3 正对照（新写法）：')
n = new_way()
lostn = [k for k in BOOK if nan(n[k])]
print('   记账量丢失：%d/%d  %s' % (len(lostn), len(BOOK), lostn))
print('     值：step=%s t_s=%s dG_max=%s nreinit=%s adv_wall=%s'
      % (n['step'], n['t_s'], n['dG_max'], n['nreinit'], n['adv_wall']))
print('   测量量保住：%d/%d（L_cal=%s ok=%s）'
      % (sum(not nan(n[k]) for k in MEAS), len(MEAS), n['L_cal'], n['ok']))
ok_all = (len(lostn) == 0) and all(not nan(n[k]) for k in MEAS)
print('   ⇒ %s' % ('✅ 记账量与测量量**同时**保住' if ok_all
                   else '⛔ 修复不完整'))
print('=' * 88)
print('结论：%s' % ('修复有效（正/负对照都符合预期）'
                   if (len(lost) == len(BOOK) and ok_all)
                   else '**修复未通过对照，不得声称已修**'))
