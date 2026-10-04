#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_dbgchk.py --- 从检查点里直接读 `_nuc`，判 s295 为什么一行都不打印。

`_bk_exp.py:448` 把整个 `_nuc` 字典（含 `dbg`）pickle 进 `st['nuc_cfg_pkl']`。
⇒ 读检查点即可知道 `nuc_cfg` 里究竟有没有 `dbg`、以及它与 `g._nuc` 是不是同一个对象。
（非侵入：只读，不动在跑的算例。）
"""
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CK = os.path.join(HERE, "_exp/_bk_t5/dry_t10N160/ckpt")
for name in sorted(os.listdir(CK)) if os.path.isdir(CK) else []:
    print("  ckpt 目录内容:", name)

cands = []
if os.path.isdir(CK):
    cands = [os.path.join(CK, f) for f in sorted(os.listdir(CK)) if f.endswith(".npz")]
if not cands:
    print("⚠ 没找到检查点 npz")
    sys.exit(1)

p = cands[-1]
print("读:", os.path.basename(p))
with np.load(p, allow_pickle=False) as z:
    print("  键:", sorted(z.files))
    if "nuc_cfg_pkl" not in z.files:
        print("  ⚠ 没有 nuc_cfg_pkl ⇒ 形核配置没进检查点")
        sys.exit(0)
    raw = z["nuc_cfg_pkl"].tobytes()
print("  nuc_cfg_pkl 字节数 =", len(raw))
cfg = pickle.loads(raw)
print("  cfg 类型 =", type(cfg).__name__)
if isinstance(cfg, dict):
    keys = sorted(cfg.keys())
    print("  cfg 键数 =", len(keys))
    print("  键:", keys)
    print()
    if "dbg" in cfg:
        d = cfg["dbg"]
        print("  ★ dbg 存在，类型 =", type(d).__name__, "内容 =", d)
    else:
        print("  ❌ **cfg 里没有 `dbg`** ⇒ 引擎的 `nucleate()` 从未执行过任何 "
              "`c.setdefault('dbg', ...)` 那几条路径")
        print("     （即：supercrit / fcrit / nan_ed / fresh_blocked / sites_resampled 全没走到）")
else:
    print("  ⚠ cfg 不是 dict ⇒ 结构与我预期不同")
