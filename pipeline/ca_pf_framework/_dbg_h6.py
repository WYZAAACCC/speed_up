import numpy as np
import windowB_surface as W
DX, N, DT, D_S = 1e-8, 64, 1e-4, 1e-13
exec(open('_chk_h6.py').read().split("print('=' * 78)")[0].split('import windowB_surface as W')[1])
g = stripe()
karr = np.argsort(g.phi, axis=0)[0]
phiw = np.take_along_axis(g.phi, karr[None], 0)[0]
print('phi_w[0,0,12:22] /dx =', np.round(phiw[0,0,12:22] / DX, 2))
print('phi_1[0,0,12:22] /dx =', np.round(g.phi[1][0,0,12:22] / DX, 2))
print('phi_0[0,0,12:22] /dx =', np.round(g.phi[0][0,0,12:22] / DX, 2))
gk = np.gradient(phiw, DX)
print('|grad phi_w| 沿 z 的最大值 = %.4f' % np.abs(gk[2]).max())
print('|grad phi_1| 沿 z 的带内中位 = %.4f'
      % np.median(np.abs(np.gradient(g.phi[1], DX)[2])[np.abs(g.phi[1]) < 1.5 * DX]))