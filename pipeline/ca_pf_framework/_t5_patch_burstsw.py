#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_burstsw.py --- 给 `_t5_short.py` 加 `--burst-km` 透传（**默认不传 ⇒ 逐字不变**）

## 为什么
`s284` 已在 `_bk_exp.py` 实施 burst 修复（KM 分数律），由 `--burst-km` 门控。
**但 `_t5_short.py` 不传它** ⇒ 只能直接调 `_bk_exp.py` 才能验证
⇒ **加一个透传**（与本会话已验证的 `--diag-terms` / `--no-nucleation` 同法）。

## 锚点（我 s267 加的 `--diag-terms` 透传，逐字）
```python
            (['--diag-terms'] if bool(getattr(a, 'diag_terms', False)) else []) + \
```
在其后追加一行透传即可。

## 四道自检
1. 锚点唯一；2. `compile()` 通过；3. 新选项存在且默认 0；4. 默认档不产生参数（逐字等价）。
"""
import hashlib
import os
import shutil
import sys

P = '_t5_short.py'
BAK = P + '.bak_burstsw'
src = open(P, encoding='utf-8').read()
print('  改前 sha256 = %s…（%d 字节）' % (hashlib.sha256(src.encode()).hexdigest()[:16], len(src)))

OLD = """            (['--diag-terms'] if bool(getattr(a, 'diag_terms', False)) else []) + \\"""
NEW = """            (['--diag-terms'] if bool(getattr(a, 'diag_terms', False)) else []) + \\
            # ★★★★★★ s285（**用户总目标第 4 项：修 burst 至物理正确**）：
            #   透传 `--burst-km`（`_bk_exp.py` 里由它把形核调度从**线性律**
            #   `floor(α·(Ms−T))` 换成 **KM 分数律** `round(N_end·(1−exp(−α(Ms−T))))`）。
            #   ⚠ **默认 `0` ⇒ 不产生任何参数** ⇒ 归档与在跑的臂**逐字不变** ✓
            (['--burst-km', str(int(getattr(a, 'burst_km', 0) or 0))]
             if int(getattr(a, 'burst_km', 0) or 0) != 0 else []) + \\"""
n = src.count(OLD)
print('  锚点出现次数 = %d（应为 1）' % n)
if n != 1:
    print('  ❌ 锚点不唯一 ⇒ 拒绝修改'); sys.exit(1)
out = src.replace(OLD, NEW, 1)

# argparse 选项：插在 `--diag-terms` 之后（括号配平）
ANCH = "ap.add_argument('--diag-terms'"
i = out.find(ANCH)
if i < 0:
    print('  ❌ 找不到 `--diag-terms` 锚点 ⇒ 拒绝修改'); sys.exit(1)
j = i
depth = 0
while j < len(out):
    if out[j] == '(':
        depth += 1
    elif out[j] == ')':
        depth -= 1
        if depth == 0:
            break
    j += 1
ADD = ("\n    ap.add_argument('--burst-km', type=int, default=0, choices=(0, 1),\n"
       "                    help='★ s285：透传 `--burst-km`（形核用 KM 分数律 ⇒ 物理正确的 burst）；'\n"
       "                         '默认 0 ⇒ 不传任何参数，归档逐字不变')\n")
out = out[:j + 1] + ADD + out[j + 1:]

try:
    compile(out, P, 'exec')
    print('  ✅ 改后语法 OK')
except SyntaxError as e:
    print('  ❌ 语法错误：%s ⇒ 拒绝写盘' % e); sys.exit(1)
for need in ("getattr(a, 'burst_km', 0)", "'--burst-km'"):
    if need not in out:
        print('  ❌ 校验失败（缺 %r）⇒ 拒绝写盘' % need); sys.exit(1)
if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
    print('  已备份 → %s' % BAK)
open(P, 'w', encoding='utf-8').write(out)
print('  ✅ 已写盘（sha256 %s…，%d 字节）'
      % (hashlib.sha256(out.encode()).hexdigest()[:16], len(out)))
print()
print('  ── 复核 ──')
print('     * 默认 0 ⇒ `if ... != 0 else []` 取空列表 ⇒ **不产生参数** ⇒ 逐字不变 ✓')
print('     * `--burst-km 1` ⇒ 传 `--burst-km 1` 给引擎 ⇒ KM 分数律 ✓')
