import os, subprocess, time
HERE='/mnt/f/speed_up/pipeline/ca_pf_framework'; PY='/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE); env0=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
# 大盒子: L = 120*0.02 = 2.4um (半边 1.2um) ; R=0.15um => elong=6 时长轴 0.9um <= 1.2um ✓
B = ['--N','120','--dx','2e-8','--R','1.5e-7','--t','2.0e-7','--df','2e8','--nstep','1200',
     '--beta','3.5','--beta_w','2.3']
JOBS = [('A0', B + ['--elong','1.0']),          # 圆盘种子
        ('A1', B + ['--elong','6.0'])]          # 椭圆种子
ps=[]
for tag,args in JOBS:
    fh=open('_A_%s.log'%tag,'w')
    p=subprocess.Popen([PY,'_chk_single_lath.py','--tag',tag]+args,stdout=fh,
                       stderr=subprocess.STDOUT,env=dict(env0,OMP_NUM_THREADS='8'))
    ps.append((tag,p,fh)); print('launched',tag,flush=True)
while any(p.poll() is None for _,p,_ in ps): time.sleep(120)
for tag,p,fh in ps: fh.close(); print('done',tag,p.returncode,flush=True)
print('ALL_DONE',flush=True)
