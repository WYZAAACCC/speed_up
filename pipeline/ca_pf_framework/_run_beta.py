import os, subprocess, time
HERE = '/mnt/f/speed_up/pipeline/ca_pf_framework'
PY = '/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE)
env0 = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
BASE = ['--aniso', '0.4', '--pair', '1', '--nstep', '60']
JOBS = [('V0', BASE + ['--mob_beta', '0.0']),
        ('V35', BASE + ['--mob_beta', '3.5']),
        ('V60', BASE + ['--mob_beta', '6.0'])]
procs = []
for tag, args in JOBS:
    e = dict(env0, OMP_NUM_THREADS='6')
    fh = open('_beta_%s.log' % tag, 'w')
    p = subprocess.Popen([PY, '_chk_m6_route.py', '--tag', tag] + args,
                         stdout=fh, stderr=subprocess.STDOUT, env=e)
    procs.append((tag, p, fh)); print('launched', tag, flush=True)
while any(p.poll() is None for _, p, _ in procs):
    time.sleep(30)
for tag, p, fh in procs:
    fh.close(); print('done', tag, p.returncode, flush=True)
print('ALL_DONE', flush=True)
