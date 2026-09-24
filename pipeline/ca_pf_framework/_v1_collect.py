#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_v1_collect.py --- 汇总 V1 给定条件验证campaign：预测 vs 实测'''
import os, json, glob, math
import numpy as np
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_v1_out')
R = {}
for f in sorted(glob.glob(os.path.join(D, '*.json'))):
    r = json.load(open(f))
    R.setdefault(r['task'], []).append(r)

def ver(rs):
    vs = [x.get('verdict') for x in rs]
    return '%d/%d PASS' % (sum(1 for v in vs if v == 'PASS'), len(vs))

print('=' * 104)
print('V1 验证campaign（56 个 worker / 16 路并行）：每个实验先写解析预测，再用同一初始条件实测')
print('=' * 104)

# ---- t1
rs = R['t1_octahedron']; r = rs[0]
print('\n[T1] 对齐取向单晶 = KD 八面体')
print('     预测: 顶点 r=ℓ(±1.5胞)、面心 r=0.577ℓ(±1.5胞)')
print('     实测: 6 个轴 r/ℓ = %.4f ~ %.4f (最大偏差 %.2f 胞)' % (
    min(r['axes_r'].values()), max(r['axes_r'].values()), r['err_axis_cells']))
print('           <111> r/ℓ = %.4f (预测 %.4f, 差 %.2f 胞)' % (r['diag'], r['diag_pred'], r['diag_err_cells']))
print('           体积 %d vs 解析 %d (%+.1f%%)  ← 胞心判据+{111}体素化的系统偏置' % (
    r['vol'], int(r['vol_pred']), r['vol_err']))
print('     判定: %s  %s' % (r['verdict'], ver(rs)))

# ---- t2
print('\n[T2] 生长速率律 d(reach)/dt = V(ΔT)/Σ(n̂)')
for r in R['t2_velocity']:
    print('     方向 %-10s Σ=%.3f  实测 %.5f vs 预测 %.5f m/s  偏差 %+.1f%%   %s' % (
        str(r['cdir']), r['sigma'], r['slope'], r['slope_pred'], r['err_pct'], r['verdict']))
print('     判定: %s' % ver(R['t2_velocity']))

# ---- t3
dev = [r['dev_ideal_max_cells'] for r in R['t3_aniso_law']]
devm = [r['dev_ideal_mean_cells'] for r in R['t3_aniso_law']]
n = sum(r['n'] for r in R['t3_aniso_law'])
print('\n[T3] 各向异性律 r/ℓ = 1/Σ（24 取向 × 13 方向 = %d 个测点）' % n)
print('     与理想律的偏离: 最大 %.2f 胞 / 平均 %.2f 胞（应 <=1.2 胞）' % (max(dev), np.mean(devm)))
print('     判定: %s' % ver(R['t3_aniso_law']))

# ---- t4
me = [r['mean_err_cells'] for r in R['t4_gb_locus'] if r['mean_err_cells'] is not None]
p95 = [r['p95_err_cells'] for r in R['t4_gb_locus'] if r['p95_err_cells'] is not None]
print('\n[T4] 双晶晶界位置 = 解析轨迹 {sup_A = sup_B}（6 对取向）')
print('     平均误差 %.2f 胞 (max %.2f)；p95 误差 %.2f 胞' % (np.mean(me), max(me), np.mean(p95)))
print('     判定: %s' % ver(R['t4_gb_locus']))

# ---- t5
cases = [c for r in R['t5_wc_pairs'] for c in r['cases']]
ok = [c['ok'] for c in cases if c.get('ok') is not None]
print('\n[T5] Walton-Chalmers 择优：对齐度最大者持有领先前沿（%d 个双晶算例）' % len(ok))
print('     符合率 = %.1f%% (%d/%d)' % (100 * np.mean(ok), sum(ok), len(ok)))
print('     判定: %s' % ver(R['t5_wc_pairs']))

# ---- t6
print('\n[T6] 9 晶粒 + 倾斜梯度：竞争与淘汰过程（8 个算例）')
cs = []
for r in R['t6_elimination']:
    c = r['curve']
    cs.append([c[i][1] for i in range(len(c))])
cs = np.array(cs)
steps = [R['t6_elimination'][0]['curve'][i][0] for i in range(cs.shape[1])]
print('     活跃(接触液相)晶粒数 vs 步数:')
print('       ' + '  '.join('s%d:%s' % (s, '%.1f' % m) for s, m in zip(steps, cs.mean(axis=0))))
print('     末态持有前沿晶粒数: %s (预测 <=3)' % [r['n_final'] for r in R['t6_elimination']])
print('     持有者对齐度 %s' % [r['hold_align'] for r in R['t6_elimination']][:3])
print('     判定: %s  (注: 均匀驱动下 envelope 与 analytic 逐位等价)' % ver(R['t6_elimination']))

# ---- t7
print('\n[T7] 体形核：形核数 vs N_max（连续形核谱）')
for r in R['t7_nucleation']:
    print('     N_max=%.0e -> 形核 %d 个 (比例 %.3f)  %s' % (
        r['Nmax'], r['n_bulk'], r['ratio'] if r['ratio'] else 0, r['verdict']))
print('     判定: %s' % ver(R['t7_nucleation']))

# ---- t8
print('\n[T8] 八面体体积偏差 vs dx（是否 O(dx)）')
for ori in ('random', 'aligned'):
    rs = sorted([r for r in R['t8_dx_conv'] if r['ori'] == ori], key=lambda x: -x['dx_um'])
    print('     %-8s' % ori + '  '.join('dx=%.1fum: %+.2f%% (ℓ=%.0f胞)' % (
        r['dx_um'], r['err_pct'], r['ell_cells']) for r in rs))
print('     判定: %s（见上方趋势：误差应随 dx 减小而减小）' % ver(R['t8_dx_conv']))