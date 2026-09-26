import os, subprocess, time
HERE = '/mnt/f/speed_up/pipeline/ca_pf_framework'
PY = '/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE)
env0 = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
# 板条级 RVE：L = 40*0.05 = 2 um；2 轴隔离（beta=0 vs 3.5）
B = ['--N', '40', '--dx', '5e-8', '--aniso', '0.4', '--pair', '1',
     '--nplate', '4', '--rfrac', '0.075', '--plate_dx', '2.0',
     '--df', '2e8', '--nstep', '400']
JOBS = [('R0', B + ['--mob_beta', '0.0']),
        ('R35', B + ['--mob_beta', '3.5'])]
procs = []
for tag, args in JOBS:
    e = dict(env0, OMP_NUM_THREADS='4')
    fh = open('_lath_%s.log' % tag, 'w')
    p = subprocess.Popen([PY, '_chk_m6_route.py', '--tag', tag] + args,
                         stdout=fh, stderr=subprocess.STDOUT, env=e)
    procs.append((tag, p, fh)); print('launched', tag, p.pid, flush=True)
while any(p.poll() is None for _, p, _ in procs):
    time.sleep(60)
for tag, p, fh in procs:
    fh.close(); print('done', tag, p.returncode, flush=True)
print('ALL_DONE', flush=True)
