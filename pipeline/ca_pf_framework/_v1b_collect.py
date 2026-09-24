#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_v1b_collect.py --- 逐晶粒 lead(沿 n̂ 的前沿推进量) vs 时间：竞争/淘汰的定量证据'''
import json, glob, os
import numpy as np
D = '_v1_out'
rows = [json.load(open(f)) for f in sorted(glob.glob(D + '/t6b_lead__*.json'))]
gs = sorted(int(k) for k in rows[0]['align'])
DX, N = 4e-6, 110
print('9 晶粒 + 倾斜梯度（n̂ 倾斜 35°）：沿 n̂ 的【前沿推进 lead】(µm)，每 30 步采样')
print('  晶粒:      ' + '  '.join('g%-5d' % g for g in gs))
print('  对齐度:    ' + '  '.join('%6.3f' % rows[0]['align'][str(g)] for g in gs))
for r in rows[:3]:
    print('  --- 算例 #%d' % r['idx'])
    for st, lead, rec in r['hist']:
        d = {int(x[0]): x[3] for x in rec}
        print('    s=%-4d ' % st + '  '.join('%6.1f' % d[g] for g in gs))
# 定量结论
allal, alllead, allact = [], [], []
for r in rows:
    for k, a in r['align'].items():
        allal.append(a); alllead.append(r['lead_last'][k])
        allact.append([x for x in r['hist'][-1][2] if str(x[0]) == k][0][4])
al = np.array(allal); ld = np.array(alllead)
print()
print('全部 %d 个 (算例,晶粒) 对:  corr(对齐度, 末态 lead) = %+.3f' % (len(al), float(np.corrcoef(al, ld)[0,1])))
# 前半段的对齐度 vs 后半段的推进量（更能反映"谁被超越"）
print()
print('  逐算例: 领先者(max lead 2 胞内) 的对齐度 vs 其余')
for r in rows:
    ls = np.array([r['lead_last'][str(g)] for g in gs]); as_ = np.array([r['align'][str(g)] for g in gs])
    top = ls.max(); on = ls >= top - 8.0
    print('    #%d: 领先 %d/%d 个; 领先者对齐度均值 %.3f (最小 %.3f) vs 被超越者 %.3f (最大 %.3f)' % (
        r['idx'], on.sum(), len(gs), as_[on].mean(), as_[on].min(),
        as_[~on].mean() if (~on).any() else float('nan'),
        as_[~on].max() if (~on).any() else float('nan')))
on_all, off_all = [], []
for r in rows:
    ls = np.array([r['lead_last'][str(g)] for g in gs]); as_ = np.array([r['align'][str(g)] for g in gs])
    on = ls >= ls.max() - 8.0
    on_all += list(as_[on]); off_all += list(as_[~on])
print()
print('  总体: 领先者(%d 个) 对齐度 %.3f±%.3f ; 被超越者(%d 个) %.3f±%.3f' % (
    len(on_all), np.mean(on_all), np.std(on_all), len(off_all),
    np.mean(off_all) if off_all else float('nan'), np.std(off_all) if off_all else float('nan')))
if off_all:
    from scipy import stats
    t, p = stats.ttest_ind(on_all, off_all, equal_var=False)
    print('  Welch t 检验: t=%.2f, p=%.3g  ⇒ %s' % (
        t, p, '领先者对齐度显著更高（WC 择优成立）' if (p < 0.05 and np.mean(on_all) > np.mean(off_all)) else '不显著'))