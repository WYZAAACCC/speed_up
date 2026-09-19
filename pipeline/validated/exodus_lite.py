#!/usr/bin/env python3
# =============================================================================
# 极简 Exodus 读取器（只读 MOOSE 输出需要的那些变量）
# =============================================================================
# 环境里没有 meshio，但有 netCDF4 —— 而 Exodus 就是 netCDF4 格式。
#
# 【为什么不用 Postprocessor 直接测三叉角】
#   三叉角需要**几何**信息（三条晶界的方向），而 MOOSE 的后处理器是标量。
#   在输入里塞几十个 PointValue 也能做，但改一次网格就得重排一遍，
#   不如把场读出来在 Python 里算。
#
# 【Exodus 的结构（本读取器依赖的部分）】
#   coordx / coordy / coordz   节点坐标
#   connect1                   单元连接（**1-based**，要减 1）
#   name_nod_var               节点变量名（char 数组，按 'vals_nod_varN' 编号）
#   vals_nod_varN              第 N 个节点变量的值，形状 (n_time, n_node)
#   time_whole                 时间序列
#
# 用法：
#   from exodus_lite import read_exodus
#   d = read_exodus("out.e")
#   d = read_exodus("out.e", names=["gr0","gr1","gr2"], time_index=-1)
# =============================================================================

import numpy as np


def _decode_names(raw):
    """
    把 Exodus 的 char 数组解成名字列表。

    ⚠ Exodus 里 `name_nod_var` 是**二维字符矩阵**（nvars × maxlen），
      每个变量占**一行**、后面用 '--' 或 NUL 补齐。
      按整块 join 会把所有变量名连成一串（实测踩过）。
    """
    if raw is None:
        return []
    arr = np.asarray(raw)

    def one(row):
        if np.asarray(row).dtype.kind == "S":
            return b"".join(bytes(x) for x in np.asarray(row).reshape(-1)) \
                .decode("utf-8", "replace")
        return "".join(chr(int(c)) for c in np.asarray(row).reshape(-1))

    if arr.ndim == 0:
        return []
    if arr.ndim == 1:
        return [one(arr)] if one(arr).strip() else []
    # 二维：逐行解
    out = []
    for r in arr:
        nm = one(r).replace("\x00", "").replace("--", "").strip()
        out.append(nm)
    # 去掉尾部空名（Exodus 会预留很多空槽）
    while out and not out[-1]:
        out.pop()
    return out


def read_exodus(path, names=None, time_index=-1, elem_var_names=None):
    """
    读取 Exodus 文件。

    返回 dict：
        x, y           节点坐标
        conn           (n_elem, n_per_elem) 的 0-based 连接
        times          时间序列
        node_vars      {名字: (n_node,) 的值}   ← 取 time_index 时刻
        elem_vars      {名字: (n_elem,) 的值}
        n_elem, n_node
    """
    import netCDF4

    out = {}
    with netCDF4.Dataset(path, "r") as ds:
        keys = set(ds.variables.keys())

        out["x"] = np.asarray(ds.variables["coordx"][:], dtype=float)
        out["y"] = (np.asarray(ds.variables["coordy"][:], dtype=float)
                    if "coordy" in keys else np.zeros_like(out["x"]))
        out["n_node"] = len(out["x"])

        # --- 连接：找 connect1（或 connect1_elem）---
        conn = None
        for k in ("connect1", "connect1_elem", "connect2"):
            if k in keys:
                conn = np.asarray(ds.variables[k][:], dtype=int) - 1  # 转 0-based
                break
        out["conn"] = conn
        out["n_elem"] = 0 if conn is None else conn.shape[0]

        # --- 时间 ---
        out["times"] = (np.asarray(ds.variables["time_whole"][:], dtype=float)
                        if "time_whole" in keys else np.array([0.0]))

        # --- 节点变量 ---
        all_names = _decode_names(ds.variables["name_nod_var"][:]
                                  if "name_nod_var" in keys else None)
        wanted = names if names else all_names
        nv = {}
        for i, nm in enumerate(all_names, start=1):
            if nm not in wanted:
                continue
            vk = "vals_nod_var%d" % i
            if vk not in keys:
                continue
            v = np.asarray(ds.variables[vk][:], dtype=float)
            if v.ndim == 1:
                v = v[None, :]
            nv[nm] = v[time_index]
        out["node_vars"] = nv
        out["node_var_names"] = all_names

        # --- 单元变量（可选）---
        ev = {}
        if elem_var_names:
            en = _decode_names(ds.variables["name_elem_var"][:]
                               if "name_elem_var" in keys else None)
            for i, nm in enumerate(en, start=1):
                if nm not in elem_var_names:
                    continue
                vk = "vals_elem_var%deb1" % i
                if vk not in keys:
                    continue
                v = np.asarray(ds.variables[vk][:], dtype=float)
                if v.ndim == 1:
                    v = v[None, :]
                ev[nm] = v[time_index]
        out["elem_vars"] = ev

    return out


def elem_centroids(d):
    """单元质心（用节点坐标平均，QUAD4 足够）。"""
    if d["conn"] is None:
        return np.zeros((0, 2))
    x = d["x"][d["conn"]].mean(axis=1)
    y = d["y"][d["conn"]].mean(axis=1)
    return np.column_stack([x, y])


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        d = read_exodus(p)
        print("%s:" % p)
        print("  节点 %d  单元 %d  时间步 %d (t=%s)"
              % (d["n_node"], d["n_elem"], len(d["times"]), d["times"][-1]))
        print("  节点变量: %s" % d["node_var_names"])
        print("  连接形状: %s" % (None if d["conn"] is None else d["conn"].shape,))
