#!/bin/bash
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
R=/root/work/p3dyn; rm -rf $R; mkdir -p $R; cd $R
for K in 0 1.0e4; do
  python3 - "$K" <<'PY'
import sys
K=sys.argv[1]
sys.path.insert(0,'/mnt/f/speed_up/pipeline/gibbs')
import gibbs_physics as GP
c0=0.036; rho=GP.RHO_MOL
K_T=GP.K_mclean(GP.T_LPBF,-11931.1); As=GP.GAMMA_MONO*K_T
AsRho=As/rho; Kex=As*1.0e6/rho
V=8e-9*8e-9*16e-9; A=8e-9*16e-9
cf=c0*rho*V/(rho*V+As*A)
tpl=open('/mnt/f/speed_up/pipeline/gibbs/validated/proto3d_gibbs_coupled.i.tpl',encoding='utf-8').read()
out=(tpl.replace('@C0@','%.10g'%c0).replace('@AS@','%.10g'%As)
        .replace('@RHOMOL@','%.10g'%rho).replace('@ASRHO@','%.10g'%AsRho)
        .replace('@KEX@','%.10g'%Kex).replace('@CF@','%.8f'%cf)
        .replace('@DEP@','%.2f'%((c0-cf)/c0*100))
        .replace('@EPSK@',K)
        .replace('@DT@','5.0e-07').replace('@TEND@','1.0e-04'))
open('g_%s.i'%K,'w',encoding='utf-8',newline='').write(out)
PY
  echo "=== EPSK = $K (解析 c_f=0.03411748) ==="
  timeout 1500 /root/projects/gibbs/gibbs-opt -i "g_$K.i" > "L_$K.log" 2>&1
  echo "rc=$?  JIT=$(grep -c 'JIT compile failed' L_$K.log)  未收敛=$(grep -c 'Solve Did NOT Converge' L_$K.log)"
  sed "s/\x1b\[[0-9;]*m//g" "L_$K.log" | grep -A6 -m1 '\*\*\* ERROR' | head -10
  head -1 "g_${K}_out.csv" 2>/dev/null
  echo "  首行: $(sed -n 2p g_${K}_out.csv)"
  echo "  末行: $(tail -1 g_${K}_out.csv)"
done
mkdir -p /mnt/f/speed_up/pipeline/gibbs/results_p3dyn
cp -f L_*.log g_*.i g_*_out.csv /mnt/f/speed_up/pipeline/gibbs/results_p3dyn/ 2>/dev/null