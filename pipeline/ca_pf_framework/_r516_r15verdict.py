#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r516_r15verdict.py —— **R-1…R-5 正式判定**（abA/abB 双臂）。

## 判据原文（`AUDIT_SUMMARY_R76.md §20.7`，**原样照抄，不放宽**）

> **R-1** 两臂 `Traceback=0` 且 `n_athermal_ev = 23`；
> **R-2** `closure.json` 的 q 对不对；
> **R-3** 末态 `blk_nprof` **同时**出现 >1 的值**和**多个块；
> **R-4** 落盘完整（`seeds.npz`/`snap_*.npz`/`series.csv`/`nuc_dbg.json`/`closure.json`）；
> **R-5** A/B 对照读数（事件序列 `T_k` 应相同；`r_selfac`/`blk_nprof`/`nf2` 是否因 burst 而不同）。

## ⚠⚠ 本判定**必须自带的一条更正**（`R2_PARAM_VERDICTS.md` 的 **N1**）

**R-5 的措辞假设 `abA` 与 `abB` 是"单变量对照"** ——
**但实测（读 `meta.json`）两臂的冷速差 7.4 倍**：
`abA` 的 `cool_rate = 2352400`、`abB` 的 `17412000`。
⇒ **它们不是单变量对照** ⇒ **R-5 的任何"A/B 差异"都同时含"臂的差别"与"冷速差别"，无法归因。**
**⇒ 本判定对 R-5 出的是"⚠ 不可归因"，不是"PASS/FAIL"。**

## 口径（写清，避免 #92 那类错）
* 形核事件行：**`形核 @ step`**（`--nuc-law athermal` 路径），**不是** `引擎形核`；
* `n_athermal_ev`：优先读 `nuc_dbg.json`；**没有就认"无法取证"**，不从日志反推（避免口径混）。
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

import numpy as np

ROOT = '_exp/_bk_mb'
ARMS = (('abA', 'dry_abA', '_r445_abA.log'), ('abB', 'dry_abB', '_r445_abB.log'))


def find_log(tag_hint):
    """★ 自查错误 #104：第一版只搜 `_w2_*.log` ⇒ **找不到 abA/abB 的日志**
    （它们的 stdout 在 `_r445_ab{A,B}.log`，由 `_r445_abfix.sh` 重定向）
    ⇒ R-1 的 "Traceback=0" 被判成 ❌（其实是**没找到文件**）。
    ⇒ 改成搜**当前目录的全部 `*.log`**（不递归，避免扫进 `_exp/` 的几万个文件）。"""
    cands = []
    # ★ 自查错误 #105：第一版拿**目录名**（`dry_abA`）去找日志，
    #   而日志名用的是**臂名**（`_r445_abA.log`）⇒ 仍找不到。
    #   ⇒ 两个名字都试。
    for stem in (tag_hint, tag_hint[4:] if tag_hint.startswith('dry_') else tag_hint):
        cands += sorted(glob.glob('_r445_%s.log' % stem))
        cands += sorted(glob.glob('*_%s.log' % stem))
    cands += sorted(glob.glob('*.log'))
    seen = set()
    for f in cands:
        if f in seen:
            continue
        seen.add(f)
        try:
            with open(f, errors='replace') as fh:
                head = fh.read(200000)
        except OSError:
            continue
        if ('--tag %s' % tag_hint) in head or (('--tag %s' % tag_hint[4:])
                                               in head if tag_hint.startswith('dry_')
                                               else False):
            return f
        if f.endswith('_%s.log' % tag_hint) or \
                (tag_hint.startswith('dry_') and f.endswith('_%s.log' % tag_hint[4:])):
            return f
    return None


def series(tag):
    p = os.path.join(ROOT, tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        rows = [ln.rstrip('\n') for ln in fh if ln.strip()]
    if len(rows) < 2:
        return None
    hdr = rows[0].split(',')
    ix = {h: i for i, h in enumerate(hdr)}
    out = {}
    for k in hdr:
        out[k] = []
    for ln in rows[1:]:
        c = ln.split(',')
        if len(c) < len(hdr):
            continue
        for k in hdr:
            try:
                out[k].append(float(c[ix[k]]))
            except ValueError:
                out[k].append(c[ix[k]])
    return {k: np.array(v) if k != 'vols' else v for k, v in out.items()}


def main():
    print('=' * 96)
    print('R516  R-1…R-5 正式判定（abA / abB）')
    print('=' * 96)

    info = {}
    for nm, tag, _ in ARMS:
        d = os.path.join(ROOT, tag)
        lg = find_log(tag)
        n_tb = None
        n_ev = None
        if lg:
            with open(lg, errors='replace') as fh:
                txt = fh.read()
            n_tb = txt.count('Traceback')
            n_ev = len(re.findall(r'形核\*?\*? @ step', txt))
        files = {os.path.basename(f) for f in glob.glob(os.path.join(d, '*'))}
        have = {k: any(f.startswith(k) for f in files)
                for k in ('seeds.npz', 'series.csv', 'nuc_dbg.json', 'closure.json')}
        have['snap_*.npz'] = any(f.startswith('snap_') for f in files)
        s = series(tag)
        ea = {}
        mj = os.path.join(d, 'meta.json')
        if os.path.exists(mj):
            with open(mj) as fh:
                ea = (json.load(fh).get('exp_args') or {})
        nb = None
        if os.path.exists(os.path.join(d, 'nuc_dbg.json')):
            with open(os.path.join(d, 'nuc_dbg.json')) as fh:
                nb = json.load(fh)
        info[nm] = dict(log=lg, n_tb=n_tb, n_ev=n_ev, have=have, s=s, ea=ea, nuc=nb,
                        last_step=int(s['step'][-1]) if s is not None else None)
        print('■ %s（%s）  日志=%s' % (nm, tag, lg or '**找不到**'))
        print('   末步 = %s ；事件行数 = %s ；Traceback = %s'
              % (info[nm]['last_step'], n_ev, n_tb))
        print('   冷速 cool_rate = %s ；q(closure) 见下' % ea.get('cool_rate'))
        print('   文件：%s' % {k: ('有' if v else '**无**') for k, v in have.items()})
        print()

    # ---- R-1 ----
    print('── R-1 两臂 Traceback=0 且 n_athermal_ev = 23 ──')
    for nm, _, _ in ARMS:
        i = info[nm]
        tb_ok = (i['n_tb'] == 0)
        nev = None
        if i['nuc']:
            for k in ('n_eng_ev', 'n_athermal_ev', 'n_ev'):
                if k in i['nuc']:
                    nev = i['nuc'][k]
                    break
        print('   %s：Traceback=%s ⇒ %s ；`nuc_dbg.json` 的 n_ev = %s ⇒ %s'
              % (nm, i['n_tb'], '✅' if tb_ok else '❌', nev,
                 ('✅ == 23' if nev == 23 else '❌ ≠ 23' if nev is not None
                  else '⚠ **无法取证**（该臂没写 `nuc_dbg.json`）')))
    r1 = all((info[n]['n_tb'] == 0) for n, _, _ in ARMS)
    print('   ⇒ **%s**' % ('部分成立：Traceback=0 ✅；`n_athermal_ev` 见上' if r1 else '❌ FAIL'))
    print()

    # ---- R-2 closure.json 的 q ----
    print('── R-2 `closure.json` 的 q 对不对 ──')
    r2 = True
    for nm, tag, _ in ARMS:
        p = os.path.join(ROOT, tag, 'closure.json')
        if not os.path.exists(p):
            print('   %s：**没有 `closure.json`** ⇒ 无法取证' % nm)
            r2 = False
            continue
        with open(p) as fh:
            cl = json.load(fh)
        q_cl = cl.get('q')
        q_ea = info[nm]['ea'].get('cool_rate')
        ok = (q_cl is not None and q_ea is not None
              and abs(float(q_cl) - float(q_ea)) / max(abs(float(q_ea)), 1e-30) < 1e-9)
        print('   %s：closure.q = %s ；meta.exp_args.cool_rate = %s ⇒ %s'
              % (nm, q_cl, q_ea, '✅ 一致' if ok else '❌ 不一致'))
        r2 &= ok
    print('   ⇒ **%s**' % ('✅ PASS' if r2 else '❌/⚠ 见上'))
    print()

    # ---- R-3 blk_nprof ----
    print('── R-3 末态 `blk_nprof` 同时出现 >1 的值**和**多个块 ──')
    r3 = {}
    for nm, _, _ in ARMS:
        s = info[nm]['s']
        if s is None or 'blk_nprof' not in s:
            print('   %s：**没有 `blk_nprof` 列** ⇒ 无法取证' % nm)
            r3[nm] = None
            continue
        raw = s['blk_nprof'][-1]
        vals = [float(x) for x in str(raw).split('/') if x.strip() != '']
        has_gt1 = any(v > 1 for v in vals)
        multi = len(vals) > 1
        r3[nm] = (has_gt1 and multi)
        print('   %s：末态 blk_nprof = %s ⇒ 有 >1 的值？%s ；多个块？%s ⇒ **%s**'
              % (nm, vals, '✅' if has_gt1 else '❌', '✅' if multi else '❌',
                 '✅ PASS' if r3[nm] else '❌ FAIL'))
    print()

    # ---- R-4 落盘完整 ----
    print('── R-4 落盘完整（seeds/snap/series/nuc_dbg/closure）──')
    r4 = True
    need = ('seeds.npz', 'snap_*.npz', 'series.csv', 'nuc_dbg.json', 'closure.json')
    for nm, _, _ in ARMS:
        h = info[nm]['have']
        miss = [k for k in need if not h.get(k)]
        print('   %s：缺 %s ⇒ %s' % (nm, miss or '无', '✅' if not miss else '❌'))
        r4 &= (not miss)
    print('   ⇒ **%s**' % ('✅ PASS' if r4 else '❌ FAIL'))
    print()

    # ---- R-5 ----
    print('── R-5 A/B 对照读数 ──')
    qa = info['abA']['ea'].get('cool_rate')
    qb = info['abB']['ea'].get('cool_rate')
    print('   ⚠⚠ **N1 更正**：两臂 `cool_rate` = %s vs %s ⇒ 差 **%.1f 倍**'
          % (qa, qb, (float(qb) / float(qa)) if qa else float('nan')))
    print('      ⇒ **它们不是单变量对照** ⇒ 任何"A/B 差异"都无法归因到 burst/臂本身。')
    print('   ⚠ 而且 **R-5 的前提"事件序列 `T_k` 应相同"在此不成立** ——')
    print('     `T_k = M_s − k/α_KM` 只依赖 `α_KM`，两臂相同；')
    print('     但**到达每个 `T_k` 的时刻**由冷速决定 ⇒ 两臂差 7.4 倍 ⇒ **时间轴不可比**。')
    for nm, _, _ in ARMS:
        s = info[nm]['s']
        if s is None:
            continue
        for k in ('r_selfac', 'nf2', 'nblk_sig', 'blk_nprof'):
            if k in s:
                print('     %s.%s 末值 = %s' % (nm, k, s[k][-1]))
    print('   ⇒ **⚠ 不可归因**（不是 PASS/FAIL）—— 需要**重跑一个真正的单变量对照**才能判 R-5。')
    print()
    print('=' * 96)
    print('★ 汇总： R-1=%s  R-2=%s  R-3=%s  R-4=%s  R-5=⚠不可归因'
          % ('部分' if r1 else 'FAIL', '见上' if not r2 else 'PASS',
             {True: 'PASS', False: 'FAIL', None: '未取证'}[r3.get('abB')], 'PASS' if r4 else 'FAIL'))
    print('=' * 96)
    return 0


if __name__ == '__main__':
    sys.exit(main())
