#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_f1.py —— 给 `eng3` 逐条核 F-1..F-4（**预登记判据**，逐点打分）。"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
F = []


def ck(tag, ok, det=''):
    print('  %-56s %s %s' % (tag, 'PASS' if ok else '**FAIL**', det))
    if not ok:
        F.append(tag)


for tag in ('eng3', 'eng2'):
    p = os.path.join(HERE, '_exp/_bk_eng', 'eng_%s' % tag, 'series.csv')
    rows = list(csv.DictReader(open(p)))
    print('=' * 96)
    print('臂 %s（%d 个测点，末 step=%s）' % (tag, len(rows), rows[-1]['step']))
    print('=' * 96)
    # F-1：nslab_n 首次达到 6 的 step
    first6 = next((int(r['step']) for r in rows if int(r['nslab_n']) >= 6), None)
    mx = max(int(r['nslab_n']) for r in rows)
    if tag == 'eng3':
        ck('F-1 nslab_n 在 step ≤ 150 达到 6', first6 is not None and first6 <= 150,
           '首次达到 6 的 step=%s；全程最大 nslab_n=%d' % (first6, mx))
        fin = rows[-1]
        fa = float(fin['f3_area_m2']) * 1e12
        vt = float(fin['Vt']) * 1e18
        ck('F-2 末态 f3_area ∈ [6.0, 8.5] µm²', 6.0 <= fa <= 8.5, '%.4f µm²' % fa)
        ck('F-3 末态 Vt ∈ [2.4, 2.9] µm³', 2.4 <= vt <= 2.9, '%.4f µm³' % vt)
        # F-4 需要快照，另由 _bk_pair.py 判
        ck('F-1b **无过形核**：全程 nslab_n ≤ 6（场用完就应停）',
           mx <= 6, '全程最大 nslab_n=%d（7 = 场用完后又在已有场里多播了一片）' % mx)
        ck('F-1c **柱内不重复**：runs 里每个场至多出现一次',
           all(len(set(r['runs'].split('/'))) == len(r['runs'].split('/'))
               for r in rows if r['runs']),
           '末态 runs=%s' % fin['runs'])
        ck('F-5 无显著碎裂（ncompbig_max ≤ 2）',
           int(fin['ncompbig_max']) <= 2, 'ncompbig_max=%s' % fin['ncompbig_max'])
    else:
        print('  （对照臂，只列关键量）首次达到 6 的 step=%s，全程最大 nslab_n=%d，'
              '末态 runs=%s' % (first6, mx, rows[-1]['runs']))
    # 轨迹
    print('  轨迹: ' + '  '.join('%s:%s片/F3=%.2f/Vt=%.2f'
                                % (r['step'], r['nslab_n'],
                                   float(r['f3_area_m2']) * 1e12,
                                   float(r['Vt']) * 1e18)
                                for r in rows if int(r['step']) % 50 == 0))
print('=' * 96)
print('FAIL = %d %s' % (len(F), F if F else ''))

# ---------- G-1..G-5：`nfsv_strict` 的预登记判据 ----------
import json
G = []
d = os.path.join(HERE, '_exp/_bk_eng/eng_eng5')
p = os.path.join(d, 'series.csv')
if not os.path.exists(p):
    print('\n（`eng_eng4` 尚未产出 ⇒ G-1..G-5 无法判定）')
    raise SystemExit(1 if F else 0)
rows = list(csv.DictReader(open(p)))
fin = rows[-1]
mx = max(int(r['nslab_n']) for r in rows)
print()
print('=' * 96)
print('G-1..G-5（`eng5` = `eng3` + `nfsv_strict` + 诊断落盘）  测点=%d  末 step=%s'
      % (len(rows), fin['step']))
print('=' * 96)


def gk(tag, ok, det=''):
    print('  %-56s %s %s' % (tag, 'PASS' if ok else '**FAIL**', det))
    if not ok:
        G.append(tag)


gk('G-1 全程 nslab_n ≤ 6 且末态 == 6', mx <= 6 and int(fin['nslab_n']) == 6,
   '全程最大=%d，末态=%s' % (mx, fin['nslab_n']))
dupr = [r['step'] for r in rows if r['runs']
        and len(set(r['runs'].split('/'))) != len(r['runs'].split('/'))]
gk('G-2 runs 里每个场至多出现一次（无重复）', not dupr,
   '重复测点=%s；末态 runs=%s' % (dupr or '无', fin['runs']))
fa = float(fin['f3_area_m2']) * 1e12
gk('G-3 末态 f3_area ∈ [6.0, 8.5] µm²', 6.0 <= fa <= 8.5, '%.4f µm²' % fa)
vt = float(fin['Vt']) * 1e18
gk('G-4 末态 Vt ∈ [2.3, 2.9] µm³', 2.3 <= vt <= 2.9, '%.4f µm³' % vt)
# ★ G-5 是关键正对照：必须证明"拒绝"真的发生过
nd = os.path.join(d, 'nuc_dbg.json')
if os.path.exists(nd):
    j = json.load(open(nd, encoding='utf-8'))
    dbg = j.get('dbg', {})
    gk('G-5 **nfsv_nofield ≥ 1**（"拒绝"真的发生过 —— 关键正对照）',
       int(dbg.get('nfsv_nofield', 0)) >= 1,
       'dbg=%s  n_eng_ev=%s  事件模式=%s'
       % ({k: v for k, v in dbg.items() if v}, j.get('n_eng_ev'),
          j.get('n_events_by_mode')))
else:
    gk('G-5 nfsv_nofield ≥ 1', False,
       '**没有 nuc_dbg.json** ⇒ 判据无法复核。'
       '⚠ 本轮真踩到这条：`eng4` 是在"落盘功能加进去之前"起跑的 ⇒ '
       '它的 dbg 只存在于内存、跑完即丢 ⇒ **关键正对照不可复核，只能重跑**。'
       '⇒ 教训：**启动长跑之前，先确认所有要判的量都已经会落盘**。')
print('=' * 96)
print('G-FAIL = %d %s' % (len(G), G if G else ''))

