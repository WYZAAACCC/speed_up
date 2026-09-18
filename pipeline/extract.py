#!/usr/bin/env python3
"""
从 MOOSE 的 Exodus 输出提取「晶粒图 + 逐面溶质」数据集。
产出直接可供逐面神经算子训练的特征与标签。

=== 核心思路 ===

相场里晶界是弥散的，所以"一个面"这样定义：

    元素 → 晶粒 ID（unique_grains 辅助变量）
    共享一个面（3D）或一条边（2D）的相邻元素，晶粒 ID 不同 → 晶界元素
    同一晶粒对 (i,j) 的连通晶界元素集合 = 一个面 f

于是"面"等价于晶粒图上的一条边，拓扑变化退化成图的增删。

=== 输出（都按 (time, id) 索引，可直接拼接成时间序列）===

grains.csv   逐晶粒：
    time, grain_id, volume, solute, c_bulk, centroid_x/y[/z],
    n_faces(配位数), face_area_total(晶粒总晶界面积), shape_factor,
    T_avg, age, theta_deg(晶体取向)

faces.csv    逐面（**这是算子训练的主表**）：
    time, face_id, grain_i, grain_j, area, solute_excess,
    centroid_x/y[/z], area_over_Ai, area_over_Aj,
    d_area, d_excess            ← 相对上一步的变化（标签来源）
    T_avg, dir_x/y, v_x/y, age
    dtheta_deg, align_i, align_j, grad_x, grad_y, align_moose

events.csv   拓扑事件：面的出现/消失、晶粒的出现/消失
conservation.csv  自洽性检查

=== 第二档列的来源（theta / dtheta / align / grad）===

这些列需要算例输出 orient_cos / orient_sin / grad_Tx / grad_Ty / grad_align
（`stage1_meltpool_d.i` 才有）。在 C 版数据上运行时**优雅退化**为 NaN 列，
不会崩 —— 因为重跑老数据集是常规操作。

* theta_deg —— 把 eta^2 加权的取向场在晶粒内体积平均，再用 atan2 反解。
  用 atan2(平均) 而不是平均角度：角度有 0/90 缠绕。
  **对 GrainTracker 的重映射免疫** —— 它读的是场，不是"序参量->取向"表。
* dtheta_deg —— 两侧晶粒取向差，四重对称取到 [0,45]。
  这是 2a 的驱动物理量（Read-Shockley 因子由它决定）。
* align_i/j —— 各晶粒易生长轴与热梯度方向的四重对齐度 cos^2(2(phi-theta))。
  这是 2b 的驱动物理量。用四重而非二重：beta-Ti 的 <100> 在 2D 是四重对称，
  二重形式会把 theta 与 theta+90 判成不同取向。
* grad_x/grad_y —— **extract.py 从解析式独立复算**，同时在启动时与 Exodus 里的
  grad_Tx/grad_Ty 交叉校验（相对偏差应 < 1e-6）。

用法：
    python3 extract.py <exodus> [--out 目录] [--stride 1]
"""

import argparse
import csv
import math
import os
import sys
from collections import defaultdict

import numpy as np
from netCDF4 import Dataset

# ---------------------------------------------------------------------------
# 第二档（2a 取向差 / 2b 热梯度选择）用到的独立复算工具
#
# 这些函数**刻意不依赖 MOOSE 的输出**，而是从解析式重算一遍，
# 用于和 Exodus 里的 grad_Tx / grad_Ty / grad_align 交叉校验。
# 若两者不一致，说明算例里的场和这里理解的不是一个东西。
# ---------------------------------------------------------------------------

# Rosenthal 场参数 —— 必须与 stage1_meltpool_d.i 的 laser_T 逐字一致
_ROS_C = 28.0 / (2.0 * math.pi * 20.0)   # eta*P/(2*pi*k)
_ROS_K = 0.6 / (2.0 * 6.0e-6)            # v/(2*alpha)
_ROS_XL0 = 1.2e-4                        # 激光初始位置（注意场里写的是 +1.2e-4）
_ROS_V = 0.6                             # 扫描速度


def rosenthal_grad(x, y, t):
    """温度场的解析梯度（与算例同一个场的解析导数）。

        T - T0 = (C/R)exp(-k(R+xi)),  xi = x + 1.2e-4 - 0.6t,  R = sqrt(xi^2+y^2+eps)
        dT/dx = (C/R)e^{-k(R+xi)} * ( -xi/R^2 - k(R+xi)/R )
        dT/dy = (C/R)e^{-k(R+xi)} * ( -y/R^2  - k*y/R    )
    """
    xi = x + _ROS_XL0 - _ROS_V * t
    r2 = xi * xi + y * y + 1e-10
    r = math.sqrt(r2)
    pre = _ROS_C / r * math.exp(-_ROS_K * (r + xi))
    gx = pre * (-xi / r2 - _ROS_K * (r + xi) / r)
    gy = pre * (-y / r2 - _ROS_K * y / r)
    return gx, gy


def misorientation_deg(ta, tb):
    """四重对称下的取向差，落在 [0, 45]。beta-Ti 的 <100> 在 2D 有四重对称，
    所以 theta 与 theta+90 是同一个取向。"""
    if not (np.isfinite(ta) and np.isfinite(tb)):
        return float("nan")
    d = abs(ta - tb) % 90.0
    return min(d, 90.0 - d)


def align4_deg(theta_deg, gx, gy):
    """取向 theta 的易生长轴与热梯度方向的四重对齐度 cos^2(2(phi-theta)) ∈ [0,1]。

    用四重而非二重：二重形式会把 theta 与 theta+90 判成不同取向 —— 错。
    """
    if not np.isfinite(theta_deg) or (gx == 0.0 and gy == 0.0):
        return float("nan")
    phi = math.degrees(math.atan2(gy, gx))
    return math.cos(math.radians(2.0 * (phi - theta_deg))) ** 2

# ---------------------------------------------------------------------------
# 单元类型的面（3D）/ 边（2D），用局部节点编号
# ---------------------------------------------------------------------------
FACES_BY_TYPE = {
    "quad4": [(0, 1), (1, 2), (2, 3), (3, 0)],
    "hex8": [
        (0, 1, 2, 3), (4, 5, 6, 7),
        (0, 1, 5, 4), (1, 2, 6, 5),
        (2, 3, 7, 6), (3, 0, 4, 7),
    ],
}


def decode_names(ds, key):
    """Exodus 用 NUL 补齐名字，要同时去掉 NUL 和空白。"""
    if key not in ds.variables:
        return []
    out = []
    for row in ds.variables[key][:]:
        try:
            s = b"".join(row).decode("utf-8", "replace")
        except Exception:
            s = str(row)
        out.append(s.replace("\x00", "").strip())
    return out


def find_var(ds, name):
    """返回 (kind, index)；kind ∈ {'elem','nod'}，index 从 1 开始。"""
    for i, n in enumerate(decode_names(ds, "name_elem_var"), 1):
        if n == name:
            return "elem", i
    for i, n in enumerate(decode_names(ds, "name_nod_var"), 1):
        if n == name:
            return "nod", i
    return None, None


def read_var(ds, kind, idx):
    """
    读变量值。

    【⚠️ 必须遍历所有单元块】Exodus 按 subdomain 分块存储：
    连接表是 connect1/connect2/...，单元变量是 vals_elem_var{j}eb{k}。
    旧版把 "eb1" 写死 —— 单块网格上没问题，但**多块网格会静默漏数据**。
    实测 LPBF 算例里熔池是独立 block（占 15.9% 的单元），
    漏掉它等于把整个凝固区丢掉，而且不会报任何错。
    """
    if kind != "elem":
        key = f"vals_{kind}_var{idx}"
        if key not in ds.variables:
            sys.exit(f"找不到变量 {key}")
        return np.asarray(ds.variables[key][:])

    blocks, k = [], 1
    while f"connect{k}" in ds.variables:
        for key in (f"vals_elem_var{idx}eb{k}", f"vals_elem_var{idx}"):
            if key in ds.variables:
                blocks.append(np.asarray(ds.variables[key][:]))
                break
        k += 1
    if not blocks:
        sys.exit(f"找不到单元变量 vals_elem_var{idx}")
    return np.concatenate(blocks, axis=-1)


def read_all_element_blocks(ds):
    """
    拼出**所有**单元块的连接表。返回 (connect, block_ids)。

    与 read_var 同样的理由：只读 connect1 会静默漏掉其它 subdomain。
    """
    eb_prop = (np.asarray(ds.variables["eb_prop1"][:]).ravel()
               if "eb_prop1" in ds.variables else [])
    conns, bids, k = [], [], 1
    while f"connect{k}" in ds.variables:
        conns.append(np.asarray(ds.variables[f"connect{k}"][:], dtype=np.int64) - 1)
        bids.append(int(eb_prop[k - 1]) if k - 1 < len(eb_prop) else k - 1)
        k += 1
    if not conns:
        sys.exit("找不到任何 connect{k} 块")
    return np.concatenate(conns), bids


def build_adjacency(connect, elem_type):
    """元素-元素邻接：共享一个面/边的元素互为邻居。"""
    faces = FACES_BY_TYPE[elem_type]
    face_map = defaultdict(list)
    for e, nodes in enumerate(connect):
        for f in faces:
            key = tuple(sorted(int(nodes[i]) for i in f))
            face_map[key].append(e)

    neighbors = defaultdict(list)
    for elems in face_map.values():
        if len(elems) == 2:
            a, b = elems
            neighbors[a].append(b)
            neighbors[b].append(a)
        elif len(elems) > 2:
            for i in range(len(elems)):
                for j in range(i + 1, len(elems)):
                    neighbors[elems[i]].append(elems[j])
                    neighbors[elems[j]].append(elems[i])
    return neighbors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exodus")
    ap.add_argument("--out", default="dataset")
    ap.add_argument("--grain-var", default="unique_grains")
    ap.add_argument("--solute-var", default="c")
    ap.add_argument("--stride", type=int, default=1, help="每隔几步取一个时间点")
    ap.add_argument("--min-area", type=float, default=None,
                    help="面面积下限（单位：单元测度）。小于它的面视为数值噪声。"
                         "默认 = 3 个单元")
    ap.add_argument("--persist", type=int, default=2,
                    help="判定面'真的消失'需要连续缺席的时间点数")
    ap.add_argument("--temp-var", default="T",
                    help="温度变量名（节点变量）。提取不出来就自动跳过。")
    args = ap.parse_args()

    ds = Dataset(args.exodus, "r")

    # ---- 网格（所有单元块，不只是 connect1）----
    connect, block_ids = read_all_element_blocks(ds)
    n_elem, npe = connect.shape
    coord = np.column_stack([
        np.asarray(ds.variables[f"coord{a}"][:], dtype=float)
        for a in "xyz" if f"coord{a}" in ds.variables
    ])
    dim = coord.shape[1]
    elem_type = {4: "quad4", 8: "hex8"}.get(npe)
    if elem_type is None:
        sys.exit(f"不支持的单元类型（每单元 {npe} 个节点）")
    # 分块情况写清楚 —— 多块网格是漏数据的高危场景，要肉眼可见
    src = "子域 ".join(str(b) for b in block_ids)
    print(f"网格: {n_elem} 单元, {dim}D, 类型 {elem_type}, "
          f"{len(block_ids)} 个单元块（subdomain {src}）")

    # ---- 单元体积/面积 ----
    def cross2d(a, b):
        return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]

    p = coord[connect]
    _ = p  # 见下方使用
    if dim == 2:
        a1 = 0.5 * np.abs(cross2d(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]))
        a2 = 0.5 * np.abs(cross2d(p[:, 2] - p[:, 0], p[:, 3] - p[:, 0]))
        elem_measure = a1 + a2
    else:
        elem_measure = np.abs(np.einsum(
            "ij,ij->i", p[:, 6] - p[:, 0], np.cross(p[:, 1] - p[:, 0], p[:, 3] - p[:, 0])
        )) / 3.0
    print(f"域的总测度: {elem_measure.sum():.6g}")

    # 面的面积下限：默认 3 个单元。小于它的视为弥散界面碎片
    min_area = args.min_area if args.min_area is not None else 3.0 * float(elem_measure.mean())
    print(f"面的面积下限: {min_area:.4g}（{min_area/elem_measure.mean():.1f} 个单元）")

    # ---- 变量 ----
    gk, gi = find_var(ds, args.grain_var)
    sk, si = find_var(ds, args.solute_var)
    if gk is None or sk is None:
        sys.exit(f"找不到变量 {args.grain_var} 或 {args.solute_var}")
    grains_ts = read_var(ds, gk, gi)
    solute_ts = read_var(ds, sk, si)
    # 序参量（用于平滑晶界权重）—— 必须在 ds.close() 之前读
    eta_names = [n for n in decode_names(ds, "name_nod_var") if n.startswith("gr")]
    eta_arrs = []
    for n in eta_names:
        ek, ei = find_var(ds, n)
        eta_arrs.append(read_var(ds, ek, ei).astype(float))
    # ---- 温度场（节点变量，算子必需的输入之一）----
    # 设计文档 §三C 把温度列为"必需"。LPBF 里温度直接决定迁移率与凝固驱动力，
    # 而且柱状晶的取向竞争正是"最大温度梯度方向"决定的。
    tk, ti = find_var(ds, args.temp_var)
    temp_ts = read_var(ds, tk, ti) if tk is not None else None

    # ---- 第二档（2a/2b）新增量：取向场与热梯度 ----
    # 只有 D 版算例输出这些；在 C 版数据上必须优雅退化（相应列全 NaN），
    # 否则重跑老数据集会直接崩。
    def _elem_var(name):
        k, i = find_var(ds, name)
        return read_var(ds, k, i).astype(float) if k is not None else None

    oc_ts = _elem_var("orient_cos")     # eta^2 加权的 cos(theta)
    os_ts = _elem_var("orient_sin")     # eta^2 加权的 sin(theta)
    gx_ts = _elem_var("grad_Tx")        # MOOSE 算的 dT/dx
    gy_ts = _elem_var("grad_Ty")        # MOOSE 算的 dT/dy
    ga_ts = _elem_var("grad_align")     # MOOSE 材料里实际用的 align4

    time = np.asarray(ds.variables["time_whole"][:], dtype=float)
    if grains_ts.ndim == 1:
        grains_ts = grains_ts[None, :]
    if solute_ts.ndim == 1:
        solute_ts = solute_ts[None, :]
    if temp_ts is not None and temp_ts.ndim == 1:
        temp_ts = temp_ts[None, :]
    ds.close()

    nt = min(len(time), grains_ts.shape[0], solute_ts.shape[0])
    if sk == "nod":
        elemsol = np.stack([solute_ts[t][connect].mean(axis=1) for t in range(nt)])
    else:
        elemsol = solute_ts[:nt]

    # ---- 温度场（节点变量，算子必需的输入之一）----
    # 设计文档 §三C 把温度列为"必需"：LPBF 里温度直接决定迁移率与凝固驱动力，
    # 而柱状晶的取向竞争正是"最大温度梯度方向"决定的。
    if temp_ts is None:
        print(f"警告：找不到温度变量 '{args.temp_var}'，温度相关列将被跳过")
        elemT = None
    elif tk == "nod":
        elemT = np.stack([temp_ts[t][connect].mean(axis=1) for t in range(nt)])
        print(f"温度场: 已读 '{args.temp_var}'（节点变量 -> 单元平均）")
    else:
        elemT = temp_ts[:nt]
        print(f"温度场: 已读 '{args.temp_var}'（单元变量）")

    # ---- 第二档量的对齐与切片 ----
    def _clip(a):
        if a is None:
            return None
        if a.ndim == 1:
            a = a[None, :]
        return a[:nt]

    # 用全新名字接收，避免复用旧名导致静态分析无法收窄（旧名此后再不出现）
    OC, OS = _clip(oc_ts), _clip(os_ts)
    GX, GY, GA = _clip(gx_ts), _clip(gy_ts), _clip(ga_ts)
    if OC is None or GX is None:
        print("提示：未找到第二档变量（orient_cos / grad_Tx 等）——"
              "多半是 C 版数据；theta/dtheta/align 列将写 NaN")
    else:
        print("第二档: 已读 orient_cos/orient_sin/grad_Tx/grad_Ty/grad_align")
        # 供类型收窄；同时保证下面循环里的下标访问一定安全
        assert OC is not None and OS is not None and GX is not None and GY is not None

        # ---- 交叉校验：MOOSE 的梯度 vs extract.py 的解析复算 ----
        # 这是 2b 真实性的关键检查 —— 若两者不符，说明算例里用的梯度
        # 和"从温度场解析求导"不是一回事。
        elem_cen = coord[connect].mean(axis=1)
        t_chk = float(time[nt - 1])
        gxa = np.empty(n_elem)
        gya = np.empty(n_elem)
        for e in range(n_elem):
            gxa[e], gya[e] = rosenthal_grad(elem_cen[e, 0], elem_cen[e, 1], t_chk)
        for nm, mo, an in (("grad_Tx", GX[nt - 1], gxa),
                           ("grad_Ty", GY[nt - 1], gya)):
            sc = max(float(np.abs(an).max()), 1e-30)
            err = float(np.abs(mo - an).max()) / sc
            print(f"  交叉校验 {nm}: 最大相对偏差 {err:.3e} "
                  f"{'OK' if err < 1e-6 else '**不一致**'}")

    print(f"时间步 {nt}，t = {time[0]:g} .. {time[nt-1]:g}，采样间隔 {args.stride}")

    # ------------------------------------------------------------------
    # 【平滑的面权重 —— 降标签噪声的关键】
    #
    # 硬阈值切面（"邻居晶粒 ID 不同 = 晶界元素"）会带来定义噪声：
    # 面边缘的元素在阈值附近反复进出，导致面含量高频抖动。
    # 实测：二阶差分与一阶差分同量级（比值 ~1.0），且阈值一变噪声就变。
    #
    # 改用连续的晶界权重：
    #     w_e = 2·(1 − Σ_i η_i²)
    # 体相 Ση²=1 → w=0；晶界中心 Ση²=0.5 → w=1。
    # 权重是序参量的连续函数，对阈值不敏感，从源头压掉抖动。
    # ------------------------------------------------------------------
    if eta_arrs:
        gbw = np.zeros((nt, n_elem))
        for t in range(nt):
            s2 = np.zeros_like(eta_arrs[0][t])
            for e_arr in eta_arrs:
                s2 = s2 + e_arr[t] ** 2
            gbw[t] = 2.0 * np.clip(1.0 - s2, 0.0, 0.5)[connect].mean(axis=1)
        print(f"已计算平滑晶界权重（{len(eta_names)} 个序参量），"
              f"范围 {gbw.min():.3f} ~ {gbw.max():.3f}")
    else:
        gbw = None
        print("警告：找不到序参量，退回硬阈值定义")

    # ---- 邻接（拓扑固定，只算一次）----
    print("建立元素邻接...")
    neighbors = build_adjacency(connect, elem_type)
    # 转成扁平数组，便于向量化
    nbr_i, nbr_j = [], []
    for e, lst in neighbors.items():
        for nb in lst:
            if e < nb:
                nbr_i.append(e)
                nbr_j.append(nb)
    nbr_i = np.array(nbr_i, dtype=np.int64)
    nbr_j = np.array(nbr_j, dtype=np.int64)
    print(f"  元素对 {len(nbr_i)} 个")

    # ---- 逐步提取 ----
    grain_rows, face_rows, cons_rows = [], [], []
    prev_faces = {}
    prev_grain_set: set = set()
    prev_face_set: set = set()
    face_id_map = {}       # (i,j) -> 稳定 face_id
    next_face_id = 0
    events = []
    absent = {}            # (i,j) -> 连续缺席计数
    present = {}           # (i,j) -> 连续在场计数
    persist = args.persist
    first = True
    # 第二档自检计数器：取向差为 0 的晶面数（见循环内的说明）
    n_zero_dth = [0]
    grain_first = {}       # 晶粒 -> 首次出现的时刻（算存在时长）
    face_first = {}        # 面 -> 首次出现的时刻
    prev_face_cen = {}     # 面 -> 上一采样点的面心（算迁移速度）
    prev_face_t = None     # 上一采样点的时刻

    iters = list(range(0, nt, args.stride))
    if iters[-1] != nt - 1:
        iters.append(nt - 1)

    for n, it in enumerate(iters):
        gid = np.rint(grains_ts[it]).astype(np.int64)     # 必须取整（浮点 ID 会翻倍）
        c = elemsol[it]
        active = gid >= 0

        # ---- 元素级邻接判断：晶粒 ID 不同即为晶界 ----
        gi_e, gj_e = gid[nbr_i], gid[nbr_j]
        is_gb = active[nbr_i] & active[nbr_j] & (gi_e != gj_e)

        pairs = np.stack([np.minimum(gi_e[is_gb], gj_e[is_gb]),
                          np.maximum(gi_e[is_gb], gj_e[is_gb])], axis=1)
        gb_elem = nbr_i[is_gb]        # 取一侧元素代表这个晶界面元

        # ---- 逐晶粒 ----
        gids = np.unique(gid[active])
        gset = {}
        for g in gids:
            m = gid == g
            vol = elem_measure[m].sum()
            cen = (coord[connect[m]].mean(axis=1) * elem_measure[m][:, None]).sum(0) / vol
            cbulk = float((c[m] * elem_measure[m]).sum() / vol)
            # 平均温度（按面积加权；elemT 是单元量）
            Tavg = (float((elemT[it][m] * elem_measure[m]).sum() / vol)
                    if elemT is not None else float("nan"))
            # 取向：把 eta^2 加权的取向场在晶粒内做体积平均，再反解 theta。
            # 用 atan2(平均值) 而不是平均角度 —— 角度有 0/90 缠绕，直接平均会错。
            if OC is not None and OS is not None:
                cs = float((OC[it][m] * elem_measure[m]).sum() / vol)
                sn = float((OS[it][m] * elem_measure[m]).sum() / vol)
                theta = float(np.degrees(np.arctan2(sn, cs)) % 90.0)
            else:
                theta = float("nan")
            gset[int(g)] = dict(vol=float(vol), cen=cen, c=cbulk, T=Tavg,
                                theta=theta)

        # ---- 逐面 ----
        # 收集每个 (i,j) 对的晶界元素
        # 【平滑加权】用 gbw（连续晶界权重）而不是硬 0/1，压掉面边缘的抖动。
        # 权重是序参量的连续函数，元素在阈值附近进出时贡献平滑变化。
        acc = {}
        for k in range(len(pairs)):
            key = (int(pairs[k, 0]), int(pairs[k, 1]))
            e = int(gb_elem[k])
            w = float(gbw[it][e]) if gbw is not None else 1.0
            if w <= 1e-6:
                continue
            if key not in acc:
                acc[key] = {"area": 0.0, "elems": [], "wts": [], "cen": np.zeros(dim)}
            acc[key]["area"] += w * elem_measure[e]
            acc[key]["elems"].append(e)
            acc[key]["wts"].append(w)
            acc[key]["cen"] += coord[connect[e]].mean(axis=0) * (w * elem_measure[e])

        # 【噪声过滤】面积小于阈值的面是弥散界面上的碎片，不是真实晶界面。
        # 细网格 + 多晶粒时这类碎片会反复闪烁，若不滤掉会污染"拓扑事件"统计。
        face_of = {k: v for k, v in acc.items() if v["area"] >= min_area}

        # 逐晶粒的配位数与总晶界面积
        for g in gset:
            gset[g]["n_faces"] = 0
            gset[g]["A_total"] = 0.0
        for (a, b), d in face_of.items():
            for g in (a, b):
                if g in gset:
                    gset[g]["n_faces"] += 1
                    gset[g]["A_total"] += d["area"]

        # 写晶粒表
        for g, d in gset.items():
            A_tot = d["A_total"] if d["A_total"] > 0 else 1.0
            shape = d["vol"] / A_tot            # 2D: 面积/周长；3D: 体积/表面积
            # 存在时长：从首次出现到现在（"这个晶粒多大了"，帮助判断是否刚生成）
            if g not in grain_first:
                grain_first[g] = float(time[it])
            age = float(time[it]) - grain_first[g]
            grain_rows.append([float(time[it]), g, d["vol"], d["c"] * d["vol"], d["c"],
                               *d["cen"].tolist(), d["n_faces"], d["A_total"], shape,
                               d["T"], age])

        # 写面表（含与上一步的差分 —— 这是算子训练的标签来源）
        cur_faces = {}
        for (a, b), d in face_of.items():
            A = d["area"]
            cen = d["cen"] / A
            ci, cj = gset[a]["c"], gset[b]["c"]
            cbulk = 0.5 * (ci + cj)
            elems = d["elems"]
            wts = np.array(d["wts"])
            # 用同一套平滑权重算过量
            excess = float(((c[elems] - cbulk) * elem_measure[elems] * wts).sum())
            Ai = gset[a]["A_total"] or 1.0
            Aj = gset[b]["A_total"] or 1.0
            cur_faces[(a, b)] = dict(A=A, ex=excess, cen=cen)

            key = (a, b)
            if key not in face_id_map:
                face_id_map[key] = next_face_id
                next_face_id += 1
            fid = face_id_map[key]

            pv = prev_faces.get(key)
            dA = A - pv["A"] if pv else 0.0
            dEx = excess - pv["ex"] if pv else 0.0

            # --- 温度：按同一套平滑权重做加权平均 ---
            if elemT is not None:
                wsum = (elem_measure[elems] * wts).sum()
                Tf = float((elemT[it][elems] * elem_measure[elems] * wts).sum()
                           / (wsum + 1e-30))
            else:
                Tf = float("nan")

            # --- 面心相对晶粒 i 质心的方向（单位向量）---
            # 描述"这个面在晶粒的哪一侧"，是设计文档 §三B 明确要求的量
            dv = cen - gset[a]["cen"]
            nv_ = float(np.linalg.norm(dv))
            dirv = (dv / nv_) if nv_ > 1e-30 else np.zeros(dim)

            # --- 面的迁移速度：面心的时间差分 ---
            # 设计文档 §三A 的"迁移速度"，由面位置时间差分得到
            pc = prev_face_cen.get(key)
            if pc is not None and prev_face_t is not None:
                dtf = float(time[it]) - prev_face_t
                vel = (cen - pc) / dtf if dtf > 1e-30 else np.zeros(dim)
            else:
                vel = np.zeros(dim)

            # --- 存在时长 ---
            if key not in face_first:
                face_first[key] = float(time[it])
            age = float(time[it]) - face_first[key]

            # --- 第二档：取向差（驱动 2a）与热梯度对齐度（驱动 2b）---
            # dtheta 是这条晶界两侧晶粒的取向差（四重对称 -> [0,45]），
            # 它决定 Read-Shockley 因子，也就是 kappa/gamma/L 的成对权重。
            ta, tb = gset[a]["theta"], gset[b]["theta"]
            dth = misorientation_deg(ta, tb)
            if dth == 0.0:
                n_zero_dth[0] += 1
            # 面心处的热梯度：用解析式独立复算（与算例里的 grad_Tx/grad_Ty 交叉校验）
            gxf, gyf = rosenthal_grad(cen[0], cen[1], float(time[it]))
            al_i = align4_deg(ta, gxf, gyf)    # 晶粒 i 的易生长轴对齐度
            al_j = align4_deg(tb, gxf, gyf)    # 晶粒 j 的
            # 材料里实际用的 eta^2 加权混合值（从 MOOSE 输出读出，仅供核对）
            if GA is not None:
                wsum2 = (elem_measure[elems] * wts).sum()
                al_m = float((GA[it][elems] * elem_measure[elems] * wts).sum()
                             / (wsum2 + 1e-30))
            else:
                al_m = float("nan")

            face_rows.append([float(time[it]), fid, a, b, A, excess,
                              *cen.tolist(), A / Ai, A / Aj, dA, dEx,
                              Tf, *dirv.tolist(), *vel.tolist(), age,
                              dth, al_i, al_j, gxf, gyf, al_m])

        # ---- 拓扑事件（带持续性过滤）----
        # 弥散界面下，小面会反复闪烁。只看单步的"出现/消失"会把噪声当成事件，
        # 所以要求状态变化持续 persist 个采样点才算真事件。
        cur_set = set(cur_faces)
        cur_grains = set(gset)

        if not first:
            # 晶粒事件（晶粒消失不闪烁，直接用）
            for g in sorted(prev_grain_set - cur_grains):
                events.append([float(time[it]), "grain_disappear", g, -1])
            for g in sorted(cur_grains - prev_grain_set):
                events.append([float(time[it]), "grain_appear", g, -1])

            # ---- 面事件：持续性过滤 ----
            #
            # 【原实现的 bug —— 会让面事件永远不触发】
            # 旧代码只在 `prev_face_set - cur_set` 这个一步差集里累加计数。
            # 但一个面从**第二帧起就不再出现在该差集里**（它上一帧已经是缺席状态，
            # 不在 prev_face_set 中），所以计数永远停在 1：
            #   persist >= 2 -> 条件 `absent[k] == persist` 永不成立，事件完全丢失
            #   persist == 1 -> 立刻触发，等于完全没过滤
            # 而"面消失/出现"正是转移算子的训练目标，丢了它核心数据就是空的。
            #
            # 正确做法：维护**持续缺席/在场的候选字典**，每帧检查候选是否仍然缺席。
            #   absent[k] = k 连续缺席了多少个采样点
            #   present[k] = k 连续在场了多少个采样点
            for k in list(absent):
                if k in cur_set:
                    absent.pop(k)                       # 回来了，取消候选
                else:
                    absent[k] += 1
                    if absent[k] == persist:
                        events.append([float(time[it]), "face_disappear", k[0], k[1]])
            for k in prev_face_set - cur_set:
                if k not in absent:                     # 刚开始缺席
                    absent[k] = 1
                    if persist <= 1:
                        events.append([float(time[it]), "face_disappear", k[0], k[1]])

            for k in list(present):
                if k in cur_set:
                    present[k] += 1
                    if present[k] == persist:
                        events.append([float(time[it]), "face_appear", k[0], k[1]])
                else:
                    present.pop(k)                      # 又没了
            for k in cur_set - prev_face_set:
                if k not in present:                    # 刚出现
                    present[k] = 1
                    if persist <= 1:
                        events.append([float(time[it]), "face_appear", k[0], k[1]])

        prev_grain_set = cur_grains
        prev_face_set = cur_set
        prev_faces = cur_faces
        prev_face_cen = {k: v["cen"] for k, v in cur_faces.items()}
        prev_face_t = float(time[it])
        first = False

        # ---- 自洽性 ----
        # 【重要】原来只对 active（晶粒）单元求和，会**漏掉液相里的溶质**。
        # LPBF 凝固过程中大量溶质富集在液相里，只统计固相会让守恒曲线
        # 出现虚假漂移（看着像不守恒，其实只是液相没算进去）。
        # 现在同时给出：全域总量（真正的守恒检查）与固相分量。
        total_all = float((c * elem_measure).sum())
        total_solid = float((c[active] * elem_measure[active]).sum())
        cons_rows.append([float(time[it]), len(gset), len(cur_faces),
                          total_all, total_solid])

        if n % max(1, len(iters) // 12) == 0:
            # 【用 .4g 而不是 .1f】LPBF 算例的时间是 1e-4 量级，
            # %.1f 会把所有时间点都显示成 0.0，长跑时完全看不出进度。
            print(f"  t={time[it]:<10.4g} 晶粒 {len(gset):4d}  面 {len(cur_faces):5d}")

    # ---- 输出 ----
    os.makedirs(args.out, exist_ok=True)

    def dump(name, header, rows):
        with open(os.path.join(args.out, name), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    ax = "xyz"[:dim]
    dump("grains.csv",
         ["time", "grain_id", "volume", "solute", "c_bulk"]
         + [f"cen_{a}" for a in ax]
         + ["n_faces", "face_area_total", "shape_factor", "T_avg", "age",
            "theta_deg"],                 # 晶粒晶体取向 <100> 与 x 轴夹角（[0,90)）
         grain_rows)
    dump("faces.csv",
         ["time", "face_id", "grain_i", "grain_j", "area", "solute_excess"]
         + [f"cen_{a}" for a in ax]
         + ["area_over_Ai", "area_over_Aj", "d_area", "d_excess",
            "T_avg"]
         + [f"dir_{a}" for a in ax]        # 面心相对晶粒 i 质心的单位方向
         + [f"v_{a}" for a in ax]          # 面心迁移速度
         + ["age"]
         # --- 第二档（2a/2b）特征 ---
         + ["dtheta_deg",                  # 两侧晶粒取向差（四重对称 -> [0,45]），驱动 2a
            "align_i", "align_j",          # 两侧晶粒易生长轴与热梯度的对齐度，驱动 2b
            "grad_x", "grad_y",            # 面心处热梯度（解析复算）
            "align_moose"],                # 材料里实际用的 eta^2 加权混合值（核对用）
         face_rows)
    dump("events.csv", ["time", "event", "a", "b"], events)
    dump("conservation.csv",
         ["time", "n_grains", "n_faces", "total_all", "total_solid"],
         cons_rows)

    print()
    print("=" * 60)
    print(f"晶粒记录 {len(grain_rows)} 行")
    print(f"面记录   {len(face_rows)} 行   ← 算子训练的主表")
    print(f"拓扑事件 {len(events)} 条")
    kinds = defaultdict(int)
    for e in events:
        kinds[e[1]] += 1
    for k, v in sorted(kinds.items()):
        print(f"   {k:18s} {v:5d}")

    # --- 第二档自检：op_num < 晶粒数时，多个晶粒共用序参量 -> 取向完全相同 ---
    # 本算例 op_num=8 而柱状晶有 11 个，必然有 3 对晶粒取向相同（dtheta=0）。
    # 在链状柱状晶里这些同取向晶粒**不相邻**，所以没有真实晶面落在 dtheta=0 上。
    # 一旦出现，说明"op 共用者不相邻"这个前提被破坏（例如熔池重熔后拓扑变了），
    # 此时 kappa/L 会退化成 ~0，必须提高 op_num 后重跑。
    if OC is not None:
        if n_zero_dth[0]:
            print(f"**警告**：{n_zero_dth[0]} 条晶面的 dtheta=0 —— "
                  f"共用序参量的两个晶粒真的相邻了；请提高 op_num 后重跑")
        else:
            print("第二档自检：无 dtheta=0 的晶面（共用序参量的晶粒确实不相邻）OK")

    print(f"输出目录: {args.out}")


if __name__ == "__main__":
    main()
