#!/usr/bin/env python3
"""_r416_gtread.py —— 读 `_r415` 三条真值臂的 `series.csv`，逐 step 比 F3 / 块结构。

判据（与 `_r415_fpgt.sh` 的 G-1/G-2/G-3 一致）：
  G-1 三条臂都有产物且无 Traceback（Traceback 由 shell 侧查，这里查行数）
  G-2 臂 B（归档行为）在 step 20 复现 `§185` 的 `nf3` 塌陷
  G-3 比较 B 与 C：若接近 ⇒ `facet_excl` 不是原因（§186 的修法无效）
"""
import csv
import os
import sys

BASE = '_exp/_bk_mb'
ARMS = [('gtA', '--facet-proj 0 （投影关闭）'),
        ('gtB', '--facet-proj 10 --facet-excl 1 （**归档行为**）'),
        ('gtC', '--facet-proj 10 --facet-excl 0 （本轮"修复"）')]
COLS = ['step', 'nf3', 'nf3_col', 'nf2', 'nf1', 'blk_nprof', 'nblk_sig',
        'blk_lruns', 'blk_lath', 'Vt', 'nslab_n', 'nreg', 'f3_area']


def P(s):
    print(s, flush=True)


def load(tag):
    p = os.path.join(BASE, 'dry_%s' % tag, 'series.csv')
    if not os.path.exists(p):
        return None, p
    rows = []
    with open(p, newline='') as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows, p


def gv(r, k):
    if k not in r:
        return None
    v = r[k]
    if v is None or v == '':
        return None
    try:
        f = float(v)
        return f
    except ValueError:
        return v


P('=' * 96)
P('_r416 —— `--facet-proj` 真值实验读数')
P('=' * 96)

data = {}
for tag, desc in ARMS:
    rows, p = load(tag)
    data[tag] = rows
    P('\n[%s] %s' % (tag, desc))
    if rows is None:
        P('    ✗ 没有产物：%s' % p)
        continue
    P('    CSV = %s  行数 = %d' % (p, len(rows)))
    hdr = [c for c in COLS if c in rows[0]]
    P('    可用列：%s' % ', '.join(hdr))
    P('    %-6s %-8s %-10s %-8s %-22s %-10s' %
      ('step', 'nf3', 'nf3_col', 'nf2', 'blk_nprof', 'f3_area'))
    for r in rows:
        P('    %-6s %-8s %-10s %-8s %-22s %-10s'
          % (r.get('step'), r.get('nf3'), r.get('nf3_col'), r.get('nf2'),
             r.get('blk_nprof'), r.get('f3_area')))

# ---------------- 判读 ----------------
P('\n' + '=' * 96)
P('[判读]')
ok_g1 = all(data[t] for t, _ in ARMS)
P('  G-1 三条臂都有产物：%s' % ('✅ PASS' if ok_g1 else '❌ FAIL'))

if data.get('gtB'):
    r20 = None
    for r in data['gtB']:
        if str(r.get('step')) in ('20', '20.0'):
            r20 = r
            break
    if r20 is None:
        r20 = data['gtB'][min(2, len(data['gtB']) - 1)]
    nf3_20 = gv(r20, 'nf3')
    P('  G-2 臂 B 的 step%s nf3 = %s（`§185` 归档：step20 时 **2**，t=0 时 1169）⇒ %s'
      % (r20.get('step'), nf3_20,
         '✅ 复现塌陷' if (nf3_20 is not None and float(nf3_20) < 50)
         else '⚠ 未复现'))

# 末态对比
def last(tag, col):
    rows = data.get(tag)
    if not rows:
        return None
    return gv(rows[-1], col)


P('\n  末态对比（最后一个 step）：')
P('    %-8s %-10s %-10s %-24s' % ('臂', 'nf3', 'nf2', 'blk_nprof'))
for tag, _ in ARMS:
    P('    %-8s %-10s %-10s %-24s'
      % (tag, last(tag, 'nf3'), last(tag, 'nf2'), last(tag, 'blk_nprof')))

b, c = last('gtB', 'nf3'), last('gtC', 'nf3')
if b is not None and c is not None:
    P('\n  G-3 末态 nf3：B（归档）= %s，C（"修复"）= %s' % (b, c))
    try:
        bb, cc = float(b), float(c)
        rel = abs(cc - bb) / max(abs(bb), 1.0)
        P('      |C−B|/B = %.3f ⇒ %s'
          % (rel, '**C ≈ B ⇒ `facet_excl` 不是原因，§186 的修法无效**'
             if rel < 0.2 else '**C 与 B 明显不同 ⇒ 修法有效**'))
    except ValueError:
        P('      非数值，无法比较')
P('=' * 96)
