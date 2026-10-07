#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R463 —— 从**已归档的 series.csv** 取证：`reinit` 到底触发过几次？（任务(1) 的 S2）

## 要回答的三个问题（都可从归档数据直接算，不需要重跑）

**Q1（定时触发）**：`reinit_dt=1e-4`，而 `dt ≈ 2.7e-8`
⇒ 需要 `1e-4/2.7e-8 ≈ 3700` 步才够一次。
**问：这次跑的总物理时间 `t_s` 够不够 1e-4？**
若 `t_s(末) < 1e-4` ⇒ **定时 reinit 一次都没触发**（不是"很少"，是"零"）。

**Q2（事件触发）**：`windowB_surface.py:4050-4054` 有一条**独立于定时**的强制路径 ——
只要本轮 `nucleate()` 真发生过事件（`_need_reinit`），就 `reinitialize(force=True)`。
**问：这次跑有几次形核事件？** 每一次都 ⇒ 一次强制 reinit。

**Q3（合计）**：Q1 + Q2 ⇒ 真正的 reinit 触发次数。

## 口径来源（不猜，逐条给出处）

* 定时判据：`windowB_surface.py:4033-4040`
  `self._t_since_reinit += dt`；`if self.reinit_dt: if _t_since_reinit >= reinit_dt: 触发`。
* 事件判据：`windowB_surface.py:4050-4054`（`_need_reinit` ⇒ `reinitialize(force=True)`，
  并 `self._forced_reinit += 1`）。
* **两个计数器（`_forced_reinit` / `_reinit_done` / `_reinit_skipped`）都没有落盘**
  ⇒ 只能用 `series.csv` 里的可观测量反推，这正是本脚本做的事。
* 形核事件的可观测量：`nreg_used`（在用场数）。每发生一次形核它就 +1
  （`_bk_exp.py` 每步记录）。
  ⚠ **必须验证这条对应关系**，不能假设 —— 本脚本同时用第二条独立证据交叉核对：
  `vols`（各场体积，斜杠分隔）里**新出现的非零场**个数。

用法：
    python3 _r463_reinitcount.py --tag dry_abB
    python3 _r463_reinitcount.py --tag dry_abA --tag dry_saSet2
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

import numpy as np


def read_rows(path):
    """★ 纪律：`/mnt/f` 是 9p 挂载，读**正在被追加**的 CSV 会静默返回过期数据
    （见 AGENTS.md §3.6）。这里读**已归档**的 CSV，仍按仓库既有做法
    反复读到与 `wc -l` 一致为止，取行数最多的那一次。"""
    best = None
    for _ in range(6):
        if not os.path.exists(path):
            return None
        with open(path) as fh:
            lines = [ln.rstrip('\n') for ln in fh if ln.strip()]
        n_disk = sum(1 for _ in open(path))
        if best is None or len(lines) > len(best):
            best = lines
        if len(lines) >= n_disk - 1:
            break
    return best


def parse(tag, root='_exp/_bk_mb'):
    d = os.path.join(root, tag)
    p = os.path.join(d, 'series.csv')
    rows = read_rows(p)
    if not rows:
        print('✗ %s 没有 series.csv' % tag)
        return None
    hdr = rows[0].split(',')
    idx = {h: i for i, h in enumerate(hdr)}
    need = ('step', 't_s', 'wall_s', 'dt', 'nreg_used', 'vols')
    miss = [k for k in need if k not in idx]
    if miss:
        print('✗ %s 缺列 %s' % (tag, miss))
        return None
    recs = []
    for ln in rows[1:]:
        c = ln.split(',')
        if len(c) < len(hdr):
            continue
        try:
            r = dict(step=int(c[idx['step']]), t_s=float(c[idx['t_s']]),
                     wall_s=float(c[idx['wall_s']]), dt=float(c[idx['dt']]),
                     nreg_used=int(c[idx['nreg_used']]), vols=c[idx['vols']])
        except ValueError:
            continue
        recs.append(r)
    return hdr, recs


def n_nonzero_vols(vs):
    """`vols` 是**斜杠分隔**的（教训 #55：曾按逗号解析 ⇒ 返回空列表、判据空过）。
    单位是 **µm³**（教训 #56/#69）。"""
    if not vs:
        return 0
    n = 0
    for s in vs.split('/'):
        s = s.strip()
        if not s:
            continue
        try:
            if abs(float(s)) > 1e-12:
                n += 1
        except ValueError:
            pass
    return n


def report(tag, reinit_dt=1e-4, root='_exp/_bk_mb'):
    got = parse(tag, root)
    if not got:
        return
    hdr, recs = got
    print('=' * 78)
    print('== %s   %d 行' % (tag, len(recs)))
    steps = np.array([r['step'] for r in recs])
    ts = np.array([r['t_s'] for r in recs])
    dts = np.array([r['dt'] for r in recs])
    walls = np.array([r['wall_s'] for r in recs])
    nreg = np.array([r['nreg_used'] for r in recs])
    nvol = np.array([n_nonzero_vols(r['vols']) for r in recs])

    print('  step      : %d → %d' % (steps[0], steps[-1]))
    print('  dt        : min=%.4e  med=%.4e  max=%.4e s' % (dts.min(), np.median(dts), dts.max()))
    print('  t_s(末)   : %.6e s' % ts[-1])
    print()
    # ---------------- Q1：定时触发 ----------------
    need = reinit_dt / np.median(dts)
    print('  ── Q1 定时触发（reinit_dt=%.3e s）──' % reinit_dt)
    print('     按 dt 中位算，需要 **%.0f 步**才够一次 reinit' % need)
    print('     本次跑的总物理时间 t_s(末) = %.6e s' % ts[-1])
    if ts[-1] < reinit_dt:
        print('     ⇒ **t_s(末) < reinit_dt ⇒ 定时 reinit 一次都没触发（零次）**')
        n_timed = 0
    else:
        n_timed = int(ts[-1] // reinit_dt)
        print('     ⇒ 定时 reinit 触发次数 ≈ floor(t_s/reinit_dt) = **%d 次**' % n_timed)
    print('     （`t_s` 是累加的 dt，判据是 `self._t_since_reinit >= reinit_dt`'
          ' 且触发后清零 ⇒ floor 是对的）')
    print()
    # ---------------- Q2：形核事件（两条独立证据）----------------
    dn_reg = np.diff(nreg)
    evA = int((dn_reg > 0).sum())
    dn_vol = np.diff(nvol)
    evB = int((dn_vol > 0).sum())
    print('  ── Q2 形核事件（= 强制 reinit 次数）──')
    print('     证据 A：`nreg_used` 递增次数           = **%d**' % evA)
    print('     证据 B：`vols` 非零场个数递增次数       = **%d**' % evB)
    agree = (evA == evB)
    print('     两者一致：%s    （不一致 ⇒ 口径有洞，**不得**引用本条结论）'
          % ('✅ 是' if agree else '❌ 否'))
    if not agree:
        # 把不一致的步号打出来，便于定位
        a_at = set(steps[1:][dn_reg > 0].tolist())
        b_at = set(steps[1:][dn_vol > 0].tolist())
        print('       只在 A 里：%s' % sorted(a_at - b_at)[:20])
        print('       只在 B 里：%s' % sorted(b_at - a_at)[:20])
        print('       两者都有的：%d 个' % len(a_at & b_at))
    print()
    # ---------------- Q3：合计 ----------------
    print('  ── Q3 合计 reinit 触发次数 = Q1 + Q2 = %d + %d = **%d 次**'
          % (n_timed, evA, n_timed + evA))
    print('     总步数 = %d ⇒ 平均每 **%.0f 步**才触发一次'
          % (steps[-1] - steps[0], (steps[-1] - steps[0]) / max(n_timed + evA, 1)))
    print()
    # ---------------- 旁证：逐段 wall 时间 ----------------
    #   ⚠⚠ **第一版写错了**（自查发现的错误）：我拿 `wall_s` 直接和 3×中位比，
    #   得到"中位 1908 s/步"这种不可能的读数。查 `_bk_exp.py:1650`：
    #       `wall_s = round(time.time() - wall0, 2)`
    #   ⇒ **`wall_s` 是"从开工到此刻的累计墙钟"，不是单步耗时**。
    #   正确的做法是取**差分** `diff(wall_s)`，再除以该段的步数。
    #   （这条也是"先核对量纲/口径再下结论"的一次实例。）
    if len(walls) > 2:
        seg = np.diff(walls) / np.maximum(np.diff(steps), 1)     # s/步，逐段
        med = float(np.median(seg))
        print('  ── 旁证：逐段墙钟（s/步；由累计 `wall_s` 差分得到）──')
        print('     中位 = %.3f s/步   总墙钟 = %.1f s   总步数 = %d'
              % (med, walls[-1] - walls[0], steps[-1] - steps[0]))
        big = np.where(seg > 3.0 * med)[0]
        if len(big) == 0:
            print('     **没有任何一段 > 3×中位**')
        else:
            print('     共 %d 段 > 3×中位' % len(big))
        # ★★ 第二版修（自查发现的错误 #73）：**3× 阈值太松**。
        #   `force=True` 走的是 `windowB_surface.py:4050-4054`，它**绕过 `skip_tol`**
        #   （`skip_tol` 只在 `:4380` 的 `(not force)` 分支里生效）
        #   ⇒ 11 次强制 reinit 是**真跑**的，其开销若 <2×则被 3× 阈值漏掉。
        #   ⇒ 改为**print 全部段**，并把"哪一段含形核事件"标出来（形核步 = nreg_used 跳变处）。
        ev_at = set(steps[1:][dn_reg > 0].tolist())
        print('     ── 逐段明细（段=相邻两行之间；`*` = 该段内含形核事件）──')
        for i in range(len(seg)):
            lo, hi = int(steps[i]), int(steps[i + 1])
            has = any(lo < e <= hi for e in ev_at)
            print('       %5d→%-5d  %7.3f s/步  %5.2f×中位  %s'
                  % (lo, hi, seg[i], seg[i] / med, '*' if has else ' '))
        if ev_at:
            a_ = np.array([seg[i] for i in range(len(seg))
                           if any(int(steps[i]) < e <= int(steps[i + 1]) for e in ev_at)])
            b_ = np.array([seg[i] for i in range(len(seg))
                           if not any(int(steps[i]) < e <= int(steps[i + 1]) for e in ev_at)])
            if len(a_) and len(b_):
                print('     ★ 含形核段 中位 %.3f s/步 (%d 段)  vs  不含形核段 中位 %.3f s/步 (%d 段)'
                      ' ⇒ 比 **%.2f×**' % (np.median(a_), len(a_), np.median(b_), len(b_),
                                           np.median(a_) / np.median(b_)))
    print('=' * 78)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', action='append', default=[])
    ap.add_argument('--root', default='_exp/_bk_mb')
    ap.add_argument('--reinit-dt', type=float, default=1e-4)
    a = ap.parse_args()
    tags = a.tag or [os.path.basename(os.path.dirname(p))
                     for p in sorted(glob.glob(os.path.join(a.root, '*', 'series.csv')))]
    for t in tags:
        report(t, a.reinit_dt, a.root)
    return 0


if __name__ == '__main__':
    sys.exit(main())
