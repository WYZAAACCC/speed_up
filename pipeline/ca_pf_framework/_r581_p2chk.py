#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_p2chk.py --- 自检：`_r581_p2.py` 的 CLI 拼装（S4 / N13 两个新开关真的接上了）。"""
import argparse
import sys

sys.path.insert(0, '.')
import _r581_p2 as P


def show(**kw):
    base = dict(N=160, m=4, B=5, steps=8, nthreads=4, out='.', tag='x',
                overlap_nm=None, periodic_seed=0)
    base.update(kw)
    c = P.cmd_of(argparse.Namespace(**base))
    def g(flag):
        return c[c.index(flag) + 1] if flag in c else '（未传）'
    print('  overlap_nm=%-6s periodic_seed=%d ⇒ --nuc-overlap-nm %-8s '
          '--nuc-periodic-seed %s' % (base['overlap_nm'], base['periodic_seed'],
                                      g('--nuc-overlap-nm'),
                                      g('--nuc-periodic-seed')))
    return c


print('=== _r581_p2.py CLI 拼装自检 ===')
print('  【基线】')
c0 = show()
print('  【S4 修复】')
show(overlap_nm=62.5)
print('  【S4 + N13 修复】')
c2 = show(overlap_nm=62.5, periodic_seed=1)
print()
print('  逐位开关档（应与 R581 收口实验一致）：')
sw = [c2[i] + ' ' + c2[i + 1] for i in range(len(c2) - 1)
      if c2[i].startswith('--') and c2[i] in
      ('--eps0-mode', '--ed-pair', '--k-loop', '--act-mode', '--argmin2-mode',
       '--grad-mode', '--pf-phi', '--h-chunk', '--extend-mode', '--eps0-tile',
       '--argmin2-reuse', '--bbox-mode', '--ufv-c')]
print('   ', ' | '.join(sw))
ok = ('--nuc-overlap-nm' not in c0) and (c2[c2.index('--nuc-overlap-nm') + 1] == '62.5') \
     and (c2[c2.index('--nuc-periodic-seed') + 1] == '1')
print()
print('  ⇒ 判据（默认不传、修复值传对）：%s' % ('✅ PASS' if ok else '❌ FAIL'))
