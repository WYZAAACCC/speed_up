import os, subprocess, time
HERE='/mnt/f/speed_up/pipeline/ca_pf_framework'; PY='/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE); env0=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
# 单核长时程：判定 aspect 是"时间不够"还是"内在饱和"（beta_h=3.5, beta_w=2.3）
ps=[]
for tag,args in [('L1200',['--beta','3.5','--beta_w','2.3','--nstep','1200']),
                 ('L1200b',['--beta','6.0','--beta_w','2.3','--nstep','1200'])]:
    fh=open('_long_%s.log'%tag,'w')
    p=subprocess.Popen([PY,'_chk_single_lath.py','--tag',tag]+args,
                       stdout=fh,stderr=subprocess.STDOUT,env=dict(env0,OMP_NUM_THREADS='6'))
    ps.append((tag,p,fh)); print('launched',tag,p.pid,flush=True)
while any(p.poll() is None for _,p,_ in ps): time.sleep(90)
for tag,p,fh in ps: fh.close(); print('done',tag,p.returncode,flush=True)
print('ALL_DONE',flush=True)
