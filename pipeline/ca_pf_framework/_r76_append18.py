import io
import os
HERE = os.path.dirname(os.path.abspath(__file__))
dst = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
src = os.path.join(HERE, '_r76_ledger_new18.md')
old = io.open(dst, encoding='utf-8').read()
if '## §110 R76' in old:
    print('已存在，跳过')
else:
    with io.open(dst, 'a', encoding='utf-8') as f:
        f.write(io.open(src, encoding='utf-8').read())
after = io.open(dst, encoding='utf-8').read()
print('lines %d -> %d (+%d)' % (old.count('\n'), after.count('\n'),
                                after.count('\n') - old.count('\n')))
print('  §110 present =', '## §110 R76' in after)
# 在 §99 第五节（"还不能说的"）处插指针
key = '### 五、⚠ 还**不能**说的'
if key in after and '§110 已查' not in after:
    after = after.replace(
        key,
        key + '\n\n> ✅ **2026-09-30 补记（§110）：第五节最后那条"尚未查"已经查了** ——\n'
        '> `ΔVt/Δstep` 分段对照显示：**差异从 step 20 起单调增大**，\n'
        '> 且**恢复后（+102.2%）比抹平窗口内（+77.6%）更大** ⇒\n'
        '> **没有"F3 缺失"特有的动力学签名**；主导效应是投影的**重塑**。\n'
        '>（⚠ 两个效应在本设计里**分不开**；分开需做"保 F3 的投影"变体，未做。）\n', 1)
    with io.open(dst, 'w', encoding='utf-8') as f:
        f.write(after)
    print('  已在 §99 第五节插入 §110 指针')
