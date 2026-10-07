import io
import os
HERE = os.path.dirname(os.path.abspath(__file__))
dst = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
src = os.path.join(HERE, '_r76_ledger_new25.md')
old = io.open(dst, encoding='utf-8').read()
if '## §118 R76' in old:
    print('已存在，跳过')
else:
    with io.open(dst, 'a', encoding='utf-8') as f:
        f.write(io.open(src, encoding='utf-8').read())
after = io.open(dst, encoding='utf-8').read()
print('lines %d -> %d (+%d)' % (old.count('\n'), after.count('\n'),
                                after.count('\n') - old.count('\n')))
print('  §118 present =', '## §118 R76' in after)
# 在 §112 与 §89 处各插一个指针（这是最重要的两条下游影响）
key1 = '### 四、⇒ 核心结论（**负面，但明确且可复现**）'
if key1 in after and 'P1-44' not in after.split(key1)[1][:1500]:
    after = after.replace(
        key1,
        key1 + '\n\n> ⛔⛔ **2026-09-30 补记（§118，P1-44）**：本节的判词**必须改述** ——\n'
        '> 实测 `r_selfac` 与弹性能密度 `E_el/Vt` **定量脱节**\n'
        '> （同几何同体积、只差变体集的两臂：**`r` 差 9.10×，而 `E_el/Vt` 只差 1.12×**）。\n'
        '> ⇒ `SA-1` FAIL 只能读作「**`r` 没走向它的下界**」，\n'
        '> **不能**读作「组织没有自协调」。\n', 1)
    with io.open(dst, 'w', encoding='utf-8') as f:
        f.write(after)
    print('  已在 §112 处插入 P1-44 指针')
    after = io.open(dst, encoding='utf-8').read()
key2 = '### 五、新增硬规程（**第 ③ 条**）'
if key2 in after and '§118 追记' not in after:
    after = after.replace(
        key2,
        '> ⚠ **2026-09-30 追记（§118）**：本节的效应量（−2.4%…−15.9%）是**用 `r_selfac` 量的**，\n'
        '> 而 `§118` 证明 `r` 把能量差异**放大约 8 倍** ⇒\n'
        '> 对应的**能量差异只有 ~0.3–2%** ⇒ **方向可信、量级要大幅下调**。\n\n'
        + key2, 1)
    with io.open(dst, 'w', encoding='utf-8') as f:
        f.write(after)
    print('  已在 §89 处插入 §118 追记')
