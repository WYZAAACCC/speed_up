#!/usr/bin/env python3
"""
逐面神经算子 —— 第一版（先验证可行性，再加守恒结构）

=== 这一版做什么 ===
  输入：一个面的局部状态 + 两侧晶粒的状态
  输出：一个时间步内，该面的溶质含量变化 Δ(Γ_f·A_f)

=== 这一版不做什么（有意为之）===
  不做"通量在两个晶粒之间怎么分"。原因见下：

  从数据里能观测到的只有：
    · 面含量的变化 Δ(Γ_f A_f)          ← 本版的标签
    · 每个晶粒含量的变化 ΔM_g
  但 ΔM_g 里还混着**几何项** c_g·ΔV_g（晶粒长大时扫过邻居的材料），
  要把它和交换通量分开，需要更精细的记账。
  所以第一版先只做面层面，把可行性验证了再说。

  守恒结构的加入（预测 J_i、J_j 并用装配保证守恒）放在第二版。

用法：
    python3 train_operator.py <数据集目录> [--epochs 300]
"""

import argparse
import os
import sys

import numpy as np
import torch
import torch.nn as nn

FACE_FEATS = ["area", "solute_excess", "area_over_Ai", "area_over_Aj"]
GRAIN_FEATS = ["volume", "c_bulk", "n_faces", "shape_factor"]


def load(ds_dir):
    import csv

    def read(name):
        with open(os.path.join(ds_dir, name)) as f:
            return list(csv.DictReader(f))

    return read("faces.csv"), read("grains.csv")


def build_samples(faces, grains, stride=1):
    gmap = {}
    for g in grains:
        gmap[(float(g["time"]), int(g["grain_id"]))] = g

    by_face = {}
    for r in faces:
        by_face.setdefault(int(r["face_id"]), []).append(r)
    for k in by_face:
        by_face[k].sort(key=lambda r: float(r["time"]))

    X, Y, meta = [], [], []
    for fid, rows in by_face.items():
        for k in range(len(rows) - stride):
            r0, r1 = rows[k], rows[k + stride]
            t0 = float(r0["time"])
            gi, gj = int(r0["grain_i"]), int(r0["grain_j"])
            g0i, g0j = gmap.get((t0, gi)), gmap.get((t0, gj))
            if g0i is None or g0j is None:
                continue

            feat = ([float(r0[c]) for c in FACE_FEATS]
                    + [float(g0i[c]) for c in GRAIN_FEATS]
                    + [float(g0j[c]) for c in GRAIN_FEATS]
                    + [float(r1["time"]) - t0])          # 时间步长
            # 无量纲化的对比量
            vi, vj = float(g0i["volume"]), float(g0j["volume"])
            ci, cj = float(g0i["c_bulk"]), float(g0j["c_bulk"])
            feat += [
                (vi - vj) / (vi + vj + 1e-12),
                (ci - cj) / (abs(ci) + abs(cj) + 1e-12),
                float(g0i["n_faces"]) - float(g0j["n_faces"]),
            ]
            X.append(feat)
            Y.append(float(r1["solute_excess"]) - float(r0["solute_excess"]))
            meta.append((t0, fid, gi, gj))

    return (np.array(X, dtype=np.float32),
            np.array(Y, dtype=np.float32), meta)


class FaceOperator(nn.Module):
    """逐面算子：共享 MLP，对每个面独立调用。"""

    def __init__(self, n_in, hidden=128, depth=3):
        super().__init__()
        layers, d = [], n_in
        for _ in range(depth):
            layers += [nn.Linear(d, hidden), nn.SiLU()]
            d = hidden
        layers += [nn.Linear(d, 1)]
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x).squeeze(-1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ds_dir")
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--out", default="operator.pt")
    args = ap.parse_args()

    faces, grains = load(args.ds_dir)
    X, Y, meta = build_samples(faces, grains, args.stride)
    print(f"样本数 {len(X)}，特征维数 {X.shape[1]}")
    if len(X) < 100:
        sys.exit("样本太少")

    mu, sd = X.mean(0), X.std(0) + 1e-8
    Xn = (X - mu) / sd
    ys = Y.std() + 1e-8
    print(f"标签(std) = {ys:.4g}")

    n = len(Xn)
    idx = np.random.default_rng(0).permutation(n)
    ntr = int(0.8 * n)
    tr, te = idx[:ntr], idx[ntr:]

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"设备 {dev}")

    model = FaceOperator(Xn.shape[1]).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    Xt = torch.tensor(Xn, device=dev)
    Yt = torch.tensor(Y, device=dev)

    best = 1e9
    for ep in range(args.epochs):
        model.train()
        opt.zero_grad()
        pred = model(Xt[tr])
        loss = ((pred - Yt[tr]) / ys).pow(2).mean()
        loss.backward()
        opt.step()

        if ep % 25 == 0 or ep == args.epochs - 1:
            model.eval()
            with torch.no_grad():
                p = model(Xt[te])
                mse = ((p - Yt[te]) / ys).pow(2).mean().item()
                mae = (p - Yt[te]).abs().mean().item()
            print(f"  ep {ep:4d}  train {loss.item():.4f}  "
                  f"test(MSE/σ²) {mse:.4f}  test MAE {mae:.4g}")
            if mse < best:
                best = mse
                torch.save({"state": model.state_dict(), "mu": mu, "sd": sd}, args.out)

    print(f"\n最佳 test(MSE/σ²) = {best:.4f}   模型: {args.out}")
    print("判读：")
    print("  < 0.1   好，算子学到了东西")
    print("  0.1–0.5 一般，可能需要更多数据或更好的特征")
    print("  > 0.5   差，接近只预测均值的基线")


if __name__ == "__main__":
    main()
