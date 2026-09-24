#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M2 判据（2026-09-25 重做，含两个真修正：自适应 dt + Λ 回到稳定区）。
   判据（可判读性，不靠自评）：
     (a) 带健康：25–40 步内**带胞不塌**、带内 |∇φ_winner| 不涨（应 ~0.5–2）
     (b) 12 个变体**全部存活**（min(V)>0）
     (c) 几何量可引用：长:短、法向 vs 相容法向夹角
   对照：Λ=10（越出 Herring 稳定界 Λ<1）与 per_field=True（方案 (a)）
用法：_chk_m2c.py <N> <nstep>
"""
import sys
import windowB_surface as W

N = int(sys.argv[1]) if len(sys.argv) > 1 else 32
nstep = int(sys.argv[2]) if len(sys.argv) > 2 else 40
for tag, kw in (('A  Λ=0.40 按区域核（默认）', dict(aniso=0.4, per_field=False)),
                ('B  Λ=0.40 按场推进（方案 a）', dict(aniso=0.4, per_field=True)),
                ('C  Λ=10.0 对照（越 Herring 界）', dict(aniso=10.0, per_field=False))):
    print('=' * 78)
    print('==== M2-%s ====' % tag)
    W.M2_twelve_variants(N=N, nstep=nstep, probe=10, **kw)