#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_gcheck.py --- ★★★★★ 复查 B/C 两项（**我怀疑我上次把轴标签写反了**）

## 上次（§234/§237）我的复算脚本里写的是：
```python
for name, th in (('沿 w（θ=0，_ca=1,_sw=0）', 0.0), ...):
    ca, sw = np.cos(th), np.sin(th)
```
**⇒ θ=0 时 `ca=cos0=1` ⇒ 那是"`a` 分量最大"的方向 ⇒ **本来就是沿 `a`**，
   而我**把它标成了"沿 w"** ⇒ **标签写反了** ⇒ **据反了的标签得出"约定反了"的结论。**

## 本次复算（**标签写对**）
`_g = _B / sqrt(_B²·_ca² + _sw²)`，`_B = 1/mob_ratio`
* `_ca = u·â`（与长轴的夹角余弦）· `_sw = u·ŵ`（与宽轴的夹角余弦）
⇒ **要回答的是：`h(a)/h(w)` 等于多少？期望 = `mob_ratio` = 9。**
"""
import numpy as np

for ratio in (9.0,):
    B = 1.0 / ratio
    print('=' * 84)
    print('★ 复算 `_g`：mob_ratio = %.1f ⇒ _B = %.4f' % (ratio, B))
    print('=' * 84)
    print('  %-34s %-10s %s' % ('方向（**标签已核对**）', '_ca, _sw', '_g'))
    for name, ca, sw in (('沿 â（长轴, _ca=1, _sw=0）', 1.0, 0.0),
                         ('45°（_ca=_sw=1/√2）', 1/np.sqrt(2), 1/np.sqrt(2)),
                         ('沿 ŵ（宽轴, _ca=0, _sw=1）', 0.0, 1.0)):
        g = B / np.sqrt(B * B * ca * ca + sw * sw)
        print('  %-34s %-10s **%.4f**' % (name, '%.2f,%.2f' % (ca, sw), g))
    ga = B / np.sqrt(B * B * 1.0 + 0.0)     # 沿 a
    gw = B / np.sqrt(0.0 + 1.0)             # 沿 w
    print()
    print('  ⇒ 沿 â = **%.4f**（**全速**）· 沿 ŵ = **%.4f**（慢 %.0f 倍）'
          % (ga, gw, ga / gw))
    print('  ⇒ **h(a)/h(w) = %.2f**  ⇒ 设计意图 = mob_ratio = **%.1f** ⇒ **%s**'
          % (ga / gw, ratio, '✅ 一致（**我上次说"反了"是错的**）'
             if abs(ga / gw - ratio) < 0.5 else '❌ 不一致'))
print()
print('=' * 84)
print('★ 那为什么 `ellipse` 与默认 `exp2` **测不出差别**？（这才是真问题）')
print('=' * 84)
for bw in (2.3,):
    print('  默认 exp2 形式的面内项：exp(−β_w·(_sw)²)   （`--beta-w` 默认 = %.1f）' % bw)
    print('    沿 â（_sw=0）⇒ exp(0)      = **%.4f**' % np.exp(0))
    print('    沿 ŵ（_sw=1）⇒ exp(−β_w)  = **%.4f**' % np.exp(-bw))
    print('    ⇒ h(a)/h(w) = **%.2f**' % (np.exp(0) / np.exp(-bw)))
    print()
    print('  而 ellipse（ratio=9）沿 ŵ = **%.4f**' % (1 / 9))
    print('  ⇒ **两者之比 = %.3f ⇒ 只差 %.0f%%**'
          % ((1/9) / np.exp(-bw), abs((1/9) / np.exp(-bw) - 1) * 100))
    print()
    print('  ⇒ ⇒ ★★★★★ **最可能的真相**：默认 `exp2`（β_w=%.1f）**本来就已经**给出了'
          % bw)
    print('     约 **%.0f:1** 的面内各向异性 ⇒ 换成 `ellipse`(9:1) **几乎是同一条曲线**' % (np.exp(bw)))
    print('     ⇒ **所以测不出差别是"两个开关本来就等价"，不是"ellipse 是空开关"**')
