import os, subprocess, time
HERE='/mnt/f/speed_up/pipeline/ca_pf_framework'; PY='/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE); env0=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
B = ['--N','80','--dx','2e-8','--R','1.2e-7','--t','2.0e-7','--df','2e8','--nstep','250',
     '--beta','3.5','--noelastic','1','--gamma','0.0','--reinit_every','0',
     '--elong','6.0','--track','25','--band_cells','20']
JOBS = [('W23', ['--beta_w','2.3']),   # 现行标定（由"长/宽 = e^beta_w"反推，本文档 §9）
        ('W50', ['--beta_w','5.0']),
        ('W60', ['--beta_w','6.0'])]
ps=[]
for tag,extra in JOBS:
    fh=open('_W_%s.log'%tag,'w')
    p=subprocess.Popen([PY,'_chk_single_lath.py','--tag',tag]+extra+B,stdout=fh,
                       stderr=subprocess.STDOUT,env=dict(env0,OMP_NUM_THREADS='6'))
    ps.append((tag,p,fh)); print('launched',tag,flush=True)
while any(p.poll() is None for _,p,_ in ps): time.sleep(60)
for tag,p,fh in ps: fh.close(); print('done',tag,p.returncode,flush=True)
print('ALL_DONE',flush=True)
