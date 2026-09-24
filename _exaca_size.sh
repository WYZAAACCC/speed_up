#!/bin/bash
cd /root/bench/ExaCA-master
echo "=== InterfacialResponseInputs 结构:"; grep -n -A22 'struct InterfacialResponseInputs' src/CAinputdata.hpp
echo; echo "=== 材料文件解析（coefficients 那一段）:"; grep -n -B4 -A20 'coefficients' src/CAinputs.hpp | head -45
echo; echo "=== 窗口内幂律拟合质量（dT 10-18K）:"
/root/miniconda3/envs/ml/bin/python - <<'EOF'
import numpy as np
from scipy.optimize import curve_fit
t = np.loadtxt('/mnt/f/speed_up/pipeline/ca_pf_framework/irf_ti64.csv', delimiter=',', skiprows=1)
dT, V = t[:,0], t[:,1]
for lo, hi in ((10,18),(12,18),(14,18),(4.745,17.974)):
    m = (dT>=lo)&(dT<=hi)
    if m.sum() < 8: print('  窗口 %g-%g 太少' % (lo,hi)); continue
    def pw(x,A,b,C): return A*x**b + C
    p,_ = curve_fit(pw, dT[m], V[m], p0=[1e-5,4,0], maxfev=200000)
    rel = np.abs(pw(dT[m],*p)-V[m])/V[m]
    print('  窗口 %5.2f-%5.2f K: 最大 %.1f%%, 平均 %.1f%%' % (lo,hi,100*rel.max(),100*rel.mean()))
EOF