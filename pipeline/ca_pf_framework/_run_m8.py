import os, subprocess, time
HERE = '/mnt/f/speed_up/pipeline/ca_pf_framework'
PY = '/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE)
env0 = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
JOBS = [('a000', '0.0'), ('a050', '0.5'), ('a090', '0.9'), ('a100', '1.0')]
procs = []
for tag, a in JOBS:
    e = dict(env0, OMP_NUM_THREADS='3')
    fh = open('_m8_%s.log' % tag, 'w')
    p = subprocess.Popen([PY, '_chk_m8_mobpin.py', '--a', a, '--tag', tag],
                         stdout=fh, stderr=subprocess.STDOUT, env=e)
    procs.append((tag, p, fh)); print('launched', tag, p.pid, flush=True)
while any(p.poll() is None for _, p, _ in procs):
    time.sleep(60)
for tag, p, fh in procs:
    fh.close(); print('done', tag, p.returncode, flush=True)
print('ALL_DONE', flush=True)
