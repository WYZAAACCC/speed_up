#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_table.py --- 把 `_r30_prof_line_N96_w1.json` 的逐行数据聚成**算子表**。

口径（必须与 `_r30_prof_line.py` 一致）：
* `advance` 帧内**逐行 incl** 沿行号划分了整个帧的时间 ⇒ 按行号区间求和 = 该区间
  的**算子总代价**（含它调用的所有子帧）；全部区间之和 ≈ `advance` 的 incl。
* 子帧（`_geom_k` / `_step_k` / `elastic_driving` …）另有自己的表。
用法：python3 _r30_table.py _r30_prof_line_N96_w1.json
"""
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else '_r30_prof_line_N96_w1.json'
d = json.load(open(path))
TOT = d['wall_untraced']
lines = {(r['file'], r['func'], r['line']): r for r in d['lines']}
# 前 400 行覆盖了绝大部分时间；检查覆盖率
cov = sum(r['incl'] for r in d['lines'])
print('wall_untraced(基准) = %.3f s/步；逐行表覆盖 incl 合计 %.3f s（%.1f%%）'
      % (TOT, cov, 100.0 * cov / TOT))

BLOCKS = [
    ('① region()（区域指派 argmin）', 2863, 2863),
    ('② winner/runner-up（par.argmin2）', 2899, 2899),
    ('③ F3 面能表 _gc_full（lath gtab gather）', 2918, 2947),
    ('④ per_field 分支（本装置未走）', 2948, 2961),
    ('⑤ 小分配 / 活跃场清单', 2962, 2967),
    ('⑥ 按场几何 _geom_k（for_each）', 2968, 3011),
    ('⑦ 弹性驱动 elastic_driving_pair', 3012, 3020),
    ('⑧ 界面法向 ndir_ / 参考取向 nd_ref（M(n) 用）', 3021, 3091),
    ('⑨ 曲率 kap_cell + 镜像 SDF 检查', 3092, 3220),
    ('⑩ 驱动力 dG_cell / v_cell', 3221, 3241),
    ('⑪ M(n) 迁移率各向异性（mob_beta/w）', 3242, 3293),
    ('⑫ 配对规范形 sigma·v_cell', 3294, 3317),
    ('⑬ 速度延拓（EDT / extend_along_normal）', 3318, 3380),
    ('⑭ 投影 V = v·n（proj2）', 3381, 3399),
    ('⑮ 逐场平流 _step_k（for_each；迎风通量）', 3400, 3439),
    ('⑯ _finish_advance（region + reinit + Stefan）', 3440, 3441),
]


def sum_incl(lo, hi, func='advance'):
    s = 0.0
    for (f, fu, ln), r in lines.items():
        if f == 'windowB_surface.py' and fu == func and lo <= ln <= hi:
            s += r['incl']
    return s


print('\n' + '=' * 96)
print('A. `advance()` 顶层算子表（N=96，Δx=125 nm，12 活跃场，workers=1，实测 %.3f s/步）' % TOT)
print('=' * 96)
print('  %-46s %9s %8s %8s' % ('算子', '含子帧(s)', '% 步时', '% 基准'))
acc = 0.0
rows = []
for name, lo, hi in BLOCKS:
    s = sum_incl(lo, hi)
    rows.append((name, s))
    acc += s
for name, s in rows:
    print('  %-46s %9.4f %7.1f%% %7.1f%%'
          % (name, s, 100 * s / acc, 100 * s / TOT))
print('  %-46s %9.4f %7.1f%% %7.1f%%' % ('—— 合计（advance 帧内）', acc, 100.0,
                                          100 * acc / TOT))

print('\n' + '=' * 96)
print('B. 子帧明细（这些时间**已含在**上表对应行里，此处只是拆开看）')
print('=' * 96)
subs = [r for r in d['funcs']
        if r['func'] not in ('advance',) and r['incl'] > 0.02]
for r in sorted(subs, key=lambda r: -r['incl']):
    print('  %-20s %-24s incl=%7.4f s  excl=%7.4f s  hits=%d'
          % (r['file'], r['func'], r['incl'], r['excl'], r['hits']))

print('\n' + '=' * 96)
print('C. `_geom_k` 内部（每步 12 次调用）')
print('=' * 96)
gs = [(ln, r) for (f, fu, ln), r in lines.items()
      if f == 'windowB_surface.py' and fu == '_geom_k']
gsum = sum(r['incl'] for _, r in gs)
print('  _geom_k 帧内 incl 合计 = %.4f s（12 次调用 ⇒ %.4f s/次）'
      % (gsum, gsum / 12.0))
for ln, r in sorted(gs):
    print('    line %-5d incl=%7.4f  excl=%7.4f  hits=%d' % (ln, r['incl'],
                                                             r['excl'], r['hits']))

print('\n' + '=' * 96)
print('D. `_step_k` 内部（每步 12 次调用）')
print('=' * 96)
ss = [(ln, r) for (f, fu, ln), r in lines.items()
      if f == 'windowB_surface.py' and fu == '_step_k']
for ln, r in sorted(ss):
    print('    line %-5d incl=%7.4f  excl=%7.4f  hits=%d' % (ln, r['incl'],
                                                             r['excl'], r['hits']))

print('\n' + '=' * 96)
print('E. `upwind_flux_vec` 模块函数内部（每步 12 次调用，432 行命中）')
print('=' * 96)
us = [(ln, r) for (f, fu, ln), r in lines.items()
      if f == 'windowB_surface.py' and fu == 'upwind_flux_vec']
for ln, r in sorted(us):
    print('    line %-5d incl=%7.4f  excl=%7.4f  hits=%d' % (ln, r['incl'],
                                                             r['excl'], r['hits']))

print('\n' + '=' * 96)
print('F. 未归入任何区间的 advance 行（应≈0）')
print('=' * 96)
covered = set()
for _, lo, hi in BLOCKS:
    covered |= set(range(lo, hi + 1))
rest = [(ln, r) for (f, fu, ln), r in lines.items()
        if f == 'windowB_surface.py' and fu == 'advance' and ln not in covered]
for ln, r in sorted(rest, key=lambda x: -x[1]['incl'])[:20]:
    print('    line %-5d incl=%7.4f  excl=%7.4f' % (ln, r['incl'], r['excl']))
print('    未覆盖 incl 合计 = %.4f s' % sum(r['incl'] for _, r in rest))
