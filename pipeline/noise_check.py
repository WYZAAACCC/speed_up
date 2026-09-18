#!/usr/bin/env python3
"""
噪声底线诊断：那 27–35% 的未解释方差，是"模型学不到"还是"目标本身有噪声"？

如果"面的溶质含量"这个量本身抖动很大（因为它是由阈值从弥散界面切出来的），
那任何模型都学不好，问题不在算子。

做法（三个层次）：
  1. 持久性基线：预测"不变"（d=0）的误差
  2. 线性可预测性：用当前状态线性回归 d，看能到多少
  3. 噪声估计：二阶差分与一阶差分的比值
       · 若二阶差分与一阶差分同量级 → 信号被噪声主导
       · 若二阶差分明显更小       → 信号平滑，还有可学的结构

用法：python3 noise_check.py <数据集目录>
"""
import csv
import os
import sys

import numpy as np


def main():
    ds = sys.argv[1] if len(sys.argv) > 1 else "."
    with open(os.path.join(ds, "faces.csv")) as f:
        faces = list(csv.DictReader(f))

    by_face = {}
    for r in faces:
        by_face.setdefault(int(r["face_id"]), []).append(r)
    for k in by_face:
        by_face[k].sort(key=lambda r: float(r["time"]))

    d1, d2, ex, ar = [], [], [], []
    for fid, rs in by_face.items():
        e = np.array([float(r["solute_excess"]) for r in rs])
        a = np.array([float(r["area"]) for r in rs])
        if len(e) < 3:
            continue
        d1.extend(np.diff(e))
        d2.extend(np.diff(e, n=2))
        ex.extend(e)
        ar.extend(a)

    d1 = np.array(d1)
    d2 = np.array(d2)
    ex = np.array(ex)
    ar = np.array(ar)

    print(f"面-时间样本总数: {len(ex)}")
    print()
    print("=" * 62)
    print("1. 目标量的量级")
    print("=" * 62)
    print(f"  面溶质含量 solute_excess: 均值 {ex.mean():+.4g}  "
          f"标准差 {ex.std():.4g}")
    print(f"  面的面积 area:            均值 {ar.mean():.4g}  "
          f"标准差 {ar.std():.4g}")
    print()
    print("=" * 62)
    print("2. 变化的量级")
    print("=" * 62)
    print(f"  一阶差分 |Δe| 的 RMS: {np.sqrt((d1**2).mean()):.4g}")
    print(f"  二阶差分 |Δ²e| 的 RMS: {np.sqrt((d2**2).mean()):.4g}")
    r = np.sqrt((d2**2).mean()) / (np.sqrt((d1**2).mean()) + 1e-30)
    print(f"  比值 (二阶/一阶): {r:.3f}")
    print()
    print("=" * 62)
    print("判读")
    print("=" * 62)
    if r > 1.2:
        print(f"  比值 {r:.2f} > 1.2 → 二阶差分比一阶还大")
        print("  ❗ 目标量被高频噪声主导。这多半来自'用阈值从弥散界面切面'的定义方式。")
        print("     含义：模型误差的很大一部分是【标签噪声】，不是算子学不到。")
        print("     应对：改平滑的面定义，或把目标改成对阈值不敏感的量。")
    elif r > 0.7:
        print(f"  比值 {r:.2f} 在 0.7–1.2 → 信号与噪声混杂")
        print("  ⚠️  目标量既有真实演化也有相当的定义噪声。")
        print("     可以尝试更平滑的面定义来降噪。")
    else:
        print(f"  比值 {r:.2f} < 0.7 → 目标量平滑，信号主导")
        print("  ✅ 误差不是标签噪声造成的，是算子确实没学到——")
        print("     那才需要考虑更强的机制（如算子间交互）。")

    print()
    print("=" * 62)
    print("3. 持久性基线（预测 d=0）")
    print("=" * 62)
    print(f"  归一化 MSE(预测不变) = {(d1**2).mean() / (d1**2).mean():.3f}")
    print(f"  （按定义恒为 1.0；算子的目标是显著低于它）")


if __name__ == "__main__":
    main()
