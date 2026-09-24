#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""{334}_beta 家族在弹性能上是否系统性优于随机方向？
   —— 决定"模拟板条法向落在 {334} 附近"是真信号还是巧合（弹性谷很平时的随机落点）。
   同时给出 24 个 {334} 成员里的最小/中位能量，与 2000 个随机方向的分位数比较。"""
import itertools
import numpy as np
from windowB_pf3d import C_iso3, _lam_full
from windowB_ti64_variants import variants

C = C_iso3(113e9, 0.34)
eps0, Fs, meta = variants()


def v334_family():
    out = []
    for perm in set(itertools.permutations((3, 3, 4))):
        for s in itertools.product((1, -1), repeat=3):
            v = np.array([p * ss for p, ss in zip(perm, s)], float)
            out.append(v / np.linalg.norm(v))
    return np.array(out)


F334 = v334_family()
print('{334} 家族成员数 =', len(F334))
rng = np.random.default_rng(0)
rand = rng.normal(size=(3000, 3))
rand /= np.linalg.norm(rand, axis=1)[:, None]
print('=' * 92)
print('%-6s %14s %14s %14s %10s' % ('变体', '{334}最小', '{334}中位', '随机中位', '倍数'))
for v in range(min(6, len(eps0))):
    e = eps0[v]
    def val(n):
        return 0.5 * float(np.einsum('ij,ijkl,kl->', e, _lam_full(C, n), e))
    f = np.array([val(n) for n in F334])
    r = np.array([val(n) for n in rand])
    print('V%-5d %14.3e %14.3e %14.3e %10.2f'
          % (v + 1, f.min(), np.median(f), np.median(r), np.median(r) / max(np.median(f), 1e-30)))
    print('       随机方向的 1%%/5%% 分位 = %.3e / %.3e ; {334}最小落在随机分布的 %.1f%% 分位'
          % (np.percentile(r, 1), np.percentile(r, 5),
             100.0 * (r < f.min()).mean()))
