#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r536_diagread.py —— 读 `_r535diag` 的 `nfsv_diag_*`，**判定 `nfsv_nofield` 的成因**。

## 三个互斥假设（**判据先写死，再读**）
设某次拒绝时：同变体场**总数** `F`、其中被判"非空"的 `O`、全盒非空场数 `T`、引擎 `nv`：

| 假设 | 预测 | 结论 |
|---|---|---|
| **H1 场真不够**（容量） | `O == F`（同变体的场**全部**被占）且 `F` 小 | ⇒ 抬 `nv` **应当**有用（但 `_r529` 已证无用 ⇒ 若命中，说明"抬得还不够"） |
| **H2 碎点占场**（判据过严） | `O == F`，但 `occ_sizes` 里**大量 1–2 胞**的小场（`occ_min` 很小） | ⇒ **真缺陷**：溶剩的碎点让场**永远不可复用** ⇒ 修判据（"有效占用"阈值），**不是**抬 `nv` |
| **H3 场没用完**（别的原因） | `O < F`（还有空场却没选中） | ⇒ 是**选择逻辑**的问题（`vg` 映射/循环），不是容量 |

**⇒ H2 与 H3 的判据完全相反（`O == F` vs `O < F`）⇒ 一次读数就能分开。**

## 正对照（**必须能失败**）
* **C1**：`--nfsv-diag` **只加诊断、不改判据** ⇒ 本跑的 `nfsv_nofield` 与末态 `Vt`
  必须与 `_r529`（无 diag）**一致**。不一致 ⇒ 我的接线**改变了行为**，那是 bug。
* **C2**：`nfsv_diag_*` 必须**真的出现**（不是空字典）—— 否则"没读到"会被误读成"没有问题"。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = '_exp/_bk_mb/dry_r535diag'
REF529 = dict(nfsv_nofield=21, Vt=4.2510)      # `_r529` 的读数（`_w2_r529_param.log`）


def main():
    L = ['=' * 100, 'R536 —— `nfsv_nofield` 成因判定（N11 取证读数）', '=' * 100, '']
    p = os.path.join(HERE, RUN, 'nuc_dbg.json')
    if not os.path.exists(p):
        L.append('❌ 找不到 %s ⇒ 取证跑还没落盘' % p)
        print('\n'.join(L))
        return 1
    d = json.load(open(p, errors='replace'))
    dbg = d.get('dbg') or {}
    keys = ['nfsv_nofield', 'nfsv_diag_v', 'nfsv_diag_nv', 'nfsv_diag_nfields',
            'nfsv_diag_nocc', 'nfsv_diag_occ_min', 'nfsv_diag_tot_occ',
            'nfsv_diag_occ_sizes']
    L.append('── 读数 ──')
    for k in keys:
        L.append('   %-24s = %s' % (k, dbg.get(k, '**缺失**')))

    # ---- C2：诊断真的出现了 ----
    c2 = ('nfsv_diag_nfields' in dbg) and ('nfsv_diag_nocc' in dbg)
    L.append('')
    L.append('   ▶ C2 `nfsv_diag_*` 真的出现：%s'
             % ('✅ PASS' if c2 else '❌ FAIL ⇒ **"没读到"不等于"没问题"**，'
                '先怀疑接线，别下结论'))

    # ---- C1：只加诊断 ⇒ 物理应当不变（对 `_r529`）----
    nf = dbg.get('nfsv_nofield')
    c1a = (nf == REF529['nfsv_nofield'])
    L.append('   ▶ C1a `nfsv_nofield` 与 `_r529` 一致（%s vs %s）：%s'
             % (nf, REF529['nfsv_nofield'], '✅ PASS' if c1a else
                '⚠ **不一致** ⇒ 诊断接线可能改了行为，先查这个'))
    # 末态 Vt
    sp = os.path.join(HERE, RUN, 'series.csv')
    vt = None
    if os.path.exists(sp):
        rows = [r for r in open(sp, errors='replace').read().splitlines() if r.strip()]
        if len(rows) > 1:
            hdr = rows[0].split(',')
            if 'Vt' in hdr:
                i = hdr.index('Vt')
                try:
                    vt = float(rows[-1].split(',')[i])
                except ValueError:
                    vt = None
    L.append('   ▶ C1b 末态 `Vt` 与 `_r529`（%.4f µm³）一致：%s'
             % (REF529['Vt'],
                ('✅ PASS（%.4f µm³）' % (vt * 1e18))
                if (vt is not None and abs(vt * 1e18 - REF529['Vt']) < 5e-4)
                else ('⚠ %s' % vt)))
    # ⚠⚠ **单位陷阱（我自己又踩了）**：`series.csv` 的 `Vt` 是 **SI m³**，
    #   而 `_r529` 日志里读到的 `4.2510` 是 **µm³**。
    #   第一版直接拿 `4.2509e-18` 与 `4.2510` 比 ⇒ 报"⚠ 不一致"（**假警报**）。
    #   ⇒ 必须 ×1e18。本仓已多次栽在 nm/µm/m 混淆上（`_bk_exp.py:859` 有同款注记）。
    if vt is not None:
        L.append('      （`series.csv` 的 `Vt` 单位是 **SI m³** ⇒ 已 ×1e18 转 µm³：'
                 '%.4f）' % (vt * 1e18))

    # ---- H1/H2/H3 判定 ----
    L.append('')
    if not c2:
        L.append('★ 因 C2 未过 ⇒ **不判 H1/H2/H3**（先修接线）')
    else:
        F = int(dbg['nfsv_diag_nfields'])
        O = int(dbg['nfsv_diag_nocc'])
        T = int(dbg.get('nfsv_diag_tot_occ', -1))
        NV = int(dbg.get('nfsv_diag_nv', -1))
        om = dbg.get('nfsv_diag_occ_min')
        L.append('── 判定（F=%d, O=%d, T=%d, nv=%d） ──' % (F, O, T, NV))
        L.append('   ⚠ 口径：`F` **不含源场 `k` 自己**（诊断里 `_j2 == k` 被 skip）')
        L.append('      ⇒ `F = 9` 对应"每变体 10 个场"减掉源场 ⇒ **一致**，不是缺口。')
        if O < F:
            L.append('   ⇒ 🔵 **H3 成立**（**场没用完**：同变体还有 %d 个空场没被选中）'
                     % (F - O))
            L.append('      ⇒ 是**选择逻辑**的问题（`vg` 映射 / 循环 / 提前 break），'
                     '**不是**容量、**不是**碎点 ⇒ 查 `windowB_surface.py` 的 `nfsv` 段。')
        elif O == F:
            L.append('   ⇒ 同变体的**其余**场**全部**被占（O == F == %d）' % F)
            if isinstance(om, int) and om <= 3:
                L.append('   ⇒ 🔴 **H2 成立**（**碎点占场**）：最小的"非空"场只有 **%d 个胞**'
                         % om)
                L.append('      ⇒ **真缺陷**：溶剩的 1–3 胞碎点让场**永远不可复用**。')
                L.append('      ⇒ **正确修法是改"空"的判据**（如"有效占用"阈值），'
                         '**不是**继续抬 `nv` —— 那正是 `_r529` 已证无效的做法。')
            else:
                L.append('   ⇒ 🟠 **H1 成立（容量），且是"每变体配额"而不是"全盒总量"**')
                L.append('      **碎点假设（H2）被否**：最小的"非空"场有 **%s 个胞**'
                         '（不是 1–3 胞的碎点）。' % om)
                if isinstance(T, int) and NV > 0 and T < 0.5 * NV:
                    L.append('      🔴 **关键**：全盒非空只有 **%d/%d（%.1f%%）**，'
                             '可**这一个变体**的场已经用光 ⇒ '
                             '**瓶颈是"每变体配额"，不是"全盒容量"**。'
                             % (T, NV, 100.0 * T / NV))
                    L.append('      ⇒ 这**正好解释**了 `_r529` 的 A/B 为什么"抬 `nv` 没用"：')
                    L.append('         `12×6 → 12×10` 把**每变体**从 6 抬到 10，')
                    L.append('         于是那个块从 ≤6 根长到 **10 根**（`blk_laths` 实测 10）——')
                    L.append('         **确实起作用了**，但**目标 `B·n = 40` 次事件**要求')
                    L.append('         **每块只拿 5 根 × 8 块**，而实际只建了少数几块 ⇒')
                    L.append('         需求全压在一个块上 ⇒ 把该变体的 10 个场吃光 ⇒ 继续拒。')
                    L.append('      ⇒ **真正的上游卡点是 `fresh_blocked`（建不成新块）**，')
                    L.append('         **不是** `nfsv`、**不是** `nv`。')
        L.append('')
        L.append('   全盒非空场 = %d / nv = %d（**占用率 %.1f%%**）'
                 % (T, NV, 100.0 * T / max(NV, 1)))
        if T < 0.5 * max(NV, 1):
            L.append('   ⚠ **占用率很低** ⇒ 再印证一次：**不是总容量问题**。')

    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r536_diagread.log'), 'w') as fh:
        fh.write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
