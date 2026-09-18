#!/usr/bin/env python3
"""
闭环回放（含拓扑事件）—— 比较不同的"溶质转移规则"

=== 要回答的问题 ===

面消失时它携带的溶质给谁、按什么比例分？
面出现时它的溶质从哪来？

守恒只要求"分配比例之和 = 1"，**任何分法都守恒**。
但**分得对不对**会影响结果的准确性——这正是要量化的。

=== 比较的规则 ===

  none    直接丢弃（不守恒）—— 用来展示"不处理会怎样"
  volume  按两侧晶粒的体积分
  area    按该面在两侧晶粒总界面中的占比分
  flux    按两侧晶粒与面的浓度差分（谁浓度高谁往外给）

=== 特征顺序必须与训练脚本一致 ===
  0-2 面静态 | 3 面含量 | 4-6 晶粒i(体积,配位,形状) | 7 i浓度
  8-10 晶粒j(…) | 11 j浓度 | 12-14 dt,体积对比,配位对比 | 15 浓度对比

用法：
    python3 replay_transfer.py <数据集> <模型.pt> --rule volume --t0 600 --t1 1400
"""

import argparse
import csv
import os
from collections import defaultdict

import numpy as np
import torch
import torch.nn as nn

# 特征顺序与 train_rollout_batched.py 共用同一份定义。
# 三处拼特征的地方（训练的数据侧、训练的 rollout 侧、这里的 feats）形状都是
# N_FEAT，**顺序写歪 assert 拦不住**，所以必须从同一个地方取。
from feat_spec import N_FEAT, tier2_features


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
    ap.add_argument("--rule", default="volume",
                    choices=["none", "volume", "area", "flux"])
    ap.add_argument("--t0", type=float, default=None)
    ap.add_argument("--t1", type=float, default=None)
    args = ap.parse_args()

    faces = read_csv(args.ds_dir, "faces.csv")
    grains = read_csv(args.ds_dir, "grains.csv")

    gt, ft = defaultdict(dict), defaultdict(dict)
    for g in grains:
        gt[float(g["time"])][int(g["grain_id"])] = g
    for r in faces:
        ft[float(r["time"])][int(r["face_id"])] = r

    times = sorted(gt.keys())
    t0 = args.t0 if args.t0 is not None else times[0]
    t1 = args.t1 if args.t1 is not None else times[-1]
    win = [t for t in times if t0 <= t <= t1]
    print(f"回放窗口 {win[0]:g} .. {win[-1]:g}（{len(win)} 点），转移规则 = {args.rule}")

    ck = torch.load(args.model, map_location="cpu", weights_only=False)
    mu = np.asarray(ck["mu"], np.float32)
    sd = np.asarray(ck["sd"], np.float32)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    st = ck["state"]
    lin = sorted([k for k in st if k.endswith(".weight")],
                 key=lambda k: int(k.split(".")[1]))
    net = Net(st[lin[0]].shape[1], hidden=st[lin[0]].shape[0],
              depth=len(lin) - 1).to(dev)
    net.load_state_dict(st)
    net.eval()

    G = {f: float(r["solute_excess"]) for f, r in ft[win[0]].items()}
    M = {g: float(r["solute"]) for g, r in gt[win[0]].items()}
    lost_total = 0.0        # 真的丢了（不守恒的规则）
    gained_total = 0.0      # 面/晶粒新建时从别处取来的量
    frozen_total = 0.0      # 曾经经过"晶粒消失"通道的溶质量（诊断用）
    # 名义成分，与算例 IC 一致（V 的原子分数 0.036，2026-09-18 由 0.35 改）。
    # 新晶粒出现时用它给初值。**改算例的 c0 时必须同步改这里。**
    C_NOMINAL = 0.036

    def feats(t, tn, fid, r, gi, gj):
        a, b = gt[t][gi], gt[t][gj]
        vi, vj = float(a["volume"]), float(b["volume"])
        ci, cj = M[gi] / vi, M[gj] / vj
        x = np.array(
            [float(r["area"]), float(r["area_over_Ai"]), float(r["area_over_Aj"]),
             G[fid]]
            + [vi, float(a["n_faces"]), float(a["shape_factor"]), ci]
            + [vj, float(b["n_faces"]), float(b["shape_factor"]), cj]
            + [tn - t, (vi - vj) / (vi + vj + 1e-12),
               float(a["n_faces"]) - float(b["n_faces"]),
               (ci - cj) / (abs(ci) + abs(cj) + 1e-12)]
            # 第二档：T / 取向差 / 对齐度 / 取向。顺序定义在 feat_spec.py，
            # 与 train_rollout_batched.py 共用同一份，避免两处写歪。
            # 温度是**已知输入**（温度场给定），所以这里读参考记录是正确的，
            # 不构成信息泄漏。
            + tier2_features(r, a, b), np.float32)
        assert x.shape[0] == N_FEAT, x.shape
        return x

    # 初始总量（在循环外算好，避免窗口只有 1 个点时 tot0 未绑定）
    tot0 = sum(G.values()) + sum(M.values())

    print()
    print(f"{'t':>8} {'面误差':>10} {'晶粒误差':>10} {'总量漂移':>12} {'事件':>6}")
    print("-" * 54)

    for k in range(len(win) - 1):
        t, tn = win[k], win[k + 1]
        fnow, fnext = ft[t], ft[tn]

        # ---- 0. 晶粒出现/消失：维护 M 的成员集合 ----
        #
        # 【2026-09-17 修】原来 M **只初始化一次、永不增删**，导致两个静默错误：
        #  (a) 消失晶粒的溶质被永久冻结在 M 里。实测 ds_full 有 10 次
        #      grain_disappear，冻结溶质合计 1547.6（占初始总量 0.44%）。
        #      而晶粒误差统计用 `gt[tn]` 过滤，**根本看不见这些晶粒**；
        #      总量 `tot` 却把它们算进去 —— 于是漂移列恒为 0 而物理上错着。
        #      这恰恰是"转移算子"最该回答的问题（晶粒消亡时溶质去哪了），
        #      实验里却完全没建模。
        #  (b) 反方向：如果数据里有**晶粒形核**，新晶粒永远进不了 M，
        #      它的所有面会被 `if gi not in M: continue` **静默跳过**（一点通量都不给），
        #      误差统计也在一个悄悄缩小的子集上报告。
        #      ds_full 新晶粒 = 0，所以目前只是潜伏；LPBF 数据大概率会命中。
        cur_grains = set(int(g) for g in gt[tn])
        prev_grains = set(int(g) for g in gt[t])

        # (a) 消失的晶粒：按规则把它剩下的溶质分给邻居
        for g in sorted(prev_grains - cur_grains):
            if g not in M:
                continue
            val = M.pop(g)
            frozen_total += val
            if args.rule == "none":
                lost_total += val
                continue
            # 分给"在 t 时刻与它有面相连、且仍然存在"的晶粒
            nbrs = []
            for r in ft[t].values():
                a, b = int(r["grain_i"]), int(r["grain_j"])
                if a == g and b in M:
                    nbrs.append(b)
                elif b == g and a in M:
                    nbrs.append(a)
            nbrs = sorted(set(nbrs))
            if not nbrs:
                lost_total += val          # 没有邻居可接，只能记为丢失
                continue
            for nb in nbrs:
                M[nb] = M.get(nb, 0.0) + val / len(nbrs)

        # (b) 新出现的晶粒：插入 M（初值按名义成分，与 IC 一致）
        for g in sorted(cur_grains - prev_grains):
            if g not in M:
                M[g] = C_NOMINAL * float(gt[tn][g]["volume"])
                gained_total += M[g]

        # ---- 1. 面消失：按规定规则分配 ----
        gone = [f for f in fnow if f not in fnext]
        for fid in gone:
            r = fnow[fid]
            gi, gj = int(r["grain_i"]), int(r["grain_j"])
            if gi not in M or gj not in M:
                G.pop(fid, None)
                continue
            val = G.get(fid, 0.0)
            G.pop(fid, None)
            if args.rule == "none":
                lost_total += val
                continue
            vi = float(gt[t][gi]["volume"])
            vj = float(gt[t][gj]["volume"])
            if args.rule == "volume":
                wi = vi / (vi + vj + 1e-30)
            elif args.rule == "area":
                ai = float(r["area_over_Ai"])
                aj = float(r["area_over_Aj"])
                wi = ai / (ai + aj + 1e-30)
            else:  # flux：浓度高的往外给
                ci, cj = M[gi] / vi, M[gj] / vj
                d = ci - cj
                wi = 0.5 + 0.5 * np.tanh(d / (abs(ci) + abs(cj) + 1e-12))
            M[gi] = M.get(gi, 0.0) + val * wi
            M[gj] = M.get(gj, 0.0) + val * (1 - wi)

        # ---- 2. 常规演化 ----
        X, keys = [], []
        for fid, r in fnow.items():
            if fid not in fnext:
                continue
            gi, gj = int(r["grain_i"]), int(r["grain_j"])
            if gi not in M or gj not in M:
                continue
            if fid not in G:
                G[fid] = float(r["solute_excess"])
            X.append(feats(t, tn, fid, r, gi, gj))
            keys.append((fid, gi, gj))
        if X:
            with torch.no_grad():
                J = net(torch.tensor((np.array(X, np.float32) - mu) / sd,
                                     device=dev)).cpu().numpy()
            for i, (fid, gi, gj) in enumerate(keys):
                dG = float(J[i])
                G[fid] = G.get(fid, 0.0) + dG
                vi = float(gt[t][gi]["volume"])
                vj = float(gt[t][gj]["volume"])
                wi = vi / (vi + vj + 1e-30)
                M[gi] = M.get(gi, 0.0) - dG * wi
                M[gj] = M.get(gj, 0.0) - dG * (1 - wi)

        # ---- 3. 面出现：按规定规则给初值 ----
        #
        # 【2026-09-17 修正 —— 原实现有两个问题】
        #  (a) 非 none 分支是**空实现**：`take = 0.0` 是死变量，
        #      注释写着"从两侧晶粒按体积取一点"，代码里根本没有。
        #  (b) 更严重：`none` 规则反而拿到**参考真值**，而 none 恰恰是
        #      这个实验要否定的那个规则 —— 它从第一步起就系统性占便宜，
        #      于是"哪个规则更好"的结论从一开始就不成立。
        #      而且 none 的不守恒还被漂移列掩盖了：新面从真值补回来的质量
        #      几乎抵消掉丢弃的质量（实测丢 493.6，漂移列却只有 +6.7e-05）。
        #
        # 现在：none 真的一律不处理（给 0、也不从晶粒扣）；
        #       其余规则都从两侧晶粒取同一份额，**规则只决定 i/j 怎么分** ——
        #       这样四条规则才可比。
        #
        # ⚠️ 取的"量"仍是**占位实现**：真正正确的答案应该由参考解给出
        #    "新面实际继承了多少"，那需要从相场数据标定，属于转移算子的学习目标。
        new = [f for f in fnext if f not in fnow]
        for fid in new:
            r = fnext[fid]
            gi, gj = int(r["grain_i"]), int(r["grain_j"])
            if gi not in M or gj not in M:
                G[fid] = 0.0
                continue
            if args.rule == "none":
                G[fid] = 0.0                      # 真的不处理
                continue
            vi = float(gt[tn][gi]["volume"])
            vj = float(gt[tn][gj]["volume"])
            if args.rule == "volume":
                wi = vi / (vi + vj + 1e-30)
            elif args.rule == "area":
                ai = float(r["area_over_Ai"])
                aj = float(r["area_over_Aj"])
                wi = ai / (ai + aj + 1e-30)
            else:  # flux：浓度高的往外给
                ci, cj = M[gi] / vi, M[gj] / vj
                d = ci - cj
                wi = 0.5 + 0.5 * np.tanh(d / (abs(ci) + abs(cj) + 1e-12))
            # 取的量：两侧晶粒含量之和的 2%（与规则无关，守恒：取多少扣多少）
            take = 0.02 * (M[gi] + M[gj])
            G[fid] = take
            M[gi] = M.get(gi, 0.0) - take * wi
            M[gj] = M.get(gj, 0.0) - take * (1 - wi)
            gained_total += take

        # ---- 4. 误差 ----
        common = [f for f in fnext if f in G]
        ref_f = np.array([float(fnext[f]["solute_excess"]) for f in common])
        my_f = np.array([G[f] for f in common])
        fe = np.sqrt(((my_f - ref_f) ** 2).mean()) / (np.sqrt((ref_f ** 2).mean()) + 1e-30)

        gs = {g: float(r["solute"]) for g, r in gt[tn].items() if g in M}
        if gs:
            rg = np.array(list(gs.values()))
            mg = np.array([M[g] for g in gs])
            ge = np.sqrt(((mg - rg) ** 2).mean()) / (np.sqrt((rg ** 2).mean()) + 1e-30)
        else:
            ge = float("nan")

        tot = sum(G.values()) + sum(M.values())
        # 漂移相对**真正的初始总量**（tot0 在循环外算好）。
        # 原来在 k==0 时把 tot0 赋成"走完第一步之后"的总量，
        # 会把第一步的丢质藏进基准里。
        print(f"{tn:>8.0f} {fe:>10.4f} {ge:>10.4f} "
              f"{(tot - tot0) / abs(tot0):>+12.2e} {len(gone):>6}")

    print()
    print(f"规则 [{args.rule}]")
    print(f"  面消失丢弃总量     {lost_total:.6g}   （非零即不守恒）")
    print(f"  新面/新晶粒取用总量 {gained_total:.6g}   （从晶粒取，守恒）")
    print(f"  经过晶粒消亡通道    {frozen_total:.6g}   "
          f"（占初始总量 {100*frozen_total/(abs(tot0)+1e-30):.3g}%）")
    print()
    print("判读指引【2026-09-17 修正】：")
    print("  ⚠ 不要用'总量漂移'列判守恒 —— 新面从晶粒取的质量会抵消")
    print("    消失面丢弃的质量，两者互相掩盖（实测丢 493.6 而漂移列只有 6.7e-05）。")
    print("    判守恒要看上面这两行：容量守恒的规则两者都应为 0（或严格配对）。")
    print("  比较不同规则下的'面误差'与'晶粒误差'—— 量化分配规则的影响。")


if __name__ == "__main__":
    main()
