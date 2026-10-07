import io
import os
HERE = os.path.dirname(os.path.abspath(__file__))
dst = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
src = os.path.join(HERE, '_r76_ledger_new26.md')
old = io.open(dst, encoding='utf-8').read()
if '## §119 R76' in old:
    print('已存在，跳过')
else:
    with io.open(dst, 'a', encoding='utf-8') as f:
        f.write(io.open(src, encoding='utf-8').read())
after = io.open(dst, encoding='utf-8').read()
print('lines %d -> %d (+%d)' % (old.count('\n'), after.count('\n'),
                                after.count('\n') - old.count('\n')))
print('  §119 present =', '## §119 R76' in after)
key = '### 三、⇒ 结论（**这是本轮最重要的框架结论**）'
if key in after and '§119 已做普适性检验' not in after:
    after = after.replace(
        key,
        key + '\n\n> ★★★ **2026-09-30 补记（§119）：普适性已检验，结论要改强** ——\n'
        '> 全库 **196 对**可比对（同 `(N,Δx)`、`|ΔVt|/Vt<10%`），其中 **82 对** `r` 真的差了\n'
        '> （`Δr/r>0.2`）⇒ 比值 `(Δr/r)/(ΔE/E)` **从 0.22 散到 66（中位 1.73）**。\n'
        '> ⇒ **`r` 不是"高估 8 倍"，而是"散得没有规律"**（有时高估 60×，有时反而低估）。\n'
        '> 本节第四节第 2 条（P-SA-1 量级下调）仍然成立，但**理由要改成"无稳定关系"**。\n', 1)
    with io.open(dst, 'w', encoding='utf-8') as f:
        f.write(after)
    print('  已在 §118 处插入 §119 指针')
