#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_v1c_exact_criterion.py --- 用【正确的择优变量 1/Σ】(径向生长速率) 重判 WC 实验
不需要重跑 CA：_wc_case 的四元数由 (seed+1) 的 rng 确定、按 place_seeds_on_perp_plane 顺序分配，
                    t6b 用 (4001+idx) 的 rng；两者都可精确重建。
同时给出【无阈值的统计判据】(binomial / Welch)。
'''
import os, sys, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ca3d as C3
import verify_ca3d_wc_cet as W
from scipy import stats

n = W.nhat_tilt(35.0)


def metrics(q):
    P = C3.quat_to_axes(q)
    dm = sum(abs(float(P[:, a] @ n)) for a in range(3))     # Σ_a|p_a·n̂|
    mm = max(abs(float(P[:, a] @ n)) for a in range(3))     # max_a|p_a·n̂|（旧的代理）
    return dm, mm


# ---------- 1) T5: 40 个双晶算例 ----------
print('=' * 96)
print('[T5 重判] 双晶 + 倾斜梯度：正确的择优预测 = 沿梯度【径向速率最大】者 = Σ_a|p_a·n̂| 最小者')
print('=' * 96)
rows = []
for f in sorted(glob.glob(os.path.join('_v1_out', 't5_wc_pairs__*.json'))):
    r = json.load(open(f))
    for c in r['cases']:
        sd = c['seed']
        rng = np.random.default_rng(sd + 1)
        quats = [C3.rand_quat(rng) for _ in range(2)]          # n_t*n_y = 2
        m = [metrics(q) for q in quats]
        onl = c['onlead']
        rows.append(dict(seed=sd, sigma=[m[0][0], m[1][0]], maxc=[m[0][1], m[1][1]],
                         onlead=onl, gids=[1, 2]))
ok_exact, ok_proxy = [], []
for r in rows:
    if not r['onlead']:
        ok_exact.append(0); ok_proxy.append(0); continue
    win_exact = int(np.argmin(r['sigma'])) + 1        # Σ 小者应胜（gid 从 1 开始）
    win_proxy = int(np.argmax(r['maxc'])) + 1         # 旧代理
    holder = r['onlead'][0]
    ok_exact.append(int(holder == win_exact))
    ok_proxy.append(int(holder == win_proxy))
k, N = int(np.sum(ok_exact)), len(ok_exact)
kp = int(np.sum(ok_proxy))
print('  算例数 %d' % N)
print('  正确判据(min Σ) 命中 %d/%d = %.1f%%' % (k, N, 100.0 * k / N))
print('  旧代理(max|c|) 命中 %d/%d = %.1f%%' % (kp, N, 100.0 * kp / N))
print('  二项检验 (H0: 随机 50%%): p = %.3g' % stats.binomtest(k, N, 0.5).pvalue)
mix = [i for i, r in enumerate(rows) if len(r['onlead']) and
       (int(np.argmin(r['sigma'])) + 1) != (int(np.argmax(r['maxc'])) + 1)]
print('  两种判据给出【不同胜者】的算例数 = %d  (说明代理不可靠)' % len(mix))
for i in mix[:6]:
    r = rows[i]
    print('     seed %d: Σ=%s (胜者 g%d)  max|c|=%s (代理胜者 g%d)  实际前沿持有者 %s' % (
        r['seed'], [round(x, 3) for x in r['sigma']], int(np.argmin(r['sigma'])) + 1,
        [round(x, 3) for x in r['maxc']], int(np.argmax(r['maxc'])) + 1, r['onlead']))

# ---------- 2) T6b: 8 算例 × 9 晶粒的 lead ----------
print()
print('=' * 96)
print('[T6b 重判] 9 晶粒 + 倾斜梯度：领先者 vs 被超越者（正确变量 Σ 与旧代理 max|c| 各自检验）')
print('=' * 96)
lead_rows = [json.load(open(f)) for f in sorted(glob.glob(os.path.join('_v1_out', 't6b_lead__*.json')))]
ex_leads, ex_sig, ex_maxc = [], [], []
for r in lead_rows:
    idx = r['idx']
    rng = np.random.default_rng(4001 + idx)
    quats = [C3.rand_quat(rng) for _ in range(9)]
    ms = [metrics(q) for q in quats]
    gids = sorted(int(k) for k in r['align'])
    leads = np.array([r['lead_last'][str(g)] for g in gids], float)
    sig = np.array([m[0] for m in ms]); mc = np.array([m[1] for m in ms])
    on = leads >= leads.max() - 8.0
    ex_leads.append((sig, leads, on, mc))
    if (~on).any():
        ex_sig += [sig[on].mean(), sig[~on].mean()]
for tag, sel in (('Σ_a|p_a·n̂|  (正确: 越小越快)', 0), ('max_a|p_a·n̂|  (旧代理)', 1)):
    onv, offv = [], []
    for sig, leads, on, mc in ex_leads:
        v = sig if sel == 0 else mc
        if (~on).any():
            onv += list(v[on]); offv += list(v[~on])
    onv, offv = np.array(onv), np.array(offv)
    t, p = stats.ttest_ind(onv, offv, equal_var=False)
    print('  %-26s 领先者均值 %.4f vs 被超越 %.4f ; Welch t=%.2f p=%.3g' % (
        tag, onv.mean(), offv.mean(), t, p))
    # 方向性: 正确判据应"领先者 Σ 更小"
    direction_ok = (onv.mean() < offv.mean()) if sel == 0 else (onv.mean() > offv.mean())
    print('     方向 %s ; 相关 corr(变量, lead) = %+.3f' % (
        '正确' if direction_ok else '相反', np.corrcoef(
            reduce_last := np.concatenate([(sig if sel == 0 else mc) for sig, leads, on, mc in ex_leads]),
            np.concatenate([leads for sig, leads, on, mc in ex_leads]))[0, 1] *
        (1 if direction_ok else 1)))