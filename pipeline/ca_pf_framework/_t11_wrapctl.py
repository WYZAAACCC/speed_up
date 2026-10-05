#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_wrapctl.py —— ②-8 绕盒守卫的**正/负对照**（掩模级，含"负对照有分辨力"断言）。

上一版失败原因（已记）：
  * `check_wrap()` 不接受 `verbose`（真实签名 `check_wrap(k=None, strict=None, tag='')`）；
  * 我构造的 SDF 没让 `region()` 认出来 ⇒ 两个对照都报 0 胞 ⇒ **负对照无分辨力，量具无效**。

本版做法：`wrap_axes` 只读 `self.region()`（`:3371-3372`，掩模的纯函数）
⇒ **直接猴子补丁 `region()`** 注入三类掩模，判据：
  A 正对照「沿 x 贯通全盒」      ⇒ 必须报轴 0
  B 正对照「沿 y 贯通、x 不贯通」 ⇒ 必须报轴 1 且**不**报轴 0
  C 负对照（生产参数）「4 µm 板条居中在 10 µm 盒里」 ⇒ 必须**不报任何轴**
  D 边界对照「只贴一面（不贯通）」 ⇒ 必须**不报**（贴面 ≠ 绕盒）
断言：A/B/C/D 结论**互不相同** ⇒ 量具有分辨力；否则判量具失效。
"""
import sys

import numpy as np

sys.path.insert(0, ".")
import windowB_surface as WS  # noqa: E402

N, DX = 160, 62.5e-9
L = N * DX
print(f"=== 生产参数 N={N} dx={DX*1e9:.1f} nm ⇒ L={L*1e6:.3f} µm ===")

g = WS.LevelSetMulti(N, L, nv=2, gamma=0.0, Mob=1.0)
xx = (np.arange(N) + 0.5) * DX
X, Y, Z = np.meshgrid(xx, xx, xx, indexing="ij")


def slab(axis, half_len, ctr=None, half_w=8.0 * DX, half_t=3.0 * DX):
    """沿 `axis` 的板条掩模；`half_len=L/2-0.4dx` 时两端贴面（贯通）。"""
    c = [L / 2, L / 2, L / 2] if ctr is None else ctr
    d = [np.abs(X - c[0]), np.abs(Y - c[1]), np.abs(Z - c[2])]
    ok = np.ones(X.shape, bool)
    for ax in range(3):
        h = half_len if ax == axis else (half_w if (ax - axis) % 3 == 1 else half_t)
        ok &= d[ax] <= h
    return ok


cases = {
    "A 正:沿x贯通全盒": slab(0, L / 2 - 0.4 * DX),
    "B 正:沿y贯通,x不贯通": slab(1, L / 2 - 0.4 * DX),
    "C 负:4µm板条居中(x)": slab(0, 2.0e-6),
    "D 边界:只贴x=−面(不贯通)": slab(0, 2.0e-6, ctr=[0.0, L / 2, L / 2]),
}

res = {}
for name, m in cases.items():
    # 猴子补丁：把 region() 换成"该掩模即变体 1"
    g.region = (lambda mm: (lambda: (mm.astype(np.int8) * 1)))(m)
    ncell = int(m.sum())
    wa = g.wrap_axes(1)
    waa = g.wrap_axes_any()
    ext, w2 = g.region_extent(1)
    res[name] = (wa, waa)
    print(f"\n  {name}: 胞数 {ncell}")
    print(f"    wrap_axes(k=1)  = {wa}")
    print(f"    wrap_axes_any() = {waa}")
    print(f"    region_extent   = {None if ext is None else np.round(ext*1e6,2)} µm, wrap={w2}")

print("\n" + "=" * 90)
a, b, c, d = (res["A 正:沿x贯通全盒"][0], res["B 正:沿y贯通,x不贯通"][0],
              res["C 负:4µm板条居中(x)"][0], res["D 边界:只贴x=−面(不贯通)"][0])
checks = [
    ("A: 报轴 0", a == [0]),
    ("B: 报轴 1 且不含轴 0", b == [1]),
    ("C: **不报任何轴**（负对照）", c == []),
    ("D: 不报（贴面 ≠ 绕盒）", d == []),
    ("★ 分辨力：A≠C", a != c),
    ("★ 分辨力：B≠A", b != a),
    ("★ 分辨力：B≠C", b != c),
]
for msg, ok in checks:
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")
print(f"\n结论：{'量具有效，守卫正确工作' if all(o for _, o in checks) else '**量具或守卫有问题，必须继续查**'}")
