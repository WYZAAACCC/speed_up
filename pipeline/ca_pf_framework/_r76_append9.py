import io
import os
HERE = os.path.dirname(os.path.abspath(__file__))
dst = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
src = os.path.join(HERE, '_r76_ledger_new9.md')
old = io.open(dst, encoding='utf-8').read()
if '## §101 R76' in old:
    print('已存在，跳过')
else:
    with io.open(dst, 'a', encoding='utf-8') as f:
        f.write(io.open(src, encoding='utf-8').read())
after = io.open(dst, encoding='utf-8').read()
print('lines %d -> %d (+%d)' % (old.count('\n'), after.count('\n'),
                                after.count('\n') - old.count('\n')))
print('  §101 present =', '## §101 R76' in after)
# 在 §100 结论⑩ 处插指针
key = '> **⑩ 六个块 + 长板条（L≥1600）在 6–7 µm 盒里放不下 —— 这是硬冲突。**'
if key in after and '§101 已解开' not in after:
    after = after.replace(
        key,
        '> **⑩ 六个块 + 长板条（L≥1600）在 6–7 µm 盒里放不下 —— 这是硬冲突。**\n'
        '>\n'
        '> ✅ **2026-09-30 补记（§101）：本条已被解开** —— 把 `cov` 做**长度归一化**\n'
        '> （`cov_norm = cov/cov_base(L)`）之后，**`sgG`（L=1000）就是合格构型**，\n'
        '> 不需要 10 µm 大盒、也不必退到 1 根/块。下面 (a)/(b)/(c) 三选一**不必再做**。\n', 1)
    with io.open(dst, 'w', encoding='utf-8') as f:
        f.write(after)
    print('  已在 §100 结论⑩ 处插入指针')
