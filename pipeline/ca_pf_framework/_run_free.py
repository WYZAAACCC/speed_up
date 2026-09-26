import os, subprocess, time
HERE='/mnt/f/speed_up/pipeline/ca_pf_framework'; PY='/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE); env0=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
# 孤立单核**自由生长**（无邻居挤压）：L=1.6 um, dx=20 nm, R=0.3 um, 厚=0.2 um(10 胞)
B=['--N','80','--dx','2e-8','--R','3.0e-7','--t','2.0e-7','--df','2e8','--nstep','2000']
ps=[]
for tag,args in [('F1', B+['--beta','3.5','--beta_w','2.3']),
                 ('F2', B+['--beta','0.0','--beta_w','0.0'])]:
    fh=open('_free_%s.log'%tag,'w')
    p=subprocess.Popen([PY,'_chk_single_lath.py','--tag',tag]+args,stdout=fh,
                       stderr=subprocess.STDOUT,env=dict(env0,OMP_NUM_THREADS='8'))
    ps.append((tag,p,fh)); print('launched',tag,p.pid,flush=True)
while any(p.poll() is None for _,p,_ in ps): time.sleep(120)
for tag,p,fh in ps: fh.close(); print('done',tag,p.returncode,flush=True)
print('ALL_DONE',flush=True)
