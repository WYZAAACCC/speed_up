#!/bin/bash
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
R=/root/work/p3c; rm -rf $R; mkdir -p $R; cd $R
# --- 常数（与 gibbs_physics.py 一致）---
python3 - <<'PY'
import sys
sys.path.insert(0,'/mnt/f/speed_up/pipeline/gibbs')
import gibbs_physics as GP
T=GP.T_LPBF; DH=-11931.1
K=GP.K_mclean(T,DH); As=GP.GAMMA_MONO*K; rho=GP.RHO_MOL; katt=1.0e6
AsRho=As/rho; Kex=As*katt/rho
c0=0.036; V=8e-9*8e-9*16e-9; A=8e-9*16e-9
cf=c0*rho*V/(rho*V+As*A)
tpl=open('/mnt/f/speed_up/pipeline/gibbs/validated/proto3d_gibbs_coupled.i.tpl',encoding='utf-8').read()
out=(tpl.replace('@C0@','%.10g'%c0).replace('@AS@','%.10g'%As)
        .replace('@RHOMOL@','%.10g'%rho).replace('@ASRHO@','%.10g'%AsRho)
        .replace('@KEX@','%.10g'%Kex).replace('@CF@','%.8f'%cf)
        .replace('@DEP@','%.2f'%((c0-cf)/c0*100))
        .replace('@DT@','5.0e-07').replace('@TEND@','1.0e-04'))
open('g.i','w',encoding='utf-8',newline='').write(out)
print("As=%.6e  AsRho=%.6e  Kex=%.6e"%(As,AsRho,Kex))
print("解析: c_f=%.8f  贫化=%.2f%%"%(cf,(c0-cf)/c0*100))
PY
timeout 1800 /root/projects/gibbs/gibbs-opt -i g.i > run.log 2>&1
echo "rc=$?  JIT失败=$(grep -c 'JIT compile failed' run.log)  未收敛=$(grep -c 'Solve Did NOT Converge' run.log)"
sed "s/\x1b\[[0-9;]*m//g" run.log | grep -A8 -m1 '\*\*\* ERROR' | head -14
echo "=== CSV ==="
head -1 g_out.csv 2>/dev/null
echo "--- 首行 ---"; sed -n 2p g_out.csv 2>/dev/null
echo "--- 末行 ---"; tail -1 g_out.csv 2>/dev/null
mkdir -p /mnt/f/speed_up/pipeline/gibbs/results_p3c
cp -f run.log g.i g_out.csv /mnt/f/speed_up/pipeline/gibbs/results_p3c/ 2>/dev/null