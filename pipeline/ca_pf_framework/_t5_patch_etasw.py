#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_etasw.py --- 给 `_t5_short.py` 加 `--ed-eta` 透传（**默认 1.0 ⇒ 不产生参数**）"""
import hashlib
import os
import shutil
import sys

P = '_t5_short.py'
BAK = P + '.bak_etasw'
src = open(P, encoding='utf-8').read()
print('  改前 sha256 = %s…（%d 字节）' % (hashlib.sha256(src.encode()).hexdigest()[:16], len(src)))

OLD = """            (['--burst-km', str(int(getattr(a, 'burst_km', 0) or 0))]
             if int(getattr(a, 'burst_km', 0) or 0) != 0 else []) + \\"""
NEW = OLD + """
            # ★★★★★★ s290（**修法 A：弹性罚能折减因子 η**，物理对应**塑性弛豫 / TRIP**）
            #   见 `windowB_surface.py` 的 `dG_cell` 与 `_bk_exp.py` 的 `g.ed_eta` 注释。
            #   `η = 1.0`（**默认**）⇒ **不产生参数** ⇒ 归档与在跑的臂**逐字不变** ✓
            (['--ed-eta', repr(float(getattr(a, 'ed_eta', 1.0) or 1.0))]
             if float(getattr(a, 'ed_eta', 1.0) or 1.0) != 1.0 else []) + \\"""
n = src.count(OLD)
print('  锚点出现次数 = %d（应为 1）' % n)
if n != 1:
    print('  ❌ 锚点不唯一 ⇒ 拒绝修改'); sys.exit(1)
out = src.replace(OLD, NEW, 1)

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
       "                    help='★ s290：透传 `--ed-eta`（弹性罚能折减因子 η，塑性弛豫/TRIP）；'\n"
       "                         '默认 1.0 ⇒ 不传任何参数，归档逐字不变；理论标定 η≈0.375')\n")
out = out[:j + 1] + ADD + out[j + 1:]

try:
    compile(out, P, 'exec')
    print('  ✅ 改后语法 OK')
except SyntaxError as e:
    print('  ❌ 语法错误：%s ⇒ 拒绝写盘' % e); sys.exit(1)
for need in ("getattr(a, 'ed_eta', 1.0)", "'--ed-eta', type=float"):
    if need not in out:
        print('  ❌ 校验失败（缺 %r）⇒ 拒绝写盘' % need); sys.exit(1)
if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
    print('  已备份 → %s' % BAK)
open(P, 'w', encoding='utf-8').write(out)
print('  ✅ 已写盘（sha256 %s…，%d 字节）'
      % (hashlib.sha256(out.encode()).hexdigest()[:16], len(out)))
print('  ── 复核 ──')
print('     * 默认 1.0 ⇒ 条件为假 ⇒ **不产生参数** ⇒ 逐字不变 ✓')
print('     * `--ed-eta 0.375` ⇒ 传 `--ed-eta 0.375` 给引擎 ✓')
