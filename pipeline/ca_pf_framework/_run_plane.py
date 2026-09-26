import os, subprocess, time
HERE='/mnt/f/speed_up/pipeline/ca_pf_framework'; PY='/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE); env0=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
ps=[]
for ax in ['n','w','a']:
    fh=open('_plane_%s.log'%ax,'w')
    p=subprocess.Popen([PY,'_chk_plane_vel.py','--axis',ax],stdout=fh,stderr=subprocess.STDOUT,
                       env=dict(env0,OMP_NUM_THREADS='6'))
    ps.append((ax,p,fh)); print('launched',ax,p.pid,flush=True)
while any(p.poll() is None for _,p,_ in ps): time.sleep(45)
for ax,p,fh in ps: fh.close(); print('done',ax,p.returncode,flush=True)
print('ALL_DONE',flush=True)
