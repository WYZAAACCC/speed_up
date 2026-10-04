#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_etawire.py --- 把 `ed_eta` 接到引擎 CLI（`--ed-eta`，**默认 1.0 ⇒ 逐位不变**）

## 锚点（`_bk_exp.py:1226`，逐字，我 s267 加 `--diag-terms` 时也用过这一带）
```python
g.diag_terms_on = bool(getattr(a, 'diag_terms', False))
```
在其后追加：
```python
g.ed_eta = float(getattr(a, 'ed_eta', 1.0) or 1.0)
```
并在 argparse 里加 `--ed-eta`（**默认 1.0**）。
"""
import hashlib
import os
import shutil
import sys

P = '_bk_exp.py'
BAK = P + '.bak_etawire'
src = open(P, encoding='utf-8').read()
print('  改前 sha256 = %s…（%d 字节）' % (hashlib.sha256(src.encode()).hexdigest()[:16], len(src)))

OLD = "    g.diag_terms_on = bool(getattr(a, 'diag_terms', False))"
if OLD not in src:
    print('  ❌ 找不到 `g.diag_terms_on` 锚点 ⇒ 拒绝修改'); sys.exit(1)
NEW = OLD + """
    # ★★★★★★ s290（**修法 A：弹性罚能折减因子 η**，物理对应**塑性弛豫 / TRIP**）
    #   见 `windowB_surface.py` 里 `dG_cell` 那一行的长注释。
    #   `η = 1.0`（**默认**）⇒ 与原文**逐字等价** ⇒ 归档与在跑的臂**逐位不变** ✓
    #   `η < 1` ⇒ 只保留 η 份弹性储存能，其余视为**塑性耗散**（TRIP）
    #   ★ 理论标定：`df(Ms) ≈ η·|ed|_plate + 2γ/t` ⇒ **η ≈ 0.375**（建议试 0.35–0.45）
    g.ed_eta = float(getattr(a, 'ed_eta', 1.0) or 1.0)"""
out = src.replace(OLD, NEW, 1)

# argparse：插在 `--burst-km` 之后（括号配平）
ANCH = "ap.add_argument('--burst-km'"
i = out.find(ANCH)
if i < 0:
    print('  ❌ 找不到 `--burst-km` 锚点 ⇒ 拒绝修改'); sys.exit(1)
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
ADD = ("\n    ap.add_argument('--ed-eta', type=float, default=1.0,\n"
       "                    help='★ s290：**弹性罚能折减因子 η**（塑性弛豫 / TRIP）。'\n"
       "                         '1.0 = 默认（逐字等价，逐位不变）；'\n"
       "                         '理论标定 η≈0.375 使 df(Ms) ≥ η·|ed|+2γ/t；建议试 0.35–0.45')\n")
out = out[:j + 1] + ADD + out[j + 1:]

try:
    compile(out, P, 'exec')
    print('  ✅ 改后语法 OK')
except SyntaxError as e:
    print('  ❌ 语法错误：%s ⇒ 拒绝写盘' % e); sys.exit(1)
for need in ("g.ed_eta = float(getattr(a, 'ed_eta', 1.0) or 1.0)", "'--ed-eta', type=float"):
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
print('     * `--ed-eta` 默认 **1.0** ⇒ `g.ed_eta = 1.0` ⇒ `η·Δed` = `Δed` ⇒ **逐字等价** ✓')
print('     * `--ed-eta 0.375` ⇒ 弹性罚能折减到 37.5% ⇒ 预期 `df(Ms) ≥ η|ed| + 2γ/t`')
print('     * 下一步：给 `_t5_short.py` 加透传，然后跑两臂对照')
