import io
import os
HERE = os.path.dirname(os.path.abspath(__file__))
dst = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
src = os.path.join(HERE, '_r76_ledger_new28.md')
old = io.open(dst, encoding='utf-8').read()
if '## §121 R76' in old:
    print('已存在，跳过')
else:
    with io.open(dst, 'a', encoding='utf-8') as f:
        f.write(io.open(src, encoding='utf-8').read())
after = io.open(dst, encoding='utf-8').read()
print('lines %d -> %d (+%d)' % (old.count('\n'), after.count('\n'),
                                after.count('\n') - old.count('\n')))
print('  §121 present =', '## §121 R76' in after)
key = '### 五、⇒ 与本轮其它结论拼起来的完整图像'
if key not in after:
    key2 = '### 四、⇒ 核心结论（**负面，但明确且可复现**）'
    if key2 in after and '§121 已给第三环' not in after:
        after = after.replace(
            key2,
            key2 + '\n\n> ★★ **2026-09-30 补记（§121）：第三环已有答案** ——\n'
            '> 加 `--el-scale 0` 的对照臂实测：**关掉弹性后两臂的 `r` 仍上升**\n'
            '> （`saSet2` 趋势 +0.0188→**+0.0198**；`saOddG` +0.0074→**+0.0011**）\n'
            '> ⇒ **E-2 成立：漂移主要是几何（碰撞改变体积分数）造成的**。\n'
            '> ⚠ 但两臂"弹性占比"差别大（≈0% vs ≈85%），且 `saOddGE0` **撞壁**\n'
            '> ⇒ **那个数未定**。\n', 1)
        with io.open(dst, 'w', encoding='utf-8') as f:
            f.write(after)
        print('  已在 §112 处插入 §121 指针')
