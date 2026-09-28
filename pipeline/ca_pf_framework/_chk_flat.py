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
for fe in (False, True):
    g=W.LevelSetMulti(N,L,C=C,eps0=eps0,gamma=0.0,Mob=1e-9,df=[0.0]+[2e8]*nv,workers=4,reinit_every=0)
    k=1
    n_h=np.asarray(npref[k],float); n_h/=np.linalg.norm(n_h)
    wv=np.asarray(g.wtab[k],float); wv/=np.linalg.norm(wv)
    al=np.asarray(g.atab[k],float); al/=np.linalg.norm(al)
    g.seed_plate(k,[L/2]*3,n_h,1.2e-7,2.0e-7,elong=6.0,along=al,flat_end=fe)
    g.init_parent()
    ph=g.phi[k]; gd=np.gradient(ph,dx); gn=np.sqrt(sum(x**2 for x in gd))+1e-30
    nd=np.stack([x/gn for x in gd],-1); nd/=(np.linalg.norm(nd,axis=-1,keepdims=True)+1e-300)
    b=np.abs(ph)<=0.5*dx
    c2a=np.einsum('...i,i->...',nd,al)**2
    c2h=np.einsum('...i,i->...',nd,n_h)**2
    c2w=np.einsum('...i,i->...',nd,wv)**2
    print('flat_end=%-5s 带胞%6d  P(端面 c2a>0.81)=%.3f  P(大面)=%.3f  P(侧面)=%.3f'
          % (fe, b.sum(), (c2a[b]>0.81).mean(), (c2h[b]>0.81).mean(), (c2w[b]>0.81).mean()))
