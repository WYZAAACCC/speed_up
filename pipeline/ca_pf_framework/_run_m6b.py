import os, subprocess, time
HERE = '/mnt/f/speed_up/pipeline/ca_pf_framework'
PY = '/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE)
env0 = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
BASE = ['--aniso', '0.4', '--pair', '1', '--nstep', '120']
JOBS = [
    ('G0', BASE + ['--mob_aniso', '0.0']),
    ('G5', BASE + ['--mob_aniso', '0.5']),
    ('G9', BASE + ['--mob_aniso', '0.9']),
    ('GX', BASE + ['--mob_aniso', '1.0']),
    ('GF', BASE + ['--mob_aniso', '0.9', '--pin_min', '0']),
]
procs = []
for tag, args in JOBS:
    e = dict(env0, OMP_NUM_THREADS='4')
    fh = open('_m6b_%s.log' % tag, 'w')
    p = subprocess.Popen([PY, '_chk_m6_route.py', '--tag', tag] + args,
                         stdout=fh, stderr=subprocess.STDOUT, env=e)
    procs.append((tag, p, fh)); print('launched', tag, p.pid, flush=True)
t0 = time.time()
while any(p.poll() is None for _, p, _ in procs):
    al = [t for t, p, _ in procs if p.poll() is None]
    print('  [%.0f s] running %s' % (time.time() - t0, ','.join(al)), flush=True)
    time.sleep(90)
for tag, p, fh in procs:
    fh.close(); print('done', tag, p.returncode, flush=True)
print('ALL_DONE', flush=True)
