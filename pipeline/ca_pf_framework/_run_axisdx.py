import os, subprocess, time
HERE='/mnt/f/speed_up/pipeline/ca_pf_framework'; PY='/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE); env0=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
ps=[]
for tag,n in [('D32','32'),('D64','64'),('D128','128')]:
    fh=open('_axisdx_%s.log'%tag,'w')
    p=subprocess.Popen([PY,'_dbg_axis_dx.py'],stdout=fh,stderr=subprocess.STDOUT,
                       env=dict(env0,OMP_NUM_THREADS='6',AV_N=n))
    ps.append((tag,p,fh)); print('launched',tag,'N='+n,flush=True)
while any(p.poll() is None for _,p,_ in ps): time.sleep(120)
for tag,p,fh in ps: fh.close(); print('done',tag,p.returncode,flush=True)
print('ALL_DONE',flush=True)
