#!/usr/bin/env python3
# =============================================================================
# Gate 0 诊断汇总器
# =============================================================================
#
# 输入：一个运行目录（.i / run.log / *_out.csv / *.e）
# 输出：diagnostics.json（机器可读）+ 人读表格
#
# 运行环境：**conda 环境 `moose`**（有 netCDF4、无 torch）。
#     source /root/miniconda3/etc/profile.d/conda.sh && conda activate moose
#     python3 gate0_report.py <运行目录> [--tag 名字]
#
# --- 复用的既有代码（不重写）-------------------------------------------------
#   Exodus 名字解码        cmp_solution.py:21-31（必须剥 空格/'-'/NUL 三种填充）
#   多块遍历               extract.py:152-195
#   日志正则/ANSI 剥离      cost_breakdown.sh:139-151
#   多进程 RSS 求和         bench_mpi_mem.sh:45-53
#
# --- 已知坑（全部踩过，别改回去）--------------------------------------------
#   * 时间变量叫 `time_whole`，不是 `time`
#   * 变量名在 name_nod_var/name_elem_var，形状 (nvar, len_name)，**按行**拼接
#   * **必须遍历所有单元块**：熔池是独立 block（本算例约 8~16% 单元），
#     写死 eb1 会静默漏掉整个凝固区
#   * **CSV 的 t=0 那一行后处理器全是 0**（材料尚未求值）——统计时必须跳过，
#     否则每个量都被读成 0，看起来像灾难性 bug
#   * 重跑前必须删 `*_out.csv`，否则读到上一次运行残留的行
#   * 日志必须剥 ANSI 色码（`\x1b\[[0-9;]*m`）
# =============================================================================

import argparse
import csv
import glob
import json
import os
import re
import sys
from typing import Any, Callable, Optional, Tuple

import numpy as np

try:
    import netCDF4 as nc
except ImportError:
    sys.exit("需要 netCDF4 —— 请在 conda 环境 `moose` 下运行（`ml` 环境有 torch 但没 netCDF4）")

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _re1(txt: str, pat: str, cast: Callable[[str], Any] = float) -> Optional[Any]:
    """取第一个捕获组并转型；没有匹配就返回 None。"""
    m = re.search(pat, txt)
    if not m:
        return None
    try:
        return cast(m.group(1))
    except (TypeError, ValueError):
        return None


# libMesh QUAD4 参考坐标下的形函数导数（中心点 ξ=η=0）
#   dN/dξ = [-1/4, 1/4, 1/4, -1/4]
#   dN/dη = [-1/4, -1/4, 1/4, 1/4]
DN_DXI = np.array([-0.25, 0.25, 0.25, -0.25])
DN_DETA = np.array([-0.25, -0.25, 0.25, 0.25])


# -----------------------------------------------------------------------------
# Exodus
# -----------------------------------------------------------------------------
def decode_names(arr):
    """(nvar, len_name) 的字符数组 -> 名字列表。

    Exodus 用 空格 / '-' / NUL 三种方式填充到 len_name，三种都要剥掉。
    实测：MOOSE 的 eb_names 用的是 '-' 填充（见 cmp_solution.py:21-31）。
    """
    out = []
    for row in np.atleast_2d(np.asarray(arr)[:]):
        s = "".join(c.decode() if isinstance(c, bytes) else str(c) for c in row)
        out.append(s.replace("\x00", "").strip().rstrip("-").strip())
    return out


def read_all_element_blocks(ds):
    """拼出**所有**单元块的连接表。返回 (connect, block_ids)。

    只读 connect1 会静默漏掉其它 subdomain（extract.py:180-195 的警告）。
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


def load_exodus(path: str) -> dict:
    """返回 dict：times, node{name: (ntime, nnode)}, elem{name: (ntime, nelem)},
    coords, connect, block_ids, block_names, n_elem_blocks"""
    ds = nc.Dataset(path)
    times = np.array(ds.variables["time_whole"][:], dtype=float)

    node = {}
    if "name_nod_var" in ds.variables:
        for i, nm in enumerate(decode_names(ds.variables["name_nod_var"][:])):
            k = f"vals_nod_var{i + 1}"
            if k in ds.variables:
                node[nm] = np.array(ds.variables[k][:], dtype=float)

    # 【必须遍历所有块】按块读再拼接，顺序与 read_all_element_blocks 一致
    elem, k, parts = {}, 1, []
    while f"connect{k}" in ds.variables:
        parts.append(np.asarray(ds.variables[f"connect{k}"][:]).shape[0])
        k += 1
    if "name_elem_var" in ds.variables:
        for i, nm in enumerate(decode_names(ds.variables["name_elem_var"][:])):
            chunks = []
            for b in range(1, len(parts) + 1):
                for key in (f"vals_elem_var{i + 1}eb{b}", f"vals_elem_var{i + 1}"):
                    if key in ds.variables:
                        chunks.append(np.asarray(ds.variables[key][:], dtype=float))
                        break
            if chunks:
                elem[nm] = np.concatenate(chunks, axis=-1)

    coords = np.column_stack([np.asarray(ds.variables["coordx"][:], dtype=float),
                              np.asarray(ds.variables["coordy"][:], dtype=float)])
    connect, bids = read_all_element_blocks(ds)
    bnames = decode_names(ds.variables["eb_names"][:]) if "eb_names" in ds.variables else []
    ds.close()
    return dict(times=times, node=node, elem=elem, coords=coords,
                connect=connect, block_ids=bids, block_names=bnames,
                n_elem_blocks=len(parts))


def grad_energy(exo: dict, eta_names: list, kappa: float) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """Σᵢ ∫ (kappa/2)·|∇ηᵢ|² dA —— QUAD4 双线性梯度，在单元中心取值。

    这是解析量，不是 MOOSE 输出的：MOOSE 里梯度能没有现成后处理器。
    系数约定：ACInterface 的残差是 L·κ·∇η·∇φ（ACInterface.C:96,102），
    对应 F_grad = Σᵢ ∫ (kappa_op/2)|∇ηᵢ|² dV。
    """
    conn, coords = exo["connect"], exo["coords"]
    if conn.shape[1] != 4:
        return None, "非 QUAD4 网格，未实现"
    xy = coords[conn]                                  # (nelem, 4, 2)
    # 单元中心处的 Jacobian
    dxdxi = xy[:, :, 0] @ DN_DXI
    dydxi = xy[:, :, 1] @ DN_DXI
    dxdeta = xy[:, :, 0] @ DN_DETA
    dydeta = xy[:, :, 1] @ DN_DETA
    detJ = dxdxi * dydeta - dxdeta * dydxi
    if np.any(np.abs(detJ) < 1e-300):
        return None, "存在退化单元（detJ=0）"
    area = np.abs(detJ)
    # ∇N = J^{-T} [dN/dξ, dN/dη]
    inv_det = 1.0 / detJ
    dNdx = (dydeta[:, None] * DN_DXI[None, :] - dydxi[:, None] * DN_DETA[None, :]) * inv_det[:, None]
    dNdy = (-dxdeta[:, None] * DN_DXI[None, :] + dxdxi[:, None] * DN_DETA[None, :]) * inv_det[:, None]

    nt = exo["times"].size
    out = np.zeros(nt)
    for nm in eta_names:
        if nm not in exo["node"]:
            return None, f"Exodus 里没有 {nm}"
        vals = exo["node"][nm]                          # (ntime, nnode)
        for it in range(nt):
            ue = vals[it][conn]                         # (nelem, 4)
            gx = ue @ dNdx.T if False else np.einsum("ei,ei->e", ue, dNdx)
            gy = np.einsum("ei,ei->e", ue, dNdy)
            out[it] += 0.5 * kappa * np.sum((gx ** 2 + gy ** 2) * area)
    return out, None


# -----------------------------------------------------------------------------
# CSV / 日志
# -----------------------------------------------------------------------------
def parse_csv(path: str) -> Tuple[list, list, Optional[dict]]:
    """返回 (columns, rows)。rows 里**跳过 time=0**（材料未求值，全是 0）。"""
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return [], [], None
    cols = [c.strip() for c in rows[0].keys()]

    def clean(r):
        return {k.strip(): v for k, v in r.items()}

    allrows = [clean(r) for r in rows]
    t0 = [r for r in allrows if float(r.get("time", 0)) == 0.0]
    body = [r for r in allrows if float(r.get("time", 0)) != 0.0]
    return cols, body, (t0[0] if t0 else None)


def parse_log(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {}
    txt = ANSI.sub("", open(path, errors="ignore").read())
    # ⚠ 正则别写成 `Finished Executing[^\]]*\]\s*\[\s*([0-9.]+) s\]` ——
    #   那要求**两个** `[x s]` 组，而实际行是 `[ 66.93 s] [  237 MB]`（第二个是内存），
    #   会静默匹配失败、墙钟永远是 None。
    wall = re.findall(r"Finished Executing\s*\[\s*([0-9.]+) s\]", txt)
    jac = [float(x) for x in re.findall(r"Computing Jacobian[^\[]*\[\s*([0-9.]+) s\]", txt)]
    setup = re.findall(r"Finished Setting Up\s*\[\s*([0-9.]+) s\]", txt)
    nres = len(re.findall(r"Nonlinear \|R\|", txt))
    last_res = re.findall(r"Nonlinear \|R\| =\s*([0-9.eE+-]+)", txt)
    steps = re.findall(r"^Time Step (\d+), time = ([0-9.eE+-]+), dt = ([0-9.eE+-]+)", txt, re.M)
    return dict(
        wall_s=float(wall[-1]) if wall else None,
        setup_s=float(setup[-1]) if setup else None,
        jacobian_mean_s=float(np.mean(jac)) if jac else None,
        jacobian_n=len(jac),
        newton_residual_evals=nres,
        last_residual=float(last_res[-1]) if last_res else None,
        n_steps=len(steps),
        last_time=float(steps[-1][1]) if steps else None,
        diverged={k: len(re.findall(rf"DIVERGED_{k}\b", txt))
                  for k in ("ITS", "FUNCTION", "LINE_SEARCH", "PC_FAILED", "DT")},
        moose_version=_re1(txt, r"MOOSE Version:\s*(.+)", str.strip),
        petsc_version=_re1(txt, r"PETSc Version:\s*(\S+)", str),
        elems=_re1(txt, r"Elems:\s*(\d+)", int),
        nodes=_re1(txt, r"Nodes:\s*(\d+)", int),
        # 正常结束的标志：MOOSE 跑完会打印 "Finished Executing"。
        # 老的 s1d_nonad 生产跑就没有它（中途被杀）——报告必须如实反映，
        # 否则会让人把"半截数据"当成完整算例。
        completed=("Finished Executing" in txt),
        aborted=("*** ERROR ***" in txt),
    )


def peak_memory_kb(d: str) -> Optional[int]:
    p = os.path.join(d, "peak_kb.txt")
    if os.path.exists(p):
        try:
            return int(open(p).read().strip())
        except ValueError:
            pass
    return None


# -----------------------------------------------------------------------------
# 派生量
# -----------------------------------------------------------------------------
def conservation(rows: list) -> Optional[dict[str, Any]]:
    """total_solute 的相对漂移。判据：机器精度量级。"""
    vals = [(float(r["time"]), float(r["total_solute"]))
            for r in rows if r.get("total_solute")]
    if len(vals) < 2:
        return None
    v0 = vals[0][1]
    dev = max(abs(v - v0) for _, v in vals)
    return dict(initial=v0, max_abs_drift=dev,
                max_rel_drift=dev / abs(v0) if v0 else None,
                n_samples=len(vals))


def order_param_stats(exo: dict, n_op: int = 8) -> Optional[dict[str, Any]]:
    """序参量越界统计。

    判据来自解析解：f/mu = Σ(η⁴/4-η²/2) + γΣ_{i<j}ηᵢ²ηⱼ²，γ=1.5 时
        晶粒内 Ση² = 1；单晶界中点 η₁=η₂=0.5 ⇒ Ση²=0.5；三叉晶界 0.4286
    ⇒ **平衡态 Ση² ∈ [0.5, 1]，>1 一定是数值伪影**（界面欠解析）。
    """
    names = [f"gr{i}" for i in range(n_op) if f"gr{i}" in exo["node"]]
    if not names:
        return None
    nt = exo["times"].size
    out = []
    for it in range(nt):
        E = np.stack([exo["node"][n][it] for n in names], axis=1)
        mx = E.max(axis=1)
        s = (E ** 2).sum(axis=1)
        out.append(dict(t=float(exo["times"][it]),
                        max_eta=float(mx.max()),
                        min_eta=float(E.min()),
                        max_sum_eta2=float(s.max()),
                        n_over_1=int((mx > 1).sum()),
                        n_over_1_frac=float((mx > 1).mean()),
                        n_neg=int((E < -0.01).sum())))
    return dict(per_frame=out,
                final=out[-1],
                # 平衡范围是 [0.5, 1]；超过 1 即伪影
                physical_sum_eta2_range=[0.5, 1.0],
                over_1 = out[-1]["max_eta"] > 1.0)


def interface_resolution(root: str) -> Optional[dict]:
    """核算 w/dx。w = sqrt(kappa_op/mu0)。

    数据来源分散在不同文件里，必须**跨目录内所有 .i 文件**收集：
      * `GENERATED_PARAMS` 行（wgb / kappa_op_iso / mu0）在 **aniso_block.i** 里
        —— 生成器写的是那个文件的头，而 `splice_aniso_noad.py` 会**重写**
        `stage1_meltpool_d.i` / `N.i` 的文件头，所以最终输入里**没有**这一行。
      * `[barrier_mu]` 的 mu0 与 `[Mesh]` 的 nx/xmin/xmax 在最终输入里。

    ⚠ 绝不能读文件头那行 `[consts] kappa_op=1.8e-6, ...` —— 它是**静态模板文本**
      （描述 C 版基线），**不随 --wgb 变化**。用它配 wGB 变体会算出错误的 w。
      （这个 bug 是做 wGB=12e-6 变体时被实验暴露的。）

    另外核对 mu0 的两个来源：生成器 MU_QP = 6σ/wGB 必须等于算例 [barrier_mu] 的 mu0，
    否则 (a*,gamma*) 与 mu 不自洽，晶界能不是目标值。
    """
    files = sorted(glob.glob(os.path.join(root, "*.i")))
    if not files:
        return None

    gp = kappa = mu0_gen = None
    mu0_case = nx = xmin = xmax = None
    src_gp = src_case = None

    for p in files:
        s = open(p, errors="ignore").read()
        if gp is None:
            m = re.search(r"GENERATED_PARAMS\s+wgb=(\S+)\s+kappa_op_iso=(\S+)"
                          r"\s+gamma_asymm_iso=(\S+)\s+mu0=(\S+)", s)
            if m:
                gp = m
                kappa = float(m.group(2))
                mu0_gen = float(m.group(4))
                src_gp = os.path.basename(p)
        if mu0_case is None:
            blk, ins = [], False
            for ln in s.splitlines():
                if not ins:
                    # 【2026-09-18 ④ 修复】barrier_mu -> barrier_muT（现在存的是 mu_T）。
                    #   精确匹配，所以名字必须完全对上，否则静默取不到。
                    if ln.strip() == "[barrier_muT]":
                        ins = True
                    continue
                if ln.strip() == "[]":
                    break
                blk.append(ln)
            m2 = re.search(r"constant_expressions = '(\S+)", "\n".join(blk))
            m3 = re.search(r"^\s+nx = (\d+)\s*$", s, re.M)
            m4 = re.search(r"^\s+xmin = \s*(\S+)\s*$", s, re.M)
            m5 = re.search(r"^\s+xmax = \s*(\S+)\s*$", s, re.M)
            if m2 and m3 and m4 and m5 and "[Mesh]" in s:
                mu0_case = float(m2.group(1))
                nx, xmin, xmax = int(m3.group(1)), float(m4.group(1)), float(m5.group(1))
                src_case = os.path.basename(p)
                # ④ 自洽性：ACGrGrPoly 的常数势垒必须等于熔化开关的 mu0
                blkc, insc = [], False
                for ln in s.splitlines():
                    if not insc:
                        if ln.strip() == "[mu_barrier_const]":
                            insc = True
                        continue
                    if ln.strip() == "[]":
                        break
                    blkc.append(ln)
                m6 = re.search(r"prop_values = '(\S+)'", "\n".join(blkc))
                if m6:
                    mu_const = float(m6.group(1))
                    if abs(mu_const - mu0_case) > 1e-12 * abs(mu0_case):
                        raise ValueError(
                            f"④ 修复自洽性失败：{src_case} 的 [mu_barrier_const] mu={mu_const:.6g} "
                            f"≠ [barrier_muT] mu0={mu0_case:.6g}；自由能不是 Landau 形式")

    if mu0_case is None:
        return None
    # 这四个量只在同一分支里一起赋值，这里显式收窄类型
    assert nx is not None and xmin is not None and xmax is not None
    if kappa is None:
        # 回退：老输入文件没有 GENERATED_PARAMS 行
        for p in files:
            s = open(p, errors="ignore").read()
            m = re.search(r"kappa_op=(\S+?)[,\s]", s)
            if m:
                kappa = float(m.group(1))
                break
        if kappa is None:
            return None

    dx = (xmax - xmin) / nx
    w = (kappa / mu0_case) ** 0.5
    return dict(input_file=src_case, generated_params_from=src_gp,
                kappa_op=kappa, mu0=mu0_case, mu0_generator=mu0_gen,
                mu0_consistent=(None if mu0_gen is None
                                else abs(mu0_gen - mu0_case) <= 1e-9 * abs(mu0_case)),
                dx=dx, w_equilibrium=w, elems_per_interface=w / dx,
                criterion="4~8 单元/界面",
                ok=bool(w / dx >= 4.0))


# -----------------------------------------------------------------------------
def find_one(root, patterns):
    hits = []
    for pat in patterns:
        hits += sorted(glob.glob(os.path.join(root, pat)))
    return hits


def main():
    ap = argparse.ArgumentParser(description="Gate 0 诊断汇总")
    ap.add_argument("run_dir", nargs="?", default=".", help="运行目录")
    ap.add_argument("--tag", default=None, help="运行标签（默认取目录名）")
    ap.add_argument("--kappa", type=float, default=None,
                    help="kappa_op（默认从 .i 自动探测，再退化到 1.8e-6）")
    ap.add_argument("--n-op", type=int, default=8)
    args = ap.parse_args()

    d = os.path.abspath(args.run_dir)
    if not os.path.isdir(d):
        sys.exit(f"不是目录：{d}")
    tag = args.tag or os.path.basename(d)

    # --- 文件发现 ---
    exo_files = [f for f in find_one(d, ["*.e"]) if not f.endswith("_in.e")]
    csv_files = find_one(d, ["*_out.csv"])
    log_files = find_one(d, ["run.log", "*.log"])

    rep: dict[str, Any] = dict(
        tag=tag, run_dir=d,
        found=dict(exodus=[os.path.basename(f) for f in exo_files],
                   csv=[os.path.basename(f) for f in csv_files],
                   log=[os.path.basename(f) for f in log_files]))

    # --- 日志（墙钟 / 迭代 / 版本 / 发散）---
    if log_files:
        # 优先 run.log，否则取最大的
        lg = (os.path.join(d, "run.log") if os.path.exists(os.path.join(d, "run.log"))
              else max(log_files, key=os.path.getsize))
        rep["log"] = parse_log(lg)
        rep["log"]["file"] = os.path.basename(lg)
    rep["peak_rss_kb"] = peak_memory_kb(d)
    if rep["peak_rss_kb"]:
        rep["peak_rss_mb"] = rep["peak_rss_kb"] / 1024.0

    # --- CSV（后处理器时间序列）---
    if csv_files:
        cf = max(csv_files, key=os.path.getsize)
        cols, rows, t0row = parse_csv(cf)
        # 用显式 Any 值的局部 dict，避免嵌套赋值的类型推断噪音
        csv_rep: dict[str, Any] = dict(
            file=os.path.basename(cf), columns=cols,
            n_rows=len(rows),
            n_rows_including_t0=len(rows) + (1 if t0row else 0),
            t0_row_all_zero=bool(t0row and all(
                float(v or 0) == 0 for k, v in t0row.items() if k != "time")),
            first_time=float(rows[0]["time"]) if rows else None,
            last_time=float(rows[-1]["time"]) if rows else None)
        rep["conservation"] = conservation(rows)
        # 每步代价序列
        for key, out in (("n_nonlin", "newton_iters"), ("n_lin", "linear_iters"),
                         ("n_elem", "n_elem")):
            seq = [float(r[key]) for r in rows if r.get(key)]
            if seq:
                csv_rep[out] = dict(min=min(seq), max=max(seq),
                                    mean=sum(seq) / len(seq), n=len(seq))
        # 自由能序列（F_loc / F_grain）
        for key in ("F_loc", "F_grain"):
            seq = [float(r[key]) for r in rows if r.get(key)]
            if seq:
                csv_rep[key] = dict(first=seq[0], last=seq[-1],
                                    min=min(seq), max=max(seq),
                                    # monotone 只对纯晶粒长大成立（液相里 mu<0，F 可以升）
                                    non_increasing=all(b <= a + 1e-15 * max(1.0, abs(a))
                                                       for a, b in zip(seq, seq[1:])))
        rep["csv"] = csv_rep

    # --- Exodus（场）---
    if exo_files:
        ef = max(exo_files, key=os.path.getsize)
        exo = load_exodus(ef)
        rep["exodus"] = dict(file=os.path.basename(ef),
                             n_frames=int(exo["times"].size),
                             n_nodes=int(exo["coords"].shape[0]),
                             n_elem=int(exo["connect"].shape[0]),
                             n_elem_blocks=exo["n_elem_blocks"],
                             block_names=exo["block_names"],
                             times=[float(x) for x in exo["times"]],
                             node_vars=sorted(exo["node"].keys()),
                             elem_vars=sorted(exo["elem"].keys()))
        rep["order_params"] = order_param_stats(exo, args.n_op)

        kap = args.kappa
        if kap is None:
            ir0 = interface_resolution(d)
            kap = ir0["kappa_op"] if ir0 else 1.8e-6
        fg, err = grad_energy(exo, [f"gr{i}" for i in range(args.n_op)], kap)
        if fg is not None:
            rep["free_energy_grad"] = dict(
                kappa_op=kap,
                formula="Σᵢ ∫ (kappa_op/2)|∇ηᵢ|² dA",
                per_frame=[dict(t=float(t), F_grad=float(v))
                           for t, v in zip(exo["times"], fg)],
                first=float(fg[0]), last=float(fg[-1]),
                non_increasing=bool(all(b <= a + 1e-12 * max(1.0, abs(a))
                                        for a, b in zip(fg, fg[1:]))))
        else:
            rep["free_energy_grad"] = dict(error=err)

    rep["interface_resolution"] = interface_resolution(d)

    # --- 写 JSON ---
    out = os.path.join(d, "diagnostics.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)

    # --- 人读表格 ---
    print("=" * 78)
    print(f"Gate 0 诊断汇总   tag={tag}")
    print(f"目录: {d}")
    print("=" * 78)
    L = rep.get("log", {})
    if L:
        print(f"[日志] {L.get('file')}  MOOSE {L.get('moose_version')}  PETSc {L.get('petsc_version')}")
        # 未跑完的算例没有 "Finished Executing"，此时墙钟为 None —— 要说明白，
        # 否则一个"被中途杀掉"的算例会看起来像正常算例（老的 s1d_nonad 就是这种）。
        if L.get("wall_s") is None:
            print("  墙钟 (无) —— 日志里没有 'Finished Executing'，"
                  f"该次运行**未正常结束**（{'有 ERROR' if L.get('aborted') else '进程被中断'}）")
        else:
            su = f"（初始化 {L['setup_s']:.1f} s）" if L.get("setup_s") else ""
            print(f"  墙钟 {L['wall_s']:.1f} s{su}  步数 {L.get('n_steps')}"
                  f"  末时刻 {L.get('last_time')}")
        print(f"  网格 {L.get('elems')} 单元 / {L.get('nodes')} 节点")
        print(f"  雅可比装配均值 {L.get('jacobian_mean_s')} s（共 {L.get('jacobian_n')} 次）")
        print(f"  末次牛顿残差 {L.get('last_residual')}")
        dv = {k: v for k, v in (L.get("diverged") or {}).items() if v}
        print(f"  发散计数: {dv if dv else '无'}")
        if L.get("aborted"):
            print("  ⚠ 日志里有 *** ERROR *** —— 该次运行未正常结束")
    if rep.get("peak_rss_mb"):
        print(f"[内存] 峰值 RSS {rep['peak_rss_mb']:.0f} MB")
    C = rep.get("csv", {})
    if C:
        print(f"[CSV] {C.get('file')}  {C.get('n_rows')} 行（另有 t=0 行: "
              f"{C.get('n_rows_including_t0', 0) - C.get('n_rows', 0)}）"
              f"  t ∈ [{C.get('first_time')}, {C.get('last_time')}]")
        for k in ("n_elem", "newton_iters", "linear_iters"):
            v = C.get(k)
            if v:
                print(f"  {k:<13} min={v['min']:.0f} max={v['max']:.0f} mean={v['mean']:.1f}")
        for k in ("F_loc", "F_grain"):
            v = C.get(k)
            if v:
                print(f"  {k:<13} {v['first']:.6e} → {v['last']:.6e}"
                      f"  非增={v['non_increasing']}")
    co = rep.get("conservation")
    if co:
        print(f"[守恒] total_solute 初值 {co['initial']:.12e}"
              f"  最大绝对漂移 {co['max_abs_drift']:.3e}"
              f"  相对 {co['max_rel_drift']:.3e}（{co['n_samples']} 个采样）")
    O = rep.get("order_params")
    if O:
        f0 = O["final"]
        print(f"[序参量] 末帧 t={f0['t']:.6g}  max η={f0['max_eta']:.4f}"
              f"  min η={f0['min_eta']:.3e}  max Ση²={f0['max_sum_eta2']:.4f}")
        print(f"  越界：η>1 的节点 {f0['n_over_1']} ({100*f0['n_over_1_frac']:.2f}%)"
              f"   η<-0.01 的节点 {f0['n_neg']}")
        print(f"  解析平衡范围 Ση² ∈ {O['physical_sum_eta2_range']} ⇒ >1 是数值伪影"
              f"   当前是否越界: {O['over_1']}")
    G = rep.get("free_energy_grad")
    if G and "first" in G:
        print(f"[梯度能] κ={G['kappa_op']:.4g}  F_grad {G['first']:.6e} → {G['last']:.6e}"
              f"  非增={G['non_increasing']}")
    IR = rep.get("interface_resolution")
    if IR:
        print(f"[界面分辨率] w={IR['w_equilibrium']*1e6:.3f} µm  dx={IR['dx']*1e6:.3f} µm"
              f"  → {IR['elems_per_interface']:.2f} 单元/界面"
              f"  {'OK' if IR['ok'] else '⚠ 欠解析（判据 ' + IR['criterion'] + '）'}")
        if IR.get("mu0_consistent") is False:
            print(f"  ⚠⚠ mu0 不自洽！生成器 {IR['mu0_generator']:.6g} "
                  f"vs 算例 [barrier_muT] {IR['mu0']:.6g} "
                  f"—— 改了 --wgb 但忘了改 barrier_muT，结果不可用")
    print("=" * 78)
    print(f"已写出: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
