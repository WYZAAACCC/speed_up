#!/usr/bin/env python3
"""
逐面神经算子 —— 第二版：加守恒结构

=== 与第一版的差别 ===

第一版：直接预测"面含量的变化"，纯数据拟合，部署时总量会漂。
第二版：预测**两个通量** (J_i, J_j)，守恒由装配方式保证。

    面的更新：Δ(Γ_f A_f) = J_i + J_j
    晶粒的更新：ΔM_g = −Σ_{f∈faces(g)} J_{g→f}
    总量：Σ_g M_g + Σ_f Γ_f A_f 严格不变（每个通量在一侧 +、一侧 −）

=== 为什么需要两个约束 ===

可观测的量：
    · Δ(Γ_f A_f)   —— 面层面的变化
    · ΔM_g         —— 晶粒层面的变化
未知：每个"晶粒-面"关联的通量（比方程多）。

单靠面约束定不出"通量在两侧晶粒间怎么分"。所以损失里同时施加：
    ① 面约束：  J_i + J_j          ≈ Δ(面含量)
    ② 晶粒约束：−Σ_f J_{g→f}        ≈ ΔM_g     （按晶粒聚合后比较）
两个一起才能定出分配。

=== 几何项说明 ===

面缩小时它携带的溶质过量被"挤"进晶粒 —— 这本身就是通过面的通量，
不需要额外加几何修正项，已经包含在 J 里。

用法：
    python3 train_operator_v2.py <数据集目录> [--epochs 500]
"""

import argparse
import csv
import os
import sys

import numpy as np
import torch
import torch.nn as nn

FACE_FEATS = ["area", "solute_excess", "area_over_Ai", "area_over_Aj"]
GRAIN_FEATS = ["volume", "c_bulk", "n_faces", "shape_factor"]


def load(ds_dir):
    def read(name):
        with open(os.path.join(ds_dir, name)) as f:
            return list(csv.DictReader(f))

    return read("faces.csv"), read("grains.csv")


def build(ds_dir, stride=1):
    """构造样本，并建立"面样本 → 晶粒-时刻"的索引，用于晶粒层面的聚合。"""
    faces, grains = load(ds_dir)

    # 晶粒-时刻表
    gtimes = sorted({(float(g["time"]), int(g["grain_id"])) for g in grains})
    gindex = {k: i for i, k in enumerate(gtimes)}
    gM = np.zeros(len(gtimes))
    gV = np.zeros(len(gtimes))
    gc = np.zeros(len(gtimes))
    gtime = np.zeros(len(gtimes))
    for g in grains:
        k = (float(g["time"]), int(g["grain_id"]))
        i = gindex[k]
        gM[i] = float(g["solute"])
        gV[i] = float(g["volume"])
        gc[i] = float(g["c_bulk"])
        gtime[i] = float(g["time"])

    gmap = {(float(g["time"]), int(g["grain_id"])): g for g in grains}

    by_face = {}
    for r in faces:
        by_face.setdefault(int(r["face_id"]), []).append(r)
    for k in by_face:
        by_face[k].sort(key=lambda r: float(r["time"]))

    X, Yface, gidx_i, gidx_j, dM_obs = [], [], [], [], []
    meta = []
    for fid, rows in by_face.items():
        for k in range(len(rows) - stride):
            r0, r1 = rows[k], rows[k + stride]
            t0, t1 = float(r0["time"]), float(r1["time"])
            gi, gj = int(r0["grain_i"]), int(r0["grain_j"])
            g0i, g0j = gmap.get((t0, gi)), gmap.get((t0, gj))
            g1i, g1j = gmap.get((t1, gi)), gmap.get((t1, gj))
            if g0i is None or g0j is None or g1i is None or g1j is None:
                continue

            vi, vj = float(g0i["volume"]), float(g0j["volume"])
            ci, cj = float(g0i["c_bulk"]), float(g0j["c_bulk"])
            feat = ([float(r0[c]) for c in FACE_FEATS]
                    + [float(g0i[c]) for c in GRAIN_FEATS]
                    + [float(g0j[c]) for c in GRAIN_FEATS]
                    + [t1 - t0,
                       (vi - vj) / (vi + vj + 1e-12),
                       (ci - cj) / (abs(ci) + abs(cj) + 1e-12),
                       float(g0i["n_faces"]) - float(g0j["n_faces"])])
            X.append(feat)
            Yface.append(float(r1["solute_excess"]) - float(r0["solute_excess"]))
            gidx_i.append(gindex[(t0, gi)])
            gidx_j.append(gindex[(t0, gj)])
            # 晶粒在 t0→t1 之间的含量变化（观测）
            dM_obs.append((float(g1i["solute"]) - float(g0i["solute"]),
                           float(g1j["solute"]) - float(g0j["solute"])))
            meta.append((t0, fid, gi, gj))

    return (np.array(X, np.float32), np.array(Yface, np.float32),
            np.array(gidx_i, np.int64), np.array(gidx_j, np.int64),
            np.array(dM_obs, np.float32), gM, gV, gc, gtime, meta)


class FaceOperator(nn.Module):
    def __init__(self, n_in, hidden=128, depth=3):
        super().__init__()
        layers, d = [], n_in
        for _ in range(depth):
            layers += [nn.Linear(d, hidden), nn.SiLU()]
            d = hidden
        layers += [nn.Linear(d, 2)]
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ds_dir")
    ap.add_argument("--epochs", type=int, default=500)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--w-grain", type=float, default=1.0,
                    help="晶粒层面约束的权重")
    ap.add_argument("--out", default="operator_v2.pt")
    args = ap.parse_args()

    (X, Yf, gi_idx, gj_idx, dM, gM, gV, gc, gtime, meta) = build(args.ds_dir, args.stride)
    n = len(X)
    print(f"面样本 {n}，特征维 {X.shape[1]}；晶粒-时刻条目 {len(gM)}")
    if n < 200:
        sys.exit("样本太少")

    # 只保留在前后两步都存在的晶粒（避免拓扑事件处的记账歧义）
    mu, sd = X.mean(0), X.std(0) + 1e-8
    Xn = (X - mu) / sd
    s_face = Yf.std() + 1e-8
    s_grain = np.abs(dM).std() + 1e-8

    idx = np.random.default_rng(0).permutation(n)
    ntr = int(0.8 * n)
    tr, te = idx[:ntr], idx[ntr:]
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    Xt = torch.tensor(Xn, device=dev)
    Yft = torch.tensor(Yf, device=dev)
    gii = torch.tensor(gi_idx, device=dev)
    gjj = torch.tensor(gj_idx, device=dev)
    dMit = torch.tensor(dM[:, 0], device=dev)
    dMjt = torch.tensor(dM[:, 1], device=dev)
    ng = len(gM)
    dM_obs_i = torch.zeros(ng, device=dev).index_add_(0, gii, dMit)
    dM_obs_j = torch.zeros(ng, device=dev).index_add_(0, gjj, dMjt)
    # 注意：一个晶粒有多个面，每个面样本都携带"该晶粒的总变化"，
    # 聚合时要取平均而不是求和，否则会重复计数
    cnt_i = torch.zeros(ng, device=dev).index_add_(0, gii, torch.ones_like(dMit))
    cnt_j = torch.zeros(ng, device=dev).index_add_(0, gjj, torch.ones_like(dMjt))
    dM_avg_i = dM_obs_i / cnt_i.clamp(min=1)
    dM_avg_j = dM_obs_j / cnt_j.clamp(min=1)

    model = FaceOperator(Xn.shape[1]).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    print(f"设备 {dev}")

    best = 1e9
    for ep in range(args.epochs):
        model.train()
        opt.zero_grad()
        out = model(Xt[tr])
        Ji, Jj = out[:, 0], out[:, 1]

        # ① 面约束
        l_face = (((Ji + Jj) - Yft[tr]) / s_face).pow(2).mean()

        # ② 晶粒约束：把每个面样本的 -J 按其所属晶粒聚合，与观测的 ΔM 比较
        tr_i, tr_j = gii[tr], gjj[tr]
        acc_i = torch.zeros(ng, device=dev).index_add_(0, tr_i, -Ji)
        acc_j = torch.zeros(ng, device=dev).index_add_(0, tr_j, -Jj)
        # 一个晶粒的总交换 = 它所有面的 -J 之和；
        # 而每个面样本携带的 dM 是"该晶粒的总变化"，所以两者直接比较
        l_grain = (((acc_i - dM_avg_i) / s_grain).pow(2).mean()
                   + ((acc_j - dM_avg_j) / s_grain).pow(2).mean())

        loss = l_face + args.w_grain * l_grain
        loss.backward()
        opt.step()

        if ep % 25 == 0 or ep == args.epochs - 1:
            model.eval()
            with torch.no_grad():
                o = model(Xt[te])
                lf = (((o[:, 0] + o[:, 1]) - Yft[te]) / s_face).pow(2).mean().item()
            print(f"  ep {ep:4d}  loss {loss.item():.4f}  面 {l_face.item():.4f}  "
                  f"晶粒 {l_grain.item():.4f}  |  测试面 {lf:.4f}")
            if lf < best:
                best = lf
                torch.save({"state": model.state_dict(), "mu": mu, "sd": sd}, args.out)

    print(f"\n最佳测试面约束 MSE/σ² = {best:.4f}")


if __name__ == "__main__":
    main()
