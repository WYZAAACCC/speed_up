#!/usr/bin/env python3
import importlib
for m in ('numpy', 'scipy', 'matplotlib', 'skimage', 'pyvista', 'vtk'):
    try:
        mod = importlib.import_module(m)
        print('%-12s OK  %s' % (m, getattr(mod, '__version__', '?')))
    except Exception as e:
        print('%-12s MISSING (%s)' % (m, type(e).__name__))
import os
print('nproc =', os.cpu_count())
print('simhei exists =', os.path.exists('/mnt/c/Windows/Fonts/simhei.ttf'))
import matplotlib
print('matplotlib backend =', matplotlib.get_backend())
