#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r540_b5verdict.py —— `_r539b5`（`--nuc-block-target 8 → 5`）的**预登记判据 Q1–Q5**。

判据原文见 `_r539_b5run.sh` 文件头，此处**原样实现，不放宽**。
对照基准 = `_r529` / `_r535diag`（同一配置、`B=8`）：`nfsv_nofield=21`、
事件 `18/40`、`fresh_blocked=17`。

★ 读数口径：`series.csv` 的 **`Vt` 是 SI m³**（要 ×1e18 才是 µm³）；
`--nuc-law athermal` 的事件行是 `形核 @ step`。
⚠ 这两条我都栽过（本仓已多次 nm/µm 混淆）⇒ 这里**显式**写在代码里。
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# ★ 用法：`_r540_b5verdict.py [tag] [root]`
#   `root` 默认 `_exp/_bk_mb`；`_r537_parrun.py` 跑出来的在 `_exp/_bk_par/<tag>`。
#   ⚠ 实际算例目录是 `<root>/<tag>/dry_<tag>`（`_bk_exp.py` 的布局）——
#     本件第一版用 `<root>/<tag>` ⇒ 读不到 ⇒ 报"缺 nuc_dbg.json"（**假警报**）。
ROOT = (sys.argv[2] if len(sys.argv) > 2 else '_exp/_bk_mb')
TAG = (sys.argv[1] if len(sys.argv) > 1 else 'dry_r539b5')
REF = dict(nfsv_nofield=21, n_ev=18, n_tgt=40, fresh_blocked=17)


def _run_dir():
    """在两种布局里找算例目录（找不到就抛，并把试过的路径打出来）。"""
    cands = [os.path.join(HERE, ROOT, TAG),
             os.path.join(HERE, ROOT, TAG, 'dry_%s' % TAG),
             os.path.join(HERE, ROOT, 'dry_%s' % TAG)]
    for c in cands:
        if os.path.exists(os.path.join(c, 'series.csv')):
            return c
    raise SystemExit('✗ 找不到算例；试过：%s' % ', '.join(cands))


def _dbg():
    p = os.path.join(_run_dir(), 'nuc_dbg.json')
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, errors='replace'))
    except Exception:                                           # noqa: BLE001
        return None


def _last_row():
    p = os.path.join(_run_dir(), 'series.csv')
    if not os.path.exists(p):
        return None
    rows = [r for r in open(p, errors='replace').read().splitlines() if r.strip()]
    if len(rows) < 2:
        return None
    hdr = rows[0].split(',')
    return {h: v for h, v in zip(hdr, rows[-1].split(','))}


def main():
    rows = []
    d = _dbg()
    last = _last_row()
    L = ['=' * 100,
         'R540 —— `_r539b5`（`--nuc-block-target 8 → 5`）预登记判据', '=' * 100]
    if d is None or last is None:
        L.append('❌ 缺 `nuc_dbg.json` 或 `series.csv`（算例还没落盘 / 落盘失败）')
        print('\n'.join(L))
        return 1

    dbg = d.get('dbg') or {}
    # ⚠⚠ **键"缺失" = 计数为 0，不是"没读到"**（`_r541` 的 b4 实测）：
    #   `nfsv_nofield` 只在**拒绝发生**时才被 `_dbg.get(...,0)+1` 创建
    #   ⇒ 一次都没拒 ⇒ **字典里根本没有这个键**。
    #   第一版用 `.get('nfsv_nofield')`（无默认）⇒ `None` ⇒ Q1 **假 FAIL**。
    #   ⇒ 修法：缺省取 **0**，并在报告里**显式标注"键未出现（= 0 次）"**，
    #     不让"0"与"没读到"混为一谈。
    _nf_raw = dbg.get('nfsv_nofield', 'ABSENT')
    nf = 0 if _nf_raw == 'ABSENT' else _nf_raw
    fb = dbg.get('fresh_blocked', 0)
    nev = d.get('n_athermal_ev')
    ntgt = d.get('n_target_final')
    ratio = (float(nev) / float(ntgt)) if (nev and ntgt) else float('nan')
    L.append('  读数：nfsv_nofield=%s  fresh_blocked=%s  事件=%s/%s=%.3f'
             % (nf if _nf_raw != 'ABSENT' else '**0（键未出现）**',
                fb, nev, ntgt, ratio))
    L.append('  对照（`B=8`）：nfsv_nofield=%d  fresh_blocked=%d  事件=%d/%d=%.3f'
             % (REF['nfsv_nofield'], REF['fresh_blocked'], REF['n_ev'],
                REF['n_tgt'], REF['n_ev'] / REF['n_tgt']))
    L.append('  末态：Vt=%.4f µm³  nf3_col=%s  nslab_n=%s'
             % (float(last.get('Vt', 'nan')) * 1e18,
                last.get('nf3_col'), last.get('nslab_n')))
    L.append('')

    def chk(n, ok, det):
        rows.append((n, bool(ok), det))

    chk('Q1 `nfsv_nofield` ≤ 5',
        (nf is not None) and (int(nf) <= 5),
        '%s（对照 %d）%s' % (nf, REF['nfsv_nofield'],
                            '' if _nf_raw != 'ABSENT' else
                            '  ← **键未出现 ⇒ 一次都没拒过**'))
    chk('Q2 事件/目标 ≥ 0.70',
        ratio == ratio and ratio >= 0.70,
        '%s/%s = %.3f（对照 %.3f）' % (nev, ntgt, ratio,
                                       REF['n_ev'] / REF['n_tgt']))
    chk('Q3 `fresh_blocked` ≤ 8',
        (fb is not None) and (int(fb) <= 8),
        '%s（对照 %d）' % (fb, REF['fresh_blocked']))

    # Q4 C3：逐块判据（需要 --pair-every 命中）
    nblk = last.get('nblk_sig', '')
    npr = last.get('blk_nprof', '')
    nlt = last.get('blk_laths', '')
    ok4 = False
    det4 = 'nblk_sig=%s blk_nprof=%s blk_laths=%s' % (nblk, npr, nlt)

    def _l(s):
        """解析 `series.csv` 里的列表型列。

        ⚠⚠ **本函数第一版是错的，导致 Q4 假 FAIL**：
          第一版写 `str(s).strip('[]').split()`（按**空白**切），
          而 `series.csv` 里这类列用的是**斜杠**分隔
          （实测原文 `blk_npro=8/1/1/1/1/1/1/1/1/1/1`，与 `runs=9/7/5/…` 同款）
          ⇒ `.split()` 只切出 1 个元素 `'8/1/1/…'` ⇒ `float()` 抛 ⇒ 返回 `[]`
          ⇒ 判据说 `blk_nprof=[]` ⇒ **Q4 假 FAIL**（而屏幕上打印的两个列表**明明相等**）。
        ⇒ 修法：**先按 `/` 切，再按空白兜底**（两种格式都吃）。
        ⚠ 这是本仓 §3.3 教训 17/29 的同款（**先怀疑自己的解析，别怀疑数据**）。
        """
        t = str(s).strip().strip('[]')
        if not t:
            return []
        for sep in ('/', ',', None):
            try:
                parts = t.split(sep) if sep else t.split()
                return [float(x) for x in parts if str(x).strip() != '']
            except ValueError:
                continue
        return []

    _p, _l2 = _l(npr), _l(nlt)
    if nblk not in ('', None) and _p and _l2 and len(_p) == len(_l2):
        ok4 = (int(float(nblk)) >= 2) and all(a == b for a, b in zip(_p, _l2))
        det4 += ' ⇒ ≥2 块=%s，逐块 nprof==nlaths=%s' % (
            int(float(nblk)) >= 2, all(a == b for a, b in zip(_p, _l2)))
    chk('Q4 C3 仍成立（`nblk_sig ≥ 2` 且逐块 `blk_nprof == blk_laths`）', ok4, det4)

    # Q5 正对照：诊断/调度参数不改物理 ⇒ 逐位可复现性由 `Vt` 与 `_r535diag` 对照
    #   ⚠ 本跑 `B` 改了 ⇒ `Vt` **本就应当不同** ⇒ 这里只查"数值健康"
    fin = last.get('finite', '1')
    chk('Q5 数值健康（`finite` 为真、无 NaN）',
        str(fin) in ('1', '1.0', 'True'), 'finite=%s' % fin)

    npass = sum(1 for _, ok, _ in rows if ok)
    L.append('')
    for n, ok, det in rows:
        L.append('  %-52s %s   %s' % (n, '✅ PASS' if ok else '❌ FAIL', det))
    L.append('')
    L.append('★ 汇总：%d/%d PASS' % (npass, len(rows)))
    L.append('★ ⇒ %s' % ('**"让 `B` 服从物理"成立**（上游卡点被打通）'
                         if npass == len(rows) else
                         '**未全部通过** ⇒ 照实记，不得宣称闭环成立。'))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r540_b5verdict.log'), 'w') as fh:
        fh.write(out + '\n')
    return 0 if npass == len(rows) else 1


if __name__ == '__main__':
    sys.exit(main())
