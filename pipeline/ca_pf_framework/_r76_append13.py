import io
import os
HERE = os.path.dirname(os.path.abspath(__file__))
dst = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
src = os.path.join(HERE, '_r76_ledger_new13.md')
old = io.open(dst, encoding='utf-8').read()
if '## §105 R76' in old:
    print('已存在，跳过')
else:
    with io.open(dst, 'a', encoding='utf-8') as f:
        f.write(io.open(src, encoding='utf-8').read())
after = io.open(dst, encoding='utf-8').read()
print('lines %d -> %d (+%d)' % (old.count('\n'), after.count('\n'),
                                after.count('\n') - old.count('\n')))
print('  §105 present =', '## §105 R76' in after)
# 在 §99 处插"第二例确认"指针
key = '### 七、状态\n\n✅ **P1-42 确诊**'
if key in after and '第二例确认见 §105' not in after:
    after = after.replace(
        key,
        '> ✅ **2026-09-30 补记（§105 第四节）：本现象已在第二个、独立的盒子上复现** ——\n'
        '> **6 块** / N=112 / L=600 / W=350 / T=510：`proj=10` 的 `f3_area` 在 step 20\n'
        '> 从 0.994 **塌到 0.0096**（约 100 倍），而 `proj=0` 臂平滑下降（0.994→0.9696→0.9293）。\n'
        '> 两例都是**严格单变量**（只差 `--facet-proj`）。\n\n'
        + key, 1)
    with io.open(dst, 'w', encoding='utf-8') as f:
        f.write(after)
    print('  已在 §99 处插入第二例确认指针')
