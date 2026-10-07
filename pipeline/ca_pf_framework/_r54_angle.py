#!/usr/bin/env python3
"""R54: **角分布算术** —— 为什么 `v_a/v_w` 只有 1.24 而不是设计给的 8.98。

## 已知（同口径实测）
* 单根**孤立**板条（`dry_single`，N=64、Δx=62.5、无邻居）：
  `d(a)` = **+1.189**、`d(w)` = **+0.956**、`d(n)` = +0.042 nm/步
  ⇒ **`v_a/v_w` = 1.24**（**与多板条臂的 1.24 完全相同 ⇒ 不是邻居/盒子造成的**）
* 同算例的面胞平均速度：`<|v|>_tip·dt` = 1.07、`<|v|>_side·dt` = **0.18**
  ⇒ **`d(w)` 是 `v_side` 的 5.3 倍** ⇒ **宽度不是靠"侧面"长出来的！**

## 本脚本要算的
`M(n)/M0 = exp(−β_h·(n·n*)² − β_w·(n·w)²)`
在 `a–w` 平面内按角度扫一遍，看**斜法向的迁移率有多高** ——
若 45° 附近的 `M` 仍有 30%，则"角胞"会主导形状演化，把 `a/w` 各向异性拉平。
"""
import math

B_H, B_W = 6.477, 2.3
# 变体 1 的坐标（与 `_r54_single` 同一构型）
#   a·n* = −0.127（R30 实测）; w·n* = 0; a·w = 0
A_DOT_N = -0.127


def mrel(theta_deg):
    """法向 `n = cosθ·a + sinθ·w` 的 M/M0。θ=0 ⇒ 端面法向；θ=90° ⇒ 侧面法向。"""
    t = math.radians(theta_deg)
    n_dot_n = math.cos(t) * A_DOT_N            # + sinθ·(w·n*) = 0
    n_dot_w = math.sin(t)
    return math.exp(-B_H * n_dot_n ** 2 - B_W * n_dot_w ** 2)


print('法向 = cosθ·a + sinθ·w   （θ=0: 端面   θ=90°: 侧面）')
print('  %-8s %-12s %-12s %s' % ('θ (deg)', 'M/M0', '相对端面', '相对侧面'))
m0 = mrel(0.0)
m90 = mrel(90.0)
for th in (0, 5, 10, 15, 20, 25, 30, 45, 60, 75, 90):
    m = mrel(th)
    print('  %-8d %-12.4f %-12.4f %.2f' % (th, m, m / m0, m / m90))
print()
print('★ 设计意图：`β_h`（6.477）把**厚度方向**钉死、`β_w`（2.3）把**侧面**压住。')
print('  但实测：θ=45° 处 `M/M0` = **%.3f** ⇒ 相对侧面仍有 **%.1f 倍**；'
      % (mrel(45), mrel(45) / m90))
print('  θ=30° 处 **%.3f**（相对侧面 %.1f 倍）' % (mrel(30), mrel(30) / m90))
print()
print('=== 沿 a 与沿 w 的"有效速度"（角平均的粗略估计）')
# 端面锥 |θ|<25° 推 a；侧面锥 |θ-90°|<25° 推 w；其余（斜）**同时**推 a 与 w
import numpy as np
th = np.linspace(0, 90, 901)
m = np.array([mrel(t) for t in th])
c = np.cos(np.radians(th)); s = np.sin(np.radians(th))
# 归一化驱动取 1（只看 M 的角分布形状）
v = m
print('  所有法向的 `M` 对 `a` 的贡献 <M·|cosθ|> = %.4f' % float(np.trapezoid(v * np.abs(c), th) / 90))
print('  所有法向的 `M` 对 `w` 的贡献 <M·|sinθ|> = %.4f' % float(np.trapezoid(v * np.abs(s), th) / 90))
ra = float(np.trapezoid(v * np.abs(c), th))
rw = float(np.trapezoid(v * np.abs(s), th))
print('  ⇒ **角平均的 a/w 各向异性 ≈ %.2f**（实测 1.24）' % (ra / rw))
print()
print('★ 结论方向：要让 `a/w` 上去，**必须压 θ 在 20°–70° 的"斜法向"**')
print('  ⇒ 要动的是 **`β_w`（甚至角函数的形状）**，不是 `β_h`。')
print('  试算：把 `β_w` 从 2.3 提到 X，看角平均各向异性怎么变：')
print('  %-8s %-14s %s' % ('β_w', '角平均 a/w', 'θ=45° 的 M/M0'))
for bw in (2.3, 4.0, 6.0, 8.0, 12.0):
    mm = np.array([math.exp(-B_H * (math.cos(math.radians(t)) * A_DOT_N) ** 2
                            - bw * math.sin(math.radians(t)) ** 2) for t in th])
    ra2 = float(np.trapezoid(mm * np.abs(c), th))
    rw2 = float(np.trapezoid(mm * np.abs(s), th))
    m45 = math.exp(-B_H * (math.cos(math.radians(45)) * A_DOT_N) ** 2
                   - bw * math.sin(math.radians(45)) ** 2)
    print('  %-8.1f %-14.2f %.4f' % (bw, ra2 / rw2, m45))
