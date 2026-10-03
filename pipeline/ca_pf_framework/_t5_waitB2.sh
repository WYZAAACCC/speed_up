#!/bin/bash
# _t5_waitB2.sh --- ★★★★★ 等 `t5B2` 的**活跃场数 ≥ 16**（问题 B 的判别点），然后自动判定
#
# ## 为什么 16 是判别点
# `t5N276`（12 变体 · B=3）在场数 16 时宽比已跌到 **5.34**、18 场时 **5.06**。
# **⇒ 若 `t5B2`（1 变体 · B=1）在场数 16–20 时宽比**仍 ≥5** ⇒ 密集堆叠/多块是原因（证实）;
#    若也崩到 ~2 ⇒ 与堆叠无关（否证）。**
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TGT=${1:-16}
LIM=${2:-5400}
T=0
echo "  等 t5B2 活跃场数 ≥ $TGT（最多 ${LIM} s）"
while [ "$T" -lt "$LIM" ]; do
  N=$($PY - <<'PYEOF' 2>/dev/null
import glob, numpy as np
fs = sorted(glob.glob('_exp/_bk_t5/dry_t5B2/snap_*.npz'))
if fs:
    with np.load(fs[-1], allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
    print(len([k for k in np.unique(reg) if k != 0]))
else:
    print(0)
PYEOF
)
  [ -n "$N" ] && [ "$N" -ge "$TGT" ] 2>/dev/null && { echo "  ★ t5B2 活跃场数 = $N"; break; }
  P=$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- '--tag t5B2')
  [ "$P" -eq 0 ] && { echo "  ⚠ t5B2 进程消失（场数 $N）"; break; }
  sleep 60; T=$((T + 60))
done
echo "NOW = $(date '+%F %T')  等了 ${T} s"
echo
echo '════ ★ 按场数对齐的判别（问题 B）════'
$PY - <<'PYEOF'
import glob, numpy as np
from scipy import ndimage
DX=62.5; S26=ndimage.generate_binary_structure(3,3)
def M(tag):
    fs=sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz'%tag))
    if not fs: return None
    P=fs[-1]; st=int(P.split('snap_')[1].replace('.npz',''))
    with np.load(P,allow_pickle=False) as z:
        reg=np.asarray(z['region']).astype(np.int32)
    ks=sorted(int(x) for x in np.unique(reg) if x!=0)
    ar=[]
    for k in ks:
        m=(reg==k); n=int(m.sum())
        if n<30: continue
        lab,_=ndimage.label(m,structure=S26); sz=np.bincount(lab.ravel())[1:]
        if sz.size==0: continue
        big=(lab==(int(np.argmax(sz))+1)); idx=np.argwhere(big).astype(float)
        if idx.shape[0]<30: continue
        c=idx-idx.mean(0); w,v=np.linalg.eigh(c.T@c); o=np.argsort(w)[::-1]
        L=float((c@v[:,o[0]]).max()-(c@v[:,o[0]]).min()+1)*DX/1000
        W=float((c@v[:,o[1]]).max()-(c@v[:,o[1]]).min()+1)*DX/1000
        ar.append(L/max(W,1e-9))
    return dict(st=st, nf=len(ks), ar=float(np.median(ar)) if ar else 0)
b=M('t5B2'); f=M('t5N276F'); a=M('t5N276')
print('  臂                    step    活跃场数   长宽比中位')
for name,r in (('t5B2 (1变体,B=1)',b),('t5N276F (修复版)',f),('t5N276 (对照)',a)):
    if r: print('  %-20s %-7d %-10d **%.2f**'%(name,r['st'],r['nf'],r['ar']))
print()
print('  ── 判据 ──')
if b:
    print('  * B2 场数 %d 时宽比 **%.2f**'%(b['nf'],b['ar']))
    print('  * `t5N276` 在 16 场时宽比 **5.34**、18 场时 **5.06**（已退化）')
    print('  ⇒ **%s**'%('✅ B2 保持 ≥5 ⇒ **密集堆叠/多块是原因**（证实）'
                     if b['ar']>=5.0 else
                     '❌ B2 也崩 ⇒ **与堆叠无关**（否证）⇒ 指向单根自身机制'))
PYEOF
