#!/usr/bin/env python3
"""检查溶质总量的守恒精度，并列出晶粒消失事件处的跳变"""
import sys
import csv

path = sys.argv[1] if len(sys.argv) > 1 else "phase0a_out.csv"

rows = []
with open(path) as f:
    for r in csv.DictReader(f):
        rows.append(r)

if not rows:
    sys.exit("CSV 为空")

t = [float(r["time"]) for r in rows]
M = [float(r["total_solute"]) for r in rows]
n = [float(r["grain_tracker"]) for r in rows]

M0 = M[0]
print(f"读入 {len(rows)} 行，t = {t[0]:g} → {t[-1]:g}")
print(f"晶粒数：{n[0]:.0f} → {n[-1]:.0f}")
print()
print("=" * 72)
print("溶质总量守恒性")
print("=" * 72)
print(f"  初始  M0 = {M0:.17g}")
print(f"  最终  M  = {M[-1]:.17g}")
print(f"  绝对变化 ΔM = {M[-1] - M0:+.6e}")
print(f"  相对变化    = {(M[-1] - M0) / M0:+.6e}")
print()

d = [(m - M0) / M0 for m in M]
worst = max(range(len(d)), key=lambda i: abs(d[i]))
print(f"  最大相对漂移 = {d[worst]:+.6e}  @ t = {t[worst]:g}")
print()

# 晶粒消失事件
events = []
for i in range(1, len(n)):
    if n[i] < n[i - 1]:
        events.append((i, t[i], n[i - 1], n[i], M[i] - M[i - 1]))

print("=" * 72)
print(f"晶粒消失事件：{len(events)} 次")
print("=" * 72)
if events:
    print(f"{'#':>3} {'时间':>8} {'晶粒数':>10} {'该步 ΔM':>18} {'相对跳变':>14}")
    print("-" * 72)
    for k, (i, ti, n0, n1, dm) in enumerate(events, 1):
        print(f"{k:>3} {ti:>8g} {n0:>4.0f} → {n1:<4.0f} {dm:>+18.6e} {dm/M0:>+14.3e}")
    print("-" * 72)
    jumps = [abs(e[4]) for e in events]
    print(f"  跳变绝对值最大 = {max(jumps):.6e}")
    print(f"  跳变相对值最大 = {max(jumps)/abs(M0):.3e}")
else:
    print("  没有检测到晶粒消失事件")

print()
print("=" * 72)
print("判读")
print("=" * 72)
mx = max(abs(x) for x in d)
if mx < 1e-13:
    print(f"  ✅ 质量守恒到机器精度（最大相对漂移 {mx:.2e}）")
    print("     → 相场 + GrainTracker 路线上，晶粒消失不破坏溶质守恒")
    print("     → 因为网格固定、swapSolutionValues 只交换序参量、不碰浓度场")
elif mx < 1e-6:
    print(f"  ⚠️  质量有微小漂移（{mx:.2e}），属数值误差量级")
else:
    print(f"  ❗ 质量显著漂移（{mx:.2e}），需要进一步排查")
