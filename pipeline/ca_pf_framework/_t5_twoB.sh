#!/bin/bash
# _t5_twoB.sh --- 两臂（t5N276F 修复版 / t5B2 问题B判别）状态 + 板条状态最新读数
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
for t in t5N276F t5B2 t5N276; do
  D=_exp/_bk_t5/dry_$t/series.csv
  printf '  %-9s 末步=%-6s nslab_n=%-4s 进程=%s\n' "$t" \
    "$(tail -1 "$D" 2>/dev/null | cut -d, -f1)" \
    "$(tail -1 "$D" 2>/dev/null | cut -d, -f9)" \
    "$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- "--tag $t")"
done
echo
echo '════ 板条状态（每臂最新一点）════'
for t in t5N276F t5B2; do
  L=$(grep -E "\[$t\]" _w2_t5_lathmon.log 2>/dev/null | sort -u | tail -1)
  [ -n "$L" ] && echo "  $L" | cut -c1-190
done
echo
echo '════ 步对齐：长宽比随 step（三臂）════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import glob, numpy as np
from scipy import ndimage
DX=62.5; S26=ndimage.generate_binary_structure(3,3)
def M(tag, st):
    fs=[f for f in glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz'%tag) if ('%05d'%st) in f]
    if not fs: return None
    with np.load(fs[0],allow_pickle=False) as z:
        reg=np.asarray(z['region']).astype(np.int32)
    ks=sorted(int(x) for x in np.unique(reg) if x!=0)
    fr,ar=[],[]
    for k in ks:
        m=(reg==k); n=int(m.sum())
        if n<30: continue
        lab,_=ndimage.label(m,structure=S26); sz=np.bincount(lab.ravel())[1:]
        if sz.size==0: continue
        fr.append(sz.max()/n)
        big=(lab==(int(np.argmax(sz))+1)); idx=np.argwhere(big).astype(float)
        if idx.shape[0]<30: continue
        c=idx-idx.mean(0); w,v=np.linalg.eigh(c.T@c); o=np.argsort(w)[::-1]
        L=float((c@v[:,o[0]]).max()-(c@v[:,o[0]]).min()+1)*DX/1000
        W=float((c@v[:,o[1]]).max()-(c@v[:,o[1]]).min()+1)*DX/1000
        ar.append(L/max(W,1e-9))
    return (len(ks), float(np.median(fr)) if fr else 0, float(np.median(ar)) if ar else 0)
print('  %-6s | %-24s | %-24s | %s'%('step','t5N276(修复前,12变体B3)','t5N276F(修复版)','t5B2(1变体B1)'))
for st in (200,400,600,800,1000):
    cells=[]
    for t in ('t5N276','t5N276F','t5B2'):
        r=M(t,st)
        cells.append('场=%-2d 占比=%3.0f%% 宽比=%4.2f'%r if r else '（未到）')
    print('  %-6d | %-24s | %-24s | %s'%(st,cells[0],cells[1],cells[2]))
PYEOF
