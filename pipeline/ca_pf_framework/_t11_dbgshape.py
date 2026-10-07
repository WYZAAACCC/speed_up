#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_dbgshape.py —— 定位 `fibonacci_sphere` 的形状问题。"""
import numpy as np
M = 10
i = np.arange(M) + 0.5
phi = np.arccos(1 - 2 * i / M)
gold = np.pi * (1 + 5 ** 0.5)
th = gold * i
print("phi", phi.shape, "th", th.shape)
nd = np.stack([np.cos(th) * np.sin(phi),
               np.sin(th) * np.sin(phi),
               np.cos(phi)], axis=1)
print("nd", nd.shape)
print("first row", nd[0])
