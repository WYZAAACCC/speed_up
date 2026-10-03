#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_elong.py --- 给 `_t5_short.py` 加 `--eng-elong` 与 `--facet-proj` 两个透传

## 为什么
**§212 查明：长宽比小有三个缺口，其中两个是**传参**就能测的**：
* **`--eng-elong`**（核的拉长率；代码自己写明物理值是 **3.75**）；
* **`--facet-proj`**（棱面投影；**默认 0 ⇒ 一次都没跑过**）。

## 安全设计（**沿用 §122 验证过的模式**）
1. 备份 → 2. 内存里改 → 3. **`compile()` 通过才写盘** → 4. 写盘后四条复核。
**⚠ 两处都带"默认档不传"的守卫 ⇒ 归档路径/正在跑的臂**逐字不变**。**
"""
import shutil
import sys

P = '_t5_short.py'
BAK = P + '.bak_elong'
shutil.copy(P, BAK)
src = open(P, encoding='utf-8').read()
print('  已备份到 %s' % BAK)

# ── ① argparse：加两个参数（放在 `--var-rule` 定义之后）──
anchor1 = "    ap.add_argument('--nuc-fresh-every', type=int, default=0,"
add1 = (
    "    # ★★★★★ R581-T5R-s213：**两个「物理开关」的透传**（§212 查明它们影响长宽比）\n"
    "    #   `--eng-elong`：核的拉长率。**代码自己写明物理值 = 3.75**（驱动层 L/W=2400/640）；\n"
    "    #     默认 0 ⇒ 走 `use_engine` 回退 = plate_L/plate_W = 2.0。\n"
    "    #   `--facet-proj`：棱面投影。**引擎默认 0 ⇒ `facet_project()` 一次都没跑过** ⇒\n"
    "    #     界面不会自发形成平整宽面 ⇒ 形状偏圆（**这是本 A/B 要测的**）。\n"
    "    ap.add_argument('--eng-elong', type=float, default=0.0,\n"
    "                    help='核拉长率（0=引擎回退 plate_L/plate_W；3.75=代码写明的物理值）')\n"
    "    ap.add_argument('--facet-proj', type=int, default=0,\n"
    "                    help='棱面投影（0=引擎默认，从未跑过；1=打开）')\n")
if anchor1 in src:
    src = src.replace(anchor1, add1 + anchor1, 1)
    print('  ① argparse 两个参数已插入')
else:
    print('  ① ⚠ 锚点没找到 ⇒ **中止**（不写盘）'); sys.exit(1)

# ── ② build()：并入**已有的 `+` 链**（不是新开 `] +`，s112 的教训）──
anchor2 = "            (['--var-rule', str(getattr(a, 'var_rule', 'ed'))]"
add2 = (
    "            # ★★★★★ R581-T5R-s213：两个物理开关（**默认档不传** ⇒ 归档/在跑的臂逐字不变）\n"
    "            (['--eng-elong', repr(float(a.eng_elong))]\n"
    "             if float(getattr(a, 'eng_elong', 0.0) or 0.0) > 0 else []) +\n"
    "            (['--facet-proj', str(int(a.facet_proj))]\n"
    "             if int(getattr(a, 'facet_proj', 0) or 0) != 0 else []) +\n")
if anchor2 in src:
    src = src.replace(anchor2, add2 + anchor2, 1)
    print('  ② build() 的条件项已并入原 `+` 链')
else:
    print('  ② ⚠ 锚点没找到 ⇒ **中止**（不写盘）'); sys.exit(1)

# ── ③ 先编译，通过才写盘 ──
try:
    compile(src, P, 'exec')
    print('  ③ ★ 内存编译通过 ⇒ 写盘')
except SyntaxError as e:
    print('  ③ ❌ 编译失败（**不写盘**）：%s' % e); sys.exit(1)
open(P, 'w', encoding='utf-8').write(src)

# ── ④ 写盘后四条复核 ──
import py_compile
s2 = open(P, encoding='utf-8').read()
print()
print('  ── 复核（五条判据）──')
ok = True
try:
    py_compile.compile(P, doraise=True); print('    ① py_compile ⇒ ✅')
except Exception as e:
    print('    ① py_compile ⇒ ❌ %s' % e); ok = False
for nm, pat, want in (('eng-elong 透传', "['--eng-elong', repr(float(a.eng_elong))]", 1),
                      ('facet-proj 透传', "['--facet-proj', str(int(a.facet_proj))]", 1),
                      ('eng-elong 定义', "add_argument('--eng-elong'", 1),
                      ('facet-proj 定义', "add_argument('--facet-proj'", 1)):
    n = s2.count(pat)
    print('    ② %-16s 出现 %d 次 ⇒ %s' % (nm, n, '✅' if n == want else '❌'))
    ok &= (n == want)
bad = "elif" in s2.split('def build')[1][:200] if 'def build' in s2 else False
print('    ③ 默认档"不传"的两个守卫 = %s ⇒ %s'
      % (('a.eng_elong', 'a.facet_proj'),
         '✅' if ("or 0.0) > 0 else []" in s2 and "or 0) != 0 else []" in s2) else '❌'))
print()
print('  ⇒ **%s**' % ('全部通过' if ok else '有未过项（备份在 %s）' % BAK))
sys.exit(0 if ok else 1)
