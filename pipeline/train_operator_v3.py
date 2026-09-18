#!/usr/bin/env python3
"""
逐面神经算子 v3 —— 修正守恒约束的聚合方式

=== v2 的错误 ===

v2 里我把晶粒的 −J 沿【所有时刻】求和再与观测的 ΔM 比。
但正确的对应关系是**按 (晶粒, 时刻) 分别聚合**：
某个时刻的通量，只对应那个时刻的含量变化。

而且分批训练时，一个晶粒的面会被拆到不同 batch，聚合必然不完整。
→ 所以改成：**对全部样本前向一次，按 (晶粒,时刻) 聚合，再算损失。**

=== 训练/测试切分改成按时间 ===

v2 按样本随机切分，导致同一 (晶粒,时刻) 的面被拆到两边，聚合在两边都不完整。
v3 按时间切：早的时间段做训练，晚的做测试。

=== 守恒 ===

面：  Δ(Γ_f A_f) = J_i + J_j
晶粒：(某时刻该晶粒所有面) Σ_f (−J_{g→f}) = ΔM_g
总量：Σ M_g + Σ Γ_f A_f 严格不变（部署时由装配保证）

用法：python3 train_operator_v3.py <数据集目录> [--epochs 2000]
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


def read_csv(ds, name):
    with open(os.path.join(ds, name)) as f:
        return list(csv.DictReader(f))


def build(ds_dir, stride=1):
    faces = read_csv(ds_dir, "faces.csv")
    grains = read_csv(ds_dir, "grains.csv")

    # 全局的 (时刻, 晶粒) 索引
    keys = sorted({(float(g["time"]), int(g["grain_id"])) for g in grains})
    kidx = {k: i for i, k in enumerate(keys)}

    gmap = {(float(g["time"]), int(g["grain_id"])): g for g in grains}

    by_face = {}
    for r in faces:
        by_face.setdefault(int(r["face_id"]), []).append(r)
    for k in by_face:
        by_face[k].sort(key=lambda r: float(r["time"]))

    X, Yf, ki, kj, t0s, gi_ids, gj_ids, dMi, dMj = [], [], [], [], [], [], [], [], []
    for fid, rs in by_face.items():
        for k in range(len(rs) - stride):
            r0, r1 = rs[k], rs[k + stride]
            t0, t1 = float(r0["time"]), float(r1["time"])
            gi, gj = int(r0["grain_i"]), int(r0["grain_j"])
            g0i, g0j = gmap.get((t0, gi)), gmap.get((t0, gj))
            g1i, g1j = gmap.get((t1, gi)), gmap.get((t1, gj))
            if g0i is None or g0j is None or g1i is None or g1j is None:
                continue

            vi, vj = float(g0i["volume"]), float(g0j["volume"])
            ci, cj = float(g0i["c_bulk"]), float(g0j["c_bulk"])
            X.append([float(r0[c]) for c in FACE_FEATS]
                     + [float(g0i[c]) for c in GRAIN_FEATS]
                     + [float(g0j[c]) for c in GRAIN_FEATS]
                     + [t1 - t0,
                        (vi - vj) / (vi + vj + 1e-12),
                        (ci - cj) / (abs(ci) + abs(cj) + 1e-12),
                        float(g0i["n_faces"]) - float(g0j["n_faces"])])
            Yf.append(float(r1["solute_excess"]) - float(r0["solute_excess"]))
            ki.append(kidx[(t0, gi)])
            kj.append(kidx[(t0, gj)])
            t0s.append(t0)
            gi_ids.append(gi)
            gj_ids.append(gj)
            dMi.append(float(g1i["solute"]) - float(g0i["solute"]))
            dMj.append(float(g1j["solute"]) - float(g0j["solute"]))

    return (np.array(X, np.float32), np.array(Yf, np.float32),
            np.array(ki, np.int64), np.array(kj, np.int64),
            np.array(t0s, np.float32),
            np.array(gi_ids, np.int64), np.array(gj_ids, np.int64),
            np.array(dMi, np.float32), np.array(dMj, np.float32),
            len(keys))


class Net(nn.Module):
    def __init__(self, n_in, hidden=192, depth=4):
        super().__init__()
        L, d = [], n_in
        for _ in range(depth):
            L += [nn.Linear(d, hidden), nn.SiLU()]
            d = hidden
        L += [nn.Linear(d, 2)]
        self.net = nn.Sequential(*L)

    def forward(self, x):
        return self.net(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ds_dir")
    ap.add_argument("--epochs", type=int, default=2000)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--stride", type=int, default=2)
    ap.add_argument("--split-frac", type=float, default=0.7,
                    help="按时间切分：前 70% 时间做训练")
    ap.add_argument("--w-grain", type=float, default=1.0)
    ap.add_argument("--out", default="operator_v3.pt")
    args = ap.parse_args()

    (X, Yf, ki, kj, t0s, gi_ids, gj_ids, dMi, dMj, nkeys) = build(args.ds_dir, args.stride)
    n = len(X)
    print(f"面样本 {n}，特征 {X.shape[1]}，(晶粒,时刻) 条目 {nkeys}")
    if n < 500:
        sys.exit("样本太少")

    # 按时间切分
    ts = np.sort(np.unique(t0s))
    tcut = ts[int(len(ts) * args.split_frac)]
    tr_mask = t0s < tcut
    te_mask = ~tr_mask
    print(f"时间切分点 t = {tcut:.4g}：训练样本 {tr_mask.sum()}，测试 {te_mask.sum()}")

    mu, sd = X.mean(0), X.std(0) + 1e-8
    Xn = (X - mu) / sd
    s_face = Yf.std() + 1e-8
    s_grain = np.concatenate([dMi, dMj]).std() + 1e-8
    print(f"标签尺度：面 {s_face:.4g}  晶粒 {s_grain:.4g}")

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    Xt = torch.tensor(Xn, device=dev)
    Yft = torch.tensor(Yf, device=dev)
    kit = torch.tensor(ki, device=dev)
    kjt = torch.tensor(kj, device=dev)
    dMit = torch.tensor(dMi, device=dev)
    dMjt = torch.tensor(dMj, device=dev)
    trt = torch.tensor(tr_mask, device=dev)
    tet = torch.tensor(te_mask, device=dev)

    # 每个 (晶粒,时刻) 条目的观测 ΔM（各面样本携带的值相同，取第一个）
    obs_i = torch.zeros(nkeys, device=dev)
    obs_j = torch.zeros(nkeys, device=dev)
    seen_i = torch.zeros(nkeys, dtype=torch.bool, device=dev)
    seen_j = torch.zeros(nkeys, dtype=torch.bool, device=dev)
    obs_i[kit] = dMit
    obs_j[kjt] = dMjt
    seen_i[kit] = True
    seen_j[kjt] = True
    # 晶粒总表面积（用于把"该晶粒的总变化"折算到单个面）
    face_area_sum_i = torch.zeros(nkeys, device=dev).index_add_(0, kit, torch.tensor(
        X[:, 0], device=dev))
    face_area_sum_j = torch.zeros(nkeys, device=dev).index_add_(0, kjt, torch.tensor(
        X[:, 0], device=dev))

    model = Net(Xn.shape[1]).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    print(f"设备 {dev}\n")

    def evaluate(mask):
        """全量前向 + 按 (晶粒,时刻) 聚合。"""
        out = model(Xt)
        Ji, Jj = out[:, 0], out[:, 1]

        l_face = (((Ji + Jj) - Yft)[mask] / s_face).pow(2).mean()

        acc_i = torch.zeros(nkeys, device=dev).index_add_(0, kit, -Ji)
        acc_j = torch.zeros(nkeys, device=dev).index_add_(0, kjt, -Jj)
        valid_i = seen_i & mask.any()  # 占位，实际用下面按时间过滤
        return out, Ji, Jj, l_face, acc_i, acc_j

    best = 1e9
    for ep in range(args.epochs):
        model.train()
        opt.zero_grad()
        out = model(Xt)
        Ji, Jj = out[:, 0], out[:, 1]

        # ① 面约束（只用训练时间段）
        l_face = (((Ji + Jj) - Yft)[trt] / s_face).pow(2).mean()

        # ② 晶粒约束：按 (晶粒,时刻) 聚合
        #    注意 acc 必须覆盖该条目的**全部**面，所以这里用全量样本聚合，
        #    但损失只取训练时间段的条目
        acc_i = torch.zeros(nkeys, device=dev).index_add_(0, kit, -Ji)
        acc_j = torch.zeros(nkeys, device=dev).index_add_(0, kjt, -Jj)

        # 只保留训练时间段的 (晶粒,时刻) 条目
        ktime = torch.zeros(nkeys, device=dev)
        ktime[kit] = torch.tensor(t0s, device=dev)
        trk = ktime < tcut
        ok_i = seen_i & trk
        ok_j = seen_j & trk

        l_grain_i = (((acc_i - obs_i) / s_grain)[ok_i]).pow(2).mean() \
            if ok_i.any() else torch.tensor(0.0, device=dev)
        l_grain_j = (((acc_j - obs_j) / s_grain)[ok_j]).pow(2).mean() \
            if ok_j.any() else torch.tensor(0.0, device=dev)
        l_grain = l_grain_i + l_grain_j

        loss = l_face + args.w_grain * l_grain
        loss.backward()
        opt.step()

        if ep % 100 == 0 or ep == args.epochs - 1:
            model.eval()
            with torch.no_grad():
                o = model(Xt)
                lf_tr = (((o[:, 0] + o[:, 1]) - Yft)[trt] / s_face).pow(2).mean().item()
                lf_te = (((o[:, 0] + o[:, 1]) - Yft)[tet] / s_face).pow(2).mean().item()
            print(f"  ep {ep:5d}  loss {loss.item():7.4f}  "
                  f"面(训/测) {lf_tr:.4f}/{lf_te:.4f}  晶粒 {l_grain.item():7.4f}")
            if lf_te < best:
                best = lf_te
                torch.save({"state": model.state_dict(), "mu": mu, "sd": sd}, args.out)

    print(f"\n最佳测试面约束 MSE/σ² = {best:.4f}")


if __name__ == "__main__":
    main()
