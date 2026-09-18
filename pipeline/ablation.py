#!/usr/bin/env python3
"""
特征消融：弄清那 27% 的误差是"特征不够"还是"机制不够"。

动机：
  完整数据集上算子只解释约 73% 的方差。剩余误差可能来自：
    (a) 特征不足 —— 没给它需要的信息
    (b) 机制不足 —— 面的演化本质上依赖非局部信息，局部算子做不到

  分清这两者很重要：
    若是 (a)，加特征就行，"逐面独立调用"的定位保得住；
    若是 (b)，才需要引入"相邻算子交互"这种更重的机制。

做法：
  按特征组逐级加入，看每一组的贡献。
  另外加一组"非局部特征"（邻面的统计量），看能否补上缺口。

用法：
    python3 ablation.py <数据集目录> [--epochs 300]
"""

import argparse
import csv
import os

import numpy as np
import torch
import torch.nn as nn


def load(ds_dir):
    def read(name):
        with open(os.path.join(ds_dir, name)) as f:
            return list(csv.DictReader(f))

    return read("faces.csv"), read("grains.csv")


def build_all(ds_dir):
    faces, grains = load(ds_dir)
    gmap = {(float(g["time"]), int(g["grain_id"])): g for g in grains}

    # 每个 (时刻, 晶粒) 的面数，用来算"这个面占晶粒多大分量"
    by_face = {}
    for r in faces:
        by_face.setdefault(int(r["face_id"]), []).append(r)
    for k in by_face:
        by_face[k].sort(key=lambda r: float(r["time"]))

    # 非局部：按 (时刻, 晶粒) 汇总该晶粒所有面的状态均值
    from collections import defaultdict
    gface = defaultdict(list)
    for r in faces:
        gface[(float(r["time"]), int(r["grain_i"]))].append(r)
        gface[(float(r["time"]), int(r["grain_j"]))].append(r)

    def neigh_feats(t, gid):
        rs = gface.get((t, gid), [])
        if not rs:
            return [0.0, 0.0, 0.0]
        ex = np.array([float(x["solute_excess"]) for x in rs])
        ar = np.array([float(x["area"]) for x in rs])
        return [float(ex.mean()), float(ex.std()), float(ar.mean())]

    rows = []
    for fid, rs in by_face.items():
        for k in range(len(rs) - 1):
            r0, r1 = rs[k], rs[k + 1]
            t0 = float(r0["time"])
            gi, gj = int(r0["grain_i"]), int(r0["grain_j"])
            g0i, g0j = gmap.get((t0, gi)), gmap.get((t0, gj))
            if g0i is None or g0j is None:
                continue

            vi, vj = float(g0i["volume"]), float(g0j["volume"])
            ci, cj = float(g0i["c_bulk"]), float(g0j["c_bulk"])

            groups = {
                "面": [float(r0["area"]), float(r0["solute_excess"]),
                       float(r0["area_over_Ai"]), float(r0["area_over_Aj"])],
                "晶粒_i": [float(g0i[c]) for c in
                           ("volume", "c_bulk", "n_faces", "shape_factor")],
                "晶粒_j": [float(g0j[c]) for c in
                           ("volume", "c_bulk", "n_faces", "shape_factor")],
                "对比": [(vi - vj) / (vi + vj + 1e-12),
                         (ci - cj) / (abs(ci) + abs(cj) + 1e-12),
                         float(g0i["n_faces"]) - float(g0j["n_faces"])],
                "非局部": neigh_feats(t0, gi) + neigh_feats(t0, gj),
            }
            y = float(r1["solute_excess"]) - float(r0["solute_excess"])
            rows.append((groups, y))

    return rows


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


def run(rows, keys, epochs, dev, seed=0):
    X = np.array([[v for k in keys for v in g[k]] for g, _ in rows], np.float32)
    Y = np.array([y for _, y in rows], np.float32)
    mu, sd = X.mean(0), X.std(0) + 1e-8
    Xn = (X - mu) / sd
    ys = Y.std() + 1e-8

    n = len(Xn)
    idx = np.random.default_rng(seed).permutation(n)
    ntr = int(0.8 * n)
    tr, te = idx[:ntr], idx[ntr:]

    Xt = torch.tensor(Xn, device=dev)
    Yt = torch.tensor(Y, device=dev)
    torch.manual_seed(seed)
    m = Net(Xn.shape[1]).to(dev)
    opt = torch.optim.Adam(m.parameters(), lr=1e-3)
    for _ in range(epochs):
        m.train()
        opt.zero_grad()
        ((m(Xt[tr]) - Yt[tr]) / ys).pow(2).mean().backward()
        opt.step()
    m.eval()
    with torch.no_grad():
        return (((m(Xt[te]) - Yt[te]) / ys).pow(2).mean().item(), Xn.shape[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ds_dir")
    ap.add_argument("--epochs", type=int, default=300)
    args = ap.parse_args()

    rows = build_all(args.ds_dir)
    print(f"样本 {len(rows)}")
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    configs = [
        ("① 只有面",              ["面"]),
        ("② 面 + 晶粒 i",         ["面", "晶粒_i"]),
        ("③ 面 + 两侧晶粒",        ["面", "晶粒_i", "晶粒_j"]),
        ("④ + 对比量（=第一版）",  ["面", "晶粒_i", "晶粒_j", "对比"]),
        ("⑤ + 非局部邻域信息",     ["面", "晶粒_i", "晶粒_j", "对比", "非局部"]),
        ("⑥ 只有非局部",           ["非局部"]),
    ]

    print()
    print(f"{'配置':<24} {'特征数':>6} {'test(MSE/σ²)':>14}")
    print("-" * 48)
    base = None
    for name, keys in configs:
        mse, nf = run(rows, keys, args.epochs, dev)
        if base is None and "④" in name:
            base = mse
        print(f"{name:<24} {nf:>6} {mse:>14.4f}")
    print()
    print("判读：")
    print("  若 ⑤ 明显优于 ④  → 是【特征不足】，加邻域信息即可，不必引入算子交互")
    print("  若 ⑤ 与 ④ 差不多  → 是【机制不足】，局部+邻域信息都不够，才需要考虑交互")


if __name__ == "__main__":
    main()
