import os, subprocess, time
HERE='/mnt/f/speed_up/pipeline/ca_pf_framework'; PY='/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE); env0=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
JOBS=[('T2', ['--t','1.0e-7']),   # 2 胞（对照，已知反常）
      ('T6', ['--t','3.0e-7']),   # 6 胞
      ('T10',['--t','5.0e-7'])]   # 10 胞
ps=[]
for tag,args in JOBS:
    fh=open('_thick_%s.log'%tag,'w')
    p=subprocess.Popen([PY,'_chk_single_lath.py','--tag',tag,'--beta','3.5','--beta_w','2.3',
                        '--nstep','1200','--track','80']+args,
                       stdout=fh,stderr=subprocess.STDOUT,env=dict(env0,OMP_NUM_THREADS='6'))
    ps.append((tag,p,fh)); print('launched',tag,p.pid,flush=True)
while any(p.poll() is None for _,p,_ in ps): time.sleep(90)
for tag,p,fh in ps: fh.close(); print('done',tag,p.returncode,flush=True)
print('ALL_DONE',flush=True)
