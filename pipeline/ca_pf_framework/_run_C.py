import os, subprocess, time
HERE='/mnt/f/speed_up/pipeline/ca_pf_framework'; PY='/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE); env0=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
# 全关 + 新阈值(0.25 自动停) + 大盒子 L=3.2um(N=160) 以进一步远离边界
B = ['--N','160','--dx','2e-8','--R','1.5e-7','--t','2.0e-7','--df','2e8','--nstep','1200',
     '--beta','3.5','--beta_w','2.3','--noelastic','1','--gamma','0.0','--reinit_every','0']
JOBS = [('C0', B + ['--elong','1.0']), ('C1', B + ['--elong','6.0'])]
ps=[]
for tag,args in JOBS:
    fh=open('_C_%s.log'%tag,'w')
    p=subprocess.Popen([PY,'_chk_single_lath.py','--tag',tag]+args,stdout=fh,
                       stderr=subprocess.STDOUT,env=dict(env0,OMP_NUM_THREADS='9'))
    ps.append((tag,p,fh)); print('launched',tag,flush=True)
while any(p.poll() is None for _,p,_ in ps): time.sleep(120)
for tag,p,fh in ps: fh.close(); print('done',tag,p.returncode,flush=True)
print('ALL_DONE',flush=True)
