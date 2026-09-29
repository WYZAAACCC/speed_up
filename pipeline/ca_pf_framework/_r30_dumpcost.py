#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30-AUDIT：落盘代价实测汇总（region-only vs region+phi，N=96 / N=192）。"""
import glob
import os
import time

import numpy as np

HERE = '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp'

print('=== A. 归档里 region-only 快照的实测压缩体积 ===')
cases = [('N=96  cl1b', HERE + '/_bk_closed/dry_cl1b'),
         ('N=96  eng12', HERE + '/_bk_eng/eng_eng12'),
         ('N=192 dry_nr', HERE + '/_bk_block/dry_nr'),
         ('N=192 dry_p3', HERE + '/_bk_block/dry_p3'),
         ('N=64  main', HERE + '/_bk_f3smoke/main')]
for tag, d in cases:
    ss = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    for p in ss[:2] + ss[-1:]:
        z = np.load(p, allow_pickle=False)
        reg = z['region']
        nbytes = os.path.getsize(p)
        nlab = len(set(reg.ravel().tolist()))
        print('  %-14s %-28s N=%3d 磁盘=%8.1f kB  region裸=%6.2f MB '
              '压缩比=%5.2f  标签数=%d'
              % (tag, os.path.basename(p), reg.shape[0], nbytes / 1e3,
                 reg.nbytes / 1e6, reg.nbytes / nbytes, nlab))
        z.close()

print()
print('=== B. region + phi 的写盘耗时（实测，本机 /mnt/f）===')
for tag, d in [('N=96 nv=7', HERE + '/_bk_block/dry_t1'),
               ('N=192 nv=7', HERE + '/_bk_block/dry_p1/'),
               ('N=64 nv=3', HERE + '/_bk_f3smoke/main')]:
    ss = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    p = ss[-1]
    z = np.load(p, allow_pickle=False)
    if 'phi' not in z.files:
        print('  %-12s 无 phi，跳过' % tag)
        z.close()
        continue
    reg, phi = z['region'], z['phi']
    t0 = time.time(); np.savez_compressed('/tmp/a.npz', region=reg)
    t_reg = time.time() - t0; s_reg = os.path.getsize('/tmp/a.npz')
    t0 = time.time(); np.savez_compressed('/tmp/b.npz', region=reg, phi=phi)
    t_both = time.time() - t0; s_both = os.path.getsize('/tmp/b.npz')
    print('  %-12s N=%3d nv=%d | region-only %6.2f MB %5.2f s | '
          'region+phi %7.2f MB %6.2f s | phi 净增 %7.2f MB'
          % (tag, reg.shape[0], phi.shape[0], s_reg / 1e6, t_reg,
             s_both / 1e6, t_both, (s_both - s_reg) / 1e6))
    z.close()
