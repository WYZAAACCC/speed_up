#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_ab.py —— **B2 的直接 A/B**：同一初值，`pre` vs `post`，比 φ。

## 为什么这个判据最直接
`B2` 的唯一改动是"投影发生在步首还是步尾"。
⇒ 在**同一条配置、同一初值**下跑 N 步，若两臂**逐位相同** ⇒ **`post` 没生效**（开关是死的）；
若不同 ⇒ **生效了**，再谈它有没有达到 `B2-D3` 的靶。

## 判据
* **J1** `post` 真的改变了推进（`max|Δφ| > 0`）；
* **J2** 变化的量级合理（不是 NaN/爆炸）；
* **J3** 两臂都跑完不崩。
"""
import os
import sys

import numpy as np

FW = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, FW)
import _bk_exp as B  # noqa: E402


def build(order, nreg=6, N=48, L=4.0e-6):
    """用与 `_bk_exp.py` 相同的路子构造引擎（尽量小：N=48）。"""
    import argparse
    a = argparse.Namespace(
        N=N, L=L, band_cells=40, beta_h=6.477, beta_w=2.3, adv='proj2',
        norm_smooth=0, facet_lam=0.0, facet_eps=0.05, mob_wulff=1, mob_dip=4.0,
        mob_iform='exp2', mob_ratio=9.0, el_scale=1.0,
        facet_proj=1, facet_proj_order=order, extend_mode='legacy',
        nthreads=2)
    return a


def main():
    print("=" * 100)
    print("B2 直接 A/B：同初值、同配置，只差 `facet_proj_order`")
    print("=" * 100)
    import inspect
    sig = inspect.signature(B.LevelSetMulti.advance) if hasattr(B, 'LevelSetMulti') else None
    print("  `advance()` 是否接受 facet_proj_order：%s"
          % ('facet_proj_order' in sig.parameters if sig else '?'))
    if sig:
        print("  默认值 = %r" % sig.parameters['facet_proj_order'].default)


if __name__ == "__main__":
    main()
