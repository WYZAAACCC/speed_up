#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_apply_edgeorder.py —— `W1-1`（`A15③`）：把全文件的 `np.gradient` 统一为 `edge_order=2`

为什么要统一（而不是只补一处）
------------------------------
`A15③` 的现场是 `advance()` 里 `np.gradient(pha - phb, self.dx)`（喂给 `_sep_conv3` 的那条）：
**周期滤波 + 盒面单边一阶差分混用** ⇒ `norm_smooth` 的 docstring 里"严格周期、无边界污染"不成立。

但只补这一处会让 `advance()` 内部**同一批耦合项**的边界处理**阶数不一致**
（有的盒面一阶、有的二阶）—— 那比两端任何一种都糟。
⇒ 按路线图 `W1-1` 的"**同文件其余同类点一并统一**"执行：**全文件统一**。

安全性
------
* **只做字面替换**，用**显式列表**（不写正则去猜括号配对）；
* 每条都有**期望计数**，不符就**中止且不写文件**；
* 写前留 `.bak_edgeorder` 备份；
* 跑完立刻用 `_chk_syntax.py`（10 文件、单判决句、非零退出）验证。

⚠ 本脚本**只跑一次**；重复跑会被"期望计数=0"挡住（幂等保护）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'windowB_surface.py')
BAK = SRC + '.bak_edgeorder'

# (旧字面, 新字面, 期望出现次数)
RULES = [
    ('np.gradient(phi0, dx)',             'np.gradient(phi0, dx, edge_order=2)',             1),
    ('np.gradient(phi, dx)',              'np.gradient(phi, dx, edge_order=2)',              2),
    ('np.gradient(self.phi, self.dx)',    'np.gradient(self.phi, self.dx, edge_order=2)',    2),
    ('np.gradient(n[i], self.dx)',        'np.gradient(n[i], self.dx, edge_order=2)',        1),
    ('np.gradient(self.phi[k], self.dx)', 'np.gradient(self.phi[k], self.dx, edge_order=2)', 5),
    ('np.gradient(phiw, self.dx)',        'np.gradient(phiw, self.dx, edge_order=2)',        2),
    ('np.gradient(pha - phb, self.dx)',   'np.gradient(pha - phb, self.dx, edge_order=2)',   1),
    ('np.gradient(dd, self.dx)',          'np.gradient(dd, self.dx, edge_order=2)',          1),
    ('np.gradient(nd[i], self.dx)',       'np.gradient(nd[i], self.dx, edge_order=2)',       2),
    ('np.gradient(pha, self.dx)',         'np.gradient(pha, self.dx, edge_order=2)',         1),
    ('np.gradient(phb, self.dx)',         'np.gradient(phb, self.dx, edge_order=2)',         1),
    ('np.gradient(dfield, self.dx)',      'np.gradient(dfield, self.dx, edge_order=2)',      1),
    ('np.gradient(d, self.dx)',           'np.gradient(d, self.dx, edge_order=2)',           2),
    ('np.gradient(d2, self.dx)',          'np.gradient(d2, self.dx, edge_order=2)',          1),
]

t = open(SRC, encoding='utf-8').read()
tot = 0
bad = []
print('=' * 92)
print('_apply_edgeorder —— W1-1/A15③：全文件 np.gradient 统一为 edge_order=2')
print('=' * 92)
for old, new, exp in RULES:
    n = t.count(old)
    tot += n
    flag = 'OK ' if n == exp else '✗  '
    print('   %s 期望 %d 实得 %d   %s' % (flag, exp, n, old))
    if n != exp:
        bad.append((old, exp, n))
    t = t.replace(old, new)

print('\n   合计替换 **%d** 处（期望 %d）' % (tot, sum(r[2] for r in RULES)))
if bad:
    print('   ⛔ 计数不符 ⇒ **不写文件**。请先核对源码（可能已被改过或行号漂移）。')
    for o, e, g in bad:
        print('      %-40s 期望 %d 实得 %d' % (o, e, g))
    sys.exit(2)

if os.path.exists(BAK):
    print('   ⚠ 备份 %s 已存在（可能已跑过一次）⇒ 不覆盖，也不写文件。' % os.path.basename(BAK))
    sys.exit(3)

open(BAK, 'w', encoding='utf-8').write(open(SRC, encoding='utf-8').read())
open(SRC, 'w', encoding='utf-8', newline='\n').write(t)
print('   备份 → %s' % os.path.basename(BAK))
print('   已写入 %s' % os.path.basename(SRC))

rest = t.count('np.gradient(')
with_ = t.count('edge_order=2')
print('\n   复核：`np.gradient(` 出现 %d 次；`edge_order=2` 出现 %d 次' % (rest, with_))
print('   （差额来自注释里提到 `np.gradient` 的文字与已有 edge_order 的调用）')
print('   ⇒ 请以 `_chk_syntax.py` + `_chk_fixes.py` + 探针回归为准。')
print('=' * 92)
