#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_c1probe2.py --- 深挖：`nuc_dbg.json` 里有没有**位点坐标**？（C1 的均匀性检验要用）"""
import json
import sys

p = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_p2/dry_smoke_n160m4/nuc_dbg.json'
d = json.load(open(p, encoding='utf-8'))

print('=== T_events 的第 1 条（完整）===')
print(json.dumps(d['T_events'][0], ensure_ascii=False, indent=2))

print()
print('=== dbg 全部键（找坐标类）===')
for k, v in d['dbg'].items():
    s = json.dumps(v, ensure_ascii=False)
    print('  %-22s %s' % (k, s[:100]))

print()
print('=== nuc_cfg 全部键 ===')
for k, v in d['nuc_cfg'].items():
    print('  %-22s %s' % (k, str(v)[:80]))

print()
print('=== ★ 有没有坐标？===')
keys = set(d.keys()) | set(d.get('dbg', {}).keys()) | set(d.get('nuc_cfg', {}).keys())
ev = d['T_events'][0] if d.get('T_events') else {}
keys |= set(ev.keys())
hits = [k for k in keys if any(t in k.lower()
                              for t in ('pos', 'coord', 'c0', 'cent', 'xyz', 'site'))]
print('  含 pos/coord/c0/cent/xyz/site 的键：%s' % (hits or '**一个都没有**'))
if not hits:
    print('  ⇒ **`nuc_dbg.json` 里没有位点坐标** ⇒ C1 的均匀性检验要另找数据源。')
    print('     可行替代：`snap_00000.npz` 的 `region` —— 每个场的**初始质心**就是它的播种位置。')
