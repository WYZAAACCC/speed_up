#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r740_read_t11.py —— 读**已存在**的 T11 `G2` A/B（`_t11_iface_ab.py` 的产物）。

## 为什么要读它（本轮的教训）
我在 `R739`/`R740` 连续两次**自己搭 T2 的 A/B**，
第二次才发现 **`_t11_iface_ab.py` 早就做过这个 A/B**（2026-10-05/06），
而且产物就在盘上（`_exp/_bk_t5/dry_ifaceOFF` / `dry_ifaceON`，各 400 步）。

⇒ **纪律**：设计实验前**先查盘上有没有现成结果**（`AGENTS.md §3.3` 教训 23
"设计实验前，先在文档里搜一遍这个量有没有现成结论" 的**运行目录版**）。

## 判据（`_t11_iface_ab.py` 原文已登记，此处**原样引用**）
* 末刻 `nslab_n`：ON 臂**显著更高** ⇒ `G2` 是必要的；
* 且 ON 臂必须有 **`iface_ok > 0`**（**独有可核查串**，`P43`！）

## ★ 对 T2 的意义
`G2` 就是"**异变体界面形核**"⇒ 若它生效，**`nf2`（异变体界面格面数）应 > 0**
⇒ **T2/F11 的前置判据可能已经被这个归档回答了。**
"""
import csv
import json
import os
import sys

ROOT = '/mnt/f/speed_up/_exp/_bk_t5'
KEYS = ['step', 'box_touch', 'nslab_n', 'nf3_col', 'nf2', 'f2_area_m2',
        'n_var_sig', 'nblk_sig', 'blk_laths', 'Vt']
DBG = ['iface_ok', 'iface_pair', 'iface_samevar', 'iface_multi', 'iface_src',
       'ok', 'cov', 'fresh_blocked', 'empty', 'att', 'exc', 'nocand', 'oob',
       'nfsv_ok', 'nfsv_nofield', 'dg_pick']


def main():
    print('=' * 100)
    print('T11 `G2`（异变体界面形核）A/B —— 读**已归档**的结果（400 步，两臂只差一个开关）')
    print('=' * 100)
    res = {}
    for tag in ('ifaceOFF', 'ifaceON'):
        d = os.path.join(ROOT, 'dry_%s' % tag)
        p = os.path.join(d, 'series.csv')
        print('\n【%s】%s' % (tag, p))
        if not os.path.isfile(p):
            print('  ⚠ 无')
            continue
        with open(p, newline='') as f:
            rows = [r for r in csv.DictReader(f) if r.get('step')]
        res[tag] = rows
        ks = [k for k in KEYS if k in rows[0]]
        print('   ' + ' '.join('%-10s' % k for k in ks))
        for r in rows:
            print('   ' + ' '.join('%-10s' % str(r.get(k, ''))[:10] for k in ks))
        # nuc_dbg
        pd = os.path.join(d, 'nuc_dbg.json')
        if os.path.isfile(pd):
            with open(pd) as f:
                j = json.load(f)
            db = j.get('dbg') or {}
            cfg = j.get('nuc_cfg') or {}
            print('   -- debug --')
            for k in DBG:
                if k in db:
                    print('      dbg.%-16s = %s' % (k, db[k]))
            print('      n_events_by_mode  = %s' % (j.get('n_events_by_mode'),))
            print('      n_eng_ev          = %s' % j.get('n_eng_ev'))
            print('      cfg.nuc_iface_nucleation = %s'
                  % cfg.get('nuc_iface_nucleation'))
    print()
    print('=' * 100)
    print('判定')
    print('=' * 100)
    for tag, rows in res.items():
        last = rows[-1]
        nf2 = [r.get('nf2', '') for r in rows]
        has2 = any(str(v).strip() not in ('', '0', '0.0') for v in nf2)
        print('  %-10s 末 step=%s  nslab_n=%s  n_var_sig=%s  nblk_sig=%s'
              % (tag, last.get('step'), last.get('nslab_n'),
                 last.get('n_var_sig'), last.get('nblk_sig')))
        print('             `nf2` 逐测点 = %s ⇒ %s'
              % (nf2, '✅ **出现 F2 界面**' if has2 else '⛔ 恒为 0'))
    if len(res) == 2:
        def lastn(rows, k):
            for r in reversed(rows):
                v = str(r.get(k, '')).strip()
                if v.replace('.', '', 1).isdigit():
                    return float(v)
            return None
        a = lastn(res['ifaceOFF'], 'nslab_n')
        b = lastn(res['ifaceON'], 'nslab_n')
        print()
        print('  末刻 nslab_n： OFF = %s   ON = %s' % (a, b))
        if a is not None and b is not None:
            if b > a:
                print('     ⇒ ON 臂**更高**（+%g）⇒ **`G2` 是必要的** ✅' % (b - a))
            else:
                print('     ⇒ 两臂相同或更低 ⇒ **`G2` 不是根数不足的原因** ❌')
        pd = os.path.join(ROOT, 'dry_ifaceON', 'nuc_dbg.json')
        if os.path.isfile(pd):
            with open(pd) as f:
                db = (json.load(f).get('dbg') or {})
            print('  ★ 独有可核查串：ON 臂 `iface_ok` = %r（应 > 0）'
                  % db.get('iface_ok'))
            print('             ON 臂 `iface_pair` = %r（应形如 \'1>2\'）'
                  % db.get('iface_pair'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
