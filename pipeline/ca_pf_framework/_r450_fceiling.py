#!/usr/bin/env python3
"""_r450_fceiling.py —— ★★★★ **转变分数 `f` 的可达范围**（v2：修掉单位错 + 更正"天花板"的说法）

## 自纠错（**自查错误 #69**）
v1 把 `vols`（**单位是 µm³**）当成 SI(m³) 又乘 `1e18` ⇒ 打出 2.5×10¹⁷ 的荒谬数。
**⇒ 这与 `_r436` 的 #56 是同一个量、同一个错**（我在 `_r436` 里**已经**记过
"`vols` 单位是 µm³"，本轮又犯）。
**⇒ 同一个 CSV 里两个体积列的进制不同**（`_r450 v2` 实测确认）：
  * `Vt`   = **SI (m³)**（如 `2.495117187500001e-19` = 0.2495 µm³）
  * `vols` = **µm³**（如 `0.249512`）
**⇒ 这条要写进量具清单，避免第三次。**

## 更正 v1 的"天花板"说法
v1 写 `f_max = nv·v_max/V_box` 并叫它"天花板" —— **不对**：
`v_max` 是**实测的已长体积**，板条还能继续长 ⇒ 那不是上限，是**下界**。
真正限制 `f` 的是 **impingement（互相撞上）**，本脚本**不算它**（要跑到才知道）。

## 本脚本改为给**三个可辩护的数**
  **f_seed** = `nv·v_seed/V_box`（**精确**，播种几何给定）
  **f_obs**  = 实测
  **f_extrap** = 按实测 `dVt/dstep` 外推到指定步数（**线性，未计 impingement 减速**）
并给 (N, nv) 的 `f_seed` 表 —— 它说明**目标第 ④ 项的"放大盒子"会压低 f**。
"""
import csv
import json
import os

import numpy as np

BASE = '_exp/_bk_mb'
ARMS = ['dry_abA', 'dry_abB']
DX = 62.5e-9
NREG_MAX = 127
V_SEED = (1000e-9) * (500e-9) * (510e-9)      # 单根播种体积 (m³)


def P(s):
    print(s, flush=True)


def parse_list(s):
    """`vols` 列：**斜杠分隔**、**单位 µm³**（`_r435`/`_r436` 实测）。"""
    if s is None:
        return []
    s = s.strip()
    if not s or s.lower() in ('none', 'nan'):
        return []
    for ch in '[],;':
        s = s.replace(ch, '/')
    out = []
    for tok in s.split('/'):
        tok = tok.strip()
        if tok:
            try:
                out.append(float(tok))
            except ValueError:
                pass
    return out


P('=' * 100)
P('_r450 v2 —— `f` 的可达范围（单位已修；"天花板"说法已更正）')
P('=' * 100)
P('\n[0] **单位记账（本轮实测确认，写进量具清单）**')
P('    `Vt`   = **SI (m³)**    例：`2.495117187500001e-19`')
P('    `vols` = **µm³**        例：`0.249512`   ← **两者不同进制！**')
P('    `ths`  = **nm**')

for tag in ARMS:
    p = os.path.join(BASE, tag, 'series.csv')
    mp = os.path.join(BASE, tag, 'meta.json')
    if not os.path.exists(p):
        P('\n[%s] ✗ 无 series.csv' % tag)
        continue
    m = json.load(open(mp)) if os.path.exists(mp) else {}
    N = int(m.get('N', 112))
    ea = m.get('exp_args', {})
    nv = len([x for x in str(ea.get('laths', '')).split(',') if x.strip()])
    L = N * DX
    Vbox = L ** 3
    rows = list(csv.DictReader(open(p, newline='')))
    vmax_um3, vtot_um3 = 0.0, 0.0
    st, vt = [], []
    chk_bad, chk_n = 0, 0
    for r in rows:
        v = parse_list(r.get('vols'))           # µm³
        if v:
            vmax_um3 = max(vmax_um3, max(v))
            vtot_um3 = max(vtot_um3, sum(v))
        try:
            st.append(int(float(r['step'])))
            _v = float(r['Vt'])                 # m³
            vt.append(_v)
        except (TypeError, ValueError):
            continue
        # ★ 单位自证：**逐行**比 `sum(vols)[µm³]·1e-18` 与同一行的 `Vt`[m³]
        #   ⚠ 自纠错（#70）：v2 第一版拿 `max(sum(vols))`（**某一行的最大值**）
        #     去比 `Vt[-1]`（**最后一行**）⇒ abA 报出 0.367 的假"口径不同"。
        #     **必须逐行比**。
        if v and _v > 0:
            chk_n += 1
            if abs(sum(v) * 1e-18 / _v - 1.0) > 0.05:
                chk_bad += 1
    st, vt = np.array(st), np.array(vt)
    f_seed = nv * V_SEED / Vbox
    f_obs = vt[-1] / Vbox
    P('\n[%s]  N=%d（盒 **%.1f µm³**）  nv=%d' % (tag, N, Vbox * 1e18, nv))
    P('   **f_seed**（精确，播种几何）= %d × %.4f µm³ / %.1f µm³ = **%.3f%%**'
      % (nv, V_SEED * 1e18, Vbox * 1e18, 100 * f_seed))
    P('   **f_obs** （末态实测）      = %.4f µm³ / %.1f µm³ = **%.3f%%**'
      % (vt[-1] * 1e18, Vbox * 1e18, 100 * f_obs))
    P('   ⇒ 已长到 `f_seed` 的 **%.2f×**' % (f_obs / max(f_seed, 1e-30)))
    P('   实测单根最大体积 = **%.4f µm³**（播种 %.4f）⇒ 长了 **%.1f×**'
      % (vmax_um3, V_SEED * 1e18, vmax_um3 / (V_SEED * 1e18)))
    P('   [单位自证·逐行] 可比 %d 行；相对差 >5%% 的 = **%d** ⇒ %s'
      % (chk_n, chk_bad,
         '✅ `sum(vols)·1e-18` 与 `Vt` 逐行同源' if chk_bad == 0
         else '⚠ 有 %d 行不同源' % chk_bad))
    if len(st) >= 6:
        k = max(3, len(st) // 4)
        slope = float(np.polyfit(st[-k:], vt[-k:], 1)[0])     # m³/步
        P('   末段 dVt/dstep（最后 %d 点）= **%.4e µm³/步**' % (k, slope * 1e18))
        for ftgt in (0.05, 0.10, 0.30):
            need = ftgt * Vbox - vt[-1]
            if slope > 0 and need > 0:
                P('      ⇒ 到 f=%.0f%% 还需 **%.0f 步**（线性外推，'
                  '**未计 impingement 减速**）' % (ftgt * 100, need / slope))
            else:
                P('      ⇒ f=%.0f%%：已达或斜率为负 ⇒ **不适用**' % (ftgt * 100))

P('\n' + '=' * 100)
P('[表] **`f_seed` 对 (N, nv)** —— 说明"放大盒子"会**压低** f')
P('=' * 100)
P('  %-6s %-9s %-11s %-13s %-13s %s'
  % ('N', '盒(µm)', '盒(µm³)', 'nv=24', 'nv=64', 'nv=126（int8 上限）'))
for N in (64, 80, 96, 112, 128, 160):
    L = N * DX
    V = L ** 3
    P('  %-6d %-9.2f %-11.1f %-13s %-13s %s'
      % (N, L * 1e6, V * 1e18,
         '%.2f%%' % (100 * 24 * V_SEED / V),
         '%.2f%%' % (100 * 64 * V_SEED / V),
         '%.2f%%' % (100 * 126 * V_SEED / V)))
P('')
P('  ⚠ `nreg = nv + 1 ≤ %d` ⇒ **nv ≤ %d**' % (NREG_MAX, NREG_MAX - 1))
P('  ⇒ 目标第 ④ 项说"把盒子放大到 ~10 µm（N=160）"：')
P('     在 nv=24 下，`f_seed` 由 N=112 的 **1.79%%** 掉到 N=160 的 **0.61%%**'
  '（降 **%.1f 倍**）' % ((160 / 112) ** 3))
P('  ⇒ **"放大盒子"与"提高转变分数"在固定 nv 下直接冲突** —— 必须记账。')
P('  ⇒ 想同时要"多块相互影响"与"高 f"，正确做法是**缩盒子 + 加场数**（nv ≤ 126）。')
P('=' * 100)
