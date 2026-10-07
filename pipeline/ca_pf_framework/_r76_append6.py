import io
import os
HERE = os.path.dirname(os.path.abspath(__file__))
dst = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
src = os.path.join(HERE, '_r76_ledger_new6.md')
old = io.open(dst, encoding='utf-8').read()
if '## §98 R76' in old:
    print('已存在，跳过')
else:
    with io.open(dst, 'a', encoding='utf-8') as f:
        f.write(io.open(src, encoding='utf-8').read())
after = io.open(dst, encoding='utf-8').read()
print('lines %d -> %d (+%d)' % (old.count('\n'), after.count('\n'),
                                after.count('\n') - old.count('\n')))
print('  §98 present =', '## §98 R76' in after)
# 同时在 §95 处插一行醒目的更正指针（避免后来人只读到 §95）
old2 = io.open(dst, encoding='utf-8').read()
key = '## §95 R76 ★★★ **条件 ③ 的隔离判决'
if key in old2 and '⛔ **本节第三节第 2 条与第四节已被 §98 更正' not in old2:
    old2 = old2.replace(
        key,
        '> ⛔ **本节第三节第 2 条（"偏离时还没接触 ⇒ 穿过母相耦合"）与第四节'
        '（"不只是弹性的"）已被 `§98` 更正** ——\n'
        '> 实测**接触起始 step 120、偏离 step 240**，顺序**正好相反**。\n'
        '> 保留的是**观测本身**（7.62%、`w` 不受影响）；机制改为**几何碰撞**。\n\n'
        + key, 1)
    with io.open(dst, 'w', encoding='utf-8') as f:
        f.write(old2)
    print('  已在 §95 处插入更正指针')
else:
    print('  §95 指针：已存在或未找到 key')
