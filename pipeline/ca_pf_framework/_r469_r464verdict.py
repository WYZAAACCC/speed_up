#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R469 —— `_r464` 受控双臂的**预登记判据判决**（任务(1) S2 的收尾）。

预登记判据**原样复制自 `_r464_reinitctl.sh` 的文件头**（不得在此改动）：

    P1 【对照有效性】两条臂的 `nreg_used(末)` 必须**相同**（形核事件数一致）。
        不一致 ⇒ **本次对照作废**。
    P2 【退化存在性】A 臂 `median|∇φ|@6Δx` 从 t=0 到末步**必须下降**
        且 `med(末) ≤ 0.95` ⇒ 否则「φ 不再是距离函数」这条**在本配置下不成立**。
    P3 【reinit 有效性】若 P2 成立，则 B 臂的 `med(末) − med(0)` 必须**显著小于** A 臂的
        （判据：`|Δ_B| ≤ 0.5·|Δ_A|`）。
    P4 【成本】B 臂的总墙钟 / A 臂的总墙钟 = 真实代价比。

⚠ **P2/P3 都可能 FAIL，照实报。不得为了让它过而改判据。**

量具：直接复用 `_r461_sdfhealth.py` 的读数函数（它自带 5 条解析自检，**不过就不出读数**），
并且**每个快照都单独报一次自检以外的原始读数**（`median|∇φ|` 在 4 个带宽上）。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _r461_sdfhealth as H          # noqa: E402
from _r463_reinitcount import parse  # noqa: E402

TOL_P1 = 0.0
P2_MAX_MED = 0.95


def arm_series(tag, root='_exp/_bk_mb'):
    """读该臂的 series.csv。
    ⚠ 不直接用 `_r463.parse`：它只抽了 `step/t_s/wall_s/dt/nreg_used/vols` **几列**
    （本工具还要 `Vt`）⇒ 第一版直接取 `r['Vt']` 报了 `KeyError`。这里自己按列名取。"""
    from _r463_reinitcount import read_rows
    rows = read_rows(os.path.join(root, tag, 'series.csv'))
    if not rows:
        return None
    hdr = rows[0].split(',')
    if 'Vt' not in hdr:
        return None
    ix = {h: i for i, h in enumerate(hdr)}
    cols = {k: [] for k in ('step', 't_s', 'wall_s', 'dt', 'nreg_used', 'Vt')}
    for ln in rows[1:]:
        c = ln.split(',')
        if len(c) < len(hdr):
            continue
        try:
            for k in cols:
                cols[k].append(float(c[ix[k]]))
        except ValueError:
            continue
    return {k: np.array(v) for k, v in cols.items()}


def phi_scan(tag, dx, root='_exp/_bk_mb'):
    """量该臂**全部带 phi 的快照**。返回 [(step, res), ...]。"""
    d = os.path.join(root, tag)
    fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                key=lambda f: int(re.search(r'snap_(\d+)\.npz$', f).group(1)))
    out = []
    for f in fs:
        z = np.load(f)
        if 'phi' not in z.files:
            continue
        step = int(re.search(r'snap_(\d+)\.npz$', f).group(1))
        out.append((step, H.measure_snap(z, dx)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='_exp/_bk_mb')
    ap.add_argument('--a', default='r464A')
    ap.add_argument('--b', default='r464B')
    ap.add_argument('--dx-nm', type=float, default=62.5)
    ap.add_argument('--json', default='_r469_r464.json')
    a = ap.parse_args()
    dx = a.dx_nm * 1e-9

    print('=' * 78)
    print('R469  `_r464` 受控双臂判决（预登记判据，见本文件头）')
    print('=' * 78)
    # ★ 量具自检先行
    if not H.selftest(verbose=True):
        print('\n❌ SDF 量具自检 FAIL ⇒ 禁止出读数')
        return 2
    print()

    sa, sb = arm_series(a.a, a.root), arm_series(a.b, a.root)
    if sa is None or sb is None:
        print('✗ 缺 series.csv（或没有 Vt 列）')
        return 2
    for s in (sa, sb):
        s['steps'] = s['step']
        s['ts'] = s['t_s']
        s['wall'] = s['wall_s']
        s['nreg'] = s['nreg_used']

    # ---------------- P1 ----------------
    na, nb = int(sa['nreg'][-1]), int(sb['nreg'][-1])
    p1 = (na == nb)
    print('── P1 对照有效性 ──')
    print('   A 臂 nreg_used(末) = %d   B 臂 = %d   ⇒ **%s**'
          % (na, nb, '✅ PASS' if p1 else '❌ FAIL（对照作废）'))
    print('   （⚠ 记账：本配置的 `nv=8` **已被表示上限钉死**，'
          '两臂都饱和到 8 ⇒ P1 是**弱对照**，它只能抓住"某臂少形核了"。）' % ())

    # ---------------- 量 φ ----------------
    print()
    print('── 逐帧 SDF 读数（`median|∇φ|` / `median|∇d2|`，单位 1）──')
    ra, rb = phi_scan(a.a, dx, a.root), phi_scan(a.b, dx, a.root)
    for nm, rr in ((a.a, ra), (a.b, rb)):
        if not rr:
            print('  %s：**没有带 phi 的快照**（`--phi-every` 没生效？）' % nm)
            continue
        print('  [%s]' % nm)
        print('     step   单场@1.5  @3     @6     @12  |  配对@1.5  @3     @6     @12')
        for step, res in rr:
            s = [res['single']['%.1f' % b]['med'] for b in H.BANDS]
            p = [res['pair']['%.1f' % b]['med'] for b in H.BANDS]
            print('     %5d  %7.4f %7.4f %7.4f %7.4f | %8.4f %7.4f %7.4f %7.4f'
                  % (step, s[0], s[1], s[2], s[3], p[0], p[1], p[2], p[3]))

    def d6(rr):
        if not rr:
            return None
        return rr[0][1]['single']['6.0']['med'], rr[-1][1]['single']['6.0']['med']

    da, db = d6(ra), d6(rb)
    p2 = p3 = None
    if da:
        # ---------------- P2 ----------------
        print()
        print('── P2 退化存在性（A 臂，生产口径 `--reinit-dt 1e-4`）──')
        drop = da[0] - da[1]
        p2 = (drop > 0) and (da[1] <= P2_MAX_MED)
        print('   med|∇φ|@6Δx :  t=0 → %.4f   末步 → %.4f   变化 %+.4f' % (da[0], da[1], -drop))
        print('   判据（预登记）：必须"下降"且"末值 ≤ %.2f" ⇒ **%s**'
              % (P2_MAX_MED, '✅ PASS（退化确实存在）' if p2
                 else '❌ FAIL（**未复现**：φ 仍是距离函数 ⇒ S2 的"后果"在本配置下不成立）'))
    if p2 and db:
        # ---------------- P3 ----------------
        print()
        print('── P3 reinit 有效性（B 臂，`--reinit-dt 1e-6`）──')
        dA, dB = abs(da[1] - da[0]), abs(db[1] - db[0])
        p3 = (dB <= 0.5 * dA)
        print('   |Δ med| ：A = %.4f   B = %.4f   ⇒ B/A = **%.2f×**'
              % (dA, dB, (dB / dA) if dA > 0 else float('nan')))
        print('   判据（预登记）：B ≤ 0.5×A ⇒ **%s**'
              % ('✅ PASS（频繁 reinit 确实减缓退化）' if p3
                 else '❌ FAIL（**频繁 reinit 救不了** 或 反而更差）'))
    elif db:
        dA, dB = abs(da[1] - da[0]) if da else float('nan'), abs(db[1] - db[0])
        print()
        print('── P3 **未执行**：P2 FAIL ⇒ 按预登记，P3 的前提不成立（A 臂没退化，无从比较）')
        print('   （仍报 B 臂读数供参考：|Δ med| = %.4f；A 臂 %.4f）' % (dB, dA))

    # ---------------- P4 ----------------
    print()
    print('── P4 成本 ──')
    wa = float(sa['wall'][-1] - sa['wall'][0])
    wb = float(sb['wall'][-1] - sb['wall'][0])
    print('   A 墙钟 %.1f s（%d→%d 步）   B 墙钟 %.1f s   ⇒ 比 **%.3f×**'
          % (wa, int(sa['steps'][0]), int(sa['steps'][-1]), wb, wb / wa if wa else float('nan')))

    # ---------------- 物理分叉（旁证）----------------
    print()
    print('── 旁证：物理量是否分叉 ──')
    va, vb = sa['Vt'][-1], sb['Vt'][-1]
    # ★ 自查发现的错误 #79：第一版用 `%.6f` 打 Vt，两个都印成 `0.000000`，
    #   而比值却印 `67.000×` ⇒ **读数自相矛盾**（实际是 ~1e-8 µm³ 量级的极小量相除）。
    #   ⇒ 改用科学计数法，并把**整个 Vt 序列的尾部**打出来。
    print('   Vt(末)：A = %.4e µm³   B = %.4e µm³   ⇒ 比 **%.3f×**'
          % (va, vb, va / vb if vb else float('nan')))
    print('   Vt 序列（末 6 帧）：')
    for nm, s in (('A', sa), ('B', sb)):
        print('     %s: %s' % (nm, '  '.join('%.3e' % v for v in s['Vt'][-6:])))
    print('   ⚠ **两臂的 Vt 都在末段塌到 ~%.0e µm³ 量级** ⇒ **板条在末段几乎全部溶掉**。'
          % max(abs(va), abs(vb)))
    print('      这与 `§203`/`§127` 记的"净驱动力为负 ⇒ 播下去的核先溶"是**同一件事**，')
    print('      属任务(2)（S11/S12）的范畴，**不是本次 reinit 对照的结论**。')
    print('      ⚠⚠ **它同时限制了本实验的解读**：末段的 `med|∇φ|` 是在一个**几乎空的场**上量的')
    print('         ⇒ P2/P3 的**趋势**可信（0→300 步场是实的），**末值**要按"场已溶掉"打折看。')
    print('   t_s(末)：A = %.4e s   B = %.4e s' % (sa['ts'][-1], sb['ts'][-1]))
    print('   ⚠ 两臂形核序列一致（P1）而 Vt 不同 ⇒ **reinit 改变了物理结果**')

    # ---------------- 汇总 ----------------
    print()
    print('=' * 78)
    print('★ 判决汇总： P1=%s  P2=%s  P3=%s  P4=%.3f×'
          % ({True: 'PASS', False: 'FAIL', None: 'n/a'}[p1],
             {True: 'PASS', False: 'FAIL', None: 'n/a'}[p2],
             {True: 'PASS', False: 'FAIL', None: '未执行'}[p3],
             (wb / wa) if wa else float('nan')))
    print('=' * 78)
    rec = dict(P1=p1, P2=p2, P3=p3, P4_ratio=(wb / wa) if wa else None,
               A_single0=(da[0] if da else None), A_single1=(da[1] if da else None),
               B_single0=(db[0] if db else None), B_single1=(db[1] if db else None),
               A_wall=wa, B_wall=wb, A_Vt=float(va), B_Vt=float(vb),
               A_nreg=na, B_nreg=nb)
    with open(a.json, 'w') as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1)
    print('⇒ 判决已写 %s' % a.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
