#!/usr/bin/env python3
"""
闭环回放测试：测算子的端到端累积误差。

=== 测什么 ===

几何与拓扑【从参考解读取】（我们不建模晶粒演化），
只有【溶质是自由演化的】—— 用算子自己的预测往下滚。

这样测出来的误差纯粹来自：算子精度 + 守恒装配。
不掺入"晶粒图演化模型"的误差（那还没建）。

=== 关键：自由演化 vs 老师强制 ===

· 老师强制：每步都喂参考解的溶质状态 → 只测单步精度，测不出累积
· 自由演化：喂算子自己的预测 → 这才是部署时的真实情况

本脚本用**自由演化**，并同时报告单步误差，便于对比。

=== 拓扑事件 ===

面出现时，其含量初值取自参考解；
面消失时的溶质转移（转移算子）本版本**尚未实现**，
所以默认只在**没有拓扑事件的时间窗**内回放。
用 --allow-events 可以强行跑，但结果会因缺少转移规则而失真。

用法：
    python3 replay.py <数据集目录> <模型.pt> [--t0 200] [--t1 500]
"""

import argparse
import csv
import os
import sys
from collections import defaultdict

import numpy as np
import torch
import torch.nn as nn

FEATS = ["area", "solute_excess", "area_over_Ai", "area_over_Aj"]
GFEATS = ["volume", "c_bulk", "n_faces", "shape_factor"]


class Net(nn.Module):
    def __init__(self, n_in, hidden=128, depth=3):
        super().__init__()
        L, d = [], n_in
        for _ in range(depth):
            L += [nn.Linear(d, hidden), nn.SiLU()]
            d = hidden
        L += [nn.Linear(d, 1)]
        self.net = nn.Sequential(*L)

    def forward(self, x):
        return self.net(x).squeeze(-1)


def read_csv(ds, name):
    with open(os.path.join(ds, name)) as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ds_dir")
    ap.add_argument("model")
    ap.add_argument("--t0", type=float, default=None)
    ap.add_argument("--t1", type=float, default=None)
    ap.add_argument("--allow-events", action="store_true")
    args = ap.parse_args()

    faces = read_csv(args.ds_dir, "faces.csv")
    grains = read_csv(args.ds_dir, "grains.csv")

    # 按时刻组织
    gt = defaultdict(dict)     # t -> {gid: row}
    for g in grains:
        gt[float(g["time"])][int(g["grain_id"])] = g
    ft = defaultdict(dict)     # t -> {face_id: row}
    for r in faces:
        ft[float(r["time"])][int(r["face_id"])] = r

    times = sorted(gt.keys())
    t0 = args.t0 if args.t0 is not None else times[0]
    t1 = args.t1 if args.t1 is not None else times[-1]
    win = [t for t in times if t0 <= t <= t1]
    print(f"回放窗口 t = {win[0]:g} .. {win[-1]:g}，共 {len(win)} 个采样点")

    # 检查窗口内有无拓扑事件
    ev = read_csv(args.ds_dir, "events.csv")
    ev_in = [e for e in ev if t0 <= float(e["time"]) <= t1]
    if ev_in and not args.allow_events:
        print(f"\n⚠️  窗口内有 {len(ev_in)} 条拓扑事件，而转移算子尚未实现。")
        print("    请换一个没有事件的窗口（用 --t0/--t1），或加 --allow-events 强行运行。")
        for e in ev_in[:5]:
            print(f"      t={e['time']}  {e['event']}  {e['a']},{e['b']}")
        sys.exit(1)
    if ev_in:
        print(f"⚠️  窗口内有 {len(ev_in)} 条事件，强行运行（缺少转移规则，结果会失真）")

    # weights_only=False：检查点里存了 numpy 数组（mu/sd），新版 torch 默认不允许
    ck = torch.load(args.model, map_location="cpu", weights_only=False)
    # 有的训练脚本存了标准化参数，有的没存（回放训练用的是原始特征）
    if "mu" in ck:
        mu = np.asarray(ck["mu"], np.float32)
        sd = np.asarray(ck["sd"], np.float32)
        print("模型带标准化参数")
    else:
        mu = np.zeros(16, np.float32)
        sd = np.ones(16, np.float32)
        print("模型不带标准化参数（原始特征）")
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    # 【从权重自动推断网络结构】不同训练脚本用的宽度/深度可能不同，
    # 写死会报 size mismatch。
    sd_ = ck["state"]
    lin = sorted([k for k in sd_ if k.endswith(".weight")],
                 key=lambda k: int(k.split(".")[1]))
    hidden = sd_[lin[0]].shape[0]
    # Net 的结构是 depth 个隐藏层 + 1 个输出层，所以隐藏层数 = 总 Linear 数 − 1
    depth = len(lin) - 1
    n_in = sd_[lin[0]].shape[1]
    print(f"网络结构: 输入 {n_in}, 隐藏 {hidden}, 深度 {depth}")
    net = Net(n_in, hidden=hidden, depth=depth).to(dev)
    net.load_state_dict(sd_)
    net.eval()

    # ---- 自由演化的状态：面含量 与 晶粒含量 ----
    G = {fid: float(r["solute_excess"]) for fid, r in ft[win[0]].items()}
    M = {g: float(r["solute"]) for g, r in gt[win[0]].items()}

    def features(t, tn, fid, r, gi, gj):
        # 【特征顺序必须与训练脚本完全一致】（见 train_rollout_batched.py 顶部注释）：
        #   0-2 面静态 | 3 面含量 | 4-6 晶粒i(体积,配位,形状) | 7 i浓度
        #   8-10 晶粒j(…) | 11 j浓度 | 12-14 dt,体积对比,配位对比 | 15 浓度对比
        a, b = gt[t][gi], gt[t][gj]
        vi, vj = float(a["volume"]), float(b["volume"])
        ci, cj = M[gi] / vi, M[gj] / vj       # 用【预测的】含量算浓度
        return np.array(
            [float(r["area"]), float(r["area_over_Ai"]), float(r["area_over_Aj"]),
             G[fid]]
            + [vi, float(a["n_faces"]), float(a["shape_factor"]), ci]
            + [vj, float(b["n_faces"]), float(b["shape_factor"]), cj]
            + [tn - t,
               (vi - vj) / (vi + vj + 1e-12),
               float(a["n_faces"]) - float(b["n_faces"]),
               (ci - cj) / (abs(ci) + abs(cj) + 1e-12)],
            np.float32)

    print()
    print(f"{'t':>8} {'面含量相对误差':>14} {'晶粒含量相对误差':>16} {'总量漂移':>12}")
    print("-" * 56)

    for k in range(len(win) - 1):
        t, tn = win[k], win[k + 1]
        fnow, fnext = ft[t], ft[tn]

        # 收集本步的预测
        X, keys = [], []
        for fid, r in fnow.items():
            if fid not in fnext:
                continue
            gi, gj = int(r["grain_i"]), int(r["grain_j"])
            if gi not in M or gj not in M:
                continue
            X.append(features(t, tn, fid, r, gi, gj))
            keys.append((fid, gi, gj))
        if not X:
            continue

        Xn = (np.array(X, np.float32) - mu) / sd
        with torch.no_grad():
            J = net(torch.tensor(Xn, device=dev)).cpu().numpy()

        # ---- 守恒装配：每个通量在一侧 −、另一侧 + ----
        newM = dict(M)
        newG = dict(G)
        # 注意：算子输出是"面含量的变化"，按第一版的设计
        # 这里把它拆给两侧晶粒：按晶粒体积加权（第一版的简化）
        for idx, (fid, gi, gj) in enumerate(keys):
            dG = float(J[idx])
            newG[fid] = G[fid] + dG
            vi, vj = float(gt[t][gi]["volume"]), float(gt[t][gj]["volume"])
            wi = vi / (vi + vj)
            newM[gi] = newM.get(gi, 0.0) - dG * wi
            newM[gj] = newM.get(gj, 0.0) - dG * (1 - wi)

        M, G = newM, newG

        # ---- 与参考解对比 ----
        # 【指标选择】不用"逐面相对误差"——面含量可能接近零，相对误差会爆炸。
        # 改用 RMSE / RMS(参考值)，这是稳健的归一化误差。
        common_f = [f for f in fnext if f in G]
        ref_f = np.array([float(fnext[f]["solute_excess"]) for f in common_f])
        my_f = np.array([G[f] for f in common_f])
        f_err = np.sqrt(((my_f - ref_f) ** 2).mean()) / (np.sqrt((ref_f ** 2).mean()) + 1e-30)

        gi_ref = {g: float(r["solute"]) for g, r in gt[tn].items() if g in M}
        ref_g = np.array([gi_ref[g] for g in gi_ref])
        my_g = np.array([M[g] for g in gi_ref])
        g_err = np.sqrt(((my_g - ref_g) ** 2).mean()) / (np.sqrt((ref_g ** 2).mean()) + 1e-30)

        # 【守恒检查】只看我自己的量：Σ面含量 + Σ晶粒含量。
        # 装配是通量形式，这个和应当严格不变。
        my_tot = sum(G[f] for f in G) + sum(M[g] for g in M)
        if k == 0:
            tot0 = my_tot
        print(f"{tn:>8.0f} {f_err:>14.4f} {g_err:>16.4f} "
              f"{(my_tot - tot0) / abs(tot0):>+12.2e}")

    print()
    print("判读：")
    print("  ‘面含量误差’随时间是否快速增长？")
    print("    若基本平稳 → 算子可长期稳定演化")
    print("    若快速增长 → 误差累积，需要更强的约束或更好的算子")
    print("  ‘守恒漂移’应当接近 0（Σ面含量+Σ晶粒含量 由通量装配保证不变）")


if __name__ == "__main__":
    main()
