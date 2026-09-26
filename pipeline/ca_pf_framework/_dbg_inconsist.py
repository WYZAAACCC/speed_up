import numpy as np, sys
sys.path.insert(0,'.')
import windowB_surface as W
N,dx=48,5e-8; L=N*dx
z=(np.arange(N)+0.5)*dx
X,Y,Z=np.meshgrid(z,z,z,indexing='ij')
a,b=0.02*L,0.03*L
def d0(g):
    col=(g.phi[1]-g.phi[2])[N//2,N//2,:]
    i=int(np.argmin(np.abs(col)))
    if i>=len(col)-1: return float(z[i])
    v0,v1=col[i],col[i+1]
    return float(z[i]) if v0==v1 else float(z[i]+(0.0-v0)*dx/(v1-v0))
def mk():
    g=W.LevelSetMulti(N,L,nv=2,gamma=0.15,Mob=1e-9)
    g.phi[1]=Z+a; g.phi[2]=-Z+b; g.phi[0]=np.full_like(g.phi[0],1e3); return g

print('解析 0.01200 um')
for rep in range(3):
    g=mk(); p0=d0(g)
    g.reinitialize(mode='pair'); p1=d0(g)
    print('  rep%d: 前 %.5f -> 后 %.5f' % (rep, p0*1e6, p1*1e6))

print('--- 先跑一次 perfield（模拟 _verify_reinit2 的顺序）后再跑 pair ---')
g=mk(); g.reinitialize(mode='perfield')
g2=mk(); print('  之后 pair: 前 %.5f -> 后 %.5f' % (d0(g2)*1e6, (g2.reinitialize(mode='pair'), d0(g2))[1]*1e6))

print('--- 检查 reinit_iters 的实际取值 ---')
g=mk(); print('  g.reinit_iters =', g.reinit_iters, ' dtau =', g.reinit_dtau, ' grad =', g.reinit_grad)
