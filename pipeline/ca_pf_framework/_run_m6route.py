# -*- coding: utf-8 -*-
"""P0.3 并行扫描驱动：5 档，每档 4 线程（5x4=20 = 本机逻辑核数）。
   用 subprocess 而不是 shell（仓库教训：外层 shell 会吃 $ / 反引号）。"""
import os, subprocess, time

HERE = '/mnt/f/speed_up/pipeline/ca_pf_framework'
PY = '/root/miniconda3/envs/ml/bin/python'
os.chdir(HERE)
env0 = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')

JOBS = [
    ('A', ['--tag', 'A', '--aniso', '0.0', '--pair', '0', '--nstep', '120']),
    ('B', ['--tag', 'B', '--aniso', '0.4', '--pair', '0', '--nstep', '120']),
    ('C', ['--tag', 'C', '--aniso', '0.4', '--pair', '1', '--nstep', '120']),
    ('D', ['--tag', 'D', '--aniso', '0.9', '--pair', '1', '--nstep', '120']),
    ('E', ['--tag', 'E', '--aniso', '0.4', '--pair', '1', '--nstep', '120', '--df', '2e7']),
]
procs = []
for tag, args in JOBS:
    e = dict(env0, OMP_NUM_THREADS='4')
    fh = open('_m6route_%s.log' % tag, 'w')
    p = subprocess.Popen([PY, '_chk_m6_route.py'] + args,
                         stdout=fh, stderr=subprocess.STDOUT, env=e)
    procs.append((tag, p, fh))
    print('launched', tag, p.pid, flush=True)
t0 = time.time()
while True:
    alive = [t for t, p, _ in procs if p.poll() is None]
    if not alive:
        break
    print('  [%.0f s] running: %s' % (time.time() - t0, ','.join(alive)), flush=True)
    time.sleep(120)
for tag, p, fh in procs:
    fh.close()
    print('done %s rc=%s' % (tag, p.returncode), flush=True)
print('ALL_DONE %.0f s' % (time.time() - t0), flush=True)
