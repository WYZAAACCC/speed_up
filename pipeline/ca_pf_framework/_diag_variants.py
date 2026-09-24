# -*- coding: utf-8 -*-
'''诊断：Burgers 对应的应变张量轨道到底有几个？(6 vs 12)'''
import numpy as np, itertools
A_B, A_A, C_A = 0.3310, 0.2950, 0.4683   # nm

def cubic_proper():
    R = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1,-1), repeat=3):
            M = np.zeros((3,3))
            for i,(p,s) in enumerate(zip(perm,signs)): M[i,p] = s
            if abs(np.linalg.det(M)-1) < 1e-12: R.append(M)
    return R

# 父相(beta)中的对应矢量（单位 nm）：t1=[1-10]a, t2=[001]a, b3=[110]a
t1 = A_B*np.array([1.,-1.,0.])
t2 = A_B*np.array([0.,0.,1.])
b3 = A_B*np.array([1.,1.,0.])
Bm = np.column_stack([t1,t2,b3])
# 子相(alpha)目标：t1 -> (A+B) = sqrt3*a_alpha * e_b ; t2 -> (B-A) = a_alpha * e_a ; b3 -> c_alpha
# 在父相笛卡尔系里，e_b = t1/|t1|, e_a = t2/|t2|, n = b3/|b3|
e_b = t1/np.linalg.norm(t1); e_a = t2/np.linalg.norm(t2); nh = b3/np.linalg.norm(b3)
Am = np.column_stack([np.sqrt(3)*A_A*e_b, A_A*e_a, C_A*nh])
F0 = Am @ np.linalg.inv(Bm)
print('F0 =\n', F0)
print('det(F0)-1 =', np.linalg.det(F0)-1)
eps0 = 0.5*(F0+F0.T) - np.eye(3)
print('eps0 (x1e-3) =\n', np.round(eps0*1e3,4))
print('eig(eps0) =', np.linalg.eigvalsh(eps0))
# 每原子体积核对
vb = A_B**3/2; va = np.sqrt(3)/2*A_A**2*C_A/2
print('V/atom ratio (exact) =', va/vb - 1)
print('det(F) ratio           =', np.linalg.det(F0) - 1)

Rs = cubic_proper()
strains, Fs = [], []
for M in Rs:
    F = M @ F0 @ M.T
    strains.append(0.5*(F+F.T)-np.eye(3)); Fs.append(F)
strains = np.array(strains)
# 去重
uniq = []
for e in strains:
    if not any(np.abs(e-x).max()<1e-10 for x in uniq): uniq.append(e)
uniq = np.array(uniq)
print()
print('24 个真旋转下的【不同】应变张量数 =', len(uniq))
for i,e in enumerate(uniq): print('  u%d eig=%s  dev_norm=%.4e' % (i, np.round(np.linalg.eigvalsh(e),6), np.linalg.norm(e-np.trace(e)/3*np.eye(3))))
print('Sigma dev =', np.linalg.norm((uniq - np.trace(uniq,axis1=1,axis2=2)[:,None,None]/3*np.eye(3)).sum(0)))
# 24 个元素中每个唯一应变出现几次
from collections import Counter
cnt = Counter()
for e in strains:
    for i,x in enumerate(uniq):
        if np.abs(e-x).max()<1e-10: cnt[i]+=1
print('每个唯一应变的出现次数 =', dict(cnt))
