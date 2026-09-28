import os, subprocess, time
HERE='/mnt/f/speed_up/pipeline/ca_pf_framework'; PY='/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE); env0=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
# 集束判据：同变体、沿 w 平行堆叠；弹性**开**（平行板条的相互作用是弹性的）
B = ['--N','80','--dx','2e-8','--R','8e-8','--t','2.0e-7','--df','2e8','--nstep','400',
     '--beta','3.5','--beta_w','2.3','--elong','6.0','--track','50','--band_cells','20']
JOBS = [('N1', B + ['--nplate','1']),                    # 单根
        ('N3', B + ['--nplate','3', '--pitch','2.4e-7']),# 3 根平行（间距 = 3R）
        ('N5', B + ['--nplate','5', '--pitch','1.6e-7'])] # 5 根平行（更密）
ps=[]
for tag,args in JOBS:
    fh=open('_BUN_%s.log'%tag,'w')
    p=subprocess.Popen([PY,'_chk_single_lath.py','--tag',tag]+args,stdout=fh,
                       stderr=subprocess.STDOUT,env=dict(env0,OMP_NUM_THREADS='6'))
    ps.append((tag,p,fh)); print('launched',tag,flush=True)
while any(p.poll() is None for _,p,_ in ps): time.sleep(60)
for tag,p,fh in ps: fh.close(); print('done',tag,p.returncode,flush=True)
print('ALL_DONE',flush=True)
