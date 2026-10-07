import io
import os
HERE = os.path.dirname(os.path.abspath(__file__))
dst = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
src = os.path.join(HERE, '_r76_ledger_new7.md')
old = io.open(dst, encoding='utf-8').read()
if '## §99 R76' in old:
    print('已存在，跳过')
else:
    with io.open(dst, 'a', encoding='utf-8') as f:
        f.write(io.open(src, encoding='utf-8').read())
after = io.open(dst, encoding='utf-8').read()
print('lines %d -> %d (+%d)' % (old.count('\n'), after.count('\n'),
                                after.count('\n') - old.count('\n')))
print('  §99 present =', '## §99 R76' in after)
# 在 §87（R75 验收）处插更正指针
key = '## §87 R76 ★★★'
if key in after and '验收判据缺了 `cov`' not in after:
    after = after.replace(
        key,
        '> ⛔ **2026-09-30 补记（§99）**：本节的验收判据（`f_flat` / `blk_nprof` / `nf2`）\n'
        '> **缺了 `cov`（同变体界面完整性）** —— 实测 `--facet-proj` 在第一次投影时把\n'
        '> **全部** F3 界面抹掉（`f3_area` 4.108 → **0.000000**，~100 步后恢复，\n'
        '> 末态仍低 8.4%），而上面三条判据**一条都看不见**。\n'
        '> ⇒ 本节的"全部通过"应读作**"在被测的量上都通过"**，不是"没有代价"。\n\n'
        + key, 1)
    with io.open(dst, 'w', encoding='utf-8') as f:
        f.write(after)
    print('  已在 §87 处插入更正指针')
