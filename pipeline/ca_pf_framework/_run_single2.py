import os, subprocess, time
HERE='/mnt/f/speed_up/pipeline/ca_pf_framework'; PY='/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE); env0=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
JOBS=[('w0',  ['--beta','3.5','--beta_w','0.0']),
      ('w23', ['--beta','3.5','--beta_w','2.3']),
      ('w40', ['--beta','3.5','--beta_w','4.0'])]
ps=[]
for tag,args in JOBS:
    fh=open('_single2_%s.log'%tag,'w')
    p=subprocess.Popen([PY,'_chk_single_lath.py','--tag',tag]+args,
                       stdout=fh,stderr=subprocess.STDOUT,env=dict(env0,OMP_NUM_THREADS='5'))
    ps.append((tag,p,fh)); print('launched',tag,p.pid,flush=True)
while any(p.poll() is None for _,p,_ in ps): time.sleep(45)
for tag,p,fh in ps: fh.close(); print('done',tag,p.returncode,flush=True)
print('ALL_DONE',flush=True)
