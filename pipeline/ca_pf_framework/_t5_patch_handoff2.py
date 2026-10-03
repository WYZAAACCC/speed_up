#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_handoff2.py --- 给「接手须知」补上 **V2 臂**

## 为什么必须补
「接手须知」现在只描述 `t5H3`。**而 `t5V2` 是判据 ③(多块)/④/⑥ 的唯一有路** ——
**若接手者不知道它在跑，会把"另一条臂"当成野生进程，或白等 `t5H3` 出多块。**
"""
import sys

P = 'R581_T5_RESTART.md'
src = open(P, encoding='utf-8').read()
orig = src

anchor = "## 0. 三十秒状态\n"
add = """
> ⚠ **本文件描述的是**第一臂** `t5H3`。另有**第二臂 `t5V2`** 在并行跑（核 8-15），
>   它是**判据 ③(多块)/④/⑥ 的唯一有路**：`--nvar 2 --m 36 --var-rule random`（`nv=72` ⇒ 内存不变），
>   判据（预先写死）：**`n_var_sig > 1`**（随机选变体生效）· **`nblk_sig ≥ 2`**（真的出现新块）· **`nf2 > 0`**（块相遇）。
>   **恢复**：`python _t5_short.py --tag t5V2 --N 160 --nvar 2 --m 36 --B 3 --steps 6000 --cores 8-15 --var-rule random --resume _exp/_bk_t5/dry_t5V2/ckpt`
>   **为什么要它**：`t5H3` 的 `m=24` **已用尽**（逐字消息"无可用空场/落位失败" @ step 801）⇒
>   它在 `nslab_n = 24` **封顶** ⇒ **多块永远不会出现**（详见 §117/§118/§121/§122）。
"""

if anchor in src and 't5V2' not in src.split('## 1.')[0]:
    src = src.replace(anchor, anchor + add, 1)
    print('  ✅ 已在「接手须知」开头补上 V2 臂说明')
elif 't5V2' in src.split('## 1.')[0]:
    print('  ⚠ 接手须知开头**已含** t5V2 ⇒ 无需重复（幂等）')
else:
    print('  ⚠ 锚点没找到 ⇒ **不写盘**'); sys.exit(1)

if src != orig:
    open(P, 'w', encoding='utf-8').write(src)
    print('  已写回 %s（%d 行）' % (P, src.count('\n') + 1))

# ── 验证 ──
s2 = open(P, encoding='utf-8').read()
head = s2.split('## 1.')[0]
print()
print('  ── 验证 ──')
print('    接手须知开头含 t5V2        = %s ⇒ %s' % ('t5V2' in head, '✅ PASS' if 't5V2' in head else '❌ FAIL'))
print('    含判据 n_var_sig > 1       = %s' % ('n_var_sig > 1' in head))
print('    含恢复命令 --tag t5V2      = %s' % ('--tag t5V2' in head))
print('    文档结构完好（接手须知标题在） = %s' % ('# ★★★★★ 接手须知' in s2))
