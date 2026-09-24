#!/usr/bin/env python3
"""W1 判据驱动：Herring 项的开/关对照（同一初始形状）"""
import windowB_surface as W

for herring in (True, False):
    W.W1_wulff(Lam=0.2, herring=herring, nstep=600)
W.W1_wulff(Lam=0.0, herring=True, nstep=600)
