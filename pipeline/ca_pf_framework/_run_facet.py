import os, subprocess, time
HERE='/mnt/f/speed_up/pipeline/ca_pf_framework'; PY='/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE); env0=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
B=['--beta','3.5','--beta_w','2.3','--nstep','1200']
JOBS=[('F0', B+['--facet','0.0']), ('F4', B+['--facet','0.4']), ('F10', B+['--facet','1.0'])]
ps=[]
for tag,args in JOBS:
    fh=open('_facet_%s.log'%tag,'w')
    p=subprocess.Popen([PY,'_chk_single_lath.py','--tag',tag]+args,
                       stdout=fh,stderr=subprocess.STDOUT,env=dict(env0,OMP_NUM_THREADS='5'))
    ps.append((tag,p,fh)); print('launched',tag,p.pid,flush=True)
while any(p.poll() is None for _,p,_ in ps): time.sleep(90)
for tag,p,fh in ps: fh.close(); print('done',tag,p.returncode,flush=True)
print('ALL_DONE',flush=True)
