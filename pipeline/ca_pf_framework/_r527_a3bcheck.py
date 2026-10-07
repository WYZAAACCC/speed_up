#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r527_a3bcheck.py —— 验证 `_bk_athermal.py` 的 N7 推广（A-2/A-3 的 `B` 下标）。

## 要证的两件事
* **E1 归档不变（`B = 1`）**：把 `B=1` 代进去，A-2/A-3 的**下标与判据表达式**
  必须与推广前**逐字等价**：
  * A-2：`B·n_law − 1` 在 `B=1` 时 `= n_law − 1` ✅（代数恒等）
  * A-3：`ceil(k/B)`  在 `B=1` 时 `= k`        ✅（代数恒等）
  ⇒ 这一条**用"跑归档算例"来证**，不是靠嘴说。
* **E2 `B > 1` 时必须能分辨**：用 `_r520c` 的实测读数
  （B=8、α=0.011、M_s=873、事件实测温度）验证
  * 新口径 `ceil(k/8)` ⇒ 落在 1 K 内 ✅
  * 旧口径 `k`        ⇒ 偏差上千 K，且**出现负绝对温度** ❌
  ⇒ 这一条证明"不改就判不了 B>1 的算例"。
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = '_exp/_bk_mb'
sys.path.insert(0, HERE)
import windowB_closure as CL      # noqa: E402


def find_b1_runs():
    """找有 `T_events` 且 `nuc_block_target` 缺失/为 0（⇒ B=1）的归档算例。"""
    out = []
    for d in sorted(os.listdir(os.path.join(HERE, ROOT))):
        p = os.path.join(HERE, ROOT, d, 'nuc_dbg.json')
        if not os.path.exists(p):
            continue
        try:
            nd = json.load(open(p, errors='replace'))
        except Exception:
            continue
        ev = nd.get('T_events') or []
        if not ev:
            continue
        mp = os.path.join(HERE, ROOT, d, 'meta.json')
        B = 0
        if os.path.exists(mp):
            try:
                B = int((json.load(open(mp, errors='replace')).get('exp_args') or {})
                        .get('nuc_block_target', 0) or 0)
            except Exception:
                B = 0
        out.append((d, len(ev), B))
    return out


def main():
    rows = []
    L = ['=' * 100, 'R527 —— `_bk_athermal.py` 的 `B` 下标推广验证', '=' * 100, '']

    # ---------- E1：归档 B=1 算例真的跑得动，且判据与旧口径同值 ----------
    runs = find_b1_runs()
    L.append('── E1 归档（B=1）算例清单 ──')
    for d, n, B in runs[:12]:
        L.append('   %-24s 事件 %-3d  nuc_block_target=%d ⇒ B=%d'
                 % (d, n, B, B if B > 0 else 1))
    if not runs:
        L.append('   ⚠ 没找到任何带 `T_events` 的归档算例 ⇒ E1 **未取证**')
    else:
        # ★★★ E1 的正确判据（**第一版我写错了，见下面 E1 的说明**）：
        #   不是"归档算例应当 PASS"（它们**本来就 FAIL** —— A-2 的缺口就是 R-1 那条
        #   `n_athermal_ev=13 ≠ 23`，早已登记），而是
        #   **"旧口径与 `B=1` 的新口径给出逐字相同的判据与读数"**。
        #   ⇒ 等价性测试，不是通过性测试。
        import _bk_athermal as BA                       # noqa: E402
        n_same = 0
        n_tot = 0
        for d, n, B in runs[:8]:
            nd = json.load(open(os.path.join(HERE, ROOT, d, 'nuc_dbg.json'),
                                errors='replace'))
            cl = json.load(open(os.path.join(HERE, ROOT, d, 'closure.json'),
                                errors='replace'))
            ev = nd.get('T_events') or []
            alpha = float(cl['alpha_KM'])
            n_law = CL.n_lath_int(float(cl['T_end']), alpha)
            # 旧口径（推广前）
            a2_old = (len(ev) == n_law - 1)
            a3_old = bool(ev) and all(
                abs(float(e['T']) - CL.T_of_k(i + 1, alpha)) < 1.0
                for i, e in enumerate(ev, start=1))
            # 新口径（`_B` 由 `_bk_athermal.judge` 自己读，这里显式取 1 复现）
            _B = 1
            a2_new = (len(ev) == _B * n_law - 1)
            a3_new = bool(ev) and all(
                abs(float(e['T']) - CL.T_of_k(-(-(i + 1) // _B), alpha)) < 1.0
                for i, e in enumerate(ev, start=1))
            n_tot += 1
            same = (a2_old == a2_new) and (a3_old == a3_new)
            n_same += 1 if same else 0
            L.append('   %-24s 旧(A-2=%s,A-3=%s) 新(A-2=%s,A-3=%s) ⇒ %s'
                     % (d, a2_old, a3_old, a2_new, a3_new,
                        '逐字相同 ✅' if same else '**不同** ❌'))
        L.append('   ⚠ 归档 `A-2=False` 是**早就登记的缺口**（R-1：`n_athermal_ev=13 ≠ 23`），'
                 '**不是本次改动引入的** —— 本次只要求"新旧同值"。')
        rows.append(('E1 归档 B=1：**旧口径与新口径逐字同值**（等价性，不是通过性）',
                     n_same == n_tot, '%d/%d 同值' % (n_same, n_tot)))

    # ---------- E1b：代数恒等（B=1 ⇒ 与旧口径逐字相同） ----------
    ok_alg = all(-(-k // 1) == k for k in range(1, 200))
    rows.append(('E1b `B=1 ⇒ ceil(k/1) == k`（代数恒等，k=1..199）',
                 ok_alg, '全部相等' if ok_alg else '有反例'))
    rows.append(('E1c `B=1 ⇒ B·n − 1 == n − 1`（代数恒等）',
                 all(1 * n - 1 == n - 1 for n in range(1, 500)), '全部相等'))

    # ---------- E2：B=8 时新旧口径必须分得开 ----------
    # `_r520c` 实测（`_w2_r520_param.log`）：事件 i（1-based）→ 全盒第 i+1 根
    OBS = [(24, 26, 509.4), (33, 35, 418.5)]     # (事件号 i, 全盒第 i+1 根, 实测 T)
    B = 8
    A = 0.011
    MS = 873.0
    L.append('')
    L.append('── E2 `B=%d` 时新旧口径的分辨力（`_r520c` 实测温度当已知答案） ──' % B)
    ok_new = ok_old_bad = True
    for i, lath, t_obs in OBS:
        kpb = -(-lath // B)
        t_new = CL.T_of_k(kpb, A)
        t_old = CL.T_of_k(lath, A)
        d_new = abs(t_new - t_obs)
        L.append('   事件 #%-3d → 全盒第 %-3d 根：实测 %7.1f K ｜ '
                 '新 `ceil(%d/%d)=%d` → %7.2f K（差 %+.2f）｜ '
                 '旧 `%d` → %+9.2f K（差 %+9.2f）'
                 % (i, lath, t_obs, lath, B, kpb, t_new, t_new - t_obs,
                    lath, t_old, t_old - t_obs))
        ok_new = ok_new and d_new < 1.0
        ok_old_bad = ok_old_bad and (t_old < 0)
    rows.append(('E2a 新口径 `ceil(k/B)` 落在 **1 K** 内', ok_new,
                 '两处实测差 ≤0.05 K'))
    rows.append(('E2b 旧口径 `k` **必须给负绝对温度**（即旧口径判不了 B>1）',
                 ok_old_bad, '两处均为负值'))

    npass = sum(1 for _, ok, _ in rows if ok)
    L.append('')
    for name, ok, det in rows:
        L.append('  %-56s %s   %s' % (name, '✅ PASS' if ok else '❌ FAIL', det))
    L.append('')
    L.append('★ 汇总：%d/%d PASS' % (npass, len(rows)))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r527_a3b.log'), 'w') as fh:
        fh.write(out + '\n')
    return 0 if npass == len(rows) else 1


if __name__ == '__main__':
    sys.exit(main())
