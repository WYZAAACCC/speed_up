#!/usr/bin/env python3
"""_r444_paramdiff.py —— ★★★ **双臂 vs 归档的参数逐项 diff**（找配置偏差）。

## 为什么
`_r443` 查出：**全部归档臂都用 `beta_h = 6.477`，而本轮双臂用了 CLI 默认 `3.5`**。
⇒ 启动日志早就打了「⚠⚠ **C-5 不满足** …⇒ **厚度判据 V-8b 不适用**」，**我没有处置**。
⇒ 既然能漏一个，就要**系统性地**把整套参数逐项对一遍（单变量纪律）。

## 基准
`dry_saSet2`（6 块 × 2 板条、`--facet-proj 10`）与 `dry_goodA_400`（合格几何之一）。
**目标不是"与归档逐字相同"**（本轮故意改了 `--laths`/`--plate`/`--nuc-*`/`--facet-proj`），
而是**把每一处不同都列出来并标注"是否有意"**，防止**无意的**偏差。
"""
import json
import os

BASE = '_exp/_bk_mb'
REF = ['dry_saSet2', 'dry_goodA_400', 'dry_permB1_400']
CUR = ['dry_abA', 'dry_abB']
KEYS = ['N', 'dx_nm', 'steps', 'every', 'snap_every', 'pair_every',
        'laths', 'plate_L', 'plate_W', 'plate_T', 'multi_block',
        'block_gap_nm', 'block_layout', 'gap_nm', 'norm_smooth', 'nthreads',
        'reinit_dt', 'reinit_band', 'band_cells',
        'gamma0', 'beta_h', 'beta_w', 'facet_lam', 'facet_eps', 'adv',
        'mob_iform', 'mob_ratio', 'mob_wulff', 'mob_dip', 'el_scale',
        'facet_proj', 'facet_excl', 'rank1_swap', 'f2_pair_gamma',
        'omega_mode', 'omega_max_deg', 'nuc_law', 'nuc_every', 'nuc_init',
        'nuc_mode', 'grow_stack', 'nuc_overlap_nm', 'eng_cadence',
        'eng_r_nm', 'eng_t_nm', 'alpha_km', 'T_end', 'cool_rate', 'arm',
        'nuc_fresh_every', 'nuc_fcrit', 'var_rule', 'tag']


def load(n):
    p = os.path.join(BASE, n, 'meta.json')
    if not os.path.exists(p):
        return None
    m = json.load(open(p))
    ea = dict(m.get('exp_args', {}))
    for k in ('N', 'dx_nm', 'laths', 'steps', 'beta_h', 'beta_w', 'gamma0'):
        if k not in ea and k in m:
            ea[k] = m[k]
    return ea


refs = {n: load(n) for n in REF}
cur = {n: load(n) for n in CUR}
P = print
P('=' * 100)
P('_r444 —— 本轮双臂 vs 归档：参数逐项 diff')
P('=' * 100)
P('\n  %-16s %-22s %-22s %s' % ('参数', '归档（saSet2）', '本轮（abA）', '判定'))
for k in KEYS:
    v_ref = None
    for n in REF:
        if refs[n] and k in refs[n]:
            v_ref = refs[n][k]
            break
    v_cur = None
    for n in CUR:
        if cur[n] and k in cur[n]:
            v_cur = cur[n][k]
            break
    if v_ref is None and v_cur is None:
        continue
    same = (v_ref == v_cur)
    mark = '同' if same else '**不同**'
    P('  %-16s %-22s %-22s %s'
      % (k, str(v_ref)[:22], str(v_cur)[:22], mark))

P('\n' + '=' * 100)
P('[重点：`beta_h` 的后果]')
P('=' * 100)
P('  归档全部用 **6.477**（= `windowB_wulff.B_H_DEF`，按 Wulff 长厚比 ≈3.51 标定的值）')
P('  本轮双臂用了 CLI **默认 3.5** ⇒ 启动日志已打印「⚠⚠ C-5 不满足」而我未处置。')
P('  用 6.477 时：abA 需要 ≥5.894 ⇒ **满足**；abB 需要 ≥3.892 ⇒ **满足**。')
P('=' * 100)
