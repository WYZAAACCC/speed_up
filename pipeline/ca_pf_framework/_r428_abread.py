#!/usr/bin/env python3
"""_r428_abread.py —— ★★ **A/B 受控双臂的读数与判据**（`§190.6` 的 R-1…R-5）。

## 判据（在 `§190.6` **跑之前**就写死了，此处逐条核）
  R-1 两臂 `Traceback = 0`，且 `n_athermal_ev` 达到 **23**（= n − 1 = 24 − 1）。
  R-2 `closure.json` 的 q：A = 2.3524e6、B = 1.7412e7；`nuc_law = athermal`。
  R-3 末态 `blk_nprof` 里**同时**出现 **>1 的值**（块内多根）**和** 多个块。
      ⚠ 这是条件③的核心要求（"块 = 多根同类板条堆叠"）。
  R-4 落盘完整：`seeds.npz` / `snap_*.npz` / `series.csv` / `nuc_dbg.json` / `closure.json`。
  R-5 **A/B 对照读数**：事件序列 `T_k` 是否相同（同 `α_KM` ⇒ 应相同）；
      `r_selfac` / `blk_nprof` / `nf2` / `nslab_n` 是否因 burst 而不同。

## 纪律
* 只读，不写任何归档产物。
* 每个量都标**来源文件**；缺文件就明说"缺"，**不猜**。
"""
import csv
import json
import os
import sys

import numpy as np

BASE = '_exp/_bk_mb'
# ⚠ 驱动把目录建成 `<out>/dry_<tag>` ⇒ 实际是 `dry_abA` / `dry_abB`（自纠错）。
ARMS = [('dry_abA', 'A：守 C-3（q=2.3524e6, steps=5922）'),
        ('dry_abB', 'B：burst（q=1.7412e7, steps=800）')]


def P(s):
    print(s, flush=True)


def rd(tag, name):
    p = os.path.join(BASE, tag, name)
    return p if os.path.exists(p) else None


def load_csv(tag):
    p = rd(tag, 'series.csv')
    if p is None:
        return None
    with open(p, newline='') as f:
        return list(csv.DictReader(f))


def load_json(tag, name):
    p = rd(tag, name)
    if p is None:
        return None
    try:
        return json.load(open(p))
    except Exception as e:
        return {'_err': repr(e)}


def num(r, k):
    v = r.get(k)
    if v in (None, ''):
        return None
    try:
        return float(v)
    except ValueError:
        return None


P('=' * 92)
P('_r428 —— A/B 受控双臂读数（判据 R-1…R-5，均**预先写死**于 `§190.6`）')
P('=' * 92)

data = {}
for tag, desc in ARMS:
    P('\n' + '#' * 92)
    P('# %s  %s' % (tag, desc))
    P('#' * 92)
    d = dict(rows=load_csv(tag), nuc=load_json(tag, 'nuc_dbg.json'),
             clo=load_json(tag, 'closure.json'))
    data[tag] = d

    # ---- R-4 落盘完整性
    files = sorted(f for f in os.listdir(os.path.join(BASE, tag))
                   if os.path.isfile(os.path.join(BASE, tag, f)))
    snaps = [f for f in files if f.startswith('snap_')]
    need = ['seeds.npz', 'series.csv', 'nuc_dbg.json', 'closure.json']
    miss = [f for f in need if f not in files]
    P('\n[R-4 落盘] 文件 %d 个，其中快照 %d 张' % (len(files), len(snaps)))
    P('     必需件缺失：%s ⇒ %s' % (miss or '无', '✅ PASS' if not miss else '❌ FAIL'))
    if snaps:
        tot = sum(os.path.getsize(os.path.join(BASE, tag, f)) for f in snaps)
        P('     快照总大小 = %.2f GB；步号范围 %s … %s'
          % (tot / 1e9, snaps[0], snaps[-1]))

    # ---- R-2 closure.json
    c = d['clo'] or {}
    P('\n[R-2 closure] nuc_law=%s  α_KM=%s  q=%s  n=%s  q_source=%s'
      % (c.get('nuc_law'), c.get('alpha_KM'), c.get('q'), c.get('n_law'),
         c.get('q_source')))

    # ---- R-1 事件数
    n = d['nuc'] or {}
    P('\n[R-1 形核] n_athermal_ev=%s  n_target_final=%s  by_requested=%s  fallback=%s'
      % (n.get('n_athermal_ev'), n.get('n_target_final'),
         n.get('n_events_by_requested_mode'), n.get('n_fresh_fallback_to_stack')))
    ne = n.get('n_athermal_ev')
    P('     ⇒ 判据「= 23」：%s' % ('✅ PASS' if ne == 23 else '⚠ 实测 %s（未达 23）' % ne))

    # ---- 逐步读数
    rows = d['rows']
    if rows:
        P('\n[逐步] 共 %d 行' % len(rows))
        hdr = ['step', 'Vt', 'nslab_n', 'nf2', 'nf3', 'r_selfac', 'blk_nprof',
               'blk_laths', 'nblk_sig']
        P('     %-7s %-11s %-8s %-7s %-8s %-9s %-24s %s'
          % ('step', 'Vt(µm³)', 'nslab', 'nf2', 'nf3', 'r_selfac', 'blk_nprof',
             'blk_laths'))
        step_sel = [0]
        for i in range(1, 6):
            step_sel.append(int(len(rows) * i / 5.0))
        step_sel.append(len(rows) - 1)
        for i in sorted(set(min(s, len(rows) - 1) for s in step_sel)):
            r = rows[i]
            vt = num(r, 'Vt')
            P('     %-7s %-11s %-8s %-7s %-8s %-9s %-24s %s'
              % (r.get('step'),
                 ('%.4f' % (vt * 1e18)) if vt is not None else '—',
                 r.get('nslab_n'), r.get('nf2'), r.get('nf3'),
                 (r.get('r_selfac') or '—')[:8],
                 (r.get('blk_nprof') or '—')[:23],
                 (r.get('blk_laths') or '—')[:30]))
        # R-3
        last = rows[-1]
        bp = (last.get('blk_nprof') or '').split('/')
        bp = [int(x) for x in bp if x.strip().isdigit()]
        multi = [x for x in bp if x > 1]
        P('\n[R-3 块结构] 末态 step=%s' % last.get('step'))
        P('     blk_laths = %s' % last.get('blk_laths'))
        P('     blk_nprof = %s' % last.get('blk_nprof'))
        P('     nblk_sig  = %s' % last.get('nblk_sig'))
        ok3 = bool(multi) and len(bp) > 1
        P('     ⇒ 「既有 >1 根的块、又有多个块」：%s（块数 %d，块内>1 根的块 %d 个）'
          % ('✅ PASS' if ok3 else '❌ FAIL', len(bp), len(multi)))

# ---------------- R-5 A/B 对照 ----------------
P('\n' + '=' * 92)
P('[R-5] A/B 对照读数')
na = (data.get('abA', {}).get('nuc') or {})
nb = (data.get('abB', {}).get('nuc') or {})
Ta = [e.get('T') for e in (na.get('T_events') or [])]
Tb = [e.get('T') for e in (nb.get('T_events') or [])]
P('  A 事件温度序列（前 8）：%s' % [round(t, 1) for t in Ta[:8]])
P('  B 事件温度序列（前 8）：%s' % [round(t, 1) for t in Tb[:8]])
if Ta and Tb:
    k = min(len(Ta), len(Tb))
    same = all(abs(Ta[i] - Tb[i]) < 1e-9 for i in range(k))
    P('  ⇒ 前 %d 个 `T_k` 是否逐位相同：%s（同一 α_KM ⇒ **应当**相同）'
      % (k, '✅' if same else '⚠ 不同'))
for tag, _ in ARMS:
    rows = data.get(tag, {}).get('rows')
    if rows:
        last = rows[-1]
        P('  %s 末态：step=%s  Vt=%.4f µm³  nslab=%s  nf2=%s  r_selfac=%s'
          % (tag, last.get('step'),
             (num(last, 'Vt') or 0) * 1e18, last.get('nslab_n'),
             last.get('nf2'), (last.get('r_selfac') or '—')[:10]))
P('=' * 92)
