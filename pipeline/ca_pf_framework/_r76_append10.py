import io
import os
HERE = os.path.dirname(os.path.abspath(__file__))
dst = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
src = os.path.join(HERE, '_r76_ledger_new10.md')
old = io.open(dst, encoding='utf-8').read()
if '## §102 R76' in old:
    print('已存在，跳过')
else:
    with io.open(dst, 'a', encoding='utf-8') as f:
        f.write(io.open(src, encoding='utf-8').read())
after = io.open(dst, encoding='utf-8').read()
print('lines %d -> %d (+%d)' % (old.count('\n'), after.count('\n'),
                                after.count('\n') - old.count('\n')))
print('  §102 present =', '## §102 R76' in after)
# 在 §93 处插更正指针
key = '## §93 R76 ★★★ **疑似 P0（待用户/专家确认）：`V1`/`V3`/`V8` 的 `n*` 与 `a` 标签可能互换**'
if key in after and '定性完成见 §102' not in after:
    after = after.replace(
        key,
        key + '\n\n> ★★★ **2026-09-30 补记（§102）**：本节已**定性完成** ——\n'
        '> `NPF` **不是**晶体学惯习面，而是 **`argmin_normal(C, ε)`（弹性能极小法向）**\n'
        '> （`T16_verify_rve.py:53`）⇒ 真正的问题不是"`NPF` 对不对"，而是\n'
        '> **"选支规则"该用弹性能还是不变平面**。\n'
        '> 已用**双重正对照 + 体积地板**（比值 0.9886）钉死不变平面确实落在 `a` 上（3 个变体）。\n'
        '> **裁定需用户/专家；裁定前不动引擎。**\n', 1)
    with io.open(dst, 'w', encoding='utf-8') as f:
        f.write(after)
    print('  已在 §93 处插入 §102 指针')
