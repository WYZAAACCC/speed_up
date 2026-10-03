#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_mob.py --- 给 `_t5_short.py` 加 4 个**迁移率各向异性**透传

## 为什么（本 goal 的核心）
**§230 查明：伸长机制**已经在框架里**，只差一个开关**：
```
windowB_surface.py:4668
  elif mob_beta > 0.0 and nd_ref_ is not None and mob_iform == 'ellipse':
```
* **`mob_beta = a.beta_h`**（= `--beta-h`，abA 基线 **6.477 > 0**）⇒ **闸门本来就开**；
* **只差 `mob_iform == 'ellipse'`**（默认 `'exp2'` ⇒ 走不到那段）；
* **代码注释**：「椭圆面内极曲线（凸）⇒ `h(a)/h(w)` **恰好等于设计比**（实测 ratio=9 给 **8.93**）」；
* **而"解析 9.90 vs 引擎实际 1.24"那个老问题是 `exp2` 形式的** —— `ellipse` 正是为修它而实现的。

## 安全（沿用 §122/§213 验证过的模式）
备份 → 内存里改 → **`compile()` 通过才写盘** → 复核；
**四个都带"默认档不传"的守卫 ⇒ 归档路径与在跑的臂逐字不变。**
"""
import shutil
import sys

P = '_t5_short.py'
BAK = P + '.bak_mob'
shutil.copy(P, BAK)
src = open(P, encoding='utf-8').read()
print('  已备份到 %s' % BAK)

# ── ① argparse ──
anchor1 = "    ap.add_argument('--eng-elong', type=float, default=0.0,"
add1 = (
    "    # ★★★★★ R581-T5R-s230：**迁移率各向异性**（= 生长阶段的伸长机制）的透传\n"
    "    #   `--mob-iform ellipse` 是关键那一个：它把面内极曲线取成**椭圆**\n"
    "    #   ⇒ 极集本身凸 ⇒ 凸化恒等 ⇒ `h(a)/h(w)` **恰等于** `--mob-ratio`\n"
    "    #   （代码实测 ratio=9 给 **8.93**）。默认 `exp2` 走不到那条分支。\n"
    "    ap.add_argument('--mob-iform', choices=['exp2', 'ellipse'], default='exp2',\n"
    "                    help='面内迁移率角函数：exp2=默认（实测各向异性只 1.24）；'\n"
    "                         'ellipse=椭圆（实测 8.93）')\n"
    "    ap.add_argument('--mob-ratio', type=float, default=9.0,\n"
    "                    help='椭圆面内极曲线长短轴比（= 目标长径比）')\n"
    "    ap.add_argument('--mob-wulff', action='store_true', help='Wulff 凸化速度律（刻面机制）')\n"
    "    ap.add_argument('--mob-dip', type=float, default=0.0,\n"
    "                    help='惯习面内 45 度方向的迁移率凹陷强度（c=4 时 h(a)/h(w)=9.73）')\n")
if anchor1 in src:
    src = src.replace(anchor1, add1 + anchor1, 1)
    print('  ① argparse 四个参数已插入')
else:
    print('  ① ⚠ 锚点没找到 ⇒ 中止'); sys.exit(1)

# ── ② build()：并入已有的 `+` 链 ──
anchor2 = "            (['--facet-proj', str(int(a.facet_proj))]"
add2 = (
    "            # ★★★★★ s230：迁移率各向异性（**默认档不传** ⇒ 归档/在跑的臂逐字不变）\n"
    "            (['--mob-iform', str(a.mob_iform)]\n"
    "             if str(getattr(a, 'mob_iform', 'exp2')) != 'exp2' else []) +\n"
    "            (['--mob-ratio', repr(float(a.mob_ratio))]\n"
    "             if str(getattr(a, 'mob_iform', 'exp2')) != 'exp2' else []) +\n"
    "            (['--mob-wulff'] if bool(getattr(a, 'mob_wulff', False)) else []) +\n"
    "            (['--mob-dip', repr(float(a.mob_dip))]\n"
    "             if float(getattr(a, 'mob_dip', 0.0) or 0.0) > 0 else []) +\n")
if anchor2 in src:
    src = src.replace(anchor2, add2 + anchor2, 1)
    print('  ② build() 的条件项已并入原 `+` 链')
else:
    print('  ② ⚠ 锚点没找到 ⇒ 中止'); sys.exit(1)

# ── ③ 编译通过才写盘 ──
try:
    compile(src, P, 'exec')
    print('  ③ ★ 内存编译通过 ⇒ 写盘')
except SyntaxError as e:
    print('  ③ ❌ 编译失败（不写盘）：%s' % e); sys.exit(1)
open(P, 'w', encoding='utf-8').write(src)

# ── ④ 复核 ──
import py_compile
s2 = open(P, encoding='utf-8').read()
ok = True
try:
    py_compile.compile(P, doraise=True); print('\n    ① py_compile ⇒ ✅')
except Exception as e:
    print('\n    ① py_compile ⇒ ❌ %s' % e); ok = False
for nm, pat, want in (('mob-iform 定义', "add_argument('--mob-iform'", 1),
                      ('mob-ratio 定义', "add_argument('--mob-ratio'", 1),
                      ('mob-wulff 定义', "add_argument('--mob-wulff'", 1),
                      ('mob-dip 定义', "add_argument('--mob-dip'", 1),
                      ('mob-iform 透传', "['--mob-iform', str(a.mob_iform)]", 1),
                      ('mob-wulff 透传', "['--mob-wulff'] if bool(", 1)):
    n = s2.count(pat)
    print('    ② %-16s 出现 %d 次 ⇒ %s' % (nm, n, '✅' if n == want else '❌'))
    ok &= (n == want)
print('    ③ "默认档不传"守卫 = %s' % ('✅' if "!= 'exp2' else []" in s2 else '❌'))
print('\n  ⇒ **%s**' % ('全部通过' if ok else '有未过项（备份在 %s）' % BAK))
sys.exit(0 if ok else 1)
