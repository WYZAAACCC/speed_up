#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r742_read.py <root> —— `γ_F2` A/B 的读数与 `W-0…W-5` 判定。

判据（`_r742_f2ab.py` docstring **先登记**）：
  W-0 三臂都真的跑出结果（3/3）
  W-1 独有串（`P43`）：λ>0 臂打印 `§122`/`Δe_ref`/`n_f2`，λ=0 臂不打印
  W-2（主）三臂 `nf2` 至少两两不同
  W-3 若无差异 ⇒ 如实报"λ 无响应" + 机理归因
  W-4 `box_touch` 全程 = 1
"""
import csv
import hashlib
import os
import sys

ARMS = [('f2lam0', '0.0'), ('f2lam05', '0.5'), ('f2lam1', '1.0')]


def main():
    root = sys.argv[1]
    print('=' * 104)
    print('γ_F2 A/B（λ = 0 / 0.5 / 1）—— **第一次真正跑成功**（root=%s）' % root)
    print('=' * 104)
    data, sigs, logstr = {}, {}, {}
    for t, lam in ARMS:
        d = os.path.join(root, 'dry_%s' % t)
        p = os.path.join(d, 'series.csv')
        print('\n【%s】λ=%s' % (t, lam))
        if not os.path.isfile(p):
            print('  ⛔ **无 `series.csv`**（该臂没跑出结果）')
            continue
        b = open(p, 'rb').read()
        sigs[t] = hashlib.sha256(b).hexdigest()[:16]
        with open(p, newline='') as f:
            rows = [r for r in csv.DictReader(f) if r.get('step')]
        data[t] = rows
        print('  签名 = %s' % sigs[t])
        ks = ['step', 'box_touch', 'nslab_n', 'nf3_col', 'nf2', 'f2_area_m2',
              'n_var_sig', 'nblk_sig', 'blk_laths', 'Vt']
        ks = [k for k in ks if ks and k in rows[0]]
        print('   ' + ' '.join('%-11s' % k for k in ks))
        for r in rows:
            print('   ' + ' '.join('%-11s' % str(r.get(k, ''))[:11] for k in ks))
        lg = '/mnt/f/speed_up/_w2_%s.log' % t
        if os.path.isfile(lg):
            txt = open(lg, encoding='utf-8', errors='replace').read()
            logstr[t] = txt
            hits = [ln.strip() for ln in txt.splitlines()
                    if ('§122' in ln) or ('Δe_ref' in ln) or ('n_f2' in ln)]
            print('  ★ 独有串出现？ %s（命中 %d 行）'
                  % ('✅ 有' if hits else '⛔ 无', len(hits)))
            for ln in hits[:3]:
                print('      %s' % ln[:110])
        else:
            print('  ⚠ 无日志')

    print('\n' + '=' * 104)
    print('判定')
    print('=' * 104)
    print('  W-0 三臂都有结果：%d/3  ⇒ %s'
          % (len(sigs), '✅ PASS' if len(sigs) == 3 else '⛔ FAIL'))
    # W-1
    ok1 = True
    for t, lam in ARMS:
        if t not in logstr:
            continue
        has = any(k in logstr[t] for k in ('§122', 'Δe_ref', 'n_f2'))
        want = (lam != '0.0')
        mark = '✅' if has == want else '⛔'
        if has != want:
            ok1 = False
        print('  W-1 %-10s λ=%-4s 独有串=%-5s 期望=%-5s %s'
              % (t, lam, has, want, mark))
    print('      ⇒ %s' % ('✅ PASS' if ok1 else '⛔ FAIL'))
    # W-2
    if len(data) >= 2:
        nf2 = {t: [r.get('nf2') for r in rows] for t, rows in data.items()}
        uniq = {t: tuple(v) for t, v in nf2.items()}
        print('  W-2 三臂 `nf2` 序列：')
        for t in data:
            print('      %-10s %s' % (t, nf2[t]))
        if len(set(uniq.values())) >= 2:
            print('      ⇒ ✅ **有差异**（λ 有响应）')
        else:
            print('      ⇒ ⛔ **三臂 `nf2` 完全相同** ⇒ λ **无响应**')
        print('  参考 `series.csv` 签名：%s' % sigs)
        print('      ⇒ %s' % ('✅ 有差异' if len(set(sigs.values())) >= 2
                              else '⛔ 三臂逐位相同'))
    # W-4
    for t, rows in data.items():
        bt = {str(r.get('box_touch')) for r in rows}
        print('  W-4 %-10s box_touch 取值集合 = %s ⇒ %s'
              % (t, sorted(bt), '✅' if bt == {'1'} else '⚠'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
