#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_analyze.py --- ★ R1 实验台的结果分析（判据 C-1..C-6 + 增量速率）

判据（**先写死**，与 `_r1_exp.py` 的文档一致）
---------------------------------------------
| C-1 | 长轴与 `a` 的夹角 | ≤ 20° |
| C-2 | `L:W`（定标口径） | ≥ 3.0 |
| C-3 | `L:T`（定标口径） | ≥ 8.0 |
| C-4 | `W:T` | 报出 + `θ` 不确定度（文献 3.75，口径未知，只作参考）|
| C-5 | `fill_n` | ≥ 0.70（区分板条/板 与 纺锤/针）|
| C-6 | 界面 `|n·a|>0.9` 占比 | ≤ 25% |

★ `R20`：跨窗口的**速率**必须用**全样本最小二乘回归**，**不得**用端点差
  （端点差 ±1 胞的噪声地板会给出 26% 的散布）。
★ `R21`：必须报**逐方向每步增量的胞数**；任一分量 < 3 胞 ⇒ **结论 INCONCLUSIVE**。
★ `R23`：比值必须是**同一样品配对**的；必须标明估计量（ratio-of-means vs mean-of-ratios）。

用法：python3 _r1_analyze.py _exp/lath1 [更多目录...]
"""
import os
import sys
import csv
import glob
import json
import argparse

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('dirs', nargs='+')
ap.add_argument('--dx-nm', type=float, default=125.0)
ap.add_argument('--skip', type=int, default=0, help='前 N 步不计入回归（瞬态）')
ap.add_argument('--every', type=int, default=4,
                help='采样间隔；当 CSV 的 step 列为空（旧版 bug）时用它按行号重建步号')
ap.add_argument('--block', action='store_true',
                help='★ 多核算例的"块"判定：逐分量量具 + `nc` 合并判据（实验 4/5/6）')
a = ap.parse_args()
dx = a.dx_nm * 1e-9


def load(d):
    p = os.path.join(d, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = []
    with open(p) as f:
        for r in csv.DictReader(f):
            rows.append(r)
    if not rows:
        return None
    out = {}
    for k in rows[0].keys():
        v = []
        for r in rows:
            s = (r.get(k) or '').strip()
            try:
                v.append(float(s))
            except ValueError:
                v.append(np.nan)
        out[k] = np.array(v)
    return out


def reg(x, y, i0):
    """R20：全样本最小二乘（去掉前 i0 个点的瞬态）⇒ 斜率（m/步）。"""
    x = np.asarray(x[i0:], float)
    y = np.asarray(y[i0:], float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 5 or np.ptp(x[m]) <= 0:
        return np.nan, np.nan, 0
    A = np.vstack([x[m], np.ones(m.sum())]).T
    sol, res, *_ = np.linalg.lstsq(A, y[m], rcond=None)
    yh = A @ sol
    ss = 1.0 - np.sum((y[m] - yh) ** 2) / max(np.sum((y[m] - y[m].mean()) ** 2), 1e-30)
    return float(sol[0]), float(ss), int(m.sum())


print('=' * 108)
for d in a.dirs:
    S = load(d)
    print('\n### %s' % d)
    if S is None:
        print('   （没有 series.csv）')
        continue
    st = S['step']
    if not np.any(np.isfinite(st)):
        # 旧版 CSV 的 `step` 列被 NaN 覆盖（见 `_r1_exp.py` 的记账）⇒ 按行号重建
        st = np.arange(len(S['V']), dtype=float) * a.every
        print('   ⚠ CSV 的 `step` 列为空（旧版 bug）⇒ 按行号 × %d 重建' % a.every)
    n = len(st)
    last = n - 1
    # ★★ 判据修正（记账）：`fill_n`（CSV 里那列）用的是 **`+dx` 三口径的乘积**，
    #   而 `T` 的 `+dx` 在本变体上**高读 +48%** ⇒ `fill_n` 被系统性压低 32%
    #   （种子实测 fill_n = 0.621，而它**确实是**一个长方体，真值应为 1.000）。
    #   ⇒ 形态判据必须用**定标口径**的填充率 `fill_cal = V/(L_cal·W_cal·T_cal)`。
    with np.errstate(invalid='ignore', divide='ignore'):
        fill_cal = S['V'] / (S['L_cal'] * S['W_cal'] * S['T_cal'])
    print('   样本 %d 行，步 %d..%d；末态：V=%.4f µm³ 胞=%d  夹角=%.1f°  '
          '**fill_cal=%.3f**（CSV 里的 fill_n=%.3f，口径有偏）  ncomp=%d  gmed=%.3f'
          % (n, int(st[0]), int(st[-1]), S['V'][last] * 1e18, int(S['ncell'][last]),
             S['ang_a_deg'][last], fill_cal[last], S['fill_n'][last],
             int(S['ncomp'][last]), S['gmed'][last]))
    # 守卫汇总
    # ★ 记账（见台账 B-6）：`ncomp>1` **只对单核**是污染。多核臂里
    #   `ncomp` 从 `nseed` 递减到 1 正是"多个核 → 合并"的**目标现象**。
    #   ⇒ 先读 `meta.json` 的 `nseed` 决定怎么报，否则会把正常状态报成告警。
    nb = int(np.nansum(S['box_touch']))
    nh = int(np.nansum(S['band_bad']))
    nseed = None
    _mp = os.path.join(d, 'meta.json')
    if os.path.exists(_mp):
        try:
            with open(_mp) as _f:
                nseed = json.load(_f).get('nseed')
        except Exception as _e:                                  # noqa: BLE001
            print('   ⚠ 读不到 meta.json 的 nseed（%s）⇒ 按单核口径报守卫'
                  % type(_e).__name__)
    if nseed is not None and nseed > 1:
        nsig = S.get('nsig', np.full(n, np.nan))
        nsup = int(np.nansum((nsig > nseed).astype(float)))
        print('   守卫（**多核臂 nseed=%d**）：盒壁 %d 次；带病 %d 次；非有限 %d 次；'
              '`nsig>nseed` %d 次'
              % (nseed, nb, nh, int(np.sum(~np.isfinite(S['V']))), nsup))
        print('      （`ncomp` 中位 %.0f —— 多核下 >1 是**正常**的，不作为告警）'
              % np.nanmedian(S['ncomp']))
    else:
        ng = int(np.nansum((S['ncomp'] > 1).astype(float)))
        print('   守卫（单核）：盒壁 %d 次；分量>1 %d 次；带病 %d 次；非有限 %d 次'
              % (nb, ng, nh, int(np.sum(~np.isfinite(S['V'])))))
    if nb:
        i = int(np.argmax(S['box_touch'] > 0))
        print('   ⛔ G-1 首次触发于 step %d ⇒ **该步及之后的形貌读数无效**（R24）'
              % int(st[i]))

    i0 = max(a.skip, 0)
    i0 = min(i0, max(n - 6, 0))

    # ================= ★ 多核算例的"块"判定（实验 4/5/6）=================
    if a.block and np.any(np.isfinite(S.get('nc', np.array([np.nan])))):
        print('\n   --- ★ 块判定（逐分量量具，判据 B-1/B-2/B-3）---')
        nc = S['nc']                      # ← 第 8 轮补回：先前编辑误删了这一行
        ncs = nc[np.isfinite(nc)]
        # ★★ 记账（第 4 轮，**靠快照解剖抓到的判据 bug，连错两次**）：
        #   ①`nc`（分量数）**不能**当"合并没有"的判据 —— 水平集会**甩出微小液滴**
        #     （`_r1_snapinfo.py`：`e4` step125 = 6 个 ~650 胞大分量 + 18 个 1–13 胞碎屑；
        #      `e6` step125 = 1 个 4806 胞(96.9%) 大分量 + 50 个碎屑）。
        #   ②`big_frac`（最大分量占比）**同样不能单独用** —— 6 根**等大**的独立板条给
        #     `big_frac ≈ 1/6 = 0.167`，看上去像"83% 是碎屑"，其实那 83% 是另外 5 根板条。
        #   ⇒ **正确量具 = 按尺寸阈值筛"显著分量"**：`nsig` = 胞数 ≥1% 总分量的分量数
        #     （未合并 ⇒ 6；已合并 ⇒ 1），`debris` = <1% 分量占的总体积比。
        nsig = S.get('nsig', np.full(n, np.nan))
        nsv = nsig[np.isfinite(nsig)]
        if nsv.size:
            print('   **`nsig`（≥1%% 胞的显著分量数）：起始 %.0f → 末态 %.0f**'
                  % (nsv[0], nsv[-1]))
            hit = int(np.argmax(nsig <= 1)) if np.any(nsig <= 1) else -1
            if hit >= 0:
                print('   ⇒ ✅ **已合并**：`nsig` 于 **step %d** 首次降到 1' % int(st[hit]))
            else:
                print('   ⇒ ⚠ **未合并**：`nsig` 全程 >1 ⇒ 判据 B-2 **未通过**')
        db = S.get('debris', np.full(n, np.nan))
        dbv = db[np.isfinite(db)]
        if dbv.size:
            print('   Q-d 洁净度 **`debris`（碎屑体积占比）：末态 %.1f%%**（数值产物，须记账）'
                  % (100 * dbv[-1]))
        for tag, col in (('Lc', 'Lc'), ('Wc', 'Wc'), ('Tc', 'Tc')):
            sl, r2, nn = reg(st, S[col], i0)
            print('   逐分量中位 %-3s 速率 = %+8.4f nm/步  R²=%.4f (n=%d)  ⇒ %+5.2f 胞/步'
                  % (tag, sl * 1e9 if np.isfinite(sl) else float('nan'), r2, nn,
                     sl / dx if np.isfinite(sl) else float('nan')))
        slL, _, _ = reg(st, S['Lc'], i0)
        slW, _, _ = reg(st, S['Wc'], i0)
        slT, _, _ = reg(st, S['Tc'], i0)
        # ⚠ 记账：`bfv` 在第 8 轮我删 `big_frac` 段落时**被一起删掉了**，
        #   但下面还在引用它 ⇒ 分析器在 e4 上崩掉（`NameError`），
        #   进而让**自走驱动**在第 1 步就以 exit 1 退出（见 `R1_STAGE_REVIEW.md`）。
        #   教训与 `AGENTS §3.24` 同类：**删一段代码时要顺着引用往回查**。
        bf = S.get('big_frac', np.full(n, np.nan))
        bfv = bf[np.isfinite(bf)]
        # ⚠ `nc` 被碎屑污染时，逐分量中位也会被碎屑拉偏 ⇒ 只在 big_frac 高时信它
        if bfv.size and bfv[-1] < 0.90:
            print('   ⚠ `big_frac`=%.3f < 0.90 ⇒ **逐分量中位被碎屑污染**，'
                  '下面的 `Lc/Wc/Tc` 速率**仅供参考**' % bfv[-1])
        if np.isfinite(slL) and slL > 0:
            print('   ⇒ 逐分量 **ΔL:ΔW:ΔT = 1 : %.3f : %.3f**（设计 1 : %.3f : %.3f）'
                  % (slW / slL, slT / slL, np.exp(-2.3), np.exp(-3.5)))
        # B-1 平行性
        # ⚠ 本判据经历过两次修正，**两次都是"量具有问题"而不是物理**：
        #   ① 原来用「**全程最大**中位夹角 ≤20°」⇒ 被单个瞬态绑架
        #      （`e4_lath6` 起末态 0.11°/0.33°，却因某一步 = 90.00° 判不通过）
        #      ⇒ 改成**双条件**（末态 ≤20° 且 ≥50% 采样 ≤20°）。
        #   ② 台账 **B-17**：所用角度是 **PCA 主轴0**，而它在**两个最大奇异值近简并**时
        #      **没有定义**（SVD 在那个子空间里任选基）。实测 `e5_equi6` σ=[2631.6,2456.3,181.]
        #      ⇒ σ₂/σ₁=0.93，主轴0/1 给 83.48°/6.52°（**同一平面的两条轴**）；
        #      `e6_mid6` 的 B-1 因此判错，**重推后由"不通过(48%)"翻转为"通过(68%)"**。
        #   ⇒ 现在**优先**用 `align_span_deg`（"跨度最大的那条轴"，三标量取 argmax
        #     ⇒ **不依赖简并**，语义仍是"伸得最长的方向是不是 `a`"）；
        #     没有该列（旧算例）才退回 `align_deg`，并**显式标注口径**。
        if 'align_span_deg' in S and np.any(np.isfinite(S['align_span_deg'])):
            al_all = np.asarray(S['align_span_deg'], float)
            tag = 'align_span_deg（**跨度最大轴**，不依赖简并）'
        else:
            al_all = np.asarray(S['align_deg'], float)
            tag = ('align_deg（**PCA 主轴0** —— ⚠ 旧口径：近简并时无定义，见 B-17）'
                   if 'align_deg' in S else None)
        if tag is not None:
            mm_ = np.isfinite(al_all)
            if mm_.any():
                al = al_all[mm_]
                i_max = int(np.argmax(np.where(mm_, al_all, -np.inf)))
                frac20 = float(np.mean(al <= 20.0))
                last_al = float(al[-1])
                ok_b1 = (last_al <= 20.0) and (frac20 >= 0.5)
                print('   B-1 口径：%s' % tag)
                if 'align_span_deg' in S and np.any(np.isfinite(S['align_span_deg'])):
                    _verdict = '**通过**' if ok_b1 else '**不通过**'
                else:
                    # ⚠ 旧算例没有 `align_span_deg` ⇒ 只能退回**已被证伪**的 PCA 口径。
                    #   按"守卫要硬失败、不静默给数"的原则，这里**拒绝给判决**，
                    #   只报数字并指向重推脚本（否则读者会把作废的判决当当前的）。
                    _verdict = ('⏸ **判决暂缓**：本算例没有 `align_span_deg` 列，'
                                '只能用**已作废**的 PCA 口径（B-17）⇒ '
                                '请用 `_r1_b1fix.py %s` 重推'
                                % os.path.basename(os.path.normpath(d)))
                print('        中位长轴夹角：起始 %.2f° → 末态 %.2f°；'
                      '全程最大 %.2f°（step %g）；≤20° 的采样占比 %.0f%%  ⇒ %s'
                      % (al[0], last_al, al.max(), st[i_max], 100 * frac20,
                         _verdict))
                # 简并度（有新列才报）：告诉读者这一行的"主轴角"可不可信
                if 'align_degen' in S and np.any(np.isfinite(S['align_degen'])):
                    dg = np.asarray(S['align_degen'], float)
                    dgv = dg[np.isfinite(dg)]
                    if dgv.size:
                        print('        简并度 σ₂/σ₁：末态 %.3f ；**≥0.9 的采样占比 %.0f%%**'
                              '（这些点上 PCA 主轴角本无定义 ⇒ 旧口径会给出任选的角）'
                              % (float(dgv[-1]), 100 * float(np.mean(dgv >= 0.9))))
                print('        （双条件：末态 ≤20° **且** ≥50%% 采样 ≤20°）')
        # B-3 间距
        # ⚠ 记账（本轮）：`gap_w_nm` 在**早期算例**（`e4_lath6`/`e6_mid6`）里是坏的
        #   （漏乘 `dx`，报 1.2e10 nm = **12 米**）。`_r1_exp.py:273-278` 已记录该列无效。
        #   ⇒ 这里加**物理合理性守卫**：间距不可能超过盒子尺寸；超过就拒绝解读。
        if np.any(np.isfinite(S.get('gap_w_nm', np.array([np.nan])))):
            g = S['gap_w_nm'][np.isfinite(S['gap_w_nm'])]
            wc = S['Wc'][np.isfinite(S['Wc'])]
            if g.size and wc.size:
                wm = float(np.median(wc)) * 1e9          # ← 米 → nm
                # 盒子尺寸：优先用 meta 里的 `N · dx_nm`（真值），取不到才用兜底
                box_nm = 1e5
                if nseed is not None or os.path.exists(_mp):
                    try:
                        with open(_mp) as _f:
                            _m2 = json.load(_f)
                        _N = _m2.get('N') or _m2.get('Nx')
                        _dx = _m2.get('dx_nm') or a.dx_nm
                        if _N and _dx:
                            box_nm = float(_N) * float(_dx)
                    except Exception:                            # noqa: BLE001
                        pass
                if np.nanmax(np.abs(g)) > box_nm:
                    print('   B-3 ⛔ **该算例的 `gap_w_nm` 列无效**'
                          '（最大 %.3g nm = %.3g m，超过盒子 %.3g nm）'
                          '⇒ 早期版本漏乘 `dx`，**拒绝解读**；'
                          '如需此量请从 `snap_*.npz` 重算'
                          % (np.nanmax(np.abs(g)), np.nanmax(np.abs(g)) * 1e-9,
                             box_nm))
                else:
                    print('   B-3 相邻分量质心沿 `w` 间距：起始 %.0f nm → 末态 %.0f nm ；'
                          '逐分量宽度中位 %.0f nm ⇒ 间距/宽度 = %.2f'
                          % (g[0], g[-1], wm, g[-1] / max(wm, 1e-30)))
        print('   ⚠ 记账（**模型的结构性限制**）：本模型只有 12 个**离散**变体，'
              '**同变体**的两根板条接触即合并 ⇒ **块内部的低角晶界无法表示**。'
              '所以"块里有几根板条"**不可观测**；可观测的是'
              '"多个平行核 → 合并成一个沿 `a` 拉长的板"。')

    print('\n   --- 增量速率（R20 全样本回归，去掉前 %d 个采样）---' % i0)
    rates = {}
    for tag, col in (('L', 'L_cal'), ('W', 'W_cal'), ('T', 'T_cal'),
                     ('L(maxmin)', 'L'), ('W(maxmin)', 'W'), ('T(maxmin)', 'T'),
                     ('L(+dx)', 'Lb'), ('W(+dx)', 'Wb'), ('T(+dx)', 'Tb')):
        sl, r2, nn = reg(st, S[col], i0)
        rates[tag] = sl
        if tag in ('L', 'W', 'T'):
            print('   %-10s d/dt = %+9.4f nm/步   R²=%.4f  (n=%d)  ⇒ %+6.2f 胞/步'
                  % (tag, sl * 1e9 if np.isfinite(sl) else float('nan'),
                     r2, nn, sl / dx if np.isfinite(sl) else float('nan')))
    if all(np.isfinite(rates[t]) and rates[t] > 0 for t in ('L', 'W', 'T')):
        L, W, T = rates['L'], rates['W'], rates['T']
        print('   ⇒ **ΔL : ΔW : ΔT = 1 : %.3f : %.3f**（设计 1 : %.3f : %.3f）'
              % (W / L, T / L, np.exp(-2.3), np.exp(-3.5)))
        print('   ⇒ 相对设计的**倍率**：W 快 ×%.1f  T 快 ×%.1f'
              % ((W / L) / np.exp(-2.3), (T / L) / np.exp(-3.5)))
        # ★★ **碎片守卫**（第 2 轮记账）：`norm_smooth > 0` 的臂出现过 `ncomp>1`
        #   （最大到 3）。而 `L_cal` 用的是**全体胞**口径 ⇒ 卫星碎片会把 L 拉长。
        #   ⇒ 用 `L_big`（**最大连通分量**的跨度）做一次**独立**回归来交叉核对。
        # ⚠ **修 bug（本轮）**：这里原来写的是 `sb, r2b, nb = reg(...)`，
        #   而 `nb` 在上面已经被用作**盒壁计数**（`nb = int(np.nansum(S['box_touch']))`）
        #   ⇒ 这一行把盒壁计数**覆盖成回归的第三个返回值**（点数，恒为真）
        #   ⇒ 下面 `if nb:` 每次都会执行，打出
        #     「⛔ 但 G-1 已触发」**即使守卫汇总明明是"盒壁 0 次"**。
        #   实测证据：`_exp/mid192_ns4` 的汇总行写"盒壁 0 次"，紧跟着却报 G-1 已触发。
        #   ⇒ 改用独立名字 `npts_b`，**不再覆盖守卫计数**。
        sb, r2b, npts_b = reg(st, S['L_big'], i0)
        fb = float(np.nanmin(S['frac_big'])) if np.any(np.isfinite(S['frac_big'])) else float('nan')
        if np.isfinite(sb) and sb > 0:
            print('   ★ 碎片守卫：`L_big`（最大分量）回归 = %+.4f nm/步（R²=%.4f）'
                  ' ⇒ `ΔL:ΔW` = 1 : %.3f（全体口径给 %.3f）；`frac_big` 最小 %.3f'
                  % (sb * 1e9, r2b, (W / sb), (W / L), fb))
            if abs((W / sb) - (W / L)) > 0.25 * (W / L):
                print('      ⚠ **全体口径与最大分量口径差 >25%% ⇒ 形貌读数被碎片污染，低置信度**')
        # ⚠ 记账（本轮）：`frac_big < 0.95 ⇒ 分裂过` 这个判据**只对单核成立**。
        #   多核臂放了 `nseed` 个同变体核 ⇒ `frac_big ≈ 1/nseed`
        #   （实测 `e4_lath6`/`e6_mid6` 的 `frac_big` 最小 **0.165–0.168 ≈ 1/6**），
        #   这正是"6 个等大核"的**预期值**，却被报成「过程中确实分裂过」。
        #   ⇒ 多核口径：`frac_big` 应与 `1/nseed` 同量级；只有**显著低于** `1/nseed`
        #     （例如 < 0.3/nseed）才提示有多余碎片。
        if fb < 0.95:
            if nseed is not None and nseed > 1:
                exp_fb = 1.0 / nseed
                if fb < 0.3 * exp_fb:
                    print('      ⚠ `frac_big` 最小 %.3f，**远低于** 1/nseed=%.3f '
                          '⇒ 有多余的微小分量' % (fb, exp_fb))
                else:
                    print('      （`frac_big` 最小 %.3f ≈ 1/nseed=%.3f —— '
                          '**多核下的预期值**，不是分裂）' % (fb, exp_fb))
            else:
                print('      ⚠ `frac_big` 最小值 %.3f < 0.95 ⇒ 过程中确实分裂过' % fb)
        # R21：逐方向胞数（**整段**的净增量，不是每步）
        dL = (S['L_cal'][last] - S['L_cal'][0]) / dx
        dW = (S['W_cal'][last] - S['W_cal'][0]) / dx
        dT = (S['T_cal'][last] - S['T_cal'][0]) / dx
        print('   R21 **整段净增量**：ΔL=%.2f 胞  ΔW=%.2f 胞  ΔT=%.2f 胞'
              % (dL, dW, dT))
        if min(dL, dW, dT) < 3.0:
            print('   ⚠ **R21：有分量净增量 < 3 胞 ⇒ 速率比 INCONCLUSIVE**'
                  '（离散噪声地板 ±0.5 胞；要拉长总时长或加密网格）')
            print('      ⚠ 特别地：**厚度方向** ΔT=%.2f 胞 ⇒ 本轮的 T 相关比值一律低置信度'
                  % dT)
    else:
        print('   ⚠ 速率回归无效（样本太少或全为 nan）')

    # 判据
    print('\n   --- 判据（先写死，再看数）---')
    if a.block:
        print('   ⚠ **多核算例：下面这套 C-1..C-6 用的是"全部胞当一个对象"的口径**'
              '（即整列的 Span/PCA），对多核**没有意义**（实测夹角 90°、W=8442 nm）。'
              '多核请看上面的 **§块判定**。')
    lastv = last
    LW = S['LW_cal'][lastv]
    LT = S['LT_cal'][lastv]
    WT = S['WT_cal'][lastv]
    ang = S['ang_a_deg'][lastv]
    fc = fill_cal[lastv]
    fa = S['f_a'][lastv]
    print('   ⚠ **遗传性判据**：`L:W`/`L:T` 的**绝对**值有一部分是**种子形状**带来的')
    print('     （种子 LW=%.2f LT=%.2f）⇒ 单看绝对值**不能**证明"长成了板条"；' % (
        S['LW_cal'][0], S['LT_cal'][0]))
    print('     **必须**同时看上面的**速率比**与下面的**增量**。')
    tests = [('C-1 长轴与 a 夹角 ≤20°', ang <= 20.0, '%.1f°' % ang),
             ('C-2 L:W ≥ 3.0', LW >= 3.0, '%.2f' % LW),
             ('C-3 L:T ≥ 8.0', LT >= 8.0, '%.2f' % LT),
             ('C-4 W:T（报出，无靶）', True, '%.2f' % WT),
             ('C-5 fill_cal ≥ 0.70', fc >= 0.70, '%.3f' % fc),
             ('C-6 |n·a|>0.9 占比 ≤25%', fa <= 0.25, '%.1f%%' % (100 * fa))]
    npass = 0
    for name, okv, val in tests:
        print('     %-30s %-6s  实测 %s' % (name, 'PASS' if okv else 'FAIL', val))
        npass += int(okv)
    print('   ⇒ **%d/6 通过**' % npass)
    if nb:
        print('   ⛔ 但 G-1 已触发 ⇒ 上面的 L/W/T 与比值**不可作为形态结论**')
print('\n' + '=' * 108)
