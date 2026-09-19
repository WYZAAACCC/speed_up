#!/usr/bin/env python3
# =============================================================================
# T9 分析器 v2：拟合三条晶界直线，再算它们的交角
# =============================================================================
# 审计判据：「三叉角误差 ≤ 5°」（三个角都应接近 120°）
#
# 【为什么放弃第一版的"绕三叉点扫描"】
#   第一版以三叉点为中心、在半径 2~5 µm 的圆上找"占优晶粒切换"处。
#   实测**角度随时间剧烈抖动**（偏差在 5°~38° 之间乱跳），还常扫出 5 条边界。
#   两个根因：
#     ① `argmin(max η)` 找三叉点**不稳定** —— 晶粒内部 max η 处处接近 1，
#        峰值不尖锐，节点之间乱跳。（已换成 argmax(min η)，t=0 时能正确给出
#        144.7/105.9/109.4，与设计的 145/110/105 吻合。）
#     ② 更本质：三叉角定义在晶界的**切线**上，而圆上采样量到的是**弦**。
#        界面宽 2 µm、采样半径 2~5 µm，晶界在这个尺度上已经弯了。
#
# 【v2 的做法：直接拟合直线】
#   三晶粒、晶界能相等时，平衡构型就是**三条直线晶界交于一点、两两成 120°**。
#   所以：
#     1. 找出晶界节点：**第二大 η > 阈值**（晶界上两个 η 都 ≈0.5；
#        晶粒内第二大 η ≈0；三叉点处三个都 ≈0.38）
#     2. 按"哪两个 η 最大"分成三组
#     3. 每组做主成分分析（PCA）拟合一条直线 —— 方向 = 最大主特征向量
#     4. 三条直线的两两夹角就是三叉角
#
#   这对弯曲不敏感（拟合的是整体方向），也比数"切换次数"稳得多。
#
# 用法：
#   python3 analyze_t9.py <exo>               # 末态
#   python3 analyze_t9.py <exo> --times       # 随时间演化
# =============================================================================

import argparse
import math
import sys

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

HERE = "/mnt/f/speed_up/pipeline/validated"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from exodus_lite import read_exodus   # noqa: E402

PAIRS = [(0, 1), (0, 2), (1, 2)]


def find_junction(E):
    """三叉点 = min(η0,η1,η2) 最大的节点（三个晶粒最势均力敌处）。"""
    return int(np.argmax(E.min(axis=1)))


def gb_lines(x, y, E, thresh=0.30, margin=1.5):
    """
    拟合三条晶界直线。

    返回 {pair: (点, 方向单位向量, 点数)}，以及三叉点索引。

    margin: 拟合时只用离三叉点足够远的点（µm）。
            三叉点附近三个 η 混在一起，会把直线方向带偏。
    """
    j = find_junction(E)
    xj, yj = x[j], y[j]

    # 每个节点：最大的两个 η 是哪两个、第二大是多少
    order = np.argsort(E, axis=1)          # 升序
    second = E[np.arange(len(E)), order[:, -2]]
    is_gb = second > thresh

    # 排除三叉点附近的点
    dd = np.hypot(x - xj, y - yj)
    is_gb &= dd > margin

    res = {}
    for (a, b) in PAIRS:
        # 属于这一对的 GB 节点：a、b 是两个最大的
        top2 = np.sort(order[:, -2:], axis=1)
        sel = is_gb & (top2[:, 0] == min(a, b)) & (top2[:, 1] == max(a, b))
        n = int(sel.sum())
        if n < 10:
            continue
        P = np.column_stack([x[sel], y[sel]])
        c = P.mean(axis=0)
        # PCA
        Q = P - c
        _, _, Vt = np.linalg.svd(Q, full_matrices=False)
        d = Vt[0]
        # 方向规范化：让 x 分量为正（便于比较）
        if d[0] < 0:
            d = -d
        res[(a, b)] = (c, d, n)
    return res, j, (xj, yj)


def angles_between(lines):
    """三条直线的方向 -> 三个夹角（度），和为 360。"""
    ks = sorted(lines.keys())
    if len(ks) != 3:
        return None, None
    # 用方向角的"直线"表示（模 180）
    thetas = []
    for k in ks:
        _, d, _ = lines[k]
        th = math.degrees(math.atan2(d[1], d[0])) % 180.0
        thetas.append(th)
    thetas.sort()
    # 三条直线把平面分成 6 个扇区；三叉角是其中交替的三个
    gaps = []
    for i in range(3):
        a0 = thetas[i]
        a1 = thetas[(i + 1) % 3] if i < 2 else thetas[0] + 180.0
        gaps.append(a1 - a0)
    # gaps 是三个"半角"；三叉角 = 相邻两个半角之和
    angs = [gaps[i] + gaps[(i + 1) % 3] for i in range(3)]
    return angs, thetas


def measure(path, time_index):
    d = read_exodus(path, time_index=time_index)
    names = [n for n in ("gr0", "gr1", "gr2") if n in d["node_vars"]]
    if len(names) < 3:
        return None
    x = np.asarray(d["x"]) * 1e6
    y = np.asarray(d["y"]) * 1e6
    E = np.column_stack([np.asarray(d["node_vars"][n]) for n in names])
    lines, j, jp = gb_lines(x, y, E)
    angs, thetas = angles_between(lines)
    return dict(jp=jp, ev=E[j], s2=float((E[j] ** 2).sum()),
                lines=lines, angs=angs, thetas=thetas,
                npts={k: v[2] for k, v in lines.items()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exo")
    ap.add_argument("--times", action="store_true")
    ap.add_argument("--margin", type=float, default=1.5,
                    help="拟合时排除三叉点周围多少 µm")
    args = ap.parse_args()

    d0 = read_exodus(args.exo)
    n_t = len(d0["times"])

    if args.times:
        print("三叉角随时间的收敛（平衡目标 120° × 3）")
        print()
        print("  %-13s %-32s %-10s" % ("t (s)", "三个夹角", "最大偏差"))
        print("  " + "-" * 58)
        idxs = list(range(0, n_t, max(1, n_t // 12)))
        if n_t - 1 not in idxs:
            idxs.append(n_t - 1)
        for k in idxs:
            r = measure(args.exo, k)
            if r is None or r["angs"] is None:
                print("  %-13.4g （晶界组不足，跳过）" % d0["times"][k])
                continue
            a = sorted(r["angs"])
            worst = max(abs(v - 120.0) for v in a)
            print("  %-13.4g %-32s %7.2f°%s"
                  % (d0["times"][k], " ".join("%7.2f°" % v for v in a),
                     worst, "" if worst <= 5 else "  <- 超 5°"))
        return

    r = measure(args.exo, -1)
    if r is None:
        sys.exit("Exodus 里没有 gr0/gr1/gr2")
    print("末态 t = %.4g s" % d0["times"][-1])
    print("三叉点 (min(η) 最大处): (%.3f, %.3f) µm" % r["jp"])
    print("  η = [%.4f, %.4f, %.4f]   Ση² = %.4f   （三点等值时理论 3/7 = 0.4286）"
          % (r["ev"][0], r["ev"][1], r["ev"][2], r["s2"]))
    print()
    if r["angs"] is None:
        sys.exit("晶界分组不足（找到 %d 组）—— 阈值或三叉点可能不合适"
                 % len(r["lines"]))
    print("三条晶界（PCA 拟合）：")
    for k in sorted(r["lines"]):
        c, dv, n = r["lines"][k]
        print("  η%d|η%d : 过 (%.2f, %.2f)，方向 %.2f°，用了 %d 点"
              % (k[0], k[1], c[0], c[1],
                 math.degrees(math.atan2(dv[1], dv[0])) % 180.0, n))
    print()
    a = sorted(r["angs"])
    print("  %-6s %12s %14s" % ("夹角", "实测", "与 120° 的差"))
    print("  " + "-" * 36)
    worst = 0.0
    for i, v in enumerate(a, 1):
        e = abs(v - 120.0)
        worst = max(worst, e)
        print("  #%-5d %11.2f° %13.2f°   %s"
              % (i, v, e, "OK" if e <= 5 else "**超 5°**"))
    print()
    print("  最大偏差 = %.2f°   ⇒  %s"
          % (worst, "T9 三叉角判据 **通过**" if worst <= 5
             else "T9 三叉角判据 **未通过**"))


if __name__ == "__main__":
    main()
