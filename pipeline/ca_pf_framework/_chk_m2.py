#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M2 几何重测（全部修好的格式）：12 变体 RVE。
   与旧结果对照：旧（无速度扩展 + 一阶迎风 + 格点键面积测度）：
     转变 14.5%、长:短 2.3–2.7、法向 vs 相容法向中位 17.5°、S_v 用格点键测度 ✗。
   ★ 本轮口径：速度扩展（EDT）+ 二阶 ENO 迎风 + Sussman(upwind2) reinit +
     **几何 coarea 面积测度**（P1）⇒ S_v、t=2f/S_v 才可信。"""
import sys
import numpy as np
import windowB_surface as W

N = int(sys.argv[1]) if len(sys.argv) > 1 else 64
nstep = int(sys.argv[2]) if len(sys.argv) > 2 else 300
adv = sys.argv[3] if len(sys.argv) > 3 else 'upwind2'
g = W.M2_twelve_variants(N=N, nstep=nstep, adv_grad=adv)
print('\n[M2 收尾] 上风口径=%s ; 完成' % adv)