import os, subprocess, time
HERE='/mnt/f/speed_up/pipeline/ca_pf_framework'; PY='/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE); env0=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
# 椭圆种子 elong=6, 全关, 每 25 步记录主轴；只跑 300 步（看**相对**增长）
B = ['--N','120','--dx','2e-8','--R','1.5e-7','--t','2.0e-7','--df','2e8','--nstep','300',
     '--beta','3.5','--beta_w','2.3','--noelastic','1','--gamma','0.0','--reinit_every','0',
     '--elong','6.0','--track','25']
JOBS = [('D20', ['--band_cells','20']),   # 默认（与 C1 同）
        ('D03', ['--band_cells','3'])]    # 远小于种子厚度(10 胞)
ps=[]
for tag,extra in JOBS:
    fh=open('_D_%s.log'%tag,'w')
    p=subprocess.Popen([PY,'_chk_single_lath.py','--tag',tag]+extra+B,stdout=fh,
                       stderr=subprocess.STDOUT,env=dict(env0,OMP_NUM_THREADS='9'))
    ps.append((tag,p,fh)); print('launched',tag,flush=True)
while any(p.poll() is None for _,p,_ in ps): time.sleep(60)
for tag,p,fh in ps: fh.close(); print('done',tag,p.returncode,flush=True)
print('ALL_DONE',flush=True)
