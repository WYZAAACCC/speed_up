#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M2 的 A/B：多界面下"配对一致性"是否修好（审计 §9.5 的判据）。
   旧病：宽带扩展按**区域**做 ⇒ 两区域之间的差分 φ_k−φ_l 被拉陡 ⇒
        带胞 36676→155、带内 |∇φ_winner| 0.51→529.9 ⇒ 几何测度静默归零 ✗。
   修法：`band = (dist<=band_cells) & same_pair({k,l})` + 延拓**跨界面连续的规范形**。
   判据：带胞数**不塌**、带内 |∇φ_winner| 中位 **不涨**（≈1–2）。
用法：_chk_m2ab.py <N> <nstep> <pair_kernel 0/1> <probe>
"""
import sys
import numpy as np
import windowB_surface as W

N = int(sys.argv[1]) if len(sys.argv) > 1 else 32
nstep = int(sys.argv[2]) if len(sys.argv) > 2 else 120
pk = bool(int(sys.argv[3])) if len(sys.argv) > 3 else False
probe = int(sys.argv[4]) if len(sys.argv) > 4 else 20
print('==== M2 A/B : pair_kernel=%s  N=%d nstep=%d ====' % (pk, N, nstep))
g = W.M2_twelve_variants(N=N, nstep=nstep, pair_kernel=pk, probe=probe)