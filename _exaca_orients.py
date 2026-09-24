#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_exaca_case.py --- 按 ExaCA Inp_TwoGrainDirSolidification 的初始条件重做
ExaCA 原算例: dx=1µm, 200^3, G=5e5 K/m, R=3e5 µm/s(=0.3 m/s), InitUndercooling=10K,
              In625 的 V(dT)=1.0533e-4 dT^2+2.2196e-3 dT-1.0302e-7 dT^3 (m/s), freezing_range=210K,
              两个种子在 (100,50) 与 (100,150)（y 方向相距 100 µm），取向取 GrainID 25 与 9936。
本机镜像: 同样【物理尺寸 200 µm】但 dx=4 µm（50^3），种子相距 25 胞，其余参数相同。
'''
import os, sys, math, time
import numpy as np
sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
from ca3d import CA3D, IRF, T_LIQ, quat_to_axes

CSV = '/mnt/f/speed_up/bench/exaca/GrainOrientationVectors.csv'


def read_orient(csv, ids):
    rows = []
    with open(csv) as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            rows.append(line)
    # 第一行是取向总数（README），其后每行 3 个分量
    n_head = int(float(rows[0].split(',')[0])) if ',' in rows[0] else None
    body = rows[1:] if n_head is not None else rows
    out = {}
    for gid in ids:
        ln = body[gid - 1] if gid - 1 < len(body) else body[-1]
        v = [float(x) for x in ln.replace(' ', ',').split(',') if x.strip() != '']
        out[gid] = np.array(v[:3], float)
        out[gid] /= np.linalg.norm(out[gid])
    return out, len(body)


ids = [25, 9936]
oris, ntot = read_orient(CSV, ids)
print('取向表条目数 = %d; GrainID 25 -> %s ; 9936 -> %s' % (
    ntot, np.round(oris[25], 4), np.round(oris[9936], 4)))


def vec_to_quat_to_P(v):
    '''ExaCA 的取向文件给的是【晶体 <100> 的方向向量】; 用它构造一组正交晶体轴:
    第 1 轴 = v, 另两轴由任意正交化得到（对包络的各向异性而言只有轴集重要）'''
    a1 = v / np.linalg.norm(v)
    tmp = np.array([0.0, 0.0, 1.0]) if abs(a1[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    a2 = np.cross(a1, tmp); a2 /= np.linalg.norm(a2)
    a3 = np.cross(a1, a2)
    # P 的列 = 晶体主轴（实验室系）：P[:,0]=<100> 方向 = a1
    return np.column_stack([a1, a2, a3])


P25 = vec_to_quat_to_P(oris[25])
P99 = vec_to_quat_to_P(oris[9936])
nhat = np.array([0.0, 0.0, 1.0])          # 梯度方向 +z
for nm, P in (('GrainID 25', P25), ('GrainID 9936', P99)):
    s = sum(abs(float(P[:, a] @ nhat)) for a in range(3))
    print('%s: Σ_a|p_a·ẑ| = %.4f  => 沿 +z 的径向速率 ∝ 1/Σ = %.4f  (小者胜)' % (nm, s, 1 / s))
sig25 = sum(abs(float(P25[:, a] @ nhat)) for a in range(3))
sig99 = sum(abs(float(P99[:, a] @ nhat)) for a in range(3))
print('=> 解析预测: 沿梯度更快的是 %s' % ('GrainID 25' if sig25 < sig99 else 'GrainID 9936'))
np.save('/mnt/f/speed_up/bench/exaca/P25.npy', P25)
np.save('/mnt/f/speed_up/bench/exaca/P99.npy', P99)