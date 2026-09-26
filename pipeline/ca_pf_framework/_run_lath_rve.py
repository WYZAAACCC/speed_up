import os, subprocess, time
HERE='/mnt/f/speed_up/pipeline/ca_pf_framework'; PY='/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE); env0=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
# 板条级 RVE：L=80*0.02=1.6 um；板条厚 0.2 um = 10 胞（**解析**）；R=0.3 um
B=['--N','80','--dx','2e-8','--nplate','2','--rfrac','0.1875','--plate_dx','10',
   '--df','2e8','--nstep','600','--mob_beta','3.5','--mob_beta_w','2.3']
J=[('LR1', B),
   ('LR2', ['--N','80','--dx','2e-8','--nplate','2','--rfrac','0.1875','--plate_dx','10',
            '--df','2e8','--nstep','600','--mob_beta','0.0','--mob_beta_w','0.0'])]
ps=[]
for tag,args in J:
    fh=open('_lathrve_%s.log'%tag,'w')
    p=subprocess.Popen([PY,'_chk_m6_route.py','--tag',tag]+args,stdout=fh,
                       stderr=subprocess.STDOUT,env=dict(env0,OMP_NUM_THREADS='8'))
    ps.append((tag,p,fh)); print('launched',tag,p.pid,flush=True)
while any(p.poll() is None for _,p,_ in ps): time.sleep(90)
for tag,p,fh in ps: fh.close(); print('done',tag,p.returncode,flush=True)
print('ALL_DONE',flush=True)
