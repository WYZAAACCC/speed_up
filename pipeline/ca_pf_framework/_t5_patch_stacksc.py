#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_stacksc.py --- ★★★★★★ 把 `supercrit` 超临界判据扩展到 **`stack` 通道**

## 根因（本轮查明，三方证据自洽）
正确判据 `ΔG_v(T) + ed_face > 2γ/t` **已实现**（`_supercrit_probe`，试放+精确回滚）、
**已开启**（`_t5_short.py:79` 传 `--nuc-supercrit 1`），但**唯一调用点在 `fresh` 分支内**
（`windowB_surface.py:2146`）⇒ 事件分布 attach 16 / stack 9 / fresh 2 ⇒ **25/27 绕过判据**
⇒ 核被放在**净驱动力为负**处 ⇒ **出生即溶解**（实测孤立种子 −87%）。

## 本 patch 做什么（**只动 `stack`**，先把 9/25 补上）
在 `stack` 分支的守卫之后、`self.seed_plate(k_new, …)` **之前**插入：
```python
if c.get('supercrit', False):
    _ok_sc, _med_sc, _fc_sc, _n_sc = self._supercrit_probe(
        k_new, cc, nrm, R, t, cover, df, c['gamma'],
        shape=c.get('nuc_shape', 'disc'))
    ... 记账 ...
    if not _ok_sc: continue
```
**逐条安全性论证：**
1. **完全由 `c.get('supercrit', False)` 门控** ⇒ 与 `fresh` 分支**同一开关、同一语义**;
   `--nuc-supercrit 0` 时**一行都不执行** ⇒ 逐位不变 ✓
2. `_supercrit_probe` 自己**真放 + 精确回滚**（净效果 = 不改任何场），
   且**拒绝时什么都不用撤销**（代码 docstring 逐字）✓
3. `cover`（`:2615`）、`cc`、`nrm`、`R`、`t`、`df`、`c['gamma']`、`k_new` **都在作用域内** ✓
4. `continue` 与既有守卫（`:2621`/`:2625`）**同类**，落在同一个 `for j in range(4)` 循环里 ✓
5. `_dbg` 是既有 dict（`:2610` 等处已在用）⇒ 只加键，不改语义 ✓
"""
import hashlib
import os
import shutil
import sys

P = 'windowB_surface.py'
BAK = P + '.bak_stacksc'
src = open(P, encoding='utf-8').read()
print('  改前 sha256 = %s…（%d 字节）' % (hashlib.sha256(src.encode()).hexdigest()[:16], len(src)))

OLD = """                            if not bool((reg[cover] == 0).all()):
                                _dbg['cov'] += 1
                                continue
                            try:
"""
NEW = """                            if not bool((reg[cover] == 0).all()):
                                _dbg['cov'] += 1
                                continue
                            # ★★★★★★ 2026-10-04（**超临界判据扩展到 `stack` 通道**）：
                            #   根因：正确判据 `ΔG_v(T) + ed_face > 2γ/t`（`PHYSICS_FIRST_SPEC §6.1`）
                            #   **已实现**（`_supercrit_probe`，试放+精确回滚）、**已开启**
                            #   （`_t5_short.py:79` 传 `--nuc-supercrit 1`），
                            #   但**唯一调用点在 `fresh` 分支内**（`:2146`）
                            #   ⇒ 事件分布 attach 16 / stack 9 / fresh 2 ⇒ **25/27 绕过判据**
                            #   ⇒ 核被放在**净驱动力为负**处 ⇒ **出生即溶解**
                            #     （实测孤立种子 −87%；F1 界面 `Δed` = −2.955e8，`<0` 占 100%）;
                            #   而代码自己实测过：放核**前** `ed` = +1.9e8、放核**后** = −2.5e8
                            #   ⇒ **符号相反** ⇒ 只有"试放后测"才有效 ⇒ **本处必须用 `_supercrit_probe`**。
                            #   ⚠ 完全由 `c.get('supercrit', False)` 门控（与 `fresh` 同开关）
                            #     ⇒ `--nuc-supercrit 0` 时**一行都不执行** ⇒ 逐位不变 ✓
                            #   ⚠ `_supercrit_probe` 自己**真放 + 精确回滚**（净效果 = 不改任何场）;
                            #     拒绝时**什么都不用撤销**（其 docstring 逐字）。
                            if c.get('supercrit', False):
                                _ok_sc, _med_sc, _fc_sc, _n_sc = self._supercrit_probe(
                                    k_new, cc, nrm, R, t, cover, df, c['gamma'],
                                    shape=c.get('nuc_shape', 'disc'))
                                _dbg['sc_try_stack'] = _dbg.get('sc_try_stack', 0) + 1
                                _dbg['sc_stack_last_df'] = float(df)
                                _dbg['sc_stack_last_ed'] = float(_med_sc)
                                _dbg['sc_stack_last_fcrit'] = float(_fc_sc)
                                if not _ok_sc:
                                    _dbg['supercrit_stack'] = _dbg.get('supercrit_stack', 0) + 1
                                    continue          # 站不住 ⇒ **试下一个落位**
                                _dbg['sc_stack_pass'] = _dbg.get('sc_stack_pass', 0) + 1
                            try:
"""
n = src.count(OLD)
print('  锚点出现次数 = %d（应为 1）' % n)
if n != 1:
    print('  ❌ 锚点不唯一 ⇒ 拒绝修改'); sys.exit(1)
out = src.replace(OLD, NEW, 1)
try:
    compile(out, P, 'exec')
    print('  ✅ 改后语法 OK')
except SyntaxError as e:
    print('  ❌ 语法错误：%s ⇒ 拒绝写盘' % e); sys.exit(1)
for need in ('_supercrit_probe(\n                                    k_new',
             "c.get('supercrit', False)",
             "sc_stack_pass"):
    if need not in out:
        print('  ❌ 校验失败（缺 %r）⇒ 拒绝写盘' % need[:40]); sys.exit(1)
if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
    print('  已备份 → %s' % BAK)
open(P, 'w', encoding='utf-8').write(out)
print('  ✅ 已写盘（sha256 %s…，%d 字节）'
      % (hashlib.sha256(out.encode()).hexdigest()[:16], len(out)))
print()
print('  ── 复核 ──')
print('     * 门控：`c.get(\'supercrit\', False)` ⇒ 与 `fresh` **同一开关** ⇒ 关时逐位不变 ✓')
print('     * 位置：`stack` 分支守卫之后、`seed_plate` 之前 ✓')
print('     * 记账键：`sc_try_stack` / `sc_stack_pass` / `supercrit_stack` ✓')
