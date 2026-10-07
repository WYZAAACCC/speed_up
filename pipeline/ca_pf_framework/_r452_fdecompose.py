#!/usr/bin/env python3
"""_r452_fdecompose.py —— ★★★★★ **`f` 低，到底卡在"根数不够"还是"每根太小"？**

## 用户的直接提问
> 当前的 f 不够，是因为**板条没有生长完全**，还是因为**单个板条体积过小**、
> 占盒子的体积过小？

## 把 `f` 拆成三个**互相独立**的因子（这样才回答得了）
    f = V_转变 / V_盒
      = [nv · v_seed / V_盒] · [n_present / nv] · [v̄_present / v_seed]
        └──── ①几何天花板 ────┘  └─ ②根数进度 ─┘  └── ③生长倍数 ──┘

* **① 几何天花板** = "如果 24 根全在场、且都只有播种大小"能占多少
  ⇒ 这一项**只由盒子与播种几何决定，与跑多久无关**。
  若它本身就只有 1.78%，那"单个板条相对盒子太小"就是**结构性**的。
* **② 根数进度** = 到目前实际形核了几根 / 应有几根 ⇒ **时间相关**。
* **③ 生长倍数** = 在场板条的平均体积 / 播种体积 ⇒ **时间相关**。

**⇒ 判读**：
  * 若 **① 已经很小** ⇒ **结构性**问题（盒子相对板条太大）⇒ **只能靠改盒子/加根数**；
  * 若 **① 不小，而 ② 或 ③ 远小于 1** ⇒ **只是还没长完** ⇒ **加时间有用**。
"""
import csv
import json
import os

import numpy as np

BASE = '_exp/_bk_mb'
ARMS = ['dry_abA', 'dry_abB']
DX = 62.5e-9
V_SEED = (1000e-9) * (500e-9) * (510e-9)      # 0.255 µm³


def P(s):
    print(s, flush=True)


def parse_list(s):
    """`vols`：**斜杠分隔**、**单位 µm³**。"""
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
P('_r452 —— `f` 的三因子分解')
P('=' * 100)
P('\n  f = [nv·v_seed/V_盒] × [n_present/nv] × [v̄_present/v_seed]')
P('       └─ ① 几何天花板 ─┘   └─ ② 根数进度 ─┘   └─ ③ 生长倍数 ─┘')
P('  v_seed = 1000×500×510 nm = **%.4f µm³**' % (V_SEED * 1e18))

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
    Vbox = (N * DX) ** 3
    f_ceil = nv * V_SEED / Vbox                       # ①
    rows = list(csv.DictReader(open(p, newline='')))

    P('\n' + '#' * 100)
    P('# %s   N=%d（盒 **%.1f µm³**）  nv=%d' % (tag, N, Vbox * 1e18, nv))
    P('#' * 100)
    P('  **① 几何天花板** = %d × %.4f / %.1f = **%.3f%%**'
      % (nv, V_SEED * 1e18, Vbox * 1e18, 100 * f_ceil))
    P('     （含义：**24 根全在场、且都只有播种大小**时的分数；与跑多久无关）')
    P('     单根占盒子的比例 = %.4f / %.1f = **%.4f%%**'
      % (V_SEED * 1e18, Vbox * 1e18, 100 * V_SEED / Vbox))
    P('     ⇒ 要把盒子填到 10%%，需要 **%.0f 根**（播种大小）'
      % (0.10 * Vbox / V_SEED))

    P('\n  %-7s %-9s %-10s %-11s %-11s %-11s %s'
      % ('step', 'Vt(µm³)', '在场根数', '②根数进度', '平均体积', '③生长倍数', 'f 实测'))
    last = None
    for r in rows:
        v = parse_list(r.get('vols'))
        try:
            vt = float(r['Vt']) * 1e18            # m³ → µm³
        except (TypeError, ValueError):
            continue
        if not v:
            continue
        pres = [x for x in v if x > 1e-9]
        npr = len(pres)
        vbar = float(np.mean(pres)) if pres else 0.0
        f2 = npr / nv
        f3 = vbar / (V_SEED * 1e18)
        f_obs = vt / (Vbox * 1e18)
        last = (int(float(r['step'])), vt, npr, f2, vbar, f3, f_obs)
        P('  %-7d %-9.4f %-10d %-11.3f %-11.4f %-11.3f %.4f%%'
          % (int(float(r['step'])), vt, npr, f2, vbar, f3, 100 * f_obs))

    if last:
        st, vt, npr, f2, vbar, f3, f_obs = last
        P('\n  【末态分解 @ step %d】' % st)
        P('    ① 几何天花板        = **%.3f%%**' % (100 * f_ceil))
        P('    ② 根数进度          = %d/%d = **%.3f**' % (npr, nv, f2))
        P('    ③ 生长倍数          = %.4f / %.4f = **%.3f**'
          % (vbar, V_SEED * 1e18, f3))
        P('    三因子乘积          = %.3f%% × %.3f × %.3f = **%.4f%%**'
          % (100 * f_ceil, f2, f3, 100 * f_ceil * f2 * f3))
        P('    实测 f              = **%.4f%%**' % (100 * f_obs))
        # 判读
        P('\n  【判读】')
        if f_ceil < 0.03:
            P('    ⚠ **① 本身就只有 %.2f%%** ⇒ **结构性**：盒子相对板条太大，'
              % (100 * f_ceil))
            P('       即使 24 根全长满播种尺寸也只有这么多。')
        P('    · ②=%.2f ⇒ %s' % (f2, '根数还没上来（**形核受限**）'
                                if f2 < 0.7 else '根数基本到位'))
        P('    · ③=%.2f ⇒ %s' % (f3, '每根**远未长完**（生长受限）'
                                if f3 < 0.7 else '每根已长过播种尺寸'))
        P('    ⇒ **结论**：%s'
          % ('两个都缺，但' +
             ('**根数**是主要短板' if f2 < f3 else '**生长**是主要短板')
             if (f2 < 0.7 and f3 < 0.7) else
             ('主要是**根数**没上来' if f2 < f3 else '主要是**生长**没完成')))
P('=' * 100)
