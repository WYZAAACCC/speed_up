#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_exaca_geom_test.py --- 单晶算例量 ExaCA 的包络几何，与解析 L1 球 (r=ℓ/Σ) 对比
ExaCA: SimulationType=SingleGrain, 101^3, dx=1µm, G=0,R=0, InitUndercooling=10K, Ti64 表
       取向 = 取向表第 1 条（三个晶轴向量已知）=> 可算解析预测
'''
import os, json, subprocess, math
import numpy as np
RUN = '/root/bench/run'
EXA = '/root/bench/ExaCA-master/build/bin/ExaCA'
D = '/mnt/f/speed_up/bench/exaca'
NX = 101
VEC = np.loadtxt(D + '/GrainOrientationVectors.csv', delimiter=',', skiprows=1).reshape(-1, 3, 3)
P = VEC[0].T                       # 列 = 晶轴（与 CSV 行向量同一组方向）
TAB = np.loadtxt(RUN + '/irf_ti64_table.csv', delimiter=',', skiprows=1)
DTU = 10.0
V10 = float(np.interp(DTU, TAB[:, 0], TAB[:, 1]))
inp = {
 "SimulationType": "SingleGrain",
 "MaterialFileName": RUN + "/Ti64.json",
 "GrainOrientationFile": RUN + "/GrainOrientationVectors.csv",
 "Domain": {"CellSize": 1, "TimeStep": 0.0666667, "Nx": NX, "Ny": NX, "Nz": NX},
 "TemperatureData": {"InitUndercooling": DTU, "G": 0, "R": 0},
 "Substrate": {"GrainOrientation": 0},
 "Printing": {"PathToOutput": RUN + "/", "OutputFile": "Geom_Single",
              "PrintBinary": False, "PrintExaConstitSize": 0,
              "Interlayer": {"Fields": ["GrainID"]}},
}
json.dump(inp, open(RUN + '/Inp_Geom.json', 'w'), indent=1)
r = subprocess.run([EXA, RUN + '/Inp_Geom.json'], cwd=RUN, capture_output=True, text=True)
print('ExaCA 单晶: rc=%d' % r.returncode)
for ln in r.stdout.split('\n'):
    if 'cycle' in ln or 'nucleated' in ln:
        print('  ', ln.strip())
fp = RUN + '/Geom_Single.vtk'
lines = open(fp).readlines()
gid = None
for i, ln in enumerate(lines):
    if ln.strip().upper().startswith('SCALARS') and 'grainid' in ln.lower():
        vals = []; j = i + 2
        while j < len(lines):
            t = lines[j].strip()
            if not t or t[0].isalpha():
                break
            vals += [int(float(x)) for x in t.split()]; j += 1
        gid = np.array(vals); break
print('  输出胞数 %d (期望 %d)' % (len(gid), NX**3))
ids, cnt = np.unique(gid[gid > 0], return_counts=True)
print('  晶粒数 = %d, 最大晶粒胞数 = %d' % (len(ids), cnt.max()))
g = gid.reshape((NX, NY := NX, NX), order='F')     # VTK: x 最快
c = NX // 2
# 由最大晶粒的胞数反推 ℓ：体积 = 8ℓ³/6 (ℓ 以胞计）
vol = int(cnt.max())
ell = (vol * 6 / 8.0) ** (1 / 3.0)
print('  由体积反推 ℓ = %.2f 胞 (解析体积 8ℓ³/6)' % ell)
print()
print('  方向           Σ_a|p_a·n̂|   ℓ/Σ(解析)   ExaCA 实测   偏差(胞)')
for nm, cv in (('crystal <100>', (1, 0, 0)), ('crystal <010>', (0, 1, 0)),
               ('crystal <001>', (0, 0, 1)), ('crystal <110>', (1, 1, 0)),
               ('crystal <111>', (1, 1, 1)), ('crystal (1,2,0)', (1, 2, 0))):
    cv = np.array(cv, float); cv /= np.linalg.norm(cv)
    nw = P @ cv
    sig = sum(abs(float(P[:, a] @ nw)) for a in range(3))
    sm = 0.0
    for rr in np.arange(0, NX * 0.49, 0.1):
        p = np.array([c + 0.5, c + 0.5, c + 0.5]) + rr * nw
        idx = np.floor(p).astype(int)
        if np.any(idx < 0) or np.any(idx >= NX):
            break
        if g[idx[0], idx[1], idx[2]] > 0:
            sm = rr
    ana = ell / sig
    print('  %-15s %.3f        %6.2f      %6.2f      %+.2f' % (nm, sig, ana, sm, sm - ana))