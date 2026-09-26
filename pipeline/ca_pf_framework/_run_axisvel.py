import os, subprocess, time
HERE='/mnt/f/speed_up/pipeline/ca_pf_framework'; PY='/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE); env0=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
ps=[]
for tag,f in [('A','_dbg_axis_vel_A.py'),('B','_dbg_axis_vel_B.py')]:
    fh=open('_axisvel%s.log'%tag,'w')
    p=subprocess.Popen([PY,f],stdout=fh,stderr=subprocess.STDOUT,env=dict(env0,OMP_NUM_THREADS='8'))
    ps.append((tag,p,fh)); print('launched',tag,p.pid,flush=True)
while any(p.poll() is None for _,p,_ in ps): time.sleep(90)
for tag,p,fh in ps: fh.close(); print('done',tag,p.returncode,flush=True)
print('ALL_DONE',flush=True)
