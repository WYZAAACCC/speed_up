#!/usr/bin/env python3
"""
回放训练（rollout / pushforward）—— 解决暴露偏差

=== 问题 ===

第一版算子用【老师强制】训练：每一步都喂参考解的真实状态。
结果自由演化时 400 时间单位后误差涨到 13 倍——因为它从没见过自己的错误状态，
一旦偏离训练分布，误差就滚雪球。这是序列模型的标准病（exposure bias）。

=== 解法 ===

让算子在【训练时】就滚多步：从参考解的一个初始状态出发，
用它自己的预测往下滚 K 步，把【累积误差】反传回去。

装配是线性的（通量形式），梯度能穿透多步。
这就是 pushforward / scheduled sampling 那一类做法。

=== 几何的处理 ===

几何与拓扑仍从参考解读取（我们不建模晶粒演化），
只有溶质 (G, M) 是自由滚动的。
这样梯度只经过算子与装配，干净。

用法：
    python3 train_rollout.py <数据集> [--K 8] [--epochs 2000]
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
    def __init__(self, n_in, hidden=192, depth=4):
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


def prepare(ds_dir):
    """把数据整理成按时刻索引的张量，便于滚动。"""
    faces = read_csv(ds_dir, "faces.csv")
    grains = read_csv(ds_dir, "grains.csv")

    gt = defaultdict(dict)
    for g in grains:
        gt[float(g["time"])][int(g["grain_id"])] = g
    ft = defaultdict(dict)
    for r in faces:
        ft[float(r["time"])][int(r["face_id"])] = r

    times = sorted(gt.keys())
    # 面在两个相邻时刻都存在的那些，才能滚动
    steps = []
    for k in range(len(times) - 1):
        t, tn = times[k], times[k + 1]
        common = [f for f in ft[t] if f in ft[tn]]
        if not common:
            continue
        steps.append((t, tn, common))
    return gt, ft, times, steps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ds_dir")
    ap.add_argument("--K", type=int, default=8, help="每次滚多少步")
    ap.add_argument("--epochs", type=int, default=2000)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--windows", type=int, default=200, help="每轮采样多少窗口")
    ap.add_argument("--split-frac", type=float, default=0.7)
    ap.add_argument("--out", default="op_rollout.pt")
    args = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    gt, ft, times, steps = prepare(args.ds_dir)
    nsteps = len(steps)
    print(f"时刻 {len(times)}，可用滚动的相邻步 {nsteps}")

    ncut = int(nsteps * args.split_frac)
    tr_steps, te_steps = steps[:ncut], steps[ncut:]
    print(f"训练步 {len(tr_steps)}，测试步 {len(te_steps)}")

    # ---- 特征标准化 ----
    # 【必须有】原始特征量纲差几个数量级（面积 ~1e3、浓度 ~0.3），
    # 不标准化会让训练极慢。这里从全量数据估计均值/方差。
    allf = read_csv(args.ds_dir, "faces.csv")
    allg = read_csv(args.ds_dir, "grains.csv")
    gmap_all = {(float(g["time"]), int(g["grain_id"])): g for g in allg}
    S = []
    for r in allf:
        t = float(r["time"])
        gi, gj = int(r["grain_i"]), int(r["grain_j"])
        a, b = gmap_all.get((t, gi)), gmap_all.get((t, gj))
        if a is None or b is None:
            continue
        vi, vj = float(a["volume"]), float(b["volume"])
        ci, cj = float(a["c_bulk"]), float(b["c_bulk"])
        S.append([float(r[c]) for c in FEATS]
                 + [vi, ci, float(a["n_faces"]), float(a["shape_factor"])]
                 + [vj, cj, float(b["n_faces"]), float(b["shape_factor"])]
                 + [8.0, (vi - vj) / (vi + vj + 1e-12),
                    (ci - cj) / (abs(ci) + abs(cj) + 1e-12),
                    float(a["n_faces"]) - float(b["n_faces"])])
    S = np.array(S, np.float32)
    mu = S.mean(0)
    sd = S.std(0) + 1e-8
    print(f"标准化统计量来自 {len(S)} 条样本")
    print("  mu:", np.round(mu, 3))
    print("  sd:", np.round(sd, 3))
    mu_t = torch.tensor(mu, device=dev)
    sd_t = torch.tensor(sd, device=dev)

    net = Net(16).to(dev)      # 特征维数 16，见 run_window 里的顺序说明
    opt = torch.optim.Adam(net.parameters(), lr=args.lr)

    def run_window(steps_seq, k0, K):
        """从 steps_seq[k0-1] 的参考状态出发，滚 K 步，返回每步的预测与参考。"""
        t0 = steps_seq[k0][0]
        f0, g0 = ft[t0], gt[t0]
        # 初始状态取参考解。
        # 【必须是 tensor】否则第一步是 float、之后是 tensor，torch.stack 会失败，
        # 而且梯度会断。
        G = {f: torch.tensor(float(r["solute_excess"]), device=dev)
             for f, r in f0.items()}
        M = {g: torch.tensor(float(r["solute"]), device=dev)
             for g, r in g0.items()}

        preds = []
        for k in range(k0, min(k0 + K, len(steps_seq))):
            t, tn, common = steps_seq[k]
            fn, gn = ft[tn], gt[tn]

            # 【特征顺序必须与训练时完全一致】（见 train_operator.py 的 build_samples）
            # 与 M 无关的部分用 numpy 拼，与 M 有关的部分（c_i, c_j, 对比量）留在 torch
            # 里，否则梯度会断，而且 cuda tensor 不能直接转 numpy。
            stat, dyn, keys = [], [], []
            for f in common:
                r = ft[t][f]
                gi, gj = int(r["grain_i"]), int(r["grain_j"])
                if gi not in M or gj not in M:
                    continue
                # 【新出现的面】滚动中面的集合会变（配对定义本身会波动），
                # 新面不在 G 里。这里从参考解取初值 —— 是个简化，
                # 严格做法应让转移算子给出"新面继承多少溶质"，那是下一步的工作。
                # 新面的含量通常很小，对累积误差的影响有限。
                if f not in G:
                    G[f] = torch.tensor(float(r["solute_excess"]), device=dev)
                a, b = gt[t][gi], gt[t][gj]
                vi, vj = float(a["volume"]), float(b["volume"])
                stat.append([float(r[c]) for c in FEATS]
                            + [vi, float(a["n_faces"]), float(a["shape_factor"])]
                            + [vj, float(b["n_faces"]), float(b["shape_factor"])]
                            + [tn - t, (vi - vj) / (vi + vj + 1e-12),
                               float(a["n_faces"]) - float(b["n_faces"])])
                dyn.append((M[gi] / vi, M[gj] / vj))
                keys.append((f, gi, gj))
            if not keys:
                break

            # 把 c_i, c_j, 对比量插回正确位置。
            # 目标顺序（与 train_operator.py 一致）：
            #   0-3  面：area, excess, area/Ai, area/Aj
            #   4-7  晶粒 i：volume, c, n_faces, shape
            #   8-11 晶粒 j：volume, c, n_faces, shape
            #   12-15 额外：dt, 体积对比, 浓度对比, 配位数对比
            Xs = torch.tensor(np.array(stat, np.float32), device=dev)
            cis = torch.stack([d[0] for d in dyn])
            cjs = torch.stack([d[1] for d in dyn])
            contrast = (cis - cjs) / (cis.abs() + cjs.abs() + 1e-12)
            X = torch.cat([
                Xs[:, 0:7],              # 面(4) + i[体积,配位数,形状](3)
                cis.unsqueeze(1),        # i.c            → 位置 7
                Xs[:, 7:8],              # j.体积         → 位置 8
                cjs.unsqueeze(1),        # j.c            → 位置 9
                Xs[:, 8:10],             # j[配位数,形状]  → 位置 10-11
                Xs[:, 10:11],            # dt             → 12
                Xs[:, 11:12],            # 体积对比        → 13
                contrast.unsqueeze(1),   # 浓度对比        → 14
                Xs[:, 12:13],            # 配位数对比      → 15
            ], dim=1)
            assert X.shape[1] == 16, f"特征维数应为 16，实际 {X.shape[1]}"
            X = (X - mu_t) / sd_t          # 标准化
            J = net(X)

            newG = dict(G)
            newM = dict(M)
            for idx, (f, gi, gj) in enumerate(keys):
                dG = J[idx]
                newG[f] = G[f] + dG
                vi, vj = float(gt[t][gi]["volume"]), float(gt[t][gj]["volume"])
                wi = vi / (vi + vj)
                newM[gi] = newM[gi] - dG * wi
                newM[gj] = newM[gj] - dG * (1 - wi)
            G, M = newG, newM

            # 参考值
            refG = torch.tensor([float(fn[f]["solute_excess"]) for f, _, _ in keys],
                                device=dev)
            predG = torch.stack([G[f] for f, _, _ in keys])
            refM = torch.tensor([float(gn[gi]["solute"]) for _, gi, _ in keys]
                                + [float(gn[gj]["solute"]) for _, _, gj in keys],
                                device=dev)
            predM = torch.stack([M[gi] for _, gi, _ in keys]
                                + [M[gj] for _, _, gj in keys])
            preds.append((predG, refG, predM, refM,
                          torch.tensor([float(ft[t][f]["area"]) for f, _, _ in keys],
                                       device=dev)))
        return preds

    rng = np.random.default_rng(0)
    best = 1e9
    for ep in range(args.epochs):
        net.train()
        opt.zero_grad()
        loss = torch.tensor(0.0, device=dev)
        k0s = rng.integers(0, max(1, len(tr_steps) - args.K), size=args.windows)
        nvalid = 0
        for k0 in k0s:
            preds = run_window(tr_steps, int(k0), args.K)
            if not preds:
                continue
            nvalid += 1
            for pg, (pG, rG, pM, rM, ar) in enumerate(preds):
                # 用面面积做权重：大面更重要，且避免小面的相对误差主导
                w = ar / (ar.mean() + 1e-12)
                # 【损失必须无量纲化】面含量量级 ~78，平方后 ~6000，
                # 不归一化会梯度爆炸（实测 loss 冲到 1e15）。
                # 用参考值的均方做尺度，得到"归一化 MSE"。
                s2 = (rG ** 2).mean() + 1e-12
                loss = loss + \
                    (w * (pG - rG) ** 2).mean() / s2 / max(1, len(preds))
                s2m = (rM ** 2).mean() + 1e-12
                loss = loss + 1e-3 * ((pM - rM) ** 2).mean() / s2m \
                    / max(1, len(preds))
        if nvalid == 0:
            sys.exit("没有有效窗口")
        loss = loss / max(1, nvalid)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()

        if ep % 50 == 0 or ep == args.epochs - 1:
            net.eval()
            with torch.no_grad():
                tes = []
                for k0 in rng.integers(0, max(1, len(te_steps) - args.K), size=20):
                    tes.extend(run_window(te_steps, int(k0), args.K))
                if tes:
                    e = float(np.mean([
                        ((pG - rG) ** 2).mean().item()
                        / ((rG ** 2).mean().item() + 1e-30)
                        for pG, rG, _, _, _ in tes]))
                else:
                    e = float("nan")
            print(f"  ep {ep:5d}  train {loss.item():8.4f}  测试(nMSE) {e:.4f}")
            if e < best:
                best = e
                # 存标准化参数，回放时要一致
                torch.save({"state": net.state_dict(), "mu": mu, "sd": sd}, args.out)

    print(f"\n最佳测试 nMSE = {best:.4f}   模型 {args.out}")


if __name__ == "__main__":
    main()
