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
g=mk(); print('  初始                    : %.5f' % (d0(g)*1e6))

# (a) 无掩模：全带对称回写
g=mk()
d=g.phi[1]-g.phi[2]; near=np.abs(d)<=6*dx
dn=W.sussman_reinit(d,dx,iters=g.reinit_iters,dtau=g.reinit_dtau,grad=g.reinit_grad)
c=np.where(near,dn-d,0.0); g.phi[1]+=0.5*c; g.phi[2]-=0.5*c
print('  (a) 无掩模 pair          : %.5f' % (d0(g)*1e6))

# (b) 现行实现（带 is_kl 掩模）
g=mk(); g.reinitialize(mode='pair')
print('  (b) 现行 reinitialize    : %.5f' % (d0(g)*1e6))

# (c) 直接量 dn 自身的零等值面（不动性检查）
g=mk(); d=g.phi[1]-g.phi[2]; near=np.abs(d)<=6*dx
dn=W.sussman_reinit(d,dx,iters=g.reinit_iters,dtau=g.reinit_dtau,grad=g.reinit_grad)
def z0(f):
    col=f[N//2,N//2,:]; i=int(np.argmin(np.abs(col)))
    if i>=len(col)-1: return float(z[i])
    v0,v1=col[i],col[i+1]
    return float(z[i]) if v0==v1 else float(z[i]+(0.0-v0)*dx/(v1-v0))
print('  (c) d 的零等值面: 前 %.5f -> sussman 后 %.5f  (应不变)' % (z0(d)*1e6, z0(dn)*1e6))
print('      |grad d| 前 %.3f -> 后 %.3f (应从2变1)' % (
    np.sqrt(sum(t**2 for t in np.gradient(d,dx))).mean(),
    np.sqrt(sum(t**2 for t in np.gradient(dn,dx))).mean()))
