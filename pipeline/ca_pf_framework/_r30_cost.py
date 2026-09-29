#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30-AUDIT ★ `phi` 落盘的**实测代价**（磁盘 + 每步墙钟），**只读**。

用 `_bk_block` 里**真实**的 `phi`（N=96, nv=6, float32）压缩一遍，
量出 `savez_compressed` 的体积与耗时 ⇒ 外推到 N=192。
再把**真实的 N=192 region** 放大成合成的 7×N³ float32 φ 场，量 N=192 的代价。

⚠ 不做任何仿真，不写 `_exp/`，只在 /tmp 写小文件。
"""
import os
import time
import glob

import numpy as np

REAL96 = glob.glob('/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/'
                   '_bk_block/dry_p1/snap_*.npz')
z = np.load(REAL96[0])
phi96 = z['phi']
print('真实 φ（_bk_block/dry_p1, N=96）：shape=%s dtype=%s 未压缩=%.1f MB'
      % (phi96.shape, phi96.dtype, phi96.nbytes / 1e6))
print('   占用率：非零胞占比 %.3f   |φ|>0.05 占比 %.3f   max=%.4f'
      % (float((phi96 != 0).mean()), float((np.abs(phi96) > 0.05).mean()),
         float(phi96.max())))

for tag, arr in (('N=96 真实', phi96),):
    t0 = time.time()
    np.savez_compressed('/tmp/r30_phi96.npz', phi=arr)
    dt = time.time() - t0
    sz = os.path.getsize('/tmp/r30_phi96.npz')
    print('   %s: 压缩后 %.2f MB  (压缩比 %.1fx)  写盘 %.2f s'
          % (tag, sz / 1e6, arr.nbytes / sz, dt))

# ---- N=192 合成：真实 region 放大 2× 再用 tanh 抹成连续场 ----
z192p = glob.glob('/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/*/*/'
                  'snap_*.npz')
cand = None
for p in z192p:
    zz = np.load(p)
    if zz['region'].shape[0] == 192:
        cand = p
        break
print('找到 N=192 的真实快照: %s' % cand)
if cand:
    zz = np.load(cand)
    reg = zz['region']
    vmap = {int(k): int(v) for k, v in zip(zz['vmap_keys'], zz['vmap_vals'])}
    nv = max(vmap) if vmap else int(reg.max())
    print('   N=192 region: nv=%d nreg_used=%d 占用率=%.4f'
          % (nv, len(set(reg.ravel().tolist()) - {0}),
             float((reg != 0).mean())))
    # 合成 φ：对每个非零场做 ±tanh 抹平（**不是**真仿真，只用于量压缩代价）
    rng = np.random.default_rng(0)
    soft = np.zeros(reg.shape, np.float32)
    for k in range(1, nv + 1):
        m = (reg == k)
        if not m.any():
            continue
        soft += np.where(m, 1.0, -1.0).astype(np.float32) * (1.0 / nv)
    soft += (rng.standard_normal(reg.shape) * 1e-3).astype(np.float32)
    out = np.empty((nv,) + reg.shape, np.float32)
    for k in range(nv):
        out[k] = soft + (0.01 * k)
    print('   合成 φ(N=192, nv=%d)：未压缩 %.1f MB' % (nv, out.nbytes / 1e6))
    t0 = time.time()
    np.savez_compressed('/tmp/r30_phi192.npz', phi=out)
    dt = time.time() - t0
    sz = os.path.getsize('/tmp/r30_phi192.npz')
    print('   压缩后 %.2f MB (压缩比 %.1fx)  写盘 %.2f s' % (sz / 1e6,
                                                         out.nbytes / sz, dt))
    t0 = time.time()
    np.savez_compressed('/tmp/r30_reg192.npz', region=reg)
    print('   对照：只存 region(N=192) %.2f MB  写盘 %.2f s'
          % (os.path.getsize('/tmp/r30_reg192.npz') / 1e6, time.time() - t0))
