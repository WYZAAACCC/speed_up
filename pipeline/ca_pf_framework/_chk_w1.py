#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1 判据驱动：Herring 项开/关 + 数值底噪 + 推进口径 三档对照"""
import sys
import windowB_surface as W
n = int(sys.argv[1]) if len(sys.argv) > 1 else 600
Lam = float(sys.argv[2]) if len(sys.argv) > 2 else 0.4
ok = W.W1_control(Lam=Lam, nstep=n)
raise SystemExit(0 if ok else 1)