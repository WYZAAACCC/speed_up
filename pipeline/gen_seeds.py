#!/usr/bin/env python3
"""
生成多分散的 Voronoi 晶粒中心文件。

【为什么需要】
  等尺寸的晶粒结构要粗化很久才会出现"晶粒消失"事件
  （60 晶粒跑 150 时间单位，一个都没掉）。而含偏析的 CH 系统很贵
  （28 秒/步），等不起自然粗化。

  办法：故意塞一些明显偏小的晶粒进去，它们会在最初几百个时间单位内消失，
  从而在低成本区间内产生足够多的拓扑事件。

【约束】
  小晶粒不能小于晶界宽度（wGB=14），否则弥散界面表示不出来。
  这里把小晶粒控制在半径 ~22（直径 ~45，约 3× wGB）。

输出格式（MOOSE PolycrystalVoronoi 的 file_name 要求）：
    第一行表头 x y
    之后每行一个晶粒中心
"""
import sys
import numpy as np

L = 1000.0          # 域尺寸
N_BASE = 45         # 常规晶粒数
N_SMALL = 15        # 额外插入的小晶粒数
D_MIN = 90.0        # 常规晶粒之间的最小间距
SMALL_OFFSET = 60.0 # 小晶粒与其搭档的距离（决定小晶粒大小）
                    # 45 时等效直径仅 22（1.6× 晶界宽度），太接近表示极限；
                    # 60 给出 ~30（2.1×），更稳
OUT = sys.argv[1] if len(sys.argv) > 1 else "seeds_poly.txt"
# 第二个参数是随机种子 —— 生产多组数据时用不同的种子得到独立的初始结构
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 42

rng = np.random.default_rng(SEED)

# ---- 1. 生成互相分得开的基底点 ----
base = []
attempts = 0
while len(base) < N_BASE and attempts < 200000:
    attempts += 1
    p = rng.uniform(0, L, 2)
    if all(np.hypot(*(p - q)) > D_MIN for q in base):
        base.append(p)

if len(base) < N_BASE:
    sys.exit(f"只放得下 {len(base)} 个基底点，请调小 D_MIN 或 N_BASE")

base = np.array(base)

# ---- 2. 选一部分基底点，在它旁边放一个小晶粒 ----
# 用周期性距离评价，避免在边界附近造出奇怪形状
def pdist(a, b):
    d = np.abs(a - b)
    d = np.minimum(d, L - d)     # 周期性
    return np.hypot(*d)

idx = rng.choice(N_BASE, size=min(N_SMALL, N_BASE), replace=False)
small = []
for i in idx:
    for _ in range(200):
        ang = rng.uniform(0, 2 * np.pi)
        p = (base[i] + SMALL_OFFSET * np.array([np.cos(ang), np.sin(ang)])) % L
        # 不能和别的点靠太近（除了它的搭档）
        ok = True
        for j, q in enumerate(base):
            if j == i:
                continue
            if pdist(p, q) < SMALL_OFFSET * 1.1:
                ok = False
                break
        if ok:
            for q in small:
                if pdist(p, q) < SMALL_OFFSET * 1.1:
                    ok = False
                    break
        if ok:
            small.append(p)
            break

small = np.array(small) if small else np.zeros((0, 2))
pts = np.vstack([base, small])

# ---- 3. 写出 ----
with open(OUT, "w") as f:
    f.write("x y\n")
    for p in pts:
        f.write(f"{p[0]:.6f} {p[1]:.6f}\n")

print(f"输出 {OUT}")
print(f"  常规晶粒 {len(base)} 个（间距 > {D_MIN:.0f}）")
print(f"  小晶粒   {len(small)} 个（距搭档 {SMALL_OFFSET:.0f}）")
print(f"  合计     {len(pts)} 个")
if len(small):
    # 估算小晶粒的等效直径
    print(f"  小晶粒的等效直径估计 ~{SMALL_OFFSET/2:.0f}"
          f"  （晶界宽度 14，比值 {SMALL_OFFSET/2/14:.1f}×）")
