#!/usr/bin/env python3
"""
第二档（2a/2b）的物理单元测试 —— 不依赖 MOOSE，直接校验 extract.py 里的解析式。

为什么要单独测：2b 要求"用实际温度场的解析导数，不是几何近似"，
而解析求导最容易写错符号。这里用**数值微分**独立核对，
再用**手算的四重对称性质**核对对齐度。

运行： python3 test_tier2_physics.py
"""

import math
import sys

from extract import align4_deg, misorientation_deg, rosenthal_grad

FAIL = []


def check(name, ok, detail=""):
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


# 与算例 [Functions]/laser_T 完全相同的温度场
def T_field(x, y, t):
    C = 28.0 / (2.0 * math.pi * 20.0)
    k = 0.6 / (2.0 * 6.0e-6)
    xi = x + 1.2e-4 - 0.6 * t
    R = math.sqrt(xi * xi + y * y + 1e-10)
    return 353.0 + C / R * math.exp(-k * (R + xi))


print("=" * 70)
print("1. rosenthal_grad 解析导数 vs 数值微分")
print("=" * 70)
# 在熔池附近与远处各取几个点；熔池中心 R->0 处场本身奇异，避开
pts = [(-1.0e-4, 3.0e-5), (-6.0e-5, 7.5e-5), (-1.4e-4, 2.0e-5),
       (0.0, 1.0e-4), (1.0e-4, 5.0e-5), (-2.0e-4, 1.2e-4)]
times = (0.0, 2.0e-4, 6.0e-4)

# 【度量说明】不能用"逐点相对误差"。
# 解析式里 gx 在激光后方 xi = -k*R^2/(1+k*R) ~ -8.3e-5 处**过零**，
# 落在零点附近的点即使绝对误差极小，相对误差也会爆掉（首次实现就踩了这个坑，
# 报出 1.1e-3 的假警报）。正确做法是用**全局梯度尺度**归一化。
h = 1e-9                              # 相对 1e-4 的尺度足够小，又不至于丢精度
num, ana, worst_pt, worst = {}, {}, None, 0.0
for t in times:
    for (x, y) in pts:
        ana[(x, y, t)] = rosenthal_grad(x, y, t)
        num[(x, y, t)] = (
            (T_field(x + h, y, t) - T_field(x - h, y, t)) / (2 * h),
            (T_field(x, y + h, t) - T_field(x, y - h, t)) / (2 * h))
gscale = max(max(abs(v) for v in num[k]) for k in num)
for k in num:
    for c in (0, 1):
        e = abs(ana[k][c] - num[k][c]) / gscale
        if e > worst:
            worst, worst_pt = e, (k, "xy"[c])
check("解析梯度与数值微分一致（按全局梯度尺度归一，偏差 < 1e-6）",
      worst < 1e-6, f"实测 {worst:.3e} @ {worst_pt}")
print(f"        全局梯度尺度 max|grad T| = {gscale:.6g} K/m")

print()
print("=" * 70)
print("2. align4 的四重对称性质（beta-Ti <100> 在 2D 是四重对称）")
print("=" * 70)
# 梯度沿 +y（phi = 90 度）
gx, gy = rosenthal_grad(-1.0e-4, 1.0e-4, 0.0)   # 只为拿一个方向，下面直接给方向
def align_of(theta, phi):
    """直接按方向角构造，避免依赖具体梯度值。"""
    gx, gy = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    return align4_deg(theta, gx, gy)

check("theta=0 与梯度沿 y（易生长轴 {0,90} 含 90）-> 1",
      abs(align_of(0, 90) - 1.0) < 1e-12, f"{align_of(0,90):.12f}")
check("theta=45 与梯度沿 y（错配最大）-> 0",
      abs(align_of(45, 90) - 0.0) < 1e-12, f"{align_of(45,90):.3e}")
check("theta=30 与梯度沿 30 度 -> 1",
      abs(align_of(30, 30) - 1.0) < 1e-12, f"{align_of(30,30):.12f}")
check("theta=30 与梯度沿 120 度 -> 1（易生长轴是 {30,120}）",
      abs(align_of(30, 120) - 1.0) < 1e-12, f"{align_of(30,120):.12f}")
worst4 = max(abs(align_of(th, 70.0) - align_of(th + 90.0, 70.0))
             for th in range(0, 90, 7))
check("四重对称：align(theta) == align(theta+90)", worst4 < 1e-12,
      f"最大差 {worst4:.3e}")
worst2 = max(abs(align_of(th, 70.0) - align_of(th + 45.0, 70.0))
             for th in range(0, 90, 7))
check("**非**二重对称：align(theta) != align(theta+45)（若相等说明写成了二重）",
      worst2 > 0.1, f"最大差 {worst2:.3f}")

print()
print("=" * 70)
print("3. misorientation_deg 的四重折叠")
print("=" * 70)
check("(0, 20) -> 20", abs(misorientation_deg(0, 20) - 20) < 1e-12,
      f"{misorientation_deg(0,20):.6f}")
check("(0, 70) -> 20（70 折叠到 20）", abs(misorientation_deg(0, 70) - 20) < 1e-12,
      f"{misorientation_deg(0,70):.6f}")
check("(0, 45) -> 45（最大取向差）", abs(misorientation_deg(0, 45) - 45) < 1e-12,
      f"{misorientation_deg(0,45):.6f}")
check("(0, 89) -> 1", abs(misorientation_deg(0, 89) - 1) < 1e-12,
      f"{misorientation_deg(0,89):.6f}")
check("取值落在 [0, 45]",
      all(0 <= misorientation_deg(a, b) <= 45
          for a in range(0, 90, 3) for b in range(0, 90, 3)))

print()
print("=" * 70)
print("4. 交叉一致性：align4 与 misorientation 的物理自洽")
print("=" * 70)
# 梯度沿 0 度时，晶粒 theta 与梯度方向的"夹角"应等于 misorientation(theta, 0)
# （四重对称下两者是同一个几何量），故 align4(theta, phi=0) 应等于 cos^2(2*Delta)
bad = 0
for th in range(0, 90, 5):
    d = misorientation_deg(th, 0.0)
    want = math.cos(math.radians(2.0 * d)) ** 2
    got = align_of(th, 0.0)
    if abs(got - want) > 1e-12:
        bad += 1
check("align4(theta, phi=0) == cos^2(2*misorientation(theta,0))", bad == 0,
      f"{bad} 个不符")

print()
print("=" * 70)
if FAIL:
    print(f"失败 {len(FAIL)} 项：{FAIL}")
    sys.exit(1)
print("全部通过")
