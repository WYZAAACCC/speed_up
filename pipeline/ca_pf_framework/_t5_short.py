#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_short.py --- ★★★★★ 实验(5)重启的**短跑定参数**（用户要求："先短跑定参数，再长跑"）

## 这一跑要回答的四件事（**全部是当前的外推项，必须实测**）
| # | 问题 | 之前的状态 |
|---|---|---|
| 1 | **N=160 的真实峰值内存** `VmHWM` | 只有"N=160 归档臂 3–4 GB"的转述 ⇒ **未实测** |
| 2 | **N=160 的真实单步耗时** | 由 abA 的 4.68 s/步(N=112) 按 N³ 外推 ⇒ **13.6 s/步【推理】** |
| 3 | **N=160 的真实检查点体积** | 由 N=64 的 20.93 MB 按 N³ 外推 ⇒ **~300–380 MB/帧【推理】** |
| 4 | **24 次形核够不够在 10 µm 盒里长出多块** | **完全未知** ← 判据③④⑤ 的前提 |

## 配置的取舍（**显式记账**）
* **物理基线 = abA**（用户逐字要求"参照 abA"）：
  `--alpha-km 0.041739`、`--T-end 298.0`、`--cool-rate 2.3524e6`、`--nuc-law athermal`
  ⇒ **形核数 `n = floor(0.041739 × (873.0 − 298.0)) = 24`**
* **⚠ 我**没有**动 `α_KM`** —— 它在日志里标着 `(user)`，是**用户给的物理输入**；
  为"提高形核数"而调它必须用户确认。**⇒ 本跑用原值，先把"够不够"量出来。**
* **`nv = 48`**（`--m 4`，12 变体 × 4）⇒ 24 个形核用掉一半场位，留有余量
* **算子**：直接复用 `_r581_p2.py` 的 `SWITCHES`（13 项逐位优化算子，**不重抄、避免漂移**）
* **断点续跑**：`--ckpt-every 20 --ckpt-keep 2`（用户要求"已能断点续跑"的代码上跑）
* **盒**：`N=160`、`dx=62.5 nm` ⇒ **10.00 µm**（用户要求 ≥10 µm）
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PY = '/root/miniconda3/envs/ml/bin/python'


def laths(m, nvar=12):
    return ','.join(str(v) for v in range(1, nvar + 1) for _ in range(m))


def build(a, switches):
    return ([PY, '-u', os.path.join(HERE, '_bk_exp.py'),
             # ★★★★★★ s287：**`--dx-nm` 透传**（原来**硬编码 '62.5'** ⇒ 改 `--N` 只改盒不改分辨率）。
             #   为什么要它：薄板厚度 `t = 312.5 nm` 在 `dx = 62.5 nm` 下**恒为 5 个胞**
             #   ⇒ 与球体基准（`T1_verify_edsign.py` 用 `dx = 20/10 nm`，收敛到 ~2.0e8）
             #     **分辨率差 3–6 倍** ⇒ **"薄板 2.96e8 vs 球体 2.0e8"含混淆变量** ⚠
             #   ⇒ 需做**只改 dx** 的单变量对照，判"**欠解析** vs **物理量**"。
             #   ⚠ **默认 62.5** ⇒ `repr(float(62.5))` = `'62.5'` ⇒ **与原字面量逐字相同**
             #     ⇒ 归档与在跑的臂**逐位不变** ✓
             '--N', str(a.N), '--dx-nm', repr(float(getattr(a, 'dx_nm', 62.5))),
             '--steps', str(a.steps), '--every', str(a.every),
             '--snap-every', str(a.snap_every), '--pair-every', str(a.pair_every),
             '--norm-smooth', '0',
             # ★★★★★ R581-T5R-s54：**把 `--phi-band-every` 与 `--snap-every` 对齐**。
             #   ## 为什么（实测依据，`R581_T5_RESTART.md §30.1`）
             #     带内 φ（`band_idx`/`band_val`/`band_fld`）**只在 `--phi-band-every` 的倍数步落盘**。
             #     原来写死 **200**，而 `--snap-every` 是 **40** ⇒ 实测只有 `snap_00000`/`snap_00200`
             #     带 band ⇒ **判据② 的厚度量具（`wide_face_thickness`）分辨率被压到 200 步**。
             #   ## 代价 vs 收益（用户的判据）
             #     代价：带 band 的快照体积增加 —— 实测 step 0 那份只有 **0.11 MB**
             #           （它只存 `|φ| ≤ 6Δx` 的胞，占 0.28%/场）⇒ **很小**；
             #     收益：**判据② 的分辨率 200 → 40 步（5×）**，且与 `nslab_n`/`nf3` 的
             #           40 步快照**同步对齐** ⇒ 可直接做时间序列对照。
             #   ⇒ **收益 ≫ 代价 ⇒ 改成跟随 `--snap-every`。**
             #   ⚠ 只影响**新起**的臂；正在跑的臂不受影响（其 band 仍是每 200 步）。
             '--phi-band-every', str(a.snap_every),
             # ★★★ R581-T5R-s112：**S14 热史档透传**（默认 `linear` ⇒ 与归档逐字相同）
             '--therm-hist', str(getattr(a, 'therm_hist', 'linear')),
             # ★★★★★ R581-T5R-s112：**`--nuc-fresh-every` 透传**（默认不传 ⇒ 引擎自动取 `K = n(T_end)`）
             #   ## 为什么要它（§111 的方案②）
             #     `fresh` 通道**只在每 `K` 个事件**尝试一次；长跑到 step 701 才出现事件 #24
             #     ⇒ **小臂到不了第一个 `K` 周期** ⇒ 拿不到 `fresh_*` 归因计数。
             #     显式传一个**更小的 K** 可让短诊断臂**更快尝试 `fresh`** ⇒ 拿到**被拒原因**。
             #   ⚠ **记账**：小臂的 `K` 与长跑不同 ⇒ 它只能回答"**`fresh` 为什么被拒**"，
             #     **不能**回答"长跑里会不会成功"（后者要靠等长跑自己到事件 47/70）。
             #   ⚠ 默认 `0` ⇒ **一个参数都不传** ⇒ 长跑/归档路径**逐字不变**。
             #   ⚠⚠ **s112 留痕（我犯的错，已修）**：第一版我在这里写成 `] + (…)`，
             #     **与原第 85 行已有的 `] +` 冲突** ⇒ `SyntaxError`（`_t5_short.py` 一度不可用，
             #     **会影响长跑的恢复**）。修法：**并入原有的 `+` 链**（见下方）。
             '--eng-cadence', '30', '--nthreads', str(a.nthreads),
             '--plate-L', '1000', '--plate-W', '500', '--plate-T', '510',
             '--gamma0', '0.25', '--beta-h', '6.477',
             '--nuc-law', 'athermal',
             # ★★★★★ s266：**`--no-nucleation` 开关**（B4S 二分实验用）。
             #   为什么要它：`--nuc-init` 是**引擎内部参数**，启动器原不接受
             #   ⇒ B4S 直接传 `--nuc-init 0` 会被 argparse 拒（实测报错）。
             #   语义：`--no-nucleation` ⇒ 去掉 `--grow-stack` 并把 `--nuc-init` 设为 **0**
             #   ⇒ **只有 t=0 的种子（场 1）**，其余场全空 ⇒ 等价"单根"。
             #   ⚠ **默认档（不传）⇒ 与归档逐字相同**（见下方 `([...] if ... else [...])`）。
             # ★★★★★ s266 修（**实测教训**）：**保留 `--grow-stack`**，只把 `--nuc-init` 设 0。
             #   第一版连 `--grow-stack` 一起去掉 ⇒ `grow=False` ⇒ 引擎走
             #   **t=0 多片播种**（`_bk_exp.py:1636`）⇒ `nvar 1 · m 23` 播 23 片 × 0.51 µm
             #   = 11.7 µm > 盒 4 µm ⇒ `ValueError: margin -2.376e-06`（中心出盒）。
             #   ⚠ `grow` 还决定"t=0 播 1 片还是 M 片"（`_bk_exp.py:1707` 逐字）
             #     ⇒ **禁形核只能靠 `--nuc-init 0`**，不能靠去掉 `--grow-stack`。
             ] + (['--grow-stack', '--nuc-init', '0']
                  if bool(getattr(a, 'no_nucleation', False))
                  else ['--grow-stack', '--nuc-init', '6']) + [
             '--nuc-block-target', str(a.B), '--nuc-shape', 'ellipsoid',
             '--nuc-supercrit', '1', '--nuc-sites-refill', '1',
             '--qs-clock', '1', '--qs-max-relax', '100',
             # ★★★★★ 物理基线 = abA（用户逐字要求"参照 abA"）
             '--alpha-km', repr(float(a.alpha_km)), '--T-end', repr(float(a.T_end)),
             '--cool-rate', '2.3524e6',
             '--facet-proj', '0', '--facet-excl', '0',
             '--reinit-dt', '1e-4', '--reinit-band', '6.0',
             '--nuc-overlap-nm', repr(float(a.overlap_nm))] + \
            # ★★★★★ s267：**`--diag-terms` 透传**（R208 三项分离诊断，**默认不传**）。
            #   为什么要它：判"孤立种子为何溶解"必须**直接测**速度律三项
            #     `|df_k−df_l|`（化学）· `|ed_k−ed_l|`（弹性）· `|stk·κ|`（曲率）,
            #   且引擎把**含母相的 F1 界面单列**（正是孤立种子的界面）。
            #   ⚠ 纯记账：只读、只统计，**不参与任何分支/数值**
            #     ⇒ `--diag-terms` 关时（**默认**）逐位不变 ✓
            (['--diag-terms'] if bool(getattr(a, 'diag_terms', False)) else []) + \
            # ★★★★★★ s285（**用户总目标第 4 项：修 burst 至物理正确**）：
            #   透传 `--burst-km`（`_bk_exp.py` 里由它把形核调度从**线性律**
            #   `floor(α·(Ms−T))` 换成 **KM 分数律** `round(N_end·(1−exp(−α(Ms−T))))`）。
            #   ⚠ **默认 `0` ⇒ 不产生任何参数** ⇒ 归档与在跑的臂**逐字不变** ✓
            (['--burst-km', str(int(getattr(a, 'burst_km', 0) or 0))]
             if int(getattr(a, 'burst_km', 0) or 0) != 0 else []) + \
            # ★★★★★★ s290（**修法 A：弹性罚能折减因子 η**，物理对应**塑性弛豫 / TRIP**）
            #   见 `windowB_surface.py` 的 `dG_cell` 与 `_bk_exp.py` 的 `g.ed_eta` 注释。
            #   `η = 1.0`（**默认**）⇒ **不产生参数** ⇒ 归档与在跑的臂**逐字不变** ✓
            (['--ed-eta', repr(float(getattr(a, 'ed_eta', 1.0) or 1.0))]
             if float(getattr(a, 'ed_eta', 1.0) or 1.0) != 1.0 else []) + \
            # ★★★★★ R581-T5R-s122：两个透传（**默认档不传** ⇒ 归档/长跑逐字不变）
            # ★★★★★ R581-T5R-s213：两个物理开关（**默认档不传** ⇒ 归档/在跑的臂逐字不变）
            (['--eng-elong', repr(float(a.eng_elong))]
             if float(getattr(a, 'eng_elong', 0.0) or 0.0) > 0 else []) +
            # ★★★★★ s230：迁移率各向异性（**默认档不传** ⇒ 归档/在跑的臂逐字不变）
            (['--mob-iform', str(a.mob_iform)]
             if str(getattr(a, 'mob_iform', 'exp2')) != 'exp2' else []) +
            (['--mob-ratio', repr(float(a.mob_ratio))]
             if str(getattr(a, 'mob_iform', 'exp2')) != 'exp2' else []) +
            (['--mob-wulff'] if bool(getattr(a, 'mob_wulff', False)) else []) +
            (['--mob-dip', repr(float(a.mob_dip))]
             if float(getattr(a, 'mob_dip', 0.0) or 0.0) > 0 else []) +
            (['--facet-proj', str(int(a.facet_proj))]
             if int(getattr(a, 'facet_proj', 0) or 0) != 0 else []) +
            (['--var-rule', str(getattr(a, 'var_rule', 'ed'))]
             if str(getattr(a, 'var_rule', 'ed')) != 'ed' else []) +
            (['--nuc-occ-guard', str(a.nuc_occ_guard)]
             if int(getattr(a, 'nuc_occ_guard', 0) or 0) > 0 else []) +
            (['--nuc-block-parallel', str(a.nuc_block_parallel)]
             if int(getattr(a, 'nuc_block_parallel', 0) or 0) > 0 else []) +
            (['--nuc-fresh-every', str(a.nuc_fresh_every)]
             if int(getattr(a, 'nuc_fresh_every', 0) or 0) > 0 else []) +
            (['--nuc-periodic-seed', '1'] if int(a.periodic_seed) == 1 else []) +
            ['--laths', laths(a.m, a.nvar),
             '--ckpt-every', str(a.ckpt_every), '--ckpt-keep', str(a.ckpt_keep)]
            + (['--resume', a.resume] if a.resume else [])
            + ['--out', a.out, '--tag', a.tag]
            + switches)


def watch(pid, box, stop, limit_kb):
    while not stop.is_set():
        try:
            with open('/proc/%d/status' % pid) as fh:
                for ln in fh:
                    if ln.startswith('VmHWM:'):
                        kb = int(ln.split()[1])
                        box['kb'] = max(box.get('kb', 0), kb)
                        if kb > limit_kb and not box.get('killed'):
                            box['killed'] = True
                            print('  ⚠⚠⚠ 内存看门狗触发：VmHWM=%.2f GB > %.2f GB ⇒ 杀'
                                  % (kb / 1048576.0, limit_kb / 1048576.0), flush=True)
                            try:
                                os.kill(pid, 9)
                            except OSError:
                                pass
                        break
        except OSError:
            pass
        stop.wait(0.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='t5s1')
    ap.add_argument('--N', type=int, default=160)
    ap.add_argument('--dx-nm', type=float, default=62.5,
                    help='★ s287：网格步长（nm）。默认 **62.5** ⇒ 与原来的硬编码值'
                         '逐字相同 ⇒ 归档逐位不变；改小 ⇒ 只改分辨率、盒子 L 不变'
                         '（薄板厚度将占更多胞 ⇒ 可判"罚能是否因欠解析偏高"）')

    ap.add_argument('--m', type=int, default=4)
    # ★★★★★ R581-T5R-s18（**形核停滞的修复**）：`--nvar` —— **活跃变体数**。
    #   ## 病灶（第 17 轮诊断跑实测，`nuc_dbg.json`）
    #     `nfsv_nofield = 6`、`n_target_final = 10`、`ok = 3`
    #     ⇒ **6 个形核事件因"同变体组里没有空闲场"被拒**。
    #   ## 机制（`windowB_surface.py:2324-2345` + 代码自己的结论 `:2385-2394`）
    #     `nfsv` 在**同一变体组**里找未被占用的场；找不到就拒绝。
    #     代码逐字：「**「空场用完」= 模型能表示的板条数到顶**
    #     （**`nv` 是个表示上限，不是物理上限**）…… 必须**拒绝 + 计数**」。
    #   ## 为什么 `--nvar` 是正确旋钮
    #     `laths(m, nvar)` = `nvar` 个变体 × 每个 `m` 个场 ⇒ **`nv = nvar·m`**。
    #     我的跑**塌缩到单变体**（`f_var = 1/0/0/…`）⇒ 该变体只有 `m` 个场
    #     ⇒ **用完即封顶**。把 `nvar` 调小、`m` 调大，**乘积（= nv = 内存）不变**，
    #     而**单变体可容纳的板条数 = m** 变大。
    #   ⚠ **取舍记账**：变体数变少**会削弱判据⑥（涌现自协调需要多变体）**
    #     ⇒ 这是显式的取舍；当前必须先解除形核封顶（否则判据③④⑤ 完全拿不到）。
    #   ⚠ **不采用** `nfsv_strict=False`（回退到已有场）—— 代码明确警告它
    #     「会把"表示不了"伪装成"又长了一片"」。
    ap.add_argument('--nvar', type=int, default=12,
                    help='活跃变体数（nv = nvar × m）。默认 12 与归档一致。')
    # ★★★ R581-T5R-s69：**S14 热史档**（透传给 `_bk_exp.py` 的 `--therm-hist`）
    #   ⚠ 留痕：第一版我只在 `build()` 里加了透传，**忘了在这里加 argparse 条目**
    #     ⇒ 传 `--therm-hist lpbf` 时本脚本 argparse **直接 exit=2**（无法识别的参数），
    #       而 6b 的判据据此报 FAIL。**是判据先失败、我才发现**（若没跑，会以为"还在待测"）。
    ap.add_argument('--therm-hist', default='linear', choices=('linear', 'lpbf'),
                    help='热史：linear（默认，归档）| lpbf（S14，未过 6a/6b/6c 勿用于结论）')
    # ★★★★★ R581-T5R-s122：**两个透传**（把"单变体单块"变成"多变体多块"的必要条件）
    #   `--var-rule`：变体选择（**只对 `fresh` 通道生效**；`ed`=归档默认 ⇒ 不传）
    #   `--nuc-fresh-every`：`fresh` 通道周期（`0`=引擎自动取 `K=n(T_end)` ⇒ 不传）
    ap.add_argument('--var-rule', default='ed', choices=('ed', 'random', 'doublet'),
                    help='变体选择（只对 fresh 生效）：ed=归档默认 | random | doublet')
    # ★★★★★ R581-T5R-s112：**`--nuc-fresh-every`**（`fresh` 通道的调度周期）
    #   `0`（**默认**）⇒ **不传** ⇒ 引擎自动取 `K = n(T_end) = 23` ⇒ 归档路径逐字不变；
    #   `>0` ⇒ 显式传给引擎 ⇒ **诊断用**（让短臂更快尝试 `fresh`，拿被拒原因）。
    #   ⚠ 小臂的 `K` 与长跑不同 ⇒ 只能回答"为什么被拒"，不能回答"长跑里会不会成功"。
    # ★★★★★ R581-T5R-s213：**两个「物理开关」的透传**（§212 查明它们影响长宽比）
    #   `--eng-elong`：核的拉长率。**代码自己写明物理值 = 3.75**（驱动层 L/W=2400/640）；
    #     默认 0 ⇒ 走 `use_engine` 回退 = plate_L/plate_W = 2.0。
    #   `--facet-proj`：棱面投影。**引擎默认 0 ⇒ `facet_project()` 一次都没跑过** ⇒
    #     界面不会自发形成平整宽面 ⇒ 形状偏圆（**这是本 A/B 要测的**）。
    # ★★★★★ R581-T5R-s230：**迁移率各向异性**（= 生长阶段的伸长机制）的透传
    #   `--mob-iform ellipse` 是关键那一个：它把面内极曲线取成**椭圆**
    #   ⇒ 极集本身凸 ⇒ 凸化恒等 ⇒ `h(a)/h(w)` **恰等于** `--mob-ratio`
    #   （代码实测 ratio=9 给 **8.93**）。默认 `exp2` 走不到那条分支。
    ap.add_argument('--mob-iform', choices=['exp2', 'ellipse'], default='exp2',
                    help='面内迁移率角函数：exp2=默认（实测各向异性只 1.24）；'
                         'ellipse=椭圆（实测 8.93）')
    ap.add_argument('--mob-ratio', type=float, default=9.0,
                    help='椭圆面内极曲线长短轴比（= 目标长径比）')
    ap.add_argument('--mob-wulff', action='store_true', help='Wulff 凸化速度律（刻面机制）')
    ap.add_argument('--mob-dip', type=float, default=0.0,
                    help='惯习面内 45 度方向的迁移率凹陷强度（c=4 时 h(a)/h(w)=9.73）')
    ap.add_argument('--eng-elong', type=float, default=0.0,
                    help='核拉长率（0=引擎回退 plate_L/plate_W；3.75=代码写明的物理值）')
    ap.add_argument('--no-nucleation', action='store_true',
                    help='★ s266：禁止引擎形核（去掉 --grow-stack 且 --nuc-init 0）'
                         '⇒ 只留 t=0 的种子；默认 False ⇒ 归档逐字不变')
    ap.add_argument('--diag-terms', action='store_true',
                    help='★ s267：透传 `--diag-terms`（R208 三项分离诊断）；'
                         '默认 False ⇒ 归档逐字不变')
    ap.add_argument('--burst-km', type=int, default=0, choices=(0, 1),
                    help='★ s285：透传 `--burst-km`（形核用 KM 分数律 ⇒ 物理正确的 burst）；'
                         '默认 0 ⇒ 不传任何参数，归档逐字不变')
    ap.add_argument('--ed-eta', type=float, default=1.0,
                    help='★ s290：透传 `--ed-eta`（弹性罚能折减因子 η，塑性弛豫/TRIP）；'
                         '默认 1.0 ⇒ 不传任何参数，归档逐字不变；理论标定 η≈0.375')




    ap.add_argument('--facet-proj', type=int, default=0,
                    help='棱面投影（0=引擎默认，从未跑过；1=打开）')
    ap.add_argument('--nuc-occ-guard', type=int, default=0, choices=(0, 1, 2),
                    help='s300: \u64ad\u79cd\u5360\u7528\u5b88\u536b')
    ap.add_argument('--nuc-block-parallel', type=int, default=0, choices=(0, 1),
                    help='s293: \u5757\u6570 = B\uff08\u524d B \u4e2a\u4e8b\u4ef6\u5404\u5efa\u65b0\u5757\uff09')
    ap.add_argument('--nuc-fresh-every', type=int, default=0,
                    help='fresh 通道周期（0=引擎自动取 K=n(T_end)；>0=诊断用）')
    ap.add_argument('--B', type=int, default=5)
    ap.add_argument('--steps', type=int, default=40)
    ap.add_argument('--every', type=int, default=5)
    ap.add_argument('--snap-every', type=int, default=200)
    ap.add_argument('--pair-every', type=int, default=20)
    ap.add_argument('--nthreads', type=int, default=4)
    ap.add_argument('--alpha-km', type=float, default=0.041739)   # ★ abA 的原值
    ap.add_argument('--T-end', type=float, default=298.0)         # ★ abA 的原值
    ap.add_argument('--ckpt-every', type=int, default=20)
    ap.add_argument('--ckpt-keep', type=int, default=2)
    # ★★★★★ S4（`--nuc-overlap-nm`）单变量 A/B 用：
    #   审计 §2 已证明它**直接**接在引擎的 `attach_overlap` 上，
    #   而本长跑走的正是 **attach 通道** ⇒ **默认 0 会破坏块内界面完整性**。
    #   `62.5` = 1Δx = 代码自带剂量–响应实测的最优；`0` = 旧默认（= 被审计的简化）。
    ap.add_argument('--overlap-nm', type=float, default=62.5)
    ap.add_argument('--periodic-seed', type=int, default=1, choices=(0, 1))
    ap.add_argument('--resume', default='')
    ap.add_argument('--out', default='_exp/_bk_t5')
    ap.add_argument('--mem-limit-gb', type=float, default=14.0)
    ap.add_argument('--cores', default='0-7')
    ap.add_argument('--archive-old', action='store_true')
    a = ap.parse_args()

    import importlib.util
    spec = importlib.util.spec_from_file_location('p2', os.path.join(HERE, '_r581_p2.py'))
    p2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(p2)
    switches = list(p2.SWITCHES)          # ★ 13 项逐位优化算子，单一真源

    if a.archive_old:
        d = os.path.join(a.out, 'dry_' + a.tag)
        if os.path.isdir(d):
            n = '%s_superseded_%d' % (d, int(time.time()))
            shutil.move(d, n)
            print('  已归档改名：%s → %s' % (d, os.path.basename(n)))

    c = build(a, switches)
    lg = '_w2_t5_short_%s.log' % a.tag
    nv = int(a.nvar) * a.m
    Ms = 873.0
    n_nuc = int((float(a.alpha_km) * (Ms - float(a.T_end))) // 1)
    print('=' * 100)
    print('T5 短跑  tag=%s  N=%d ⇒ 盒 %.2f µm' % (a.tag, a.N, a.N * 62.5 / 1000))
    print('  nv=%d  B=%d  steps=%d  threads=%d  内存上限 %.1f GB  绑核 %s'
          % (nv, a.B, a.steps, a.nthreads, a.mem_limit_gb, a.cores))
    print('  ★ 物理基线 = abA：α_KM=%.6f  T_end=%.1f  ⇒ **导出形核数 n = %d**'
          % (a.alpha_km, a.T_end, n_nuc))
    print('  ★ 优化算子 = %d 项（复用 `_r581_p2.SWITCHES`）：%s'
          % (len(switches) // 2, ' '.join(switches[:8]) + ' …'))
    print('  ★ 断点续跑：--ckpt-every %d --ckpt-keep %d%s'
          % (a.ckpt_every, a.ckpt_keep,
             '  **续跑自 %s**' % a.resume if a.resume else ''))
    print('  ★ S4：--nuc-overlap-nm = **%s**（62.5 = 1Δx 修复值；0 = 旧默认）'
          % a.overlap_nm)
    print('  ★ N13：--nuc-periodic-seed = %d' % int(a.periodic_seed))
    print('=' * 100)
    sys.stdout.flush()

    env = dict(os.environ)
    for k in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        env.pop(k, None)
    env.pop('MALLOC_MMAP_THRESHOLD_', None)
    env.pop('MALLOC_TRIM_THRESHOLD_', None)
    t0 = time.time()
    with open(lg, 'wb') as fh:
        pr = subprocess.Popen(['taskset', '-c', a.cores] + c, stdout=fh,
                              stderr=subprocess.STDOUT, env=env)
        box, stop = {}, threading.Event()
        th = threading.Thread(target=watch, args=(pr.pid, box, stop,
                                                  a.mem_limit_gb * 1048576.0))
        th.daemon = True
        th.start()
        pr.wait()
        stop.set()
        th.join(timeout=2)
    el = time.time() - t0
    txt = open(lg, encoding='utf-8', errors='replace').read()
    steps = [int(m.group(1)) for m in re.finditer(r'\[\s*(\d+)\]\s+Vt=', txt)]
    sps = [float(m.group(1)) for m in re.finditer(r'\|\s*([\d.]+)s/步', txt)]
    print()
    print('  exit=%d  墙钟 %.1f s' % (pr.returncode, el))
    print('  峰值 RSS（VmHWM，看门狗实测）= **%.2f GB**%s'
          % (box.get('kb', 0) / 1048576.0, '  ⚠ 被看门狗杀' if box.get('killed') else ''))
    print('  走到 step %s（共 %d 步）' % (steps[-1] if steps else '?', a.steps))
    if sps:
        print('  单步耗时：中位 **%.2f s/步**  最小 %.2f  最大 %.2f（%d 个采样）'
              % (sorted(sps)[len(sps) // 2], min(sps), max(sps), len(sps)))
    ck = os.path.join(a.out, 'dry_' + a.tag, 'ckpt')
    if os.path.isdir(ck):
        fs = sorted(os.listdir(ck))
        print('  ★ 检查点：%d 个文件 —— %s' % (len(fs), ', '.join(fs[:6])))
        for f in fs:
            print('      %-24s %8.1f MB' % (f, os.path.getsize(os.path.join(ck, f)) / 1048576.0))
    print('  日志 %s' % lg)
    print('=' * 100)


if __name__ == '__main__':
    main()
