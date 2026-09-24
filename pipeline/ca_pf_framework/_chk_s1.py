#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S0/S1 回归（④ 移植 + 速度扩展 + 二阶 ENO 之后必须复核）"""
import windowB_surface as W
print(W.S0_curvature())
print(W.S1_GibbsThomson())
print(W.M1_multiregion_conservation())
print(W.M3_McLean())
print(W.M4_conservation())