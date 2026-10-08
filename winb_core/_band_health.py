#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_band_health.py —— `W0-5`：把「界面带健康度」做成一等公民（**只读，零引擎改动**）

为什么必须做（依据 `W0-2/3` 的实测，`_w023.log`）
--------------------------------------------------
实测（N=96，Δx=50 nm，120 步）：

* 带内 `median|∇d2|`：**0.8953 → 0.6652**（退化 **26%**）；
* **全域** `median|∇d2|`：**恒为 0.9999**（几乎不动）；
* 全域 `max|∇d2|`：1.00 → **4.89**（⇒ 算子的伪时间步被压到 ≈20%）；
* `reinit` 触发 **4 次**，而退化曲线**完全单调光滑、无任何回弹** ⇒ **reinit 效果 ≈ 0**；
* **告警 0 次** —— 因为告警门槛是 `|_med−1| > 0.5`，而实测只到 `|0.665−1| = 0.335`。

⇒ **三个量（带内 `median|∇d2|`、全域 `median`、全域 `max`）原本一个都不出现在心跳里**，
唯一提到带内中位的**只有告警文案**，而且**门槛太高、漏报**。
**没有这三个量，就无法判断一次运行到底"健康不健康"** —— 这正是 `N1` 拖到现在才被发现的原因。

本模块提供什么
--------------
`health(g, ...)` —— 一次只读扫描，返回：

| 键 | 含义 | 为什么要报 |
|---|---|---|
| `med_d2` | **带内** `median\|∇d2\|`（引擎 `reinitialize()` 的口径） | **真正要紧的量**；应 ≈1 |
| `med_phi` | 带内 `median\|∇φ_win\|` | 与引擎自带"带健康 probe"对账 |
| `gm_all` | **全域** `median\|∇d2\|` | 算子的归一化门槛只看它 ⇒ 必须与 `med_d2` 并排看 |
| `gmax_all` | **全域** `max\|∇d2\|` | 驱动 `_dte` ⇒ **节流比** |
| `throttle` | `min(1, 1/max(gmax_all,1))` = `_dte/dtau` | **预测**伪时间步被压到多少 |
| `norm_on` | `\|gm_all−1\| > 0.2` | 算子**会不会**做全域归一化（实测恒为 False） |
| `nband` | 带胞数 | 带是否被撑大 |
| `bonds` | 界面键数（6 邻域跨界） | `P0-3` 的离散测度 |
| `rdone`/`rskip` | `reinit` 执行/跳过次数 | 跳过率 |
| `med_last` | 引擎内部最后一次 `_reinit_last_med` | 与 `med_d2` 对账 |

用法
----
    from _band_health import health, fmt
    h0 = health(g);  print('  baseline:', fmt(h0))
    ...
    if it % 20 == 0:
        print('       ' + fmt(health(g), base=h0), flush=True)

**开销**：用 `np.partition(...,1)` 取两个最小场（**不是 `argsort`**）+ 两次 `np.gradient`，
在 N=192 上实测远低于 `T16.stats()` 的 12 次 FFT，可安全放进每 20 步的心跳。

**记账**：本模块**只读**，不修改引擎、不改变任何数值；**`reinit_strict` 不在此处打开**
（理由见 `WINDOWB_ROADMAP_TO_CORRECT.md` W0-5：硬失败会中途杀掉小时级作业，
而 `reinit` 本身正要按 Gate A-1 处置 ⇒ 当前需要的是**信息**，不是中断）。
"""
import numpy as np


def health(g, band_cells=6.0, op_grad=True):
    """一次只读扫描，返回界面带健康度。见模块 docstring 的字段表。

    ★★ 2026-09-28 更正（本字段曾被自己人误用）：`throttle` 原用**中心差分**的全域 `max` 估算，
    实测**严重低估**算子的真实节流 —— `_probe_grad_fixpoint.py` 实测同一个新鲜场：
      中心差分全域 `max|∇d2|` = **1.00**   ← 旧口径据此报"节流 = 1.000（无节流）"
      而算子真正用的 `max(upwind_grad2)` = **68.5**  ← 真实节流 **0.0146**
    ⇒ 现在默认**同时**用算子自己的 `upwind_grad2` 算 `gmax_op` / `throttle_op`
      （`op_grad=False` 可关掉以省时；关掉时 `throttle_op` 为 `nan` 并**不得引用**）。
    """
    ph = g.phi
    dx = g.dx
    # 两个最小场：用 partition（O(n)）而不是 argsort（O(n log n)）—— 心跳要便宜。
    part = np.partition(ph, 1, axis=0)
    pha, phb = part[0], part[1]
    d2 = 0.5 * (pha - phb)

    gd2 = np.gradient(d2, dx)
    gd2n = np.sqrt(gd2[0] ** 2 + gd2[1] ** 2 + gd2[2] ** 2)
    gph = np.gradient(pha, dx)
    gphn = np.sqrt(gph[0] ** 2 + gph[1] ** 2 + gph[2] ** 2)

    near = np.abs(d2) <= band_cells * dx
    nb = int(near.sum())
    gmax = float(np.max(gd2n))
    gm_all = float(np.median(gd2n))

    # ---- 算子真实口径：`_gmax = max(upwind_grad2)`（`windowB_surface.py:203-210`）----
    #   ★★ 2026-09-28 更正（A-1 启用后）：算子现在**按 `self.reinit_band_cells` 决定统计量的域** ——
    #     `None` ⇒ 全域（旧行为）；`6.0` ⇒ **只在 `|φ| ≤ 6·dx` 的带内取 max**。
    #     所以本字段**必须跟着引擎的设置走**，否则会报出**算子根本不再使用**的那个数。
    #     （第一版在 A-1 启用后仍报全域 max ⇒ 把节流报成 2.4%，而算子实际用的是带内 max。）
    gmax_op = float('nan')
    _bc = getattr(g, 'reinit_band_cells', None)
    if op_grad:
        import sys as _sys
        _W = _sys.modules.get('windowB_surface')
        if _W is not None and hasattr(_W, 'upwind_grad2'):
            _S = d2 / np.sqrt(d2 ** 2 + dx ** 2)
            _gm2 = _W.upwind_grad2(d2, _S, dx)
            if _bc is None:
                gmax_op = float(np.max(_gm2))            # 旧行为：全域
            else:
                _sel = np.abs(d2) <= float(_bc) * dx     # 与引擎同一条件
                gmax_op = (float(np.max(_gm2[_sel])) if _sel.any()
                           else float(np.max(_gm2)))     # 空带 ⇒ 引擎会退回全域

    reg = g.region()
    bonds = 0
    for ax in range(3):
        bonds += int((reg != np.roll(reg, -1, axis=ax)).sum())
    _thr_cen = float(min(1.0, 1.0 / max(gmax, 1.0)))
    _thr_op = (float(min(1.0, 1.0 / max(gmax_op, 1.0)))
               if gmax_op == gmax_op else float('nan'))
    return dict(
        med_d2=float(np.median(gd2n[near])) if nb else float('nan'),
        med_phi=float(np.median(gphn[near])) if nb else float('nan'),
        gm_all=gm_all,
        gmax_all=gmax,
        throttle=_thr_cen,          # 旧口径（中心差分）—— **低估**，只作对照
        gmax_op=gmax_op,            # 算子真正用的那个
        throttle_op=_thr_op,        # ★ **应当引用的节流比**
        norm_on=bool(abs(gm_all - 1.0) > 0.2),
        nband=nb,
        bonds=bonds,
        rdone=int(getattr(g, '_reinit_done', 0)),
        rskip=int(getattr(g, '_reinit_skipped', 0)),
        med_last=getattr(g, '_reinit_last_med', None),
    )


def fmt(h, base=None):
    """紧凑单行。给了 `base` 就附带**相对基线的变化**（判据用"变化量"，不用水平值 —— `R4`/教训 #26）。"""
    _to = h.get('throttle_op', float('nan'))
    _go = h.get('gmax_op', float('nan'))
    s = ('[带健康] 带内med|∇d2|=%.4f  带内med|∇φ|=%.4f | 全域med=%.4f | '
         '算子上限=%s 节流(算子)=%s [中心口径 %7.2f→%.3f，**低估**] | 归一化=%s | '
         '带胞=%-7d 界面键=%-6d | reinit=%d/%d'
         % (h['med_d2'], h['med_phi'], h['gm_all'],
            ('%7.2f' % _go) if _go == _go else '   n/a ',
            ('%.4f' % _to) if _to == _to else ' n/a  ',
            h['gmax_all'], h['throttle'],
            'ON' if h['norm_on'] else 'off', h['nband'], h['bonds'],
            h['rdone'], h['rskip']))
    if base is not None:
        d_d2 = h['med_d2'] - base['med_d2']
        d_bd = (h['nband'] / max(base['nband'], 1) - 1.0) * 100.0
        d_bo = (h['bonds'] / max(base['bonds'], 1) - 1.0) * 100.0
        s += (' | Δ带内med=%+.4f  带胞%+.1f%%  界面键%+.1f%%' % (d_d2, d_bd, d_bo))
        # ★ 判据用**变化量**；节流用**算子口径**（中心口径会低估，实测 1.00 vs 68.5）。
        flags = []
        if d_d2 < -0.2:
            flags.append('⚠带内退化>0.2')
        if d_bd > 30.0:
            flags.append('⚠带胞膨胀>30%')
        if d_bo > 30.0:
            flags.append('⚠界面键膨胀>30%')
        if _to == _to and _to < 0.5:
            flags.append('⚠reinit节流(算子)=%.3f<0.5' % _to)
        if flags:
            s += '  ' + ' '.join(flags)
    return s
