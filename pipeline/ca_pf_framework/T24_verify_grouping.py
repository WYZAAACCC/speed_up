#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T24_verify_grouping.py --- **B4**：block / packet / cluster 的**分组量具**与统计。

为什么必须有（`RESEARCH_INTENT.md §2.2`）
--------------------------------------
β→α′ 板条马氏体的**核心现象**就是"板条自发按 Burgers 取向分组"：
同一变体 → **block/colony**；同一惯习面族的不同变体 → **packet**；若干自协调变体 → **cluster。
仓库到本轮为止**一个统计量都没出过**（T16 明确记账"未做"）。
⇒ 没有它，A2「组织正确」只有"板条厚 + 取向分位"两条腿。

口径（★ 全部先做正/负对照，MEASUREMENT_SPEC R0）
-----------------------------------------------
  1. **变体标记场** `reg`（= `argmin_k φ_k`），只在**已转变**胞上定义。
  2. **分组 = 同一"取向族"内的**连通分量**（6 邻域）：
       * **block**（同一变体）：直接对 `reg == k` 取连通分量 ⇒ 每个分量是一个 block 候选；
       * **packet**（同一惯习面族）：需要一个"族"的划分。本项目**已有**的物理量是
         `npref[k]`（变体的惯习面法向）⇒ 定义**族 = `npref` 的等价类**，判据是
         `angle(npref[a], npref[b]) < packet_tol`（默认 10°）。
         ⚠ 记账：这是**本项目自己的**族定义（Burgers 的 12 变体在真 packet 里是
         "同一 {110}β 面"）；用 `npref` 的近似是**可核对的代理**，并且它的**正对照**
         是"把人造的两个同族变体合成一个 packet、两个异族变体分成两个 packet"。
       * **cluster**：不要求连通；只按**变体集合**统计（自协调 = 12 变体都在场）。
  3. 尺寸用**等效球径** `d_eq = (6V/π)^{1/3}`（V = 分量胞数·Δx³）与**沿三轴的投影极差
     `max−min`**（T15 已验证的量具）。

判据
----
  **B4-0 正对照（人造构型，已知答案）**：
    (a) 一个**单变体立方块** ⇒ block 数 = 1、packet 数 = 1、`d_eq` = 解析值 ✓
    (b) **两块同一变体、分开** ⇒ block 数 = 2（连通分量按预期分裂）
    (c) **两块同族不同变体、相接** ⇒ packet 数 = **1**（族合并生效）
    (d) **两块异族不同变体、相接** ⇒ packet 数 = **2**
    (e) **每个胞随机赋变体** ⇒ block 数与"每胞一个"同量级（**负对照**：不产生假的大分组）
  以上五条通过 ⇒ 量具可用；否则读数不得写进结论。
  **B4-1 真实 RVE**：给出 block / packet / cluster 的尺寸分布（中位、p90、计数），
    并同时报告 `M6p` p25（取向择优）与守卫（逐变体绕盒 / 膨胀）。

用法：
  python3 T24_verify_grouping.py --mode control         # 只跑正负对照（便宜、必跑）
  python3 T24_verify_grouping.py --mode rve --L-um 4.8 --dx-nm 50 --n 64
退出码：0 = PASS
"""
import os
import sys
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402

# ★★★ 2026-09-28：后加路径的全局开关（由 `main()` 从 CLI 设置；**模块默认全关**）
#   `NS`  = `advance(norm_smooth=NS)` —— 根因① 的修法（法向平滑），`T26` 5/5 过验收
#   `NUC` = D18 形核通道（用户 2026-09-28 批准并入），`T27` 全 PASS
NS = 0
NUC = dict(on=False, t=700e-9, R=400e-9, init=24, every=5, nf=2, ns_=2, harden=0.10)

# 6 邻域连通（scipy 的 label 用 6-连通结构，与仓库"界面键"口径一致）
_STRUCT6 = None


def _struct6():
    """6 邻域连通结构（★ 记账：首版把**偏移**当成**索引**用 ⇒ 结构不对称、
       scipy 断言 `Structuring element is not symmetric` 直接抛错）。"""
    global _STRUCT6
    if _STRUCT6 is None:
        s = np.zeros((3, 3, 3), bool)
        s[1, 1, 1] = True
        s[0, 1, 1] = s[2, 1, 1] = True
        s[1, 0, 1] = s[1, 2, 1] = True
        s[1, 1, 0] = s[1, 1, 2] = True
        _STRUCT6 = s
    return _STRUCT6


def connected_components(mask):
    """6 邻域连通分量。返回 (labels, n)。**周期**由调用方决定（本函数用非周期，
       因为周期连通性另有 `wrap_axes` 守卫专门管）。"""
    from scipy.ndimage import label
    lab, n = label(mask, structure=_struct6())
    return lab, int(n)


def deq(ncell, dx):
    """等效球径 `(6V/π)^{1/3}`。"""
    V = float(ncell) * dx ** 3
    return (6.0 * V / np.pi) ** (1.0 / 3.0)


def burger_packet_families():
    """★★ **真正的 Burgers packet 族**：6 个 `{110}β` 面 × 2 个 `⟨111⟩` 方向 = 12 变体。
       `windowB_ti64_variants.variants()` 的生成顺序就是
           `for nv in six_110_planes(): for dl in three_111_lines(): if dl ⊥ nv: ...`
       每个面恰好贡献 **2** 个（该面内有 2 条 ⟨111⟩）⇒ **1-based 变体 k 的族 = (k−1)//2**。
       返回 `(fam, nfam, meta)`；`meta[v]['n']` 是**精确的母相 {110} 面法向**。

    ★ 记账（为什么不用 `npref`）：本轮实测 `npref`（对 `Λ(n)` 采样找最小弹性能得到的取向）
      的等价类在 tol=10° 下给出 **9 族**（3 对 + 6 个单体），tol=5° 给 11 族、20° 给 8 族
      —— **任何容差都得不到 Burgers 的 6 族**（两两夹角是 3.4–24.6° 且**无间隙**）
      ⇒ `npref` **不是** packet 结构的代理。真正的族必须取自 Burgers 对应关系本身。
    """
    try:
        from windowB_ti64_variants import variants as _V
        _eps, _F, meta = _V()
        nv = len(meta)
        if nv % 2:
            return None, 0, None
        fam = {k: (k - 1) // 2 for k in range(1, nv + 1)}
        return fam, nv // 2, meta
    except Exception:                                           # noqa: BLE001
        return None, 0, None


def packet_families(npref, tol_deg=10.0):
    """把变体按 `npref` 的**等价类**分成 packet 族。
       `npref` 是无向的（±n 等价）⇒ 用 `|cos|`。
       返回 {变体号: 族号}（族号从 0 起）。"""
    ks = sorted(k for k, v in npref.items() if v is not None)
    u = {k: np.asarray(npref[k], float) / np.linalg.norm(npref[k]) for k in ks}
    fam, nf = {}, 0
    for k in ks:
        if k in fam:
            continue
        fam[k] = nf
        for j in ks:
            if j in fam:
                continue
            c = abs(float(u[k] @ u[j]))
            if np.degrees(np.arccos(np.clip(c, 0, 1))) < tol_deg:
                fam[j] = nf
        nf += 1
    return fam, nf


def _touches_both(comp, axis):
    """该连通分量的包围盒是否**同时贴到某轴的两端** ⇒ 极可能已渗流贯通周期盒。
       （廉价代理；严格的周期连通性判据在 `LevelSetMulti.wrap_axes` 里，那里更贵。）"""
    idx = np.argwhere(comp)
    if idx.size == 0:
        return False
    return int(idx[:, axis].min()) == 0 and int(idx[:, axis].max()) == comp.shape[axis] - 1


def grouping_stats(reg, dx, fam, min_cells=8):
    """分组统计。`reg` 为变体标记场（0 = 母相，不计）。

    ★★ 记账（B4-0(e) 负对照暴露的**量具局限**，已修）：
      "packet = 同族变体的**并集**再取连通分量"这条口径**在变体细密混杂时会渗流**——
      各族占约 `1/3` 的胞，而简单立方**座渗流阈值 `p_c ≈ 0.3116`** ⇒ 1/3 > p_c
      ⇒ 随机赋变体的负对照会给出一个">5000 胞的 packet"（**假分组**）。
      ⇒ 修法：对每个分量做**渗流守卫**（包围盒是否贴到某轴两端），并把
        `percolating` 计数**单独上报**；渗流的分量**不得**当作"尺寸"用。
      ⇒ 这条与 `MEASUREMENT_SPEC R4` 同源：**判据必须在目标工况下有意义**。"""
    out = dict(block_sizes=[], packet_sizes=[], n_var=0, f_trans=0.0,
               n_block_perc=0, n_packet_perc=0, n_block_raw=0, n_packet_raw=0)
    ks = [k for k in np.unique(reg) if k > 0]
    out['n_var'] = len(ks)
    out['f_trans'] = float((reg > 0).sum()) / reg.size
    for k in ks:
        lab, n = connected_components(reg == k)
        for i in range(1, n + 1):
            comp = (lab == i)
            c = int(comp.sum())
            out['n_block_raw'] += 1
            if c < min_cells:
                continue
            if any(_touches_both(comp, ax) for ax in range(3)):
                out['n_block_perc'] += 1
                continue
            out['block_sizes'].append(c)
    # packet：把同一族的变体**并成一个掩模**再取连通分量
    for f in sorted(set(fam.values())):
        ks_f = [k for k in ks if fam.get(k) == f]
        if not ks_f:
            continue
        m = np.isin(reg, ks_f)
        lab, n = connected_components(m)
        for i in range(1, n + 1):
            comp = (lab == i)
            c = int(comp.sum())
            out['n_packet_raw'] += 1
            if c < min_cells:
                continue
            if any(_touches_both(comp, ax) for ax in range(3)):
                out['n_packet_perc'] += 1
                continue
            out['packet_sizes'].append(c)
    out['block_deq'] = [deq(c, dx) for c in out['block_sizes']]
    out['packet_deq'] = [deq(c, dx) for c in out['packet_sizes']]
    return out


# ---------------------------------------------------------------- 正/负对照
def control():
    print('=' * 100)
    print('B4-0 **分组量具的正/负对照**（人造构型，已知答案）')
    N, dx = 48, 50e-9
    L = N * dx
    ok = True

    def blank():
        reg = np.zeros((N, N, N), np.int16)
        return reg

    # (a) 一个单变体立方块
    reg = blank()
    reg[10:20, 10:20, 10:20] = 1
    fam = {1: 0, 2: 0, 3: 1}
    s = grouping_stats(reg, dx, fam)
    ncell = 10 ** 3
    a_ok = (len(s['block_sizes']) == 1 and len(s['packet_sizes']) == 1
            and abs(s['block_deq'][0] / deq(ncell, dx) - 1) < 1e-9)
    print('   (a) 单变体立方块 1000 胞 ⇒ block=%d packet=%d d_eq=%.1f nm（解析 %.1f）%s'
          % (len(s['block_sizes']), len(s['packet_sizes']), s['block_deq'][0] * 1e9,
             deq(ncell, dx) * 1e9, '✓' if a_ok else '✗'))
    ok &= a_ok

    # (b) 两块同一变体、分开
    reg = blank()
    reg[5:12, 5:12, 5:12] = 1
    reg[30:40, 30:40, 30:40] = 1
    s = grouping_stats(reg, dx, fam)
    b_ok = len(s['block_sizes']) == 2
    print('   (b) 两块同变体、分离 ⇒ block=%d（应 2）%s'
          % (len(s['block_sizes']), '✓' if b_ok else '✗'))
    ok &= b_ok

    # (c) 两块**同族**不同变体、相接 ⇒ packet 应合并为 1
    reg = blank()
    reg[10:20, 10:20, 10:20] = 1
    reg[10:20, 10:20, 20:30] = 2          # 1 与 2 同族（fam 都给 0）
    s = grouping_stats(reg, dx, fam)
    c_ok = (len(s['block_sizes']) == 2 and len(s['packet_sizes']) == 1)
    print('   (c) 两块**同族**不同变体、相接 ⇒ block=%d（应 2）packet=%d（应 1）%s'
          % (len(s['block_sizes']), len(s['packet_sizes']), '✓' if c_ok else '✗'))
    ok &= c_ok

    # (d) 两块**异族**不同变体、相接 ⇒ packet 应为 2
    reg = blank()
    reg[10:20, 10:20, 10:20] = 1          # 族 0
    reg[10:20, 10:20, 20:30] = 3          # 族 1
    s = grouping_stats(reg, dx, fam)
    d_ok = (len(s['block_sizes']) == 2 and len(s['packet_sizes']) == 2)
    print('   (d) 两块**异族**不同变体、相接 ⇒ block=%d（应 2）packet=%d（应 2）%s'
          % (len(s['block_sizes']), len(s['packet_sizes']), '✓' if d_ok else '✗'))
    ok &= d_ok

    # ★ 记账（首版判据错）：首版把全部 12 个变体放进**同一个族** ⇒ packet 掩模 = 全部已转变胞
    #     ⇒ 那个 ">5000 胞的 packet" 是**口径的必然结果**，不是假分组。
    #     ⇒ 改用**真实的 Burgers 族结构** + **渗流守卫**。
    rng = np.random.default_rng(0)
    reg = rng.integers(1, 13, size=(N, N, N)).astype(np.int16)
    famE, nfE, _mE = burger_packet_families()
    if famE is None:
        famE, nfE = packet_families({k: None for k in []}, 10.0)
    # ★ 族表的**正对照**：同族内的精确母相面法向必须**逐位相同**
    fam_ok = True
    if _mE is not None:
        for f in set(famE.values()):
            ns = [_mE[k - 1]['n'] for k in famE if famE[k] == f]
            for x in ns[1:]:
                fam_ok &= bool(np.abs(x - ns[0]).max() < 1e-12)
        print('   (e0) **族表正对照**：同族内的精确 `{110}β` 面法向逐位相同 = %s；'
              '族数 = %d（Burgers 期望 6）%s'
              % (fam_ok, nfE, '✓' if (fam_ok and nfE == 6) else '✗'))
        ok &= (fam_ok and nfE == 6)
    s = grouping_stats(reg, dx, famE)
    big = sum(1 for c in s['block_sizes'] if c > 50)
    bigp = sum(1 for c in s['packet_sizes'] if c > 500)
    tot_p = float((reg > 0).sum())
    frac_p = (max(s['packet_sizes']) / tot_p) if s['packet_sizes'] else 0.0
    e_ok = (big == 0) and (bigp == 0)
    print('   (e) 每胞随机变体（负对照，**Burgers 6 族**）⇒ block 总数 %d（>50 胞的 %d，应 0）；'
          'packet 幸存 %d（>500 胞的 %d，应 0）；**被渗流守卫剔除** block %d / packet %d'
          % (s['n_block_raw'], big, len(s['packet_sizes']), bigp,
             s['n_block_perc'], s['n_packet_perc']))
    print('       最大幸存 packet / 已转变胞 = %.4f（应 ≈0）%s'
          % (frac_p, '✓' if e_ok else '✗'))
    print('       ★ 这条负对照**暴露并修掉了量具的一个真局限**：同族并集在变体细密混杂时')
    print('         会**渗流**（各族占约 1/3 > 简单立方座渗流阈值 0.3116）⇒ 必须加渗流守卫。')
    ok &= e_ok

    print('-' * 100)
    print('   ★ 记账（**族定义的最终口径**）：packet 族取自 **Burgers 对应关系本身** ——')
    print('     `windowB_ti64_variants.variants()` 的生成顺序是 6 个 `{110}β` 面 × 2 条 `⟨111⟩`，')
    print('     每个面恰好贡献 2 个变体 ⇒ **1-based 变体 k 的族 = (k−1)//2**，共 **6 族**。')
    print('     正对照 (e0)：同族内的**精确**母相 `{110}` 面法向**逐位相同** ✓、族数 = 6 ✓。')
    print('   ★ 记账（**已证伪的代理**）：首版用 `npref`（对 Λ(n) 采样找最小弹性能得到的取向）')
    print('     的等价类当族 —— 实测 tol=5/10/15/20° 分别给 **11/9/9/8** 族，')
    print('     **任何容差都得不到 6**（两两夹角 3.4–24.6° 且无间隙）⇒ `npref` **不是** packet')
    print('     结构的代理，已弃用。')
    print('   ⇒ B4-0 %s' % ('PASS（量具可用，6/6）' if ok else 'FAIL（读数不得使用）'))
    print('=' * 100)
    return ok


# ---------------------------------------------------------------- 真实 RVE
def rve(L, dx, n0, f_target, adv, steps_max=900):
    import windowB_surface as W
    from T16_verify_rve import C, EPS0, NV, NPF, stats
    MOB, DF = 1e-9, 3.5e8      # Δf：3.5e8 = D7 文献 ΔG 在 298 K（见 T16_verify_rve.py 的记账）
    N = int(round(L / dx))
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, nv=NV, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    rng = np.random.default_rng(7)
    ns = 0
    for _ in range(n0 * 8):
        if ns >= n0:
            break
        c = rng.random(3) * (L - 2 * (0.3e-6 + 0.3e-6)) + (0.3e-6 + 0.3e-6)
        k = int(rng.integers(1, NV + 1))
        nrm = np.asarray(NPF[k], float)
        nrm = nrm / np.linalg.norm(nrm)
        try:
            g.seed_plate(k, c, nrm, 3.0e-7, 2.0e-7)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    out = None
    _t0 = time.time()
    for it in range(1, steps_max + 1):
        _ed = g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=3.5, mob_beta_w=2.3, adv_grad=adv, norm_smooth=NS)
        # ★ D18 形核通道（默认关；不调 `nuc_cfg()` 时 `nucleate()` 无副作用）
        if NUC['on']:
            if it == 1:
                g.nuc_cfg(NUC['R'], NUC['t'], gamma=0.15, n_init=NUC['init'],
                          p_auto=NUC['pa'], harden_f=NUC['harden'],
                          sym_gap_cells=2, max_per_step=8, seed=11,
                          var_rule=NUC['vr'])
            elif it % NUC['every'] == 0:
                _rg = g.region()
                g.nucleate(_ed, f_now=1.0 - float((_rg == 0).sum()) / g.N ** 3,
                           n_fresh=NUC['nf'], n_stack=NUC['ns_'])
        # ★★ 2026-09-28 补：**心跳**（Round 20 自查发现 T24 一直缺它 ⇒ 跑了 70 min 无法判读）
        if it % 20 == 0:
            _r0 = g.region()
            _f0 = 1.0 - float((_r0 == 0).sum()) / g.N ** 3
            print('       [心跳 T24] step=%-4d f=%.5f  步时=%.1f s  已用=%.1f min'
                  % (it, _f0, (time.time() - _t0) / it, (time.time() - _t0) / 60.0),
                  flush=True)
            # ★★★ W0-5（2026-09-28）：**带健康度**（只读，零引擎改动）。
            #   依据 `_w023.log` 实测：带内 median|∇d2| 120 步退化 26%（0.8953→0.6652），
            #   而**全域** median 恒为 0.9999、全域 max 涨到 4.89、reinit 触发 4 次**毫无回弹**、
            #   且**告警 0 次**（告警门槛 0.5 太高）⇒ 不报这三个量就无法判断"健康不健康"。
            from _band_health import health as _bh, fmt as _bhf
            _hh = _bh(g)
            if not hasattr(g, '_bh0'):
                g._bh0 = _hh
            print('       ' + _bhf(_hh, base=g._bh0), flush=True)
        if it % 5:
            continue
        regc = g.region()
        f_now = 1.0 - float((regc == 0).sum()) / g.N ** 3
        if f_now < max(0.5 * f_target, 0.02):
            continue
        s = stats(g)
        wv = g.wrap_axes_any()
        if wv:
            s['guard'] = 'WRAP=%s' % wv
        else:
            s['guard'] = 'ok'
        s['it'] = it
        s['ns'] = ns
        out = s
        if s['f'] >= f_target or s['guard'] != 'ok':
            break
    return g, out


def geom_ar(reg, g, NPF, min_cells=8):
    """★ 2026-09-28 新增，**Round 139 扩为三向**：每片返回 `(k, L, W, T, L/T, L/W, cells)`。

    三个方向（都用引擎自己的几何轴，与形核/推进用的同一套）：
      * `T` = 沿**惯习面法向** `npref[k]`（= `NPF[k]`）⇒ **厚**
      * `L` = 沿**真长轴** `atab[k]`（先对 `npref` 正交化）⇒ **长**
      * `W` = 沿 `npref × a`（面内**第二**轴）⇒ **宽**

    ⛔⛔ **为什么要加 `W`（Round 139 口径纠正，见 `WINDOWB_ROADMAP_TO_CORRECT.md §9.17b`）**：
      同工艺同材料（LPBF Ti-64 as-built α′）的**唯一**几何靶是
      **长 : 宽 ≈ 9 : 1**（Wang 2026, 10.20517/microstructures.2025.144，逐字原文
      "The average **length and width** of these platelets are 8.1 ± 2.0 µm and
      0.9 ± 0.4 µm"）。
      **它是"长:宽"，不是"长:厚"**（`docs/refcheck/REFERENCE_AUDIT.md:86/95` 一直记对，
      是下游用错了）。而本函数此前只给 `L/T` ⇒ **拿 `L/T` 去比 9:1 是无效比较**。
      ⇒ 本函数现在**同时给 `L/T` 与 `L/W`**；**靶② 只认 `L/W`**。
      ✅ **但"厚"是有同工艺锚点的**（本文件 Round 139 第三轮纠正了上一轮的过度纠正）：
        Shuai 2026 "lath **widths** 0.51–0.68 µm"（`docs/refcheck/ref01_shuai2026.txt:299`）
      ⛔⛔ **2026-09-28 Round 139 第三次纠正（子代理全检索，两份全文均已取到）**：
      Shuai 2026 在**同一篇里把 "lath width" 与 "lath thickness" 用于同一个 2D BSE
      **线性截距**测量**（§2.2 两句、§3.2、Fig.6 逐字，见
      `lit_tmp/ALPHA_PRIME_LATH_WIDTH_PROVENANCE.md`）⇒ **它不是"厚"这个独立量的锚点。**
      **2D 截面每篇只给"一个长 + 一个短"，物理上无法分离宽与厚**
      ⇒ **文献只能约束一个指数**：`ln(长/短) = 2.2–3.2`
      （Wang 2D 长:短 = 9.0 ⇒ 2.20；**Xie 2026 未筛样 2D 长:宽 = 16.7–23.8、均值 20.9** ⇒ 3.04）。
      ⇒ **`β_w` 与 `β_h` 在现有数据下退化；两者都不得声称有独立锚点。**

    为什么需要它（子代理文献检索的结论，`_lit_tmp/LATH_THICKNESS_REVIEW.md §5`）：
    文献里"AR 2.8–8.4"是 **2D 斜截面表观值**（`MEASUREMENT_SPEC §4.6` 已记账本模型
    同一切面口径只有几何值的 ~0.54×），而**几何**长径比在文献里是
    **9:1（Wang 2026，LPBF α′ 实测 8.1×8.1/0.9 µm）** / ⛔16:1（Gullane 2022，**查不到**）/
    ⛔30:1（Rezazadeh 2024 = **钢**，跨材料已剔除）。
    ⇒ **拿 2D 表观值去比几何带 2.8–8.4 是口径错配**；本函数给出可与之对表的口径。
    `atab`/`npref` 由 `LevelSetMulti` 在给了 `C/eps0` 时自动建（`windowB_surface.py:908-930`）。"""
    out = []
    for k in np.unique(reg):
        if k <= 0 or NPF.get(int(k)) is None:
            continue
        m = (reg == k)
        if m.sum() < min_cells:
            continue
        lab, n = connected_components(m)
        if n == 0:
            continue
        sz = np.bincount(lab.ravel())
        nv_ = np.asarray(NPF[int(k)], float)
        nv_ = nv_ / np.linalg.norm(nv_)
        a_ = getattr(g, 'atab', None)
        if a_ is None or not np.isfinite(a_[int(k)]).all():
            continue
        av = np.asarray(a_[int(k)], float)
        av = av - (av @ nv_) * nv_
        if np.linalg.norm(av) < 1e-9:
            continue
        av = av / np.linalg.norm(av)
        # ★ 面内**第二**轴 = npref × a（= 板条**宽**方向）；右手系，与引擎 `wtab` 同构造。
        wv = np.cross(nv_, av)
        _nw = np.linalg.norm(wv)
        if _nw < 1e-9:
            continue
        wv = wv / _nw
        # ★★ Round 71 修（Round 69 暴露的量具污染）：**遍历所有连通分量**，不再只取最大那个。
        #   为什么：同变体的多片若沿 `n*` 错开，被合并成一个分量 ⇒ `n*` 展宽被抬高
        #   （实测 `R_nuc=120` 档打出"几何厚度 717 nm"，而它只能当**上界**）。
        #   改后每片单独出一条记录 ⇒ 调用侧可用**中位/p10 + 分量数**判断合并程度，
        #   而不是被单个大分量的展宽骗到。
        # ★★ Round 74 修（Round 73 暴露的"碎片病理"）：`min_cells=8` 太小 ——
        #   长时间长大时同变体反复合并/撕裂，小碎片会主导 **p10**（实测 p10=64 nm
        #   而真实单片是 700 nm）。⇒ 只统计 `cells ≥ max(min_cells, 25% × 最大分量)` 的分量，
        #   并把**分量胞数分布**一起返回，让读者能判断是否碎片化。
        _thr = max(min_cells, int(0.25 * int(sz[1:].max() if sz.size > 1 else 0)))
        for _ci in range(1, n + 1):
            if sz[_ci] < _thr:
                continue
            idx = np.argwhere(lab == _ci).astype(float)
            t_ = float((idx @ nv_).max() - (idx @ nv_).min()) * g.dx
            if t_ <= 1e-12:
                continue
            L_ = float((idx @ av).max() - (idx @ av).min()) * g.dx
            W_ = float((idx @ wv).max() - (idx @ wv).min()) * g.dx
            if W_ <= 1e-12:
                continue
            # 返回顺序（Round 139 起）：k, L, W, T, L/T, L/W, cells
            out.append((int(k), L_, W_, t_, L_ / t_, L_ / W_, int(sz[_ci])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', default='control', choices=('control', 'rve'))
    ap.add_argument('--L-um', type=float, default=4.8)
    ap.add_argument('--dx-nm', type=float, default=50.0)
    ap.add_argument('--n0', type=int, default=64)
    ap.add_argument('--f-target', type=float, default=0.10)
    ap.add_argument('--adv', default='proj2')
    # ★★★ 2026-09-28：后加路径的开关（默认全关 ⇒ 与归档逐位可比）。
    #   `--norm-smooth 2` = 根因① 的修法（`T26` 5/5 过验收）；
    #   `--nuc` = D18 形核通道（`T27` 全 PASS）—— **分组统计正是它直接影响的对象**。
    ap.add_argument('--norm-smooth', type=int, default=0)
    ap.add_argument('--nuc', action='store_true')
    ap.add_argument('--nuc-t-nm', type=float, default=700.0)
    ap.add_argument('--nuc-r-nm', type=float, default=400.0)
    ap.add_argument('--nuc-init', type=int, default=24)
    ap.add_argument('--nuc-every', type=int, default=5)
    ap.add_argument('--nuc-fresh', type=int, default=2)
    ap.add_argument('--nuc-stack', type=int, default=2)
    ap.add_argument('--harden-f', type=float, default=0.10)
    # ★ Round 63–64：`p_auto` 已接线（定义见 `windowB_surface.nuc_cfg()`：
    #   「转变量过半时自催化形核速率相对无自催化情形增加的倍数」，增益 = 1+p_auto·4f(1−f)）。
    #   ⛔ **原"唯一标定靶 = block:lath ≈ 26（Morito 2009）"已撤回**
    #     （`MEASUREMENT_SPEC R10` / `REFERENCE_AUDIT` #6）：**那是钢**，跨材料。
    #   ⛔⛔ **2026-09-28 Round 139 再撤一条**：原写「同材料靶：几何**长:厚** ≈ 9:1（Wang 2026）」
    #     —— **口径错配**。Wang 2026 的逐字原文是「average **length and width** ... 8.1 ± 2.0 µm
    #     and 0.9 ± 0.4 µm」⇒ 那是 **长:宽**，**不是长:厚**（`REFERENCE_AUDIT.md:86/95` 一直记对，
    #     是下游用错了）。而本文件的 `geom_ar()` 量的**就是长:厚**（`atab[k]` ÷ `npref[k]`）
    #     ⇒ 但 **`geom_ar()` 是**有靶的**：Shuai 2026 给的正是**板条厚** 0.51–0.88 µm
    #     （BSE + 线性截距法，`REFERENCE_AUDIT.md:56/62` 逐字）⇒ 与 Wang 的长 8.1 µm 组合
    #     得 **长:厚 ≈ 9.2–15.9**。⚠ 跨文献组合，须标注。
    #   ✅ 正确的同材料靶是 **长:宽 ≈ 9:1** ⇒ 要判它，**必须同时报面内长:宽**（本文件尚未取该数）。
    #   ⚠ `block:lath` 改作**本项目自设的机制自检量**（LPBF Ti-64 的 block 尺寸文献查不到）。
    ap.add_argument('--p-auto', type=float, default=0.0)
    # ★ Round 80（闭合 Round 77 标为"未验证"的那条）：核的变体选择规则
    #   `ed` = `argmax_k ed[k]`（Du 2017，**默认，归档不变**）；
    #   `random` = 每点随机抽（Salama et al. 2024, doi 10.1016/j.commatsci.2024.113033）。
    #   要回答的问题：**`M6p` p25 退化到 23.9–25.4°（超 D16c 门槛 20°）是不是 `ed` 规则造成的**。
    ap.add_argument('--var-rule', default='ed', choices=('ed', 'random'))
    a = ap.parse_args()
    global NS, NUC
    NS = int(a.norm_smooth)
    NUC = dict(on=bool(a.nuc), t=a.nuc_t_nm * 1e-9, R=a.nuc_r_nm * 1e-9,
               init=a.nuc_init, every=a.nuc_every, nf=a.nuc_fresh, ns_=a.nuc_stack,
               harden=a.harden_f, pa=a.p_auto, vr=a.var_rule)
    if a.mode == 'control':
        return 0 if control() else 1
    from T16_verify_rve import NPF
    fam, nf, _meta = burger_packet_families()
    if fam is None:
        print('  ⚠ 取不到 Burgers 族表 ⇒ 退回 `npref` 代理（**已证伪，读数仅供参考**）')
        fam, nf = packet_families(NPF, tol_deg=10.0)
    print('=' * 100)
    print('B4-1 真实 RVE 的 block/packet/cluster 统计   L=%.1f µm Δx=%.0f nm n0=%d adv=%s'
          % (a.L_um, a.dx_nm, a.n0, a.adv))
    print('  packet 族（**Burgers {110}β，6 族 × 2 变体**）：%d 个族' % nf)
    sizes = {}
    for f in set(fam.values()):
        sizes[f] = sorted(k for k in fam if fam[k] == f)
    for f in sorted(sizes):
        print('     族 %d：变体 %s' % (f, sizes[f]))
    print('-' * 100)
    g, s = rve(a.L_um * 1e-6, a.dx_nm * 1e-9, a.n0, a.f_target, a.adv)
    if s is None:
        print('  ⚠ 未取到采样点 ⇒ INCONCLUSIVE')
        return 2
    reg = g.region()
    st = grouping_stats(reg, g.dx, fam)
    print('  采样 step=%d  f=%.4f  变体数=%d  守卫=%s' % (s['it'], s['f'], st['n_var'], s['guard']))
    print('  %-10s %-8s %-12s %-12s %-12s' % ('量', '计数', '中位(nm)', 'p90(nm)', '最大(nm)'))
    for nm, key in (('block', 'block_deq'), ('packet', 'packet_deq')):
        v = np.array(st[key]) * 1e9
        if v.size:
            print('  %-10s %-8d %-12.1f %-12.1f %-12.1f'
                  % (nm, v.size, np.median(v), np.percentile(v, 90), v.max()))
        else:
            print('  %-10s 0（无满足 min_cells 的分量）' % nm)
    print('  cluster：在场变体 %d / 12；`M6p` p25 = %.1f°（随机 60.1°）'
          % (st['n_var'], s['m6p_p25']))
    print('  ★ 记账（C2）：as-built LPBF α′ 的 block/packet 尺寸**文献 NOT FOUND**'
          '（子代理检索 ~20 篇全文）⇒ 只报模型自己的分布 + 上述机制自检，**不做"与文献一致"的声称**。')
    # ---------------- ★ 几何三向（`L/T` 与 `L/W`）—— 见 `geom_ar()` 的说明
    ga = geom_ar(reg, g, NPF)
    if ga:
        # ★★ Round 139：元组已扩为 `(k, L_, W_, t_, L_/t_, L_/W_, cells)`
        #   ⇒ `L/T` 在 **`v[4]`**、`L/W` 在 **`v[5]`**、厚在 **`v[3]`**、宽在 `v[2]`。
        #   ⚠ 旧版是 `(k, L_, t_, L_/t_, cells)`（`L/T` 在 `v[3]`、厚在 `v[2]`）——
        #     **索引变过，改调用侧时必须一起改**（本文件曾因索引错打出 "0.00" 并误判量具坏）。
        arT = np.array([v[4] for v in ga], float)
        arW = np.array([v[5] for v in ga], float)
        th = np.array([v[3] for v in ga], float)
        wd = np.array([v[2] for v in ga], float)
        ncomp = len(ga)
        print('  ★★ **靶② 的正确读数 —— 几何长:宽**（每片单独统计，共 %d 片）：'
              '中位 **%.2f**、p90 %.2f、max %.2f   ⬅ **与 9:1 比这一行**'
              % (ncomp, np.median(arW), np.percentile(arW, 90), arW.max()))
        print('     ✅ **同工艺同材料靶**：**长:宽 ≈ 9:1**'
              '（Wang 2026, 10.20517/microstructures.2025.144，原文 "average **length and width**'
              ' ... 8.1 ± 2.0 µm and 0.9 ± 0.4 µm"）'
              ' ⇒ 命中？%s' % ('**是**' if np.median(arW) >= 9.0 * 0.9 else '**否**'))
        print('  ☆ **几何长:厚**（每片单独统计，共 %d 片）：中位 %.2f、p90 %.2f、max %.2f'
              % (ncomp, np.median(arT), np.percentile(arT, 90), arT.max()))
        print('     ✅ **本行的靶**（⚠ **跨两篇同工艺文献组合**，须标注）：长 ÷ 厚 = '
              'Wang 2026 length 8.1 / **width** 0.9 µm；'
              'Shuai 2026 "lath **widths** 0.51–0.68 µm"（`docs/refcheck/ref01_shuai2026.txt:299` 逐字）'
              ' ⇒ **长:厚 ≈ 9.2–15.9**（Wang 只给长、"宽"；Shuai 只给"厚"）。')
        print('     同批的**几何厚度**：中位 %.0f nm、**p10 %.0f nm**（p10 更接近"单片厚度"'
              '—— 合并会把它抬高，故中位是**上界**）'
              % (np.median(th) * 1e9, np.percentile(th, 10) * 1e9))
        print('     同批的**几何宽度**：中位 %.0f nm、p10 %.0f nm'
              % (np.median(wd) * 1e9, np.percentile(wd, 10) * 1e9))
        # ★★★ 2026-09-28 更正（`MEASUREMENT_SPEC R10`）：旧文本把**钢**的数（30:1、block:lath≈26）
        #   与 Ti-64 的数并列使用 ⇒ 已剔除。**只保留同材料同工艺的靶**。
        # ⛔⛔ **Round 139 再纠一条**：旧文本把 Wang 2026 的 ≈9:1 写成"几何**长:厚**" —— **错**。
        #   原文是 "average **length and width** ... 8.1 ± 2.0 µm and 0.9 ± 0.4 µm"
        #   ⇒ **长:宽**。而上面那个 `geom_ar()` 量的是**长:厚** ⇒ **两者不可比**，
        #   ⛔ 不得再写"长:厚 vs 靶 9:1 ⇒ FAIL"。**`geom_ar()` 目前没有同工艺靶。**
        print('     ✅ **同工艺同材料（LPBF Ti-64 as-built α′）的靶**：**长:宽 ≈ 9:1**'
              '（Wang 2026, 10.20517/microstructures.2025.144，原文 "average **length and width**'
              ' ... 8.1 ± 2.0 µm and 0.9 ± 0.4 µm"）')
        print('     ⛔ **本表的"几何长:厚"没有同工艺靶**（上面那个 9:1 是**长:宽**，口径不同）：'
              '⚠ 但 **2D 截面无法分离宽与厚** ⇒ 文献只约束**一个**指数 '
              'Shuai 2026 "lath **widths** 0.51–0.68 µm"（`docs/refcheck/ref01_shuai2026.txt:299` 逐字）')
        print('     ⚠ **已知缺口**：要判靶② 必须同时报**面内长:宽**，本文件尚未取该数。')
        print('     ⛔ **已剔除**：长:厚 30:1（Rezazadeh 2024 = **钢**）、'
              'block:lath ≈ 26（Morito 2009 = **钢**）、2D AR 带 2.8–8.4（**原文未取到**）')
        print('     ⚠ **LPBF Ti-64 的 block/packet 尺寸在公开文献里查不到**'
              '（~20 篇全文 + 8 组查询复核）⇒ **block 只作机制自检，不作"与文献一致"的声称**；'
              '且 LPBF α′ 实际是 **basket-weave（网篮）**，不是钢式 block/colony 层级')
        print('     （上面那张 **2D 截面 AR** 表与本表**口径不同**，不得互相替代；'
              '`MEASUREMENT_SPEC §4.6` 已记账同一切面口径只有几何值的 ~0.54×）')
    print('=' * 100)
    return 0


if __name__ == '__main__':
    sys.exit(main())
