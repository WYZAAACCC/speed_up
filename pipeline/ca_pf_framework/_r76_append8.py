import io
import os
HERE = os.path.dirname(os.path.abspath(__file__))
dst = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
src = os.path.join(HERE, '_r76_ledger_new8.md')
old = io.open(dst, encoding='utf-8').read()
if '## §100 R76' in old:
    print('已存在，跳过')
else:
    with io.open(dst, 'a', encoding='utf-8') as f:
        f.write(io.open(src, encoding='utf-8').read())
after = io.open(dst, encoding='utf-8').read()
print('lines %d -> %d (+%d)' % (old.count('\n'), after.count('\n'),
                                after.count('\n') - old.count('\n')))
print('  §100 present =', '## §100 R76' in after)
# 在 §99 第六节处插一个"已撤回"的指针
key = '### 六、★ 几何验收判据的**缺口**（本轮我自己的错）'
if key in after and '结论已被 §100 更正' not in after:
    after = after.replace(
        key,
        key + '\n\n> ⛔ **2026-09-30 补记（§100）**：本节把根因归到"`T` 的格点相位"——'
        '**该归因已被 §100 的全库普查撤回**：\n'
        '> 主控变量是 **`--plate-L`**（`cov(t=0)` 随 `L` 单调升），`T` 不是。\n'
        '> 「两条判据都要」这条规程**仍然有效**，但 `cov ≥ 0.85` **有长度依赖**，'
        '不能一刀切。\n', 1)
    with io.open(dst, 'w', encoding='utf-8') as f:
        f.write(after)
    print('  已在 §99 第六节插入更正指针')
