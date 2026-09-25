#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""drive_thin.py --- V4 收口：把抗截留标定搬到**薄界面区制**（W << l_D = D_L/V = 95 nm）。

为什么（上一轮的决定性诊断，见 README §4.6）：
  W = 200/60/20 nm 上 ALPHA* = 6.5/8.7/14.1 ⇒ **"ALPHA 是普适常数"不成立**，
  因为 VW/D_L = 2.1/0.63/0.21 已经不在 Karma–Rappel/Plapp 的 `∝W` 推导适用区（要求 W << l_D）。
  ⇒ 唯一能判定"是形式错还是区制错"的实验：**在 W << l_D 重做标定**。

判据（薄界面区制）：
  (a) ALPHA=0 时 c_int < target（截留）——负对照；
  (b) 存在 ALPHA* 使 c_int = target；
  (c) **ALPHA* 必须与 W 无关**（这是"抗截留是普适修正"的可证伪形式）；
  (d) 对照理论系数（Plapp/KR 形式 ⇒ 见 P11_SPEC；本文件的输出直接给出 ALPHA*）。

观测量：c_int = 末态剖面上 φ 首次跨 0.5 处的 c；target = c_inf/k_e(T_int) = 0.056664
（k_e = 0.63532 由模型自己的 f_loc 在 T_int = 1911.1 K 反解，见 README §4.4b）。
用法：drive_thin.py <W_nm,逗号分隔> <A,逗号分隔> [travel_um]
"""
import io
import os
import re
import sys
import time
import concurrent.futures as cf
import drive_ak3 as D

TARGET = 0.056664
X0 = 2.0e-7          # 模板里的界面起点
V_PULL = 0.1         # m/s


def make_cases(Wnms, As, travel_um):
    # ★ 记账：`drive_ak3.make_input` 里的探针点是硬编码的 x=4/6/8 µm（它的域 ≥12 µm）
    #   ⇒ 我这个小域必须**改写模块级 `D.PROBES`**，否则 PointValue 会因"域内无该点"直接 ERROR。
    D.PROBES = [3.0e-6, 4.5e-6]
    out = []
    for Wnm in Wnms:
        dxnm = Wnm / 4.0                      # 判据 Δx ≤ W/4（MATH_FRAMEWORK §5.6）
        xmax = X0 + travel_um * 1e-6 + 0.5e-6
        nx = int(round(xmax / (dxnm * 1e-9)))
        tend = travel_um * 1e-6 / V_PULL
        for A in As:
            tag = "%s_W%g_A%g" % (os.path.basename(D.BASE).replace(".i", ""), Wnm, A)
            out.append((tag, xmax, nx, tend, "%.4e" % (Wnm * 1e-9), "%.4f" % A,
                        min(4000, nx + 1)))
    return out


if __name__ == "__main__":
    Ws = [float(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else [10.0]
    As = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [0.0, 1.0, 2.0, 4.0, 8.0]
    trav = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0
    if len(sys.argv) > 4 and sys.argv[4] != "base":
        # 换底模板（例如 p1c_kr.i = KR/Plapp 形式的 F_at）⇒ 目录标签加后缀避免与旧算例混
        D.BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), sys.argv[4])
        print("底模板 = %s" % D.BASE)
    cs = make_cases(Ws, As, trav)
    print("目标 c_int = %.6f ; 界面速度 %.2f m/s ; 行程 %.1f um" % (TARGET, V_PULL, trav))
    print("%-18s %-4s %-6s %-5s %-6s | %-9s %-9s %-9s %-9s" %
          ("tag", "nx", "sec", "jit", "steps", "alpha", "c_int", "vs目标", "c_peak"))
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for tag, res in ex.map(D.run_case, cs):
            A = float(re.search(r"_A([0-9.]+)$", tag).group(1))
            ci = res.get("c_int", float("nan"))
            print("%-18s %-4d %-6.0f %-5s %-6s | %-9.3f %-9.6f %+8.1f%% %-9.6f" %
                  (tag, [c for c in cs if c[0] == tag][0][2], res.get("sec", 0),
                   res.get("jit", "-"), res.get("steps", "-"), A, ci,
                   100.0 * (ci / TARGET - 1.0), res.get("c_peak", float("nan"))))
            if res.get("err_line"):
                print("     ERR: " + res["err_line"])
            if res.get("err"):
                print("     EXC: " + res["err"])
