import io
import os
HERE = os.path.dirname(os.path.abspath(__file__))
dst = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
src = os.path.join(HERE, '_r76_ledger_new24.md')
old = io.open(dst, encoding='utf-8').read()
if '## §117 R76' in old:
    print('已存在，跳过')
else:
    with io.open(dst, 'a', encoding='utf-8') as f:
        f.write(io.open(src, encoding='utf-8').read())
after = io.open(dst, encoding='utf-8').read()
print('lines %d -> %d (+%d)' % (old.count('\n'), after.count('\n'),
                                after.count('\n') - old.count('\n')))
print('  §117 present =', '## §117 R76' in after)
key = '### 四、⇒ 核心结论（**负面，但明确且可复现**）'
if key in after and '§117 已量化加固' not in after:
    after = after.replace(
        key,
        key + '\n\n> ★★ **2026-09-30 补记（§117）：本条已量化加固** ——\n'
        '> 用"**走完可动范围的比例**" `frac=(r(0)−r(末))/(r(0)−r_min)`：\n'
        '> `saOddG` = **−59.2%**、`saSet2` = **−125.0%**（两臂**都倒退**）。\n'
        '> 且两臂的可动空间**相当**（0.0487 vs 0.0595）——\n'
        '> ⚠ 我一度以为 `saOddG` 起手就在下界（**错**：等分值 0.0482 > 单纯形最优 0.0000）⇒\n'
        '> **两臂都是"有空间却不走"的证据，结论比原先更强**。\n', 1)
    with io.open(dst, 'w', encoding='utf-8') as f:
        f.write(after)
    print('  已在 §112 处插入 §117 指针')
