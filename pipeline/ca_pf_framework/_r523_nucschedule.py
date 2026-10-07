#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r523_nucschedule.py —— 从 `_r520c` 的运行日志里**逐事件**重建形核时刻表。

## 为什么要这个
`_r520c` 的日志里出现
  * `T_k 理论 = −1399.7 K`（N7：负绝对温度，口径错）
  * 一步之内连发 8 个事件（step 301 上 #24–#31）
两件事**都很像"时钟坏了"**。但 N7 已证明判据是对的
（`while n_ath_tgt < _tgt`，`_tgt = B·n(T_now)`）。
⇒ 那批次发事件到底是**缺陷**还是**准静态时钟的必然**？本量具把它算清楚。

## 本量具要回答的三个问题（**先写死预期，再看数**）
* **Q1 档温**：`--qs-dT` 实际取多少？预期 = `1/α_KM = 90.909 K`
  （即 `PHYSICS_FIRST_SPEC §6.6` 的**方案 A**）⇒ 档温应落在 `T_k = M_s − k/α_KM`。
* **Q2 每档事件数**：预期 = **B**（块数）。
  理由：一档降 `ΔT`，`n(T)` 就涨 `α_KM·ΔT`；取 `ΔT = 1/α_KM` ⇒ 每块涨 **1**
  ⇒ 全盒涨 `B` ⇒ **每档恰好 B 个事件 = 每块各得 1 根**。
  ⇒ 若是这样，则"一步 8 个事件"**不是缺陷**，而是**每块各长 1 根**。
* **Q3 `--nuc-fresh-every K` 与 `--nuc-block-target B` 是否自洽**：
  期望 `K = n(T_end)`（banner 自己这么说）。
  代码口径（`_bk_exp.py:1854`）：`_fresh_now = (n_ath_tgt % K == 0)`，
  其中 `n_ath_tgt` 是**自增前**的值 ⇒ 打印出来的 fresh 事件是 **#1, K+1, 2K+1, …**
  ⇒ 建块数 = `1 + floor((N_ev − 1)/K)`，要等于 `B` 需 `K = (N_ev−1)/(B−1)`。
  ⚠ **本量具要把"实际建了几个块"数出来**，与 `--nuc-block-target` 比对。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, '_w2_r520_param.log')
ALPHA = 0.011
MS = 873.0                      # `T_1 = M_s − 1/α` = 782.09 ⇒ M_s = 873.0（由 banner 反解）
B_TGT = 8                       # `--nuc-block-target`
K_FRESH = 6                     # `--nuc-fresh-every`

RE_EV = re.compile(
    r'\*\*athermal 形核\*\* @ step (\d+)：T=([\d.\-]+) K'
    r'（T_(\d+) 理论=([\d.\-]+) K）'
    r'，df=([\d.eE+\-]+)，场 (\d+)（累计 (\d+)/(\d+)；模式 \*\*(\w+)\*\*；'
    r'累计 fresh=(\d+) stack=(\d+)）')


def main():
    if not os.path.exists(LOG):
        print('❌ 找不到 %s' % LOG)
        return 1
    txt = open(LOG, errors='replace').read()
    evs = []
    for m in RE_EV.finditer(txt):
        evs.append(dict(step=int(m.group(1)), T=float(m.group(2)),
                        k_print=int(m.group(3)), T_theory=float(m.group(4)),
                        df=float(m.group(5)), field=int(m.group(6)),
                        cum=int(m.group(7)), tgt=int(m.group(8)),
                        mode=m.group(9), fresh_cum=int(m.group(10))))
    n_rej = len(re.findall(r'被引擎拒', txt))

    # ★ 也要数**被拒的尝试**（`⚠ athermal 事件 #N 被引擎拒…@ step S`）
    #   否则"每档事件数 = B"会被拒绝截断而假 FAIL（第一版就是这么错的）。
    REJ = re.compile(r'被引擎拒（[^）]*）@ step (\d+)')
    att_by_step = {}
    for m in REJ.finditer(txt):
        s = int(m.group(1))
        att_by_step[s] = att_by_step.get(s, 0) + 1
    for e in evs:
        att_by_step[e['step']] = att_by_step.get(e['step'], 0) + 1

    L = ['=' * 100, 'R523 —— `_r520c` 形核时刻表重建', '=' * 100,
         '  事件行 = %d 条；被拒行 = %d 条' % (len(evs), n_rej), '']
    if not evs:
        L.append('❌ 一条事件都没解析到 ⇒ **先怀疑正则，别下结论**（本仓 §3.3 教训 17/29）')
        out = '\n'.join(L)
        print(out)
        return 1

    # ---- 按 step 分组 ----
    by_step = {}
    for e in evs:
        by_step.setdefault(e['step'], []).append(e)
    L.append('  ── 按 step 分组（每组的 T 应当**完全相同** = 准静态档温） ──')
    L.append('  %-8s %-10s %-6s %-28s %s' % ('step', 'T (K)', '事件数', '事件号范围', '模式'))
    for st in sorted(by_step):
        g = by_step[st]
        ks = [x['k_print'] for x in g]
        L.append('  %-8d %-10.1f %-6d #%d–#%d%-*s %s'
                 % (st, g[0]['T'], len(g), min(ks), max(ks),
                    max(0, 22 - len('#%d–#%d' % (min(ks), max(ks)))), '',
                    '+'.join(sorted(set(x['mode'] for x in g)))))

    # ---- Q1 档温 vs T_k ----
    L.append('')
    L.append('  ── Q1 档温是否 = `T_k = M_s − k/α_KM`（即 `--qs-dT = 1/α_KM`） ──')
    L.append('  1/α_KM = %.3f K；M_s(由 banner 反解) = %.1f K' % (1 / ALPHA, MS))
    ok1 = True
    for st in sorted(by_step):
        g = by_step[st]
        T = g[0]['T']
        kf = (MS - T) * ALPHA
        L.append('     step %-5d T=%7.1f K ⇒ (M_s−T)·α_KM = **%.3f**（整数 ⇒ 正落在某个 T_k 上）'
                 % (st, T, kf))
        ok1 = ok1 and abs(kf - round(kf)) < 0.02
    L.append('     ⇒ %s' % ('✅ 每一档都精确落在 `T_k` 上' if ok1
                            else '❌ 有档**不**落在 `T_k` 上'))

    # ---- Q2 每档事件数 ----
    L.append('')
    L.append('  ── Q2 每档**尝试**数是否 = B（块数） ──')
    L.append('     一档降 `ΔT`，`n(T)` 涨 `α_KM·ΔT`；取 `ΔT = 1/α_KM` ⇒ 每块涨 **1**')
    L.append('     ⇒ 全盒涨 `B` ⇒ **每档恰好 B 次尝试 = 每块各得 1 根**。')
    L.append('     （⚠ **要数"尝试"，不是"成功"** —— 被拒的也算尝试，'
             '否则会被拒绝截断而假 FAIL。）')
    cnts = [len(by_step[s]) for s in sorted(by_step)]
    _steps = sorted(by_step)
    atts = [att_by_step.get(s, 0) for s in _steps]
    # ⚠⚠ **第 1 档要 +1**：`t=0` 预摆的那片板条**就是第 1 根**
    #   （banner 原话：「`n(M_s)=0` ⇒ t=0 预摆的那片就是第 1 根」；
    #     实测 `[0] nslab=1 Vt=0.2495 µm³`，而第 1 档最早打印的事件号是 **#2**）
    #   ⇒ 它**不打印事件行**，所以只数打印行会少 1，把第 1 档误判成 7。
    #   ⚠ 这正是本量具第一版的错：**拿"成功数"当"尝试数"**，
    #     又漏掉不打印的那一次 ⇒ 假 FAIL。**改推导，不放宽阈值。**
    atts_theory = list(atts)
    if atts_theory:
        atts_theory[0] += 1
    L.append('     各档**成功**数 = %s' % cnts)
    L.append('     各档**尝试**数 = %s（**第 1 档已 +1** 计入 `t=0` 预摆的那片）'
             % atts_theory)
    L.append('     `--nuc-block-target` B = %d' % B_TGT)
    ok2 = all(c == B_TGT for c in atts_theory)
    L.append('     ⇒ %s' % ('✅ **每档恰好 B 次** ⇒ 一档降 `ΔT = 1/α_KM`、'
                            '每块涨 1 根 ⇒ 全盒涨 B ⇒ '
                            '**"一步 8 个事件" = 8 个块各长 1 根**，不是爆发、不是缺陷'
                            if ok2 else
                            '⚠ 各档尝试数不等 ⇒ 需要单独解释'))
    if cnts:
        L.append('     成功 %s vs 尝试 %s ⇒ 差额 = **被引擎拒**（本算例 %d 次）'
                 % (cnts, atts_theory, n_rej))

    # ---- Q3 fresh 交错的相位与建块数 ----
    L.append('')
    L.append('  ── Q3 `--nuc-fresh-every %d` 实际建了几个块 ──' % K_FRESH)
    fresh_ks = [e['k_print'] for e in evs if e['mode'] == 'fresh']
    L.append('     `mode == fresh` 的事件号 = %s（共 %d 个）' % (fresh_ks, len(fresh_ks)))
    L.append('     代码口径 `(n_ath_tgt %% %d) == 0`（**自增前**）⇒ 期望 #1, %d, %d, …'
             % (K_FRESH, K_FRESH + 1, 2 * K_FRESH + 1))
    exp = [1 + i * K_FRESH for i in range(len(fresh_ks))]
    L.append('     实测是否吻合 = %s' % (fresh_ks == exp))
    n_ev_tot = max(e['k_print'] for e in evs)
    L.append('     总事件数 = %d；`--nuc-block-target` = %d ⇒ **要 B 个块需 K = (N−1)/(B−1) = %.2f**'
             % (n_ev_tot, B_TGT, (n_ev_tot - 1) / max(B_TGT - 1, 1)))
    L.append('     banner 自己说：`取 K = n(T_end)`；而 `n(T_end) = floor(%.3f·(%.0f−350)) = %d`'
             % (ALPHA, MS, int(ALPHA * (MS - 350))))
    L.append('     ⇒ **实际建块数 = %d，与 `--nuc-block-target %d` %s**'
             % (len(fresh_ks), B_TGT,
                '一致 ✅' if len(fresh_ks) == B_TGT else
                '**不一致 ❌**（K 应取 n(T_end)，不是 %d）' % K_FRESH))

    # ---- N7 打印口径：块内序号 ----
    L.append('')
    L.append('  ── N7 交叉核对：实测 T 是否 = `T_of_k(ceil(k/B))` ──')
    okn = True
    for e in evs[:6] + evs[-4:]:
        kpb = -(-e['k_print'] // B_TGT)
        t_pred = MS - kpb / ALPHA
        L.append('     #%-3d（块内 %d）实测 %7.1f K；`T_of_k(%d)` = %7.2f K ⇒ 差 %+.2f K'
                 % (e['k_print'], kpb, e['T'], kpb, t_pred, e['T'] - t_pred))
        okn = okn and abs(e['T'] - t_pred) < 0.15
    L.append('     ⇒ %s' % ('✅ 全部吻合 ⇒ **判据对、只有那行 `T_k 理论` 打印错（N7）**'
                            if okn else '❌ 有偏差 ⇒ N7 的解释不完整'))

    npass = sum([bool(ok1), bool(ok2), bool(okn)])
    L.append('')
    L.append('★ 汇总：Q1(档温落在 T_k)=%s  Q2(每档=B)=%s  N7(块内序号吻合)=%s'
             % ('PASS' if ok1 else 'FAIL', 'PASS' if ok2 else 'FAIL',
                'PASS' if okn else 'FAIL'))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r523_schedule.log'), 'w') as fh:
        fh.write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
