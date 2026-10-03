#!/bin/bash
# _t5_wait1000.sh --- ★★★★★ 等 `t5N276F` 到 step 1000，**按预登记判据自动判定**
#
# ## 预登记判据（**跑之前写死**，见 `0c531d03`）
#   ① 活跃场数 > 19（修复前同期 19）
#   ② 最大分量占比 ≥ 90%（修复前同期 **59%**）
#   ③ 长宽比（按最大分量）≥ 5（修复前同期 **4.28**）
#   ⇒ 三条全满足 ⇒ 修复在数量与形貌两方面都成立
#   ⇒ 任一条不满足 ⇒ 还有别的机制（继续查，不含糊）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TGT=${1:-1000}
LIM=${2:-5400}
T=0
echo "  等 t5N276F 到 step $TGT（最多 ${LIM} s）"
while [ "$T" -lt "$LIM" ]; do
  S=$(tail -1 _exp/_bk_t5/dry_t5N276F/series.csv 2>/dev/null | cut -d, -f1)
  [ -n "$S" ] && [ "$S" -ge "$TGT" ] 2>/dev/null && { echo "  ★ 已到 step $S"; break; }
  P=$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- '--tag t5N276F')
  [ "$P" -eq 0 ] && { echo "  ⚠ 引擎进程消失（末步 $S）"; break; }
  sleep 60; T=$((T + 60))
done
echo "NOW = $(date '+%F %T')  等了 ${T} s"
echo
echo '════ ★ 步对齐判定（同口径）════'
$PY _t5_samecmp.py "$TGT" t5N276,t5N276F 2>&1 | tail -12
echo
echo '════ ★ 预登记判据的自动判定 ════'
$PY - <<'PYEOF'
import glob, numpy as np
from scipy import ndimage
DX=62.5; S26=ndimage.generate_binary_structure(3,3)
def M(tag, st):
    fs=[f for f in glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz'%tag) if ('%05d'%st) in f]
    if not fs: return None
    with np.load(fs[0],allow_pickle=False) as z:
        reg=np.asarray(z['region']).astype(np.int32)
        nh=np.asarray(z['n_hab'],float) if 'n_hab' in z.files else None
    if nh is not None: nh=nh/(np.linalg.norm(nh)+1e-300)
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
    return dict(nf=len(ks), fr=float(np.median(fr)) if fr else 0,
                ar=float(np.median(ar)) if ar else 0)
for st in (1000,):
    a=M('t5N276',st); b=M('t5N276F',st)
    if not b:
        print('  （修复版还没到 step %d 的快照）'%st); continue
    print('  step %d ：修复前 场=%s 占比=%.0f%% 宽比=%.2f'
          %(st, a['nf'] if a else '?', 100*(a['fr'] if a else 0), (a['ar'] if a else 0)))
    print('           修复版 场=%s 占比=%.0f%% 宽比=%.2f'
          %(b['nf'], 100*b['fr'], b['ar']))
    r1 = (b['nf'] > 19) if a else None
    r2 = (b['fr'] >= 0.90)
    r3 = (b['ar'] >= 5.0)
    print()
    print('  ① 活跃场数 > 19      ：%s（实际 %d）'%('✅' if r1 else '❌', b['nf']))
    print('  ② 最大分量占比 ≥90%%  ：%s（实际 %.0f%%）'%('✅' if r2 else '❌', 100*b['fr']))
    print('  ③ 长宽比 ≥ 5         ：%s（实际 %.2f）'%('✅' if r3 else '❌', b['ar']))
    print()
    print('  ⇒ **%s**'%('✅ 三条全过 ⇒ 修复在数量与形貌两方面都成立'
                     if (r2 and r3) else
                     '⚠ 有未过项 ⇒ 说明还有别的机制，需继续查（不含糊）'))
PYEOF
