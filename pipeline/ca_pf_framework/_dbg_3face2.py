import numpy as np, sys
sys.path.insert(0,'.')
import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants
C=C_cubic(134.0e9,110.0e9,36.0e9); eps0,_F,_m=variants(); nv=12
rng=np.random.default_rng(0); npref={}
for v in range(nv):
    best,bn=None,None
    for n in rng.normal(size=(400,3)):
        n=n/np.linalg.norm(n)
        val=0.5*float(np.einsum('ij,ijkl,kl->',eps0[v],_lam_full(C,n),eps0[v]))
        if best is None or val<best: best,bn=val,n
    npref[v+1]=bn
N,dx=80,2e-8; L=N*dx
g=W.LevelSetMulti(N,L,C=C,eps0=eps0,gamma=0.0,Mob=1e-9,df=[0.0]+[2e8]*nv,workers=4,reinit_every=0)
k=1
n_h=np.asarray(npref[k],float); n_h/=np.linalg.norm(n_h)
wv=np.asarray(g.wtab[k],float); wv/=np.linalg.norm(wv)
al=np.asarray(g.atab[k],float); al/=np.linalg.norm(al)
g.seed_plate(k,[L/2]*3,n_h,1.2e-7,2.0e-7,elong=6.0,along=al)
g.init_parent(); g.c[:]=0.036; g.pf=None
M=1e-9; dt=0.15*dx/(M*2e8)
ph0=g.phi[k].copy()
gd0=np.gradient(ph0,dx); gn=np.sqrt(sum(x**2 for x in gd0))+1e-30
nd=np.stack([x/gn for x in gd0],-1); nd/=(np.linalg.norm(nd,axis=-1,keepdims=True)+1e-300)
o=np.argsort(ph0,axis=0); karr=o[0]
print('karr==k 胞数:', int((karr==k).sum()), ' / N^3 =', N**3)
print('|ph0|<=0.5dx 胞数:', int((np.abs(ph0)<=0.5*dx).sum()))
band0=(np.abs(ph0)<=0.5*dx)
print('band0 & (karr==k):', int((band0&(karr==k)).sum()))
c2h=np.einsum('...i,i->...',nd,n_h)**2
print('c2h 在 band0 内: median %.3f p90 %.3f max %.3f' % (
    np.median(c2h[band0]), np.percentile(c2h[band0],90), c2h[band0].max()))
print('c2h>0.81 胞数(band0内):', int((band0&(c2h>0.81)).sum()))
print('c2h>0.81 且 karr==k:', int((band0&(c2h>0.81)&(karr==k)).sum()))
print('c2h>0.25 且 karr==k:', int((band0&(c2h>0.25)&(karr==k)).sum()))
