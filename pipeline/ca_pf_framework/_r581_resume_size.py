#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_resume_size.py --- 续跑要存的东西**各有多大**（决定可行性）"""
NV, N = 240, 160
print('=' * 92)
print('续跑要存的状态，各有多大（N=160 / nv=240 的生产规模）')
print('=' * 92)
items = [
    ('`region`（场号图，int16）', N ** 3 * 2, '✅ 已在快照里'),
    ('界面带（逐场：idx+val+fld）', 552988 * (4 + 4 + 2), '✅ 已在快照里（实测 55.3 万条）'),
    ('★ **`rng.bit_generator.state`**', 200, '**★ 缺 —— 但只有几百字节**'),
    ('`t_s` / `step` / 标量', 100, '✅ 已在快照里'),
    ('**整场 φ**（N³ float64）', N ** 3 * 8, '**缺 —— 可用 EDT 从 `region` 重建**'),
    ('**`PF3D.phi`（弹性态，nv·N³ f64）**', NV * N ** 3 * 8, '**★ 缺 —— 存它不现实**'),
    ('同上若存 f32', NV * N ** 3 * 4, '（仍很大）'),
    ('形核位点池（假设 nreg·32 B）', 240 * 32, '**缺 —— 很小**'),
]
tot = 0
for name, b, note in items:
    tot += b
    if b > 1e9:
        s = '%.2f GB' % (b / 1e9)
    elif b > 1e6:
        s = '%.1f MB' % (b / 1e6)
    elif b > 1e3:
        s = '%.1f KB' % (b / 1e3)
    else:
        s = '%d B' % b
    print('  %-38s %-11s %s' % (name, s, note))
print('  ' + '-' * 86)
print('  合计 %.2f GB  ⇒ **★ 若必须存弹性态，续跑不可行**；' % (tot / 1e9))
print('     若弹性态**可重建**，则只需 %.1f MB（可忽略）'
      % ((tot - NV * N ** 3 * 8) / 1e6))
print()
print('  ⇒ **结论**：续跑的可行性**完全取决于"弹性态能不能从 `region` 重建"**')
print('     能 ⇒ 便宜（MB 级）；不能 ⇒ 不可行（GB 级、每段一次）')
print('=' * 92)
