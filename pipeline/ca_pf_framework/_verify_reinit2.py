import numpy as np, sys
sys.path.insert(0,'.')
import windowB_surface as W
N, dx = 48, 5e-8; L = N*dx
z = (np.arange(N)+0.5)*dx
X,Y,Z = np.meshgrid(z,z,z,indexing='ij')
a,b = 0.02*L, 0.03*L
zt = (b-a)/2
def d0(g):
    col = (g.phi[1]-g.phi[2])[N//2, N//2, :]
    i = int(np.argmin(np.abs(col)))
    if i >= len(col)-1: return float(z[i])
    v0, v1 = col[i], col[i+1]
    if v0 == v1: return float(z[i])
    return float(z[i] + (0.0 - v0)*dx/(v1 - v0))
def mk(nv=2):
    g = W.LevelSetMulti(N, L, nv=nv, gamma=0.15, Mob=1e-9)
    g.phi[1] = Z + a; g.phi[2] = -Z + b
    # 干净构型：只有变体 1、2（母相不参与 => phi1=phi2 就是真实界面）
    g.phi[0] = np.full_like(g.phi[0], 1e3)
    return g
print('解析界面 z = %.5f um' % (zt*1e6))
g = mk(); print('  重初始化前      : %.5f um' % (d0(g)*1e6))
g.reinitialize(mode='perfield'); print('  旧 perfield 后  : %.5f um  (应显著偏离)' % (d0(g)*1e6))
g2 = mk(); g2.reinitialize(mode='pair'); print('  新 pair 后      : %.5f um  (应基本不变)' % (d0(g2)*1e6))
