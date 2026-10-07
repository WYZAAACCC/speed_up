import io
import os
HERE = os.path.dirname(os.path.abspath(__file__))
dst = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
src = os.path.join(HERE, '_r76_ledger_new23.md')
old = io.open(dst, encoding='utf-8').read()
if '## §116 R76' in old:
    print('已存在，跳过')
else:
    with io.open(dst, 'a', encoding='utf-8') as f:
        f.write(io.open(src, encoding='utf-8').read())
after = io.open(dst, encoding='utf-8').read()
print('lines %d -> %d (+%d)' % (old.count('\n'), after.count('\n'),
                                after.count('\n') - old.count('\n')))
print('  §116 present =', '## §116 R76' in after)
# 在 §113 处插指针
key = '### 六、⇒ `§93/§102` 的最终意义'
if key in after and '§116 已逐列量出' not in after:
    after = after.replace(
        key,
        key + '\n\n> ★★★ **2026-09-30 补记（§116）：影响面已**逐列**量出** ——\n'
        '> **97 列里 55 列改变 >1%**，其中 `nf2`（异变体接触面）**47 → 520（11 倍）**、\n'
        '> 同变体 `f3_area` **−55%**、`n_tip` **1947 → 8250**、`a_lath` **+18%**、`n_lath` **+16.6%**。\n'
        '> **只有 21 列不受影响**（含 `r_selfac`、`n_habit`、`nblk_sig`、`dt`、`box_touch`）。\n'
        '> ⇒ 本节的"形态学结论会变"应读作**"报告量的一半以上会变"**，\n'
        '> 含 `§87` 的 B-2（`nf2`）与 `§98` 的碰撞机制描述。\n', 1)
    with io.open(dst, 'w', encoding='utf-8') as f:
        f.write(after)
    print('  已在 §113 处插入 §116 指针')
