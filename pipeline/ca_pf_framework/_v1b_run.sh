#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
seq 0 7 | xargs -P 8 -I{} env OMP_NUM_THREADS=1 /root/miniconda3/envs/ml/bin/python _v1b_lead.py {}
echo "=== lead 实验完成"
/root/miniconda3/envs/ml/bin/python - <<'EOF'
import json, glob, os
import numpy as np
D = '_v1_out'
rows = [json.load(open(f)) for f in sorted(glob.glob(D + '/t6b_lead__*.json'))]
print('9 晶粒 + 倾斜梯度：逐晶粒的"前沿推进 lead"  (单位 µm, 沿 n̂ 投影)')
print('  算例  ' + '  '.join('g%-5d' % g for g in sorted(rows[0]['align'])))
print('  对齐度 ' + '  '.join('%.3f ' % rows[0]['align'][str(g)] if str(g) in rows[0]['align'] else '  -   '
                             for g in sorted(rows[0]['align'])))
for r in rows:
    gs = sorted(r['align'])
    leads = [r['lead_last'][str(g)] for g in gs]
    print('  #%-4d ' % r['idx'] + '  '.join('%6.1f' % v for v in leads))
# 统计: 对齐度 vs lead 的相关性
al, ld = [], []
for r in rows:
    for k, a in r['align'].items():
        al.append(a); ld.append(r['lead_last'][k])
al = np.array(al); ld = np.array(ld)
print()
print('全部 %d 个 (晶粒,算例): corr(对齐度, lead) = %+.3f' % (len(al), float(np.corrcoef(al, ld)[0,1])))
# lead = 最大值 - 2 胞 以上者算"仍在领先前沿"
tot = 0; poor = 0
for r in rows:
    ls = np.array([r['lead_last'][k] for k in r['align']])
    as_ = np.array([r['align'][k] for k in r['align']])
    top = ls.max()
    on = ls >= top - 2 * 4.0    # 2 胞 = 8 µm
    tot += len(ls); poor += int((~on).sum())
    print('  算例 #%d: 领先(>max-8µm) %d/%d 个, 其对齐度 %s' % (
        r['idx'], int(on.sum()), len(ls),
        ' '.join('%.3f' % a for a in sorted(as_[on], reverse=True))))
print('合计: 被超越(lead 落后 >8µm)的晶粒 %d/%d = %.0f%%' % (poor, tot, 100.0*poor/tot))
EOF