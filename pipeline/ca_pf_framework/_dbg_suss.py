import numpy as np, sys
sys.path.insert(0,'.')
import windowB_surface as W
N,dx=48,5e-8; L=N*dx
z=(np.arange(N)+0.5)*dx
X,Y,Z=np.meshgrid(z,z,z,indexing='ij')
d = 2.0*Z + (0.02-0.03)*L          # |grad d| = 2
gn0 = np.sqrt(sum(t**2 for t in np.gradient(d,dx)))
b0 = np.abs(d) <= 6*dx
print('输入: |grad d| 全域 %.4f, 带内 %.4f' % (gn0.mean(), gn0[b0].mean()))
for it in (100, 300, 1000, 3000):
    for dt in (None, 0.5*dx, 0.25*dx, 0.1*dx):
        dn = W.sussman_reinit(d.copy(), dx, iters=it, dtau=dt, grad='upwind2')
        gn = np.sqrt(sum(t**2 for t in np.gradient(dn,dx)))
        b = np.abs(dn) <= 6*dx
        # 零等值面位置
        col = dn[N//2,N//2,:]
        i = int(np.argmin(np.abs(col)))
        zi = z[i] if i>=len(col)-1 else (z[i] if col[i]==col[i+1] else z[i]+(0-col[i])*dx/(col[i+1]-col[i]))
        print('  iters=%-5d dtau=%-9s 带内|grad d|=%.4f (目标1.0)  d=0 在 %.5f (应 0.012)'
              % (it, str(dt), gn[b].mean() if b.any() else np.nan, zi*1e6))
