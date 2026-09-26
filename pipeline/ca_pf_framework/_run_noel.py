import os, subprocess, time
HERE='/mnt/f/speed_up/pipeline/ca_pf_framework'; PY='/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE); env0=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
B=['--N','80','--dx','2e-8','--nplate','2','--rfrac','0.1875','--plate_dx','10',
   '--df','2e8','--nstep','700','--mob_beta','3.5','--mob_beta_w','2.3','--elong','6.0']
for tag,extra in [('NE1',['--noelastic','1']), ('NE0',['--noelastic','0'])]:
    fh=open('_noel_%s.log'%tag,'w')
    subprocess.Popen([PY,'_chk_m6_route.py','--tag',tag]+extra+B,stdout=fh,
                     stderr=subprocess.STDOUT,env=dict(env0,OMP_NUM_THREADS='8'))
    print('launched',tag,flush=True)
time.sleep(99999)
