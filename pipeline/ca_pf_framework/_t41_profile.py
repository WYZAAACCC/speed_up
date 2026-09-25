#!/usr/bin/env python3
"""T4.1 -- where does a Window-B 3D step actually spend its time?

Context (code fact, 2026-09-25): the Window-B production engine
`windowB_surface.LevelSetMulti` is **explicit + FFT** -- there is no implicit
sparse linear system anywhere in it, so "replace the solver with AMG" is not
an available lever.  The levers that DO exist are (i) the explicit CFL /
number of sub-steps, (ii) the cost of the 12-variant numpy loops, (iii) the
FFT (elasticity), (iv) the narrow-band restriction.

This script measures (ii)+(iii)+(iv) with cProfile on one realistic box.
Usage: _t41_profile.py [N] [dx_nm] [nstep] [aniso(0/1)]
"""
import cProfile
import pstats
import io as _io
import sys
import time
import numpy as np

N = int(sys.argv[1]) if len(sys.argv) > 1 else 64
DX = float(sys.argv[2]) * 1e-9 if len(sys.argv) > 2 else 60e-9
NSTEP = int(sys.argv[3]) if len(sys.argv) > 3 else 3
ANISO = bool(int(sys.argv[4])) if len(sys.argv) > 4 else False

import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

GPA = 1e9
C = C_cubic(134.0 * GPA, 110.0 * GPA, 36.0 * GPA)
eps0, Fs, meta = variants()
nv = len(eps0)

g = W.LevelSetMulti(N, N * DX, C=C, eps0=eps0, gamma=0.15, Mob=1e-9,
                    df=[0.0] + [-1e8] * nv, workers=6, reinit_every=25,
                    aniso_elastic=ANISO)
npref = {}
rng = np.random.default_rng(0)
for v in range(nv):
    best, bn = None, None
    for n in rng.normal(size=(200, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best:
            best, bn = val, n
    npref[v + 1] = bn
R = 0.08 * N * DX
for v in range(nv):
    g.seed_plate(v + 1, (rng.random(3) * max(N * DX - 2 * R, 1e-9) + R), npref[v + 1], R, 2 * DX)
g.init_parent()
dt = 0.15 * DX / (1e-9 * 1e8)

print("== T4.1 profile: N=%d dx=%.0f nm L=%.2f um  nv=%d  aniso_elastic=%s" %
      (N, DX * 1e9, N * DX * 1e6, nv, ANISO))
print("   cells = %.2e ; mem/field(8B) = %.2f GB ; fields = %d" %
      (N ** 3, N ** 3 * 8 / 1024.0 ** 3, nv + 1))
t0 = time.time()
g.advance(dt, aniso=0.4, npref=npref, iface_band=2.0)
print("   first step (incl. warm-up): %.2f s" % (time.time() - t0))

pr = cProfile.Profile()
pr.enable()
t0 = time.time()
for _ in range(NSTEP):
    g.advance(dt, aniso=0.4, npref=npref, iface_band=2.0)
    dt = g.suggest_dt(cfl=0.15, dt_prev=dt) or dt
wall = time.time() - t0
pr.disable()
print("   %d steps: %.2f s total -> %.3f s/step ; projected 300 steps = %.2f h"
      % (NSTEP, wall, wall / NSTEP, 300 * wall / NSTEP / 3600.0))
s = _io.StringIO()
pstats.Stats(pr, stream=s).sort_stats('tottime').print_stats(18)
txt = s.getvalue().splitlines()
print("   ---- top by TOTTIME (self time) ----")
for l in txt:
    if 'ncalls' in l or ('{' in l) or (' ' in l and l.strip() and not l.startswith(' ' * 4 + '-')):
        pass
for l in txt[4:]:
    if l.strip():
        print("   " + l.rstrip()[:140])