#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_fix_stack.py --- ★★★★★ 修 `stack` 通道不创建新场的缺陷（**一行级的三处**）

## 缺陷（**逐字定位**）
`windowB_surface.py` 里三个通道播种时用的场号：
```
2173:  out.append((**kk**,    'fresh'))    ✓ 新场
2567:  self.seed_plate(**k_new**, …)        ✓ 新场
2572:  out.append((**k_new**, 'attach'))    ✓ 新场
2629:  self.seed_plate(**k**, …)            ✗ **源场**
2632:  along=_along_of(**k**)               ✗ **源场**
2634:  out.append((**k**, 'stack'))         ✗ **源场**
```
**⇒ `nfsv` 算出了新场 `k_new`（所以 `nfsv_ok = 67`），但 `stack` 分支**没用它****：
* 种子播进**源场** ⇒ **不产生新板条**（实测：15 次 stack ⇒ 0 根新板条）；
* 同一个场被塞进第二个种子 ⇒ **碎片化**（实测：新场首现即 2–5 块）；
* 实测总账：计划 66 根 ⇒ 实际 19 根（少 15 根正好 = stack 次数）。

## 修法（**最小改动，默认路径逐位不变**）
把上面三处的 `k` 改成 `k_new`。
**安全性论证**：
1. `k_new` 在作用域内（2320 行 `k_new = k` 初始化；attach 分支已在用）；
2. **`k_new` 的初值就是 `k`，只有 `nfsv` 找到空场时才被改写**
   ⇒ **`nfsv` 关掉时（归档路径）三处仍是 `k`** ⇒ **逐位不变** ✓；
3. `nfsv` 要求**同变体**（`vg.get(_j) == _v`）⇒ `_along_of(k_new)` 与 `_along_of(k)` **同向** ✓；
4. `cover`/`reg` 守卫（2625）不引用 `k` ⇒ 不受影响 ✓。
"""
import hashlib
import os
import re
import shutil
import sys

P = 'windowB_surface.py'
BAK = P + '.bak_stackfield'

src = open(P, encoding='utf-8').read()
h0 = hashlib.sha256(src.encode()).hexdigest()
print('  改前 sha256 = %s…（%d 字节）' % (h0[:16], len(src)))

# ── 定位 stack 分支的那一次 seed_plate（**锚点唯一化**）──
old = """                            try:
                                self.seed_plate(k, cc, nrm, R, t,
                                                shape=c.get('nuc_shape', 'disc'),
                                                elong=c.get('elong', 1.0),
                                                along=_along_of(k),
                                                flat_end=True)
                                out.append((k, 'stack'))"""
new = """                            try:
                                # ★★★★★ 2026-10-04（**修 stack 不建新场**）：
                                #   原来这里三处都用 **源场 `k`** ⇒ `nfsv` 算出的
                                #   新场 `k_new`（2320–2332）**被丢弃** ⇒
                                #   ① 不产生新板条（实测 15 次 stack ⇒ 0 根新板条，
                                #      总账 计划 66 根 → 实际 19 根，**少 15 根正好 = stack 次数**）；
                                #   ② 同一场被塞第二个种子 ⇒ **碎片化**
                                #      （实测：新场首现即 2–5 块，且 34 核只生成 19 个场）。
                                #   对照 `attach` 分支（2567–2572）三处**全部**用 `k_new` ✓。
                                #   ⚠ `k_new` 初值 = `k`（2320）⇒ **`nfsv` 关时逐位不变**；
                                #     且 `nfsv` 要求同变体 ⇒ `_along_of` 同向 ⇒ 无额外行为变化。
                                self.seed_plate(k_new, cc, nrm, R, t,
                                                shape=c.get('nuc_shape', 'disc'),
                                                elong=c.get('elong', 1.0),
                                                along=_along_of(k_new),
                                                flat_end=True)
                                out.append((k_new, 'stack'))"""

n = src.count(old)
print('  锚点出现次数 = %d（应为 **1**）' % n)
if n != 1:
    print('  ❌ 锚点不唯一 ⇒ **拒绝修改**')
    sys.exit(1)

if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
    print('  已备份 → %s' % BAK)

out = src.replace(old, new, 1)
# 语法自检（不写盘先编译）
try:
    compile(out, P, 'exec')
    print('  ✅ 改后语法 OK')
except SyntaxError as e:
    print('  ❌ 语法错误：%s ⇒ **拒绝写盘**' % e)
    sys.exit(1)

open(P, 'w', encoding='utf-8').write(out)
h1 = hashlib.sha256(out.encode()).hexdigest()
print('  改后 sha256 = %s…（%d 字节）' % (h1[:16], len(out)))
print('  ⇒ 已写盘')

# ── 复核：三处是否都换成了 k_new ──
chk = open(P, encoding='utf-8').read()
seg = chk[chk.index('self.seed_plate(k_new, cc, nrm, R, t,'):][:420]
print()
print('  ── 复核改后的那一段 ──')
for line in seg.splitlines()[:10]:
    print('     %s' % line.rstrip()[:120])
print()
print('  ✅ `seed_plate(k_new` 出现 = %d 次（attach 1 + stack 1 = 2）'
      % chk.count('self.seed_plate(k_new'))
print('  ✅ `out.append((k_new, \'stack\'))` 出现 = %d 次（应 1）'
      % chk.count("out.append((k_new, 'stack'))"))
print('  ⚠ 残留 `out.append((k, \'stack\'))` = %d 次（应 0）'
      % chk.count("out.append((k, 'stack'))"))
