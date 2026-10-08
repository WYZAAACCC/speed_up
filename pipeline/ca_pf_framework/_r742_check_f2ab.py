#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r742_check_f2ab.py —— 核实**已归档**的 γ_F2 A/B（`f2L0/f2L05/f2L1`）是否**无效应**。

## 背景
`_t11_f2_ab.py` 已经做过 λ = 0 / 0.5 / 1 的三臂 A/B（2026-10-05/06）。
但它用 `--laths 1×70`（**全部同变体**）⇒ `R741` 证明这种配置 `nf2 ≡ 0`
⇒ **三臂很可能逐位相同（无效应）**。

## 本脚本问
1. 三臂的 `series.csv` 是否**逐位相同**？
2. 各臂的 `nf2` 是否恒为 0？
3. `--f2-pair-gamma` 的"独有串"（`§122`、`Δe_ref`、`n_f2`）有没有打印？
   ⇒ **这是判"λ 生效了没有"的唯一依据**（`P43`）。
"""
import hashlib
import os
import sys

ROOT = '/mnt/f/speed_up/_exp/_bk_t5'
ARMS = ['f2L0', 'f2L05', 'f2L1']


def main():
    print('=' * 100)
    print('核实归档的 γ_F2 A/B（`_t11_f2_ab.py` 的产物）')
    print('=' * 100)
    sigs = {}
    for t in ARMS:
        d = os.path.join(ROOT, 'dry_%s' % t)
        p = os.path.join(d, 'series.csv')
        print('\n【%s】' % t)
        if not os.path.isfile(p):
            print('  ⚠ 无 series.csv')
            continue
        b = open(p, 'rb').read()
        sigs[t] = hashlib.sha256(b).hexdigest()[:16]
        print('  series.csv sha256[:16] = %s  字节=%d' % (sigs[t], len(b)))
        # nf2
        import csv
        with open(p, newline='') as f:
            rows = [r for r in csv.DictReader(f) if r.get('step')]
        if rows and 'nf2' in rows[0]:
            nf2 = [r['nf2'] for r in rows]
            print('  `nf2` 逐测点 = %s' % nf2)
            print('  ⇒ %s' % ('⛔ 恒为 0（无作用对象）'
                             if all(str(v).strip() in ('0', '0.0', '') for v in nf2)
                             else '✅ 有非零'))
        else:
            print('  ⚠ 无 nf2 列')
        for k in ('nslab_n', 'nf3_col', 'n_var_sig'):
            if rows and k in rows[0]:
                print('  %-10s = %s' % (k, [r.get(k) for r in rows]))
        # 独有串
        lg = '/mnt/f/speed_up/_w2_%s.log' % t
        if os.path.isfile(lg):
            txt = open(lg, encoding='utf-8', errors='replace').read()
            has122 = ('§122' in txt) or ('Δe_ref' in txt) or ('de_ref' in txt)
            nf2m = [ln for ln in txt.splitlines()
                    if ('n_f2' in ln) or ('Δe_ref' in ln)]
            print('  ★ 独有串（`§122`/`Δe_ref`/`n_f2`）出现？ %s（命中 %d 行）'
                  % ('✅ 有' if has122 else '⛔ **无**', len(nf2m)))
            for ln in nf2m[:4]:
                print('      %s' % ln.strip()[:110])
        else:
            print('  ⚠ 无日志 %s' % lg)
    print('\n' + '=' * 100)
    print('判定')
    print('=' * 100)
    if len(sigs) >= 2:
        uniq = set(sigs.values())
        print('  `series.csv` 签名 = %s' % sigs)
        if len(uniq) == 1:
            print('  ⇒ ⛔ **三臂 `series.csv` 逐位相同** ⇒ **λ 是空操作** ⇒ A/B **无效应**')
        else:
            print('  ⇒ ✅ 三臂有差异（%d 种签名）' % len(uniq))
    return 0


if __name__ == '__main__':
    sys.exit(main())
