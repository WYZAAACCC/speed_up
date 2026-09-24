#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
echo "=== 1) 原有 envelope 判据是否还过（E1）:"
OMP_NUM_THREADS=1 /root/miniconda3/envs/ml/bin/python verify_ca3d_envelope.py 2>&1 | sed -n '1,12p'
echo; echo "=== 2) 单晶调试（envelope 模式）:"
OMP_NUM_THREADS=1 /root/miniconda3/envs/ml/bin/python - <<'EOF'
import sys, math
import numpy as np
sys.path.insert(0,'/mnt/f/speed_up/pipeline/ca_pf_framework')
from ca3d import CA3D, IRF, T_LIQ
def qaa(axis, deg):
    a=np.array(axis,float); a/=np.linalg.norm(a); th=math.radians(deg)
    return (math.cos(th/2), *(a*math.sin(th/2)))
ca = CA3D(81,81,81,1e-6, irf=IRF(), seed=7, capture='envelope')
g = ca.add_grain(40,40,40, quat=qaa((0.3,0.7,0.2),37.0))
V = float(ca.irf.capped(np.array([12.0]))[0][0]); dt = 1e-6/(4*V)
t=0.0
for s in range(60):
    ca.t=t; ca.step(dt, ca.T_iso(12.0), window='full'); t+=dt
print('  晶粒数 =', len(ca.grain_ids()), ' 该晶粒胞数 =', int((ca.gid==g).sum()))
print('  标称 ℓ =', V*60*dt/1e-6, '胞 ; Lg[g] =', ca._Lg[g]/1e-6, '胞')
idx = np.argwhere(ca.gid>0)
print('  gid 的 x 范围:', idx[:,0].min(), idx[:,0].max())
print('  最大 |x-40| =', np.abs(idx[:,0]-40).max(), '胞')
EOF