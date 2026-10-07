#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_a3meta.py --- A-3 实验的**审计轨迹**核对：两个臂是否只差 `facet_lam` 一个参数？

为什么必须核对
--------------
A-3 的结论完全建立在"两臂只差 `--facet-lam`"这个前提上。
若 `meta.json` 里**没记** `facet_lam`，就无法从产物证明两臂真的不同
—— 只能靠"我记得我传了"（本项目最贵的一类错误）。
⇒ 本脚本直接读 `meta.json`，把两臂的**全部**配置**并排**列出并逐项比对。

判据
----
  M-1 `facet_lam` 必须**已被记录**（非 None）；
  M-2 两臂并排后，**唯一**不同的键必须是 `facet_lam`（及其派生的 `sha256` 无关项）；
      任何**其它**差异都要打印出来（若存在 ⇒ 该对照**不是单变量**，结论无效）。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def meta(d):
    p = os.path.join(HERE, '_exp', d, 'meta.json')
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p))
    except Exception as e:                                           # noqa: BLE001
        print('%s: meta 读不了 %s' % (d, e))
        return None


pairs = [(sys.argv[1], sys.argv[2])] if len(sys.argv) > 2 else \
    [('_facetctl_00', '_facetctl_04'), ('a3_facet00', 'a3_facet04')]

for A, B in pairs:
    ma, mb = meta(A), meta(B)
    print('=' * 92)
    if ma is None or mb is None:
        print('%s vs %s ：（至少一臂还没有 meta.json —— 可能还没跑）' % (A, B))
        continue
    print('%s  vs  %s' % (A, B))
    keys = sorted(set(ma) | set(mb))
    diff = []
    # ⚠ 记账（本脚本第一版）：白名单只排除了 `sha256`/`git`，却把 **`t0`（墙钟时间戳）**
    #   也报成"额外差异" ⇒ 误判"不是单变量对照"。
    #   `t0` 是**运行时刻**，两臂本来就必然不同，且与物理无关
    #   ⇒ 属于**元数据**，必须与物理参数分开。这是"判据定得太严"的又一例。
    META_KEYS = ('sha256', 'git', 't0', 't_wall', 'host', 'pid')
    for k in keys:
        va, vb = ma.get(k, '（缺）'), mb.get(k, '（缺）')
        if k in META_KEYS:
            continue                     # 元数据（时间戳/引擎哈希/git），不参与单变量判据
        if va != vb:
            diff.append((k, va, vb))
    # M-1
    fl_a, fl_b = ma.get('facet_lam'), mb.get('facet_lam')
    print('M-1 `facet_lam` 已记录： A=%s  B=%s  ⇒ %s'
          % (fl_a, fl_b,
             '✅' if (fl_a is not None and fl_b is not None) else '⛔ **没记！审计轨迹缺失**'))
    # M-2
    print('M-2 两臂配置差异（应为空或只含 `facet_lam`）：')
    if not diff:
        print('    （**无任何差异** —— 若确实传了不同的 `facet_lam`，说明它没被记录）')
    for k, va, vb in diff:
        flag = '✅ 期望的单变量' if k == 'facet_lam' else '⚠ **额外差异**'
        print('    %-14s A=%s   B=%s   %s' % (k, va, vb, flag))
    extra = [k for k, _, _ in diff if k != 'facet_lam']
    print('    ⇒ %s' % ('✅ **单变量对照成立**（只差 `facet_lam`）' if not extra
                        else '⛔ 存在额外差异 %s ⇒ **不是单变量对照**' % extra))
    # 关键项并排（便于人眼核对）
    print('    关键项：norm_smooth=%s/%s  nseed=%s/%s  N=%s/%s  steps=%s/%s'
          % (ma.get('norm_smooth'), mb.get('norm_smooth'), ma.get('nseed'),
             mb.get('nseed'), ma.get('N'), mb.get('N'),
             ma.get('steps'), mb.get('steps')))
print('=' * 92)
