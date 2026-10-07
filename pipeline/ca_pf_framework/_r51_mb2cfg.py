#!/usr/bin/env python3
"""R51: 现有**多块**臂（`eng_mb2`）的配置 —— 好让"满足 Δx≤63 nm"的新臂**只差一个变量**。"""
import json
import os

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
for arm in ('_exp/_bk_mb/eng_mb2', '_exp/_bk_mb/eng_mb3', '_exp/_bk_mb/dry_mb1L',
            '_exp/_bk_mb/dry_mb1s62'):
    p = os.path.join(arm, 'meta.json')
    if not os.path.exists(p):
        continue
    m = json.load(open(p))
    pl = m.get('plate') or {}
    N = m['N']
    dx = m['dx_nm']
    print('=== %s' % os.path.basename(arm))
    print('   N=%s  dx=%.1f nm  ⇒ 盒边长 = %.2f µm' % (N, dx, N * dx / 1000))
    print('   laths=%s  (变体数=%d)'
          % (m.get('laths'), len(set(m.get('laths') or []))))
    print('   plate: L=%.0f W=%.0f T=%.0f T_phys=%.0f nm'
          % (pl.get('L', 0), pl.get('W', 0), pl.get('T', 0), pl.get('T_physical', 0)))
    print('   t/Δx（含界面）= %.2f   t_phys/Δx = %.2f'
          % (pl.get('T', 0) / dx, pl.get('T_physical', 0) / dx))
    print('   gap_nm=%s  nuc_every=%s  steps=%s  nthreads=%s  stem=%s'
          % (m.get('gap_nm'), m.get('nuc_every'), m.get('steps'),
             m.get('nthreads'), m.get('grow_stack')))
    print('   beta_h=%s beta_w=%s gamma0=%s' % (m.get('beta_h'), m.get('beta_w'),
                                                m.get('gamma0')))
print()
print('★ 若 `eng_mb2` 已经是"多变异 + N=96"，那么满足 §33 的新臂应**只改 Δx**')
print('  （125 → 62.5），盒随之从 12 µm 变 6 µm ⇒ 板条尺寸需等比缩小以仍能容纳。')
