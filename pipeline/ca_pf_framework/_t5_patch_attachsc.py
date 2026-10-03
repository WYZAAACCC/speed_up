#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_attachsc.py --- ★★★★★★ 把 `supercrit` 判据扩展到 **`attach` 通道**（16/28 事件）

## 为什么（承 s270 的根因）
正确判据 `ΔG_v(T) + ed_face > 2γ/t` 已实现、已开启，但唯一调用点在 `fresh` 分支内。
s271 已把补丁打到 `stack`（10/28）;**本 patch 补 `attach`（16/28）** ⇒ 合计 **26/28 = 93%**。

## 实测支撑（`t5SCV` 验证臂，配置同 t5B2）
```
step 101 / 201 的事件模式都是 **attach**；Vt：1.4548 → 1.4197 → **1.3936 µm³**（**在下降**）
⇒ **新核出生即溶解**，且**本轮事件全走 attach** ⇒ 必须补这一处。
```

## 锚点（逐字，`windowB_surface.py:2560–2566`）
```
                            _okr = reg[cover]
                            if not bool(np.isin(_okr, (0, k)).all()):
                                _dbg['cov'] += 1
                                continue
                            try:
                                self.seed_plate(k_new, cc, nrm, R, _t_use,
```
## 安全性（与 stack 版同）
1. **完全由 `c.get('supercrit', False)` 门控** ⇒ 关时**一行都不执行** ⇒ 逐位不变 ✓
2. `_supercrit_probe` **真放 + 精确回滚**（净效果 = 不改任何场）⇒ 拒绝时无需撤销 ✓
3. **厚度传 `_t_use`**（与紧随其后的 `seed_plate` 一致，而不是 `t`）——
   因为 `attach` 用的是 `_t_use`（含末片减薄），传 `t` 会与真实落位不符 ✓
4. `continue` 与既有守卫同类，落在同一个候选循环里 ✓
"""
import hashlib
import os
import shutil
import sys

P = 'windowB_surface.py'
BAK = P + '.bak_attachsc'
src = open(P, encoding='utf-8').read()
print('  改前 sha256 = %s…（%d 字节）' % (hashlib.sha256(src.encode()).hexdigest()[:16], len(src)))

OLD = """                            _okr = reg[cover]
                            if not bool(np.isin(_okr, (0, k)).all()):
                                _dbg['cov'] += 1
                                continue
                            try:
                                self.seed_plate(k_new, cc, nrm, R, _t_use,
"""
NEW = """                            _okr = reg[cover]
                            if not bool(np.isin(_okr, (0, k)).all()):
                                _dbg['cov'] += 1
                                continue
                            # ★★★★★★ 2026-10-04（**超临界判据扩展到 `attach` 通道**）：
                            #   承 `stack` 分支的同一处补丁（见该处长注释）。根因：
                            #   正确判据 `ΔG_v(T) + ed_face > 2γ/t`（`PHYSICS_FIRST_SPEC §6.1`）
                            #   已实现（`_supercrit_probe`，试放+精确回滚）、已开启
                            #   （`_t5_short.py:79` 传 `--nuc-supercrit 1`），
                            #   但**唯一调用点在 `fresh` 分支内** ⇒ 事件分布
                            #   attach 16 / stack 9 / fresh 2 ⇒ **25/27 绕过判据**。
                            #   **实测（`t5SCV`）**：step 101/201 的事件全是 `attach`，
                            #   且 `Vt` 在事件后**下降**（1.4548 → 1.4197 → 1.3936 µm³）
                            #   ⇒ **新核出生即溶解** ✓ 与本根因吻合。
                            #   ⚠ 完全由 `c.get('supercrit', False)` 门控（与 `fresh`/`stack`
                            #     **同一个开关**）⇒ `--nuc-supercrit 0` 时一行都不执行 ⇒ 逐位不变 ✓
                            #   ⚠ **厚度传 `_t_use`**（不是 `t`）—— 紧随其后的 `seed_plate`
                            #     用的就是 `_t_use`（含末片减薄 `t_last_reduce`）
                            #     ⇒ 传 `t` 会与真实落位不一致。
                            #   ⚠ `_supercrit_probe` 自己**真放 + 精确回滚**（净效果 = 不改任何场）;
                            #     拒绝时**什么都不用撤销**（其 docstring 逐字）。
                            if c.get('supercrit', False):
                                _ok_sc, _med_sc, _fc_sc, _n_sc = self._supercrit_probe(
                                    k_new, cc, nrm, R, _t_use, cover, df, c['gamma'],
                                    shape=c.get('nuc_shape', 'disc'))
                                _dbg['sc_try_att'] = _dbg.get('sc_try_att', 0) + 1
                                _dbg['sc_att_last_df'] = float(df)
                                _dbg['sc_att_last_ed'] = float(_med_sc)
                                _dbg['sc_att_last_fcrit'] = float(_fc_sc)
                                if not _ok_sc:
                                    _dbg['supercrit_att'] = _dbg.get('supercrit_att', 0) + 1
                                    continue          # 站不住 ⇒ **试下一个候选落位**
                                _dbg['sc_att_pass'] = _dbg.get('sc_att_pass', 0) + 1
                            try:
                                self.seed_plate(k_new, cc, nrm, R, _t_use,
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
for need in ("sc_att_pass", "k_new, cc, nrm, R, _t_use, cover, df, c['gamma']"):
    if need not in out:
        print('  ❌ 校验失败（缺 %r）⇒ 拒绝写盘' % need[:44]); sys.exit(1)
if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
    print('  已备份 → %s' % BAK)
open(P, 'w', encoding='utf-8').write(out)
print('  ✅ 已写盘（sha256 %s…，%d 字节）'
      % (hashlib.sha256(out.encode()).hexdigest()[:16], len(out)))
print()
print('  ── 覆盖率复核 ──')
print('     fresh（原有） + stack（s271） + **attach（本 patch）**')
print('     ⇒ 事件分布 attach 16 / stack 10 / fresh 2 ⇒ **28/28 = 100% 全过判据** ✓')
