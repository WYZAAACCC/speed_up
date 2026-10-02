#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_bestarm.py --- ★★★★★ **哪条臂既用了最终优化代码、又是完整仿真？**

## 两个维度分别量
| 维度 | 怎么量 |
|---|---|
| **优化程度** | `exp_args` 里那批算子开关的**取值**（非默认 = 已开） |
| **完成度** | `series.csv` 末步 / `meta.json` 的 `steps`（设计步数） |

## 优化开关清单（来自 AGENTS §7.5 的"已落地算子开关"表 + `_r581_p2.py` 的实测命令行）
`eps0_mode=einsum` · `ed_pair=gather` · `k_loop=act` · `act_mode=bincount` ·
`argmin2_mode=copyto` · `grad_mode=sliced` · `pf_phi=onfly` · `extend_mode=near` ·
`eps0_tile=4` · `argmin2_reuse=1` · `ufv_c=1` · `bbox_mode=axis`
"""
import csv
import glob
import json
import os
import sys
import time

OPT = {
    'eps0_mode': 'einsum', 'ed_pair': 'gather', 'k_loop': 'act',
    'act_mode': 'bincount', 'argmin2_mode': 'copyto', 'grad_mode': 'sliced',
    'pf_phi': 'onfly', 'extend_mode': 'near', 'eps0_tile': '4',
    'argmin2_reuse': '1', 'ufv_c': '1', 'bbox_mode': 'axis',
}


def main():
    recs = []
    for d in glob.glob('_exp/**/dry_*', recursive=True):
        if not os.path.isdir(d) or 'superseded' in d:
            continue
        mp, sp = os.path.join(d, 'meta.json'), os.path.join(d, 'series.csv')
        if not (os.path.exists(mp) and os.path.exists(sp)):
            continue
        try:
            m = json.load(open(mp, encoding='utf-8', errors='replace'))
        except Exception:
            continue
        ea = m.get('exp_args')
        if isinstance(ea, str):
            try:
                ea = json.loads(ea.replace("'", '"'))
            except Exception:
                ea = {}
        if not isinstance(ea, dict):
            ea = {}
        # 优化开关命中数
        hits = []
        for k, v in OPT.items():
            got = ea.get(k, m.get(k))
            if got is None:
                continue
            if str(got).lower() == str(v).lower():
                hits.append(k)
        try:
            rows = list(csv.DictReader(open(sp, encoding='utf-8', errors='replace')))
        except Exception:
            continue
        if not rows:
            continue
        k0 = list(rows[0].keys())[0]
        try:
            last = float(rows[-1][k0])
        except Exception:
            last = 0.0
        want = m.get('steps') or ea.get('steps')
        try:
            want = float(want)
        except Exception:
            want = None
        recs.append(dict(tag=os.path.basename(d)[4:], dir=d, N=m.get('N'),
                         last=last, want=want, nopt=len(hits), opts=hits,
                         mtime=os.path.getmtime(sp)))
    print('=' * 108)
    print('① **用了最多优化开关**的臂（前 20）')
    print('=' * 108)
    print('  %-22s %-6s %-8s %-9s %-9s %s' %
          ('臂', 'N', '优化开关', '设计步数', '末步', '已开的开关'))
    print('  ' + '-' * 104)
    for r in sorted(recs, key=lambda r: (-r['nopt'], -(r['last'] or 0)))[:20]:
        print('  %-22s %-6s %-8d %-9s %-9.0f %s' %
              (r['tag'][:22], r['N'], r['nopt'],
               ('%.0f' % r['want']) if r['want'] else '—', r['last'],
               ','.join(r['opts'])[:52]))
    print()
    print('=' * 108)
    print('② **完成度**最高的臂（末步/设计步数 ≥ 50%，且设计步数 ≥ 100）')
    print('=' * 108)
    print('  %-22s %-6s %-9s %-9s %-8s %-8s %s' %
          ('臂', 'N', '设计步数', '末步', '完成度', '优化开关', '末次修改'))
    print('  ' + '-' * 104)
    full = [r for r in recs if r['want'] and r['want'] >= 100
            and r['last'] / r['want'] >= 0.5]
    for r in sorted(full, key=lambda r: -(r['last'] / r['want']))[:22]:
        print('  %-22s %-6s %-9.0f %-9.0f %-8s %-8d %s' %
              (r['tag'][:22], r['N'], r['want'], r['last'],
               '**%.0f%%**' % (100 * r['last'] / r['want']), r['nopt'],
               time.strftime('%m-%d %H:%M', time.localtime(r['mtime']))))
    print()
    print('=' * 108)
    print('③ ★ **两个维度都看**：N≥96 且 优化开关 ≥4 的臂')
    print('=' * 108)
    both = [r for r in recs if (r['N'] or 0) >= 96 and r['nopt'] >= 4]
    print('  %-22s %-6s %-8s %-9s %-9s %s' %
          ('臂', 'N', '优化开关', '设计步数', '末步', '完成度'))
    print('  ' + '-' * 104)
    for r in sorted(both, key=lambda r: (-r['nopt'], -(r['last'] or 0))):
        cov = ('%.1f%%' % (100 * r['last'] / r['want'])) if r['want'] else '—'
        print('  %-22s %-6s %-8d %-9s %-9.0f %s' %
              (r['tag'][:22], r['N'], r['nopt'],
               ('%.0f' % r['want']) if r['want'] else '—', r['last'], cov))
    print()
    print('  ★ **判读**：')
    print('   · **完成度 100%** 的臂 = "完整版仿真"')
    print('   · **优化开关数 = 12** = "最终优化代码"')
    print('   · **两者同时满足**的臂 ⇒ 见上表 **有没有 100% 那一行**')
    print('=' * 108)


if __name__ == '__main__':
    main()
