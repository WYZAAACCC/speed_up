#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_exp.py —— **阶段 3 生产装置**：在一个盒子里播 M 根同变体板条，看它们
能否各自长大、沿 @@\\mathbf n^*@@ 堆叠成块、被低角晶界分隔（F3）、而不是合并。

## 与 `_bk_smoke_f3.py` 的区别

| | smoke | **本文件（生产）** |
|---|---|---|
| 板条表 | 复制 `eps0`（无 θ） | **`windowB_lath.LathTable`**：逐板条变体 + 小转动 ⇒ F3 面能 = @@\\gamma_{\\rm RS}(\\theta)@@ |
| 板条数 | 2 | **M（`--laths`）** |
| 布条方式 | 面对面 | **沿 @@\\mathbf n^*@@ 堆叠**（`--gap-nm`） |
| 量具 | 内嵌 | **`_bk_measure.measure_state`**（16 条对照已验证） |
| 记账 | 无 sha | **meta.json 记引擎 sha + 全部参数 + 臂定义** |
| 落盘 | snap | snap（全量 φ+region）+ series.csv + meta.json，**目录带时间戳不覆盖** |

## 臂（`--arm`）

| 臂 | 含义 |
|---|---|
| `dry` | F3 面能 = @@\\gamma_{\\rm RS}(\\theta)@@（**C-1/C-3 的物理结论**，主臂） |
| `wet` | F3 面能 = @@\\gamma_f@@（规定值；= 用户要的"Gibbs 面薄膜"） |
| `gpos` | **量具正对照**：@@\\gamma_\\Sigma@@=100 J/m²（界面必须明显移动） |
| `gneg` | **量具负对照**：所有板条播进**同一个场**（F3 必须恒为 0） |
| `g0` | **极限对照**：@@\\gamma_\\Sigma@@=0（界面无面能） |

## 用法

    python3 _bk_exp.py --dry-run                       # 只构造+播种+初始测量
    python3 _bk_exp.py --arm dry --steps 400 --N 192 --dx-nm 62.5
"""
import argparse
import csv
import json
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_lath as WL                                       # noqa: E402
import _bk_measure as BM                                        # noqa: E402
import windowB_km as KM                                         # noqa: E402
import windowB_closure as CL                                    # noqa: E402
from T16_verify_rve import C, EPS0, NPF, DF, MOB                # noqa: E402
from windowB_km import (ALPHA_KM_REF, M_S_TI64, T0_TI64, DS_REF,
                        DG_CRIT_REF)                            # noqa: E402

COLS = ['step', 't_s', 'wall_s', 'dt', 'V0', 'Vt', 'M', 'nreg_used',
        'nslab_n', 'nf3_col', 'runs', 'ncomp_min', 'ncomp_max', 'ncompbig_max',
        # ★ Round 10：**逐板条的体积与厚度，每一步都存**。
        #   为什么必须加：`Vt` 只有总量，而 V-2（"每根都在长"）与"咬入是否把
        #   旧片削薄"都只能靠**快照**判 —— 而快照默认 50 步一个 ⇒ 中间过程全丢。
        #   用户的要求是"全过程数据留盘、量具有 bug 也能事后重测"
        #   ⇒ 这两列必须在**每个测点**上写。用 `'/'` 连接（与 `runs` 同格式），
        #   这样 COLS 固定、M 可变。
        'vols', 'ths',
        # ★★★ R18：**逐对 F3 面积**（`i-j:A/...`，µm²）。加它的理由（R17 的线索）：
        #   实测引擎臂在**每次形核后的 10 步内** `f3_area` 掉 7–13%，
        #   而驱动层 `gs5` 只掉 0.6% ⇒ "每次新事件把已存在的界面推开一部分"。
        #   但**总量**看不出是**哪几对**被吃 ⇒ 必须逐对、且**每个测点**都记。
        #   `--pair-every 0`（默认）⇒ 不记 ⇒ 与改动前逐位相同（列会是空串）。
        'f3_pairs',
        # ★ R29（Round 18）：**逐对界面位置**（沿 n*，单位 Δx）。
        #   加它的理由见 `_pairpos_str` 的记账：`f3_pos_dx` 是汇总量，
        #   在各对面积不等且在变时会让 `V-3g` 给出假 FAIL。
        #   ⚠ 只落数据；对应的逐对判据**未实现未验证**。
        'f3_pairs_pos',
        'nf3', 'f3_area_m2', 'f3_area_stair', 'f3_pos_m', 'f3_pos_dx',
        # ★ R31：F2（异变体界面）—— 块—块相遇的签名
        'nf2', 'f2_area_m2',
        # ★★★★★ R218（`R30_AUDIT_LEDGER.md` §137.7）：**F1（含母相）聚合面积**。
        #   原先只有逐根的 `f1_faces_<k>` ⇒ "三类界面各占多少"答不出来，
        #   而 `§137.5` 的头号候选解释正是"F2 在**总**面积里占比小"。
        'nf1', 'f1_area_m2', 'f1_area_stair',
        'f3_std_m', 'n_lath', 'w_lath', 'a_lath', 'box_touch', 'finite',
        'psi_mean',
        # ★★★ R29：**CFL 实际用量** `dt·M·dG_max/dx`（单位：胞/步）。
        #   为什么必须落盘：`advance` 把**总驱动**（`Δf + Δed − γκ`，含弹性与曲率）
        #   的最大值写在 `g.dG_max`，而本驱动层定 dt 用的是**化学驱动力** `Δf`。
        #   本仓库已有前车之鉴（`suggest_dt` 的 docstring）：只按 `Δf` 定 dt，
        #   实测会让界面每步位移到 **0.6–0.75 dx**（超 CFL 4–5 倍）⇒ 剖面失真。
        #   ⇒ 实际用量必须落盘，判据才能事后核。
        #   （`_bk_defcheck.py` 只遍历**旧行**的键 ⇒ 新增列不影响归档的逐位比较。）
        'cfl_used',
        # ★★★ R30（`R30_AUDIT_LEDGER.md` P0-1）：柱剖面的**修正口径**。
        #   归档口径 `nslab_n`/`runs`/`nf3_col` 有两个静默少读（`min_run=2` 丢薄层、
        #   `r_col=300 nm` 硬编码看不见面内偏置的板条）—— 实测 6 层 2Δx 读成 5、
        #   `dry_cln11` step2000 的场 2 完全不可见。
        #   ⇒ **两个口径都存**：旧列保留（历史读数可复现），新列供判决。
        #   `r_col_nm`/`col_cover_min` 是**可见性守卫**：静默丢层从此是落盘数字。
        'nslab_n1', 'runs1', 'nf3_col1', 'r_col_nm', 'col_cover_min',
        # ★★★ R50（P1-29）：**去重场数**（= 柱里真正穿过的板条根数）。
        #   `nslab_n` 是**段数**，柱穿出一根再穿回来时会**多读**（实测 1.17–1.67×）
        #   ⇒ "`nslab_n == M`"不能当"块已形成"的判据。见 `_nslab_dedup` 的注释。
        'nslab_nu', 'nslab_nu1',
        # ★★★ R31（目标第 (2) 项）：**全局弹性能** + **块表**
        #   （`BLOCK_SELFAC.md` 的 J-1/J-3；`P-SA-1`/`P-SA-3` 的判据量）。
        #   块表只在 `--pair-every` 命中时算（它含 3D 连通标注）⇒ 否则列为空串。
        'E_el_J',
        'nblk_sig', 'blk_laths', 'blk_vars', 'n_var_sig', 'n_habit', 'f_var',
        'r_selfac',
        # ★ R31：**逐块沿它自己的 n\*** 数板条（多块配置下沿单一 n* 的柱剖面无意义）。
        'blk_nlath', 'blk_span_nm', 'blk_alen_nm', 'blk_wlen_nm',
        # ★★★ R76（**P1-33**）：`blocks()` 里**早就算了** `blk_nprof` / `blk_nruns`，
        #   但 `_blk_cols` 没转发 ⇒ 两个最有信息量的逐块诊断**根本没落盘**。
        #   R75 的判决因此只能吃**全局** `nslab_n`（多块下无效，见 P1-34）。
        #   口径（三个并存，谁也别偷偷改谁）：
        #     `blk_nlath`  该连通分量**覆盖的场数** —— **上界**（层并成一片也照样报满）
        #     `blk_nprof`  沿**该块自己的 n\*** 投影分箱、众数里**出现过的不同场数**
        #                  ⇒ **主口径**（几何的、且对分箱噪声免疫）
        #     `blk_nruns`  同上，但数**连续段** —— 诊断（分箱抖动会**多读**）
        'blk_nprof', 'blk_nruns',
        # ★ R38（P1-22）：**孤儿免疫**的撞壁判据与核心记账
        'box_touch_core', 'core_vox', 'ncomp_all',
        # ★ R41（P1-25）：`dG_max` 离群性诊断
        'dG_max_Jm3', 'dG_p999', 'dG_ratio', 'dG_near_max',
        # ★ R45（P1-25 直测）：按界面法向分档的 `ed` / `dG`
        'ed_tip', 'ed_side', 'ed_wide', 'dG_tip', 'dG_side', 'dG_wide',
        'ed_obl', 'dG_obl', 'n_obl',
        # ★★★ R49（结清 R48 的遗留）：同一算例上的 **p90 / max** —— 判"哪个
        #   统计量才预测面运动"。`dG_*`（中位）保留不动，新列并列存。
        'dG_tip_p90', 'dG_side_p90', 'dG_tip_max', 'dG_side_max',
        'ed_tip_p90', 'ed_side_p90',
        # ★★★ R49：**面速率的直接预言** `<M(n)·dG>_面 · dt`（nm/步）——
        #   与 `tip_sep_nm/side_sep_nm` 的时间导数**同量纲、可直接比**。
        #   这是 P1-25（"端面慢 44 倍"）的正确判据量。
        'v_tip_nsgn', 'v_tip_nabs', 'v_side_nsgn', 'v_side_nabs', 'v_wide_nabs',
        'v_obl_nabs',
        # ★★★ R49：**F1-only 面速度** + F1 占比守卫（F3 驱动的面会被混进来 ⇒ 低估）
        'v_tip_f1', 'v_side_f1', 'v_wide_f1', 'f1_tip', 'f1_side', 'f1_wide',
        # ★ R49：面分类的**胞数**守卫（档位退化时 CSV 能看出来，不静默为空）
        'n_tip', 'n_side', 'n_wide',
        # ★★★ R47：**面间距**（三个面族）—— 「长大速率」的金标准口径。
        #   实测：包围盒跨度把它放大 2.5–2.8×；逐胞中位 dG **不预测**它。
        'tip_sep_nm', 'side_sep_nm', 'wide_sep_nm']
assert len(COLS) == len(set(COLS))


_BLK_EMPTY = dict(nblk_sig='', blk_laths='', blk_vars='', n_var_sig='',
                  n_habit='', f_var='', r_selfac='', blk_nlath='', blk_span_nm='',
                  blk_alen_nm='', blk_wlen_nm='', blk_nprof='', blk_nruns='')


def _facesep_cols(g, dx, vmap):
    """★ R47：**三个面族的面间距**（「长大速度」的**金标准**口径）→ CSV 列。

    对每个**在场**的场算 `face_separations`，取**中位数**（与 `ths`/`n_lath` 同一口径），
    单位 nm；不可测就留空串（**不填 0**）。
    ⚠ 只在 `--pair-every` 命中时调用（每个场一次 `np.gradient`）。
    """
    import _bk_measure as _BM
    _ax = {}
    for _v in sorted(set(int(x) for x in vmap.values())):
        _n = np.asarray(NPF[_v], float)
        _nref, _, _ = W.argmin_normal_cached(C, np.asarray(EPS0[_v - 1], float))
        _R = W.LevelSetMulti._rank1_axes(np.asarray(EPS0[_v - 1], float), _nref)
        _ax[_v] = dict(tip=np.asarray(_R[1], float), side=np.asarray(_R[2], float),
                       wide=_n)
    acc = {'tip': [], 'side': [], 'wide': []}
    for _k in sorted(vmap):
        if not bool((g.region() == _k).any()):
            continue
        d = _BM.face_separations(g.phi, dx, _ax[int(vmap[_k])], _k)
        for t in acc:
            if t in d:
                acc[t].append(d[t] * 1e9)
    out = {}
    for t in acc:
        out['%s_sep_nm' % t] = (round(float(np.median(acc[t])), 1)
                                if acc[t] else '')
    return out


def _ebf(g, tag, which):
    """★ R45：从引擎的 `ed_by_face`（按界面法向分档的 `ed`/`dG` 统计量）取一个值。

    取不到 ⇒ 返回空串（**不假装是 0**）。`which`：0 = `ed` 中位，1 = `dG` 中位；
    ★ R49 新增 3 = `ed` p90，4 = `dG` p90，5 = `dG` max，6 = `dG` p99
    —— 供 R48 那条"**哪个统计量才预测面运动**"的受控检验使用。
    ⚠ 索引 0/1 的语义与取值**逐位不变**（旧列不受影响）。
    """
    d = getattr(g, 'ed_by_face', None)
    if not d or tag not in d:
        return ''
    try:
        return round(float(d[tag][which]), 6)
    except (TypeError, ValueError, IndexError):
        return ''


def _nslab_dedup(runs_str):
    """★★★ R50（**P1-29**）：柱里穿过的**去重场数** `len(set(runs))`。

    为什么必须与 `nslab_n = len(runs)` 并列报：
    一根**笔直**的柱可能**穿出一根板条再穿回来**（板条在面内有偏置、或形状不直）
    ⇒ 同一根场被切成 2+ 段 ⇒ `nslab_n` **多读**。
    实测（`_r50_dedup.py`，逐臂扫过）：
      `dry_mb1Ls`  M=3 ⇒ `nslab_n`=5（**1.67×**）而 **去重=3 ✅**
      `eng_eng3`   M=6 ⇒ `nslab_n`=7（1.17×）而 **去重=6 ✅**
    ⇒ `nslab_n == M` **不是**"块已形成"的可靠判据：**好块也会被判 FAIL**。
    而 `len(set(runs)) == M` 是**必要**条件（每根板条都出现在柱里），
    但**不充分**（不能排除"同一根出现两次而另一根缺席"）。
    ⚠ 两个量**都留**（本仓库纪律：两个口径都存、判决用新的、原始值留档）。
    ⚠ 去重值是**离线可复算**的 —— 所有归档臂的 `runs` 列都在 CSV 里，
      **不需要重跑**（这正是"全过程数据留盘"的价值）。
    """
    if not runs_str:
        return ''
    try:
        return len({int(x) for x in str(runs_str).split('/') if x})
    except (TypeError, ValueError):
        return ''


def _vbf(g, tag, which, dt):
    """★★★ R49：**面上直接可比的速度预言**（nm/步）。

    引擎的 `v_by_face[tag] = (带符号平均 v_cell, |v_cell| 平均, n)`。
    乘 `dt` 换算成"每步推进多少 nm" —— 这才是与 `tip_sep_nm/side_sep_nm`
    的**时间导数**直接对比的量。

    ⚠ 与 `dG_*` 系列的关系：`dG_*` 是**先取统计量**；本函数是**先乘再平均**
    （`<M(n)·dG>`）。实测（`_r49_dgacct.py`）两者对 `side` 面差 2.9 倍
    ⇒ **后者才是对的**（`M(n)` 在面上变化 9 倍）。
    取不到 ⇒ 空串（不假装是 0）。
    """
    d = getattr(g, 'v_by_face', None)
    if not d or tag not in d or dt is None:
        return ''
    try:
        return round(float(d[tag][which]) * float(dt) * 1e9, 4)
    except (TypeError, ValueError, IndexError):
        return 'NAN'


def _vbf_f1(g, tag, dt):
    """★★★ R49：**只看 F1（变体-母相）胞**的面速度平均（nm/步）。

    为什么必须单独给：3 根同类板条堆叠时板条间是 **F3（同变体）**，
    驱动力**逐位为 0** ⇒ 混在一起平均会把"冻结的 F3 面"算进去，
    与面位置速率比较时**系统性偏低**。本函数给"活的那部分面"的速度。
    """
    d = getattr(g, 'v_by_face', None)
    if not d or tag not in d or dt is None:
        return ''
    try:
        return round(float(d[tag][3]) * float(dt) * 1e9, 4)
    except (TypeError, ValueError, IndexError):
        return ''


def _vbf_f1frac(g, tag):
    """F1 胞在该面族里占的比例（守卫：太低 ⇒ 该面族读数不可用）。"""
    d = getattr(g, 'v_by_face', None)
    if not d or tag not in d:
        return ''
    try:
        n1, n = int(d[tag][4]), int(d[tag][2])
        return round(n1 / float(n), 4) if n else ''
    except (TypeError, ValueError, IndexError):
        return ''


def _blk_cols(g, reg, dx, vmap):
    """★ R31（J-1/J-2）：**块表**的 CSV 列（`_bk_measure.blocks()` 的薄包装）。

    ⚠ 只在 `--pair-every` 命中时调用（含 3D 连通标注）；否则由 `_BLK_EMPTY` 填空串，
    ⇒ `series.csv` 的列**永远存在**（`COLS` 的 `_miss` 硬检查不会炸）。
    """
    try:
        import _bk_measure as _BM
        ax = {}
        for _v in sorted(set(int(x) for x in vmap.values())):
            _n = np.asarray(NPF[_v], float)
            _nref, _, _ = W.argmin_normal_cached(C, np.asarray(EPS0[_v - 1], float))
            _R = W.LevelSetMulti._rank1_axes(np.asarray(EPS0[_v - 1], float), _nref)
            ax[_v] = (np.asarray(NPF[_v], float), np.asarray(_R[1], float),
                      np.asarray(_R[2], float))
        b = _BM.blocks(reg, dx, vmap, eps0_var=EPS0, npf_var=NPF, axes_var=ax)
        return dict(nblk_sig=int(b['nblk_sig']), blk_laths=b['blk_laths'],
                    blk_vars=b['blk_vars'], n_var_sig=int(b['n_var_sig']),
                    n_habit=int(b['n_habit']), f_var=b['f_var'],
                    blk_nlath=b.get('blk_nlath', ''),
                    blk_nprof=b.get('blk_nprof', ''),
                    blk_nruns=b.get('blk_nruns', ''),
                    blk_span_nm=b.get('blk_span_nm', ''),
                    blk_alen_nm=b.get('blk_alen_nm', ''),
                    blk_wlen_nm=b.get('blk_wlen_nm', ''),
                    r_selfac=(round(float(b['r_selfac']), 6)
                              if np.isfinite(b['r_selfac']) else ''))
    except Exception as exc:                                    # pragma: no cover
        print('⚠ 块表计算失败（不影响仿真）: %s' % exc, flush=True)
        return dict(_BLK_EMPTY)


def _sparse_band(phi, dx, band_cells):
    """★★★ R30（`R30_AUDIT_LEDGER.md` **P0-4**）：**带内稀疏 φ** 的落盘编码。

    为什么需要它（用户的硬要求 + `BLOCK_DERIVATION §10 I-6` 的原文）：
      「将仿真过程的全部数据保存在 F 盘下 …… 之后也能使用新的测量工具重新测量」
      —— 而实测：全库 297–517 个 `snap_*.npz` 里 **`phi` 键出现 0 次**
      （`_r30_scanphi.py`）⇒ 任何需要 φ 的量（界面剖面 / 法向 / **曲率 κ** /
      亚胞厚度 / `§8 P-1b` 的判据 / `§7 S-10` 的检验办法）**都无法离线重算**。

    为什么是"带内稀疏"而不是整场：
      整场 φ 在 N=192/7 场是 **+164.7 MB / 快照、+10.5 s / 次**（S5 实测）；
      而界面带只占全盒的 **0.02–0.4%** ⇒ 稀疏编码把代价降到 **~1 MB / 快照**。

    编码（三个等长的一维数组 + 一个标量）：
      `band_idx`  int32   线性索引（C 序，`np.ravel_multi_index`）
      `band_val`  float32 φ 的值（**米**）
      `band_fld`  int16   该胞属于哪个场
      `band_cells` int    `band_cells`（判定带用的胞数，重建时要）

    ⚠ 记账：**只存 `|φ| ≤ band_cells·Δx` 的胞** ⇒ 带外重建不出来。
      对本模型这够用（界面几何全部在带内），但**必须写清**，不得说成"全量 φ"。
    """
    idxs, vals, flds = [], [], []
    nreg = phi.shape[0]
    for k in range(nreg):
        m = np.abs(phi[k]) <= band_cells * dx
        if not m.any():
            continue
        ii = np.flatnonzero(m.ravel()).astype(np.int32)
        idxs.append(ii)
        vals.append(phi[k].ravel()[ii].astype(np.float32))
        flds.append(np.full(ii.size, k, np.int16))
    if not idxs:
        return dict(band_idx=np.zeros(0, np.int32),
                    band_val=np.zeros(0, np.float32),
                    band_fld=np.zeros(0, np.int16),
                    band_cells=np.int64(band_cells))
    return dict(band_idx=np.concatenate(idxs),
                band_val=np.concatenate(vals),
                band_fld=np.concatenate(flds),
                band_cells=np.int64(band_cells))


# ══════════════════════════════════════════════════════════════════════════════
# ★★★★★ R581-ckpt（goal「原生精度断点续跑」）—— 检查点的**采集 / 原子写 / 滑动窗口**
#
#   ## 三条硬约束（都来自 goal）
#   1. **全部默认关**（`--ckpt-every 0`）⇒ **归档路径逐位不变**（门 4）；
#   2. **φ 必须 f64**（与 `g.phi` 同精度）⇒ **不得为省事降精度**；
#   3. **滑动窗口用 A/B 交替**（goal 任务(3) 逐字）⇒ `n_keep=2` 时
#      **完全不需要删除**，磁盘天然恒定；`n_keep>2` 才用步号命名 + `_superseded`，
#      且 `_superseded` 用**滚动名 + `os.replace` 覆盖**（**不用 `rm`**，遵守硬禁令）。
#
#   ## 为什么不能用 `pickle` 存/取**整个对象**
#   `windowB_par.ParCtx` 含 `ThreadPoolExecutor`/`threading.local`，
#   `dG_of_T`/`T_of_t`/`pf._h_src` 是闭包/绑定方法 ⇒ **实测都不可 pickle**
#   ⇒ 本文件**只 pickle 数据**（`_nuc` 的纯值字典、RNG 的 state），
#   恢复走「**同一命令行重建对象 + 逐项回填**」（见 `--resume`）。
# ══════════════════════════════════════════════════════════════════════════════
CKPT_VER = 1
#: 版本哈希要覆盖的引擎文件（goal 硬要求「记录复现命令 + seed + 版本哈希」）
CKPT_ENGINE_FILES = ('windowB_surface.py', 'windowB_pf3d.py', 'windowB_par.py',
                     'windowB_lath.py', 'windowB_acct.py', 'windowB_pf.py',
                     '_bk_exp.py')


def _engine_sha():
    """引擎文件的 `sha256` 前 16 位（JSON 串）。**读不到就给 `?`，不抛。**"""
    import hashlib
    base = os.path.dirname(os.path.abspath(__file__))
    h = {}
    for fn in CKPT_ENGINE_FILES:
        try:
            with open(os.path.join(base, fn), 'rb') as fh:
                h[fn] = hashlib.sha256(fh.read()).hexdigest()[:16]
        except Exception:
            h[fn] = '?'
    return json.dumps(h, sort_keys=True)


def _ckpt_gather(g, it, t_sim, drv, N, L, nv, nreg, vmap, tstep=None):
    """★ **只读地**采集「续跑所需的全部状态」（goal 任务(1) 的 1a–1k）。

    **本函数不得修改 `g` 或任何入参** —— 它每步都可能被调用，
    一旦有副作用就会破坏"归档逐位不变"（门 4）。
    """
    import pickle
    st = {}

    # ── 1k 元信息 ─────────────────────────────────────────────────────
    st['ckpt_ver'] = np.int64(CKPT_VER)
    st['step'] = np.int64(it)
    st['t_s'] = np.float64(t_sim)
    st['N'] = np.int64(N)
    st['L'] = np.float64(L)
    st['nv'] = np.int64(nv)
    st['nreg'] = np.int64(nreg)
    st['phi_prec'] = np.array(str(getattr(g, 'phi_prec', 'f64')))
    st['cmdline'] = np.array(' '.join(str(x) for x in sys.argv))
    st['engine_sha'] = np.array(_engine_sha())
    st['vmap_keys'] = np.array(sorted(vmap), dtype=np.int64)
    st['vmap_vals'] = np.array([int(vmap[k]) for k in sorted(vmap)], dtype=np.int64)

    # ── 1a ★ 完整 φ（f64，**不是带内**）───────────────────────────────
    #   ⚠ 收窄成 f32 会**主动丢精度** ⇒ goal 明令禁止。dtype 原样保留。
    st['phi'] = np.asarray(g.phi)

    # ── 1c 引擎计时 / 节拍 ────────────────────────────────────────────
    st['t'] = np.float64(getattr(g, 't', 0.0))
    _T = getattr(g, 'T', None)
    st['T'] = np.float64(_T) if _T is not None else np.float64(np.nan)
    _df = getattr(g, 'df', None)
    st['df'] = np.asarray(_df) if _df is not None else np.zeros(1)
    st['_cnt'] = np.int64(getattr(g, '_cnt', 0))
    st['_t_since_reinit'] = np.float64(getattr(g, '_t_since_reinit', 0.0))
    st['_forced_reinit'] = np.int64(getattr(g, '_forced_reinit', 0))
    st['_need_reinit'] = np.int64(1 if getattr(g, '_need_reinit', False) else 0)
    st['dG_max'] = np.float64(getattr(g, 'dG_max', np.nan))
    st['_fp_cnt'] = np.int64(getattr(g, '_fp_cnt', 0))

    # ── 1b/1d ★ 形核通道（`_nuc` 整字典 + RNG state + sites + dbg['ok']）──
    nuc = getattr(g, '_nuc', None) or {}
    dbg = nuc.get('dbg') or {}
    # ★ `dbg['ok']` 单独拎出来（`:2534` 用它的**奇偶**决定 attach 先试哪一端）
    st['nuc_ok'] = np.int64(int(dbg.get('ok', 0) or 0))
    st['nuc_n_activated'] = np.int64(int(nuc.get('n_activated', 0) or 0))
    # RNG：只存**位发生器的 state**（PCG64 只有两个整数）
    _rng = nuc.get('rng')
    try:
        st['nuc_rng_state'] = np.frombuffer(
            pickle.dumps(_rng.bit_generator.state), dtype=np.uint8)
    except Exception:
        st['nuc_rng_state'] = np.zeros(0, np.uint8)
    # 位点池：list[(k, xyz)] ⇒ (n,4) float（k 放第 0 列）
    _sites = nuc.get('sites') or []
    _arr = np.zeros((len(_sites), 4), float)
    for _i, _s in enumerate(_sites):
        try:
            _arr[_i, 0] = float(_s[0])
            _arr[_i, 1:4] = np.asarray(_s[1], float).ravel()[:3]
        except Exception:
            pass
    st['nuc_sites'] = _arr
    # 其余**纯值**键（31 个配置键 + dbg）⇒ **pickle 数据**（不是 pickle 对象）
    #   ⚠ 用 pickle 而不是 `int(v)`：N12 的教训 —— `dbg` 里有 `list` 型值，
    #     无条件 `int()` 会让**整份文件**写崩（`nuc_dbg.json` 曾写出 0 字节）。
    _cfg = {k: v for k, v in nuc.items() if k not in ('rng', 'sites')}
    try:
        st['nuc_cfg_pkl'] = np.frombuffer(pickle.dumps(_cfg), dtype=np.uint8)
    except Exception:
        st['nuc_cfg_pkl'] = np.zeros(0, np.uint8)

    # ── 1e ★ 热启动 / 口径状态（最容易漏的一类）──────────────────────
    _ae = getattr(g, '_ae_eps', None)
    st['ae_eps'] = np.asarray(_ae) if _ae is not None else np.zeros(0, np.float32)
    _pf = getattr(g, 'pf', None)
    _lag = getattr(_pf, '_eps0_lag', None) if _pf is not None else None
    st['pf_eps0_lag'] = np.asarray(_lag) if _lag is not None else np.zeros(0, np.float32)
    # `pf.phi` 只在**物化档**下才是"上一次弹性解的 h"（诊断口径）⇒ 记录是否物化
    st['pf_phi_mode'] = np.array(str(getattr(g, '_pf_phi_mode', '?')))
    if (str(getattr(g, '_pf_phi_mode', '')) == 'materialized'
            and _pf is not None and getattr(_pf, 'phi', None) is not None):
        st['pf_phi'] = np.asarray(_pf.phi)
    else:
        st['pf_phi'] = np.zeros(0, np.float32)

    # ── 1f ★ `npref_tab`（`_npref_of()` 拿不到会 **raise**）────────────
    _np_tab = getattr(g, 'npref_tab', None)
    try:
        st['npref_pkl'] = np.frombuffer(
            pickle.dumps(_np_tab) if _np_tab is not None else b'', dtype=np.uint8)
    except Exception:
        st['npref_pkl'] = np.zeros(0, np.uint8)

    # ── 1g 可选通道（按开关）────────────────────────────────────────
    for _k, _attr in (('c', 'c'), ('Gam_mol', 'Gam_mol'), ('Gam', 'Gam'),
                      ('Gam_derived', '_Gam_derived'), ('psi', 'psi')):
        _v = getattr(g, _attr, None)
        st['aux_' + _k] = np.asarray(_v) if _v is not None else np.zeros(0, np.float32)

    # ── 1h ★ 模块全局（**它们不是实例属性** ⇒ 不显式存就会静默退档）──
    try:
        import windowB_surface as _ws
        st['g_ufv_mode'] = np.array(str(getattr(_ws, '_UFV_MODE', '?')))
        st['g_bbox_mode'] = np.array(str(getattr(_ws, '_BBOX_MODE', '?')))
    except Exception:
        st['g_ufv_mode'] = np.array('?')
        st['g_bbox_mode'] = np.array('?')

    # ── 1i ★ 外部注入开关（类内**从不赋值** ⇒ 对象快照拍不到）──────
    _inj = {}
    for _k in ('pair_curvature', '_pc_legacy', 'pair_sig_from_seed', 'facet_excl',
               'wrap_strict', 'reinit_bbox', 'reinit_bbox_margin',
               'reinit_skip_tol', 'reinit_guard_region', 'reinit_strict',
               'diag_terms_on', 'diag_edv_on'):
        if hasattr(g, _k):
            _inj[_k] = getattr(g, _k)
    try:
        st['injected_pkl'] = np.frombuffer(pickle.dumps(_inj), dtype=np.uint8)
    except Exception:
        st['injected_pkl'] = np.zeros(0, np.uint8)

    # ── 1j ★ 驱动层状态（**不在对象里** ⇒ 由调用方传进来）────────────
    _drv = dict(drv or {})
    _dV = _drv.get('_qs_dV')
    st['drv_dV'] = (np.asarray(_dV, float) if _dV is not None
                    else np.zeros(0, float))          # ★ 滑动窗口列表（顺序敏感）
    _drv2 = {k: v for k, v in _drv.items() if k != '_qs_dV'}
    try:
        st['drv_pkl'] = np.frombuffer(pickle.dumps(_drv2), dtype=np.uint8)
    except Exception:
        st['drv_pkl'] = np.zeros(0, np.uint8)

    # ── 步时统计（便于事后看"哪一段慢"）────────────────────────────
    st['tstep'] = np.asarray(tstep or [], float)
    return st


def _ckpt_write(outdir, st, keep=2, atomic=True, milestone=False):
    """★ **原子写 + 滑动窗口**（goal 任务(3)）。

    ## 命名
    * **`n_keep == 2`**（默认）⇒ **A/B 交替**（`ckpt_A.npz` / `ckpt_B.npz`）
      ⇒ **磁盘恒定，且**完全不需要删除****（goal 逐字推荐的做法）；
    * **`n_keep != 2`** ⇒ 步号命名（`ckpt_%06d.npz`）+ 多余帧 `os.replace` 进
      `_superseded/`（**滚动名覆盖，不用 `rm`** —— 遵守硬禁令）；
    * **里程碑**（`ckptms_%06d.npz`）**不参与滑动**。

    ## 原子性
    `atomic=True` 时先写 `<name>.tmp` 再 `os.replace()` ⇒
    **任何时刻都有一帧是完整的**（被 `kill` 也只会留一个 `.tmp`）。
    """
    cdir = os.path.join(outdir, 'ckpt')
    os.makedirs(cdir, exist_ok=True)
    it = int(st['step'])
    if milestone:
        name = 'ckptms_%06d.npz' % it
    elif int(keep) == 2:
        name = 'ckpt_%s.npz' % ('A' if (it % 2 == 0) else 'B')      # ★ A/B 交替
    else:
        name = 'ckpt_%06d.npz' % it
    final = os.path.join(cdir, name)
    tmp = final + '.tmp'
    if atomic:
        np.savez_compressed(tmp, **st)
        os.replace(tmp, final)
    else:
        np.savez_compressed(final, **st)

    # ── 滑动窗口（只对**非里程碑**、且 `keep != 2` 时）──────────────
    if (not milestone) and int(keep) != 2:
        import re as _re
        fs = []
        for f in os.listdir(cdir):
            m = _re.fullmatch(r'ckpt_(\d{6})\.npz', f)
            if m:
                fs.append((int(m.group(1)), f))
        fs.sort()
        if len(fs) > max(int(keep), 1):
            sup = os.path.join(cdir, '_superseded')
            os.makedirs(sup, exist_ok=True)
            # ★ 滚动名：`os.replace` 覆盖旧内容 ⇒ **磁盘恒定，且没有 `rm`**
            for _i, (_s, f) in enumerate(fs[:-max(int(keep), 1)]):
                try:
                    os.replace(os.path.join(cdir, f),
                               os.path.join(sup, 'ckpt_rolled_%d.npz' % (_i % 2)))
                except Exception:
                    pass
    return final


def read_series(path):
    """读 `series.csv` ⇒ `{列名: np.ndarray}`；整型列给 int，数值列给 float，
    其余（如 `runs='5/3/1/2/4/6'`）原样给 str。

    ★★ 为什么不能用 `np.genfromtxt(..., names=True, dtype=None)`：
    `runs` 这一列是**斜杠分隔的字符串**，而 genfromtxt 的类型自动升级会按
    `bool→int→float→complex→longdouble` 一路试到底，最后抛
    `ValueError: Cannot convert string '1/2'`。
    实测后果：`dry_gs2` **老老实实跑完 200 步**（数据全部落盘、完好），
    却在收尾打印判决时崩掉 ⇒ **主判据一个字都没打出来**，
    日志尾部看起来像"跑挂了"。（`--dry-run` 走不到这里，所以之前没暴露。）
    """
    import csv as _csv
    with open(path, newline='') as f:
        rows = list(_csv.DictReader(f))
    if not rows:
        return {}
    out = {}
    for c in rows[0]:
        vals = [r[c] for r in rows]
        for conv in (int, float):
            try:
                out[c] = np.array([conv(v) for v in vals])
                break
            except (TypeError, ValueError):
                continue
        else:
            out[c] = np.array(vals, dtype=object)
    return out


def sha256(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def build_table(laths, omega_max_deg, omega_mode, a_ax=None, gamma0=0.15,
                f2_lam=0.0):
    """按 `--laths` 建板条表。`a_ax` 给出时把倾转轴定为板条长轴。

    ★ R164：`f2_lam` 透传给 `LathTable`（**F2 的配对依赖**，`§122`）。
      `0.0`（默认）⇒ `gtab` 的 F2 项**保持 NaN** ⇒ 引擎走原标量路径 ⇒ **逐位不变**。
    """
    M = len(laths)
    om = WL.default_omega(M, omega_max_deg, axis=a_ax, mode=omega_mode)
    return WL.LathTable(laths, omegas=om, eps0_var=EPS0, npref_var=NPF,
                        gamma0=gamma0, f2_lam=f2_lam)


def _block_span_n(g, n_hab, BM_):
    """当前 α′ 集合沿 n* 的 (中心, 最小投影, 最大投影)。只在小包围盒上算。"""
    reg = g.region()
    m = (reg > 0)
    if not m.any():
        return None
    bb = BM_._bbox_of(m, pad=2)
    cc = BM_._sub_coord(bb, g.dx)
    pn = (n_hab[0] * cc[0][:, None, None] + n_hab[1] * cc[1][None, :, None]
          + n_hab[2] * cc[2][None, None, :])
    v = pn[m[bb]]
    return float(v.min()), float(v.max())


def _js_diag(v):
    """把任意**诊断值**转成 JSON 可序列化的原生类型（**尽量不抛**）。

    ★ N12（2026-10-04）：原来落盘时对每个值**无条件 `int()`**
      ⇒ 只要有一个键不是标量（如 `list`）就抛异常 ⇒ 被 `except` 吞掉
      ⇒ **`nuc_dbg.json` 变成 0 字节，整份形核诊断全丢**（实测 `_r535diag`）。
    ⇒ 改成**类型感知**：
        `bool/np.bool_` → `bool`（**必须先于 int 判**，否则 `True` 会变成 `1`）
        `int/np.integer` → `int` ｜ `float/np.floating` → `float`（非有限值转 `str`）
        `ndarray` → 递归 `tolist()` ｜ `list/tuple` → 逐个递归 ｜ `dict` → 键转 `str`
        `None/str` → 原样 ｜ 其他 → `str`
    ⚠ **提到模块级是为了能被单测**（`_r538_n12check.py`）；
      原来它嵌在 `run()` 里 ⇒ 只能靠跑 601 步来验证，代价太大。
    """
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        _f = float(v)
        return _f if np.isfinite(_f) else str(_f)
    if isinstance(v, np.ndarray):
        return _js_diag(v.tolist())
    if isinstance(v, (list, tuple)):
        return [_js_diag(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _js_diag(x) for k, x in v.items()}
    if v is None or isinstance(v, str):
        return v
    return str(v)


def _js_diag_key(k, v, notes=None):
    """**逐键降级**：某个键转不动 ⇒ 只把**那个键**变成 `str` 并记账，**绝不**连累整份文件。

    ★ N12 的第 ② 条修法。本仓 `R30_AUDIT_LEDGER.md §R31` 已经因为
      "嵌套 ndarray 漏转 ⇒ 静默落盘失败"修过一次；这次是"非标量/标量混用"再来一遍
      ⇒ 用**降级 + 记账**从结构上堵死这一类。

    ⚠⚠ **降级本身也必须"不可能失败"**（`_r538` 的 T8b 实测抓出来的）：
      第一版这里写的是 `return str(v)` —— 而 `str(v)` **正是刚刚抛出来的那一步**
      ⇒ 若某个对象的 `__str__` 也抛，异常会**继续往外冒** ⇒ **整份文件照样丢**。
      ⇒ 兜底改成 **`'<%s>' % type(v).__name__`**：只读类型名，**不执行用户代码**
      （`type(v).__name__` 对任何对象都安全），并再套一层 `try` 保证**绝对不抛**。
      **⇒ 修法：降级路径必须是"全函数"。**
    """
    try:
        return _js_diag(v)
    except Exception as exc:                                    # noqa: BLE001
        if notes is not None:
            notes.append('%s: %s' % (k, exc))
        try:
            # ⚠ **不要**在这里用 `str(v)` —— 它可能就是刚刚抛的那个（T8b 实测）
            return '<%s>' % type(v).__name__
        except Exception:                                       # noqa: BLE001
            return '<unrepresentable>'


def run(a):
    N, L = a.N, a.dx_nm * 1e-9 * a.N
    dx = L / N
    tag = a.tag or time.strftime('%m%d_%H%M%S')
    outdir = os.path.join(a.out, '%s_%s' % (a.arm, tag))
    os.makedirs(outdir, exist_ok=True)
    P = lambda s: print(s, flush=True)
    P('=' * 104)
    P('_bk_exp  臂=%s  N=%d  Δx=%.2f nm  L=%.3f µm  steps=%d  tag=%s'
      % (a.arm, N, dx * 1e9, L * 1e6, a.steps, tag))
    P('=' * 104)

    # ---------------- 臂定义 ----------------
    laths = [int(x) for x in a.laths.split(',') if x.strip()]
    M = len(laths)
    single_field = (a.arm == 'gneg')
    if single_field:
        laths_eff = [laths[0]]
        P('★ 负对照 gneg：**%d 根板条全部播进同一个场 φ_%d** ⇒ F3 应恒为 0'
          % (M, laths[0]))
    else:
        laths_eff = laths

    # ================= ★★★★★ R131（**用户裁定 C**）：选支规则受控对照 ==========
    #   背景（`R30_AUDIT_LEDGER.md` **§93 / §102**）：
    #     `NPF[v] = argmin_normal(C, ε)` 是**弹性能泛函的极小法向**，**不是**晶体学惯习面。
    #     按晶体学的「惯习面 = 不变平面」（`Fᵀp = p`）判据，**`V1`/`V3`/`V8`** 三个变体的
    #     厚向应是 `a` 而不是 `NPF`（差 82°），另 9 个两者一致。
    #   ⇒ 用户裁定：**两条都跑，作受控对照**（不预设哪条对）。
    #   ⇒ 本开关 `--rank1-swap invariant`：**只对判据说"该换"的那些变体**把 `n*` 与 `a` 对调。
    #     ⚠ `w` 不变（`w = n × a`，对调后 `cross(a,n) = −cross(n,a)` ⇒ **同一条线**）。
    #     ⚠ 默认 `none` ⇒ **逐位不变**（由 `_r30_regress.sh` 把关）。
    #   ⚠ **受影响集合是算出来的，不是写死的** —— 判据自带正对照（合成 IPS 上必须选 `p`）。
    def _rB(F, u):
        """`rB(u) = ‖(F−I)·B_u‖₂`（`B_u` = 平面 ⟂u 的正交基）。
        `rB = 0` ⟺ 该平面**不变** ⇒ `u` 是惯习面法向。"""
        u = np.asarray(u, float); u = u / np.linalg.norm(u)
        t = (np.array([1.0, 0.0, 0.0]) if abs(u[0]) < 0.9
             else np.array([0.0, 1.0, 0.0]))
        b1 = np.cross(u, t); b1 /= np.linalg.norm(b1)
        b2 = np.cross(u, b1)
        return float(np.linalg.norm((np.asarray(F, float) - np.eye(3))
                                    @ np.stack([b1, b2], 1), 2))

    _SWAP = set()
    if a.rank1_swap == 'invariant':
        from windowB_ti64_variants import variants as _VARF
        _E_, _FV_, _M_ = _VARF()
        # ---- 正对照：合成 IPS `F = I + 0.2·d pᵀ` 上，判据必须选 `p` ----
        _p = np.array([0.0, 0.0, 1.0]); _d = np.array([1.0, 0.0, 0.0])
        _Fi = np.eye(3) + 0.2 * np.outer(_d, _p)
        if not (_rB(_Fi, _p) < _rB(_Fi, _d)):
            raise SystemExit('✗✗ 选支判据**正对照失败**（合成 IPS 上没选中 `p`）'
                             ' ⇒ `--rank1-swap invariant` 不可用')
        for _v in range(1, len(EPS0) + 1):
            _n0 = np.asarray(NPF[_v], float)
            _n0 = _n0 / np.linalg.norm(_n0)
            _R = W.LevelSetMulti._rank1_axes(np.asarray(EPS0[_v - 1], float), _n0)
            _a0 = np.asarray(_R[1], float)
            _a0 = _a0 / np.linalg.norm(_a0)
            if _rB(_FV_[_v - 1], _a0) < _rB(_FV_[_v - 1], _n0):
                _SWAP.add(_v)
        P('★★★★★ **选支受控对照（用户裁定 C）**：`--rank1-swap invariant`')
        P('   判据 `rB(u)=‖(F−I)B_u‖₂`（平面 ⟂u 内向量不动）；正对照（合成 IPS）**PASS**')
        P('   **受影响变体（`NPF` 不是不变平面法向 ⇒ 与 `a` 对调）：%s**'
          % (sorted(_SWAP) if _SWAP else '无'))
        for _v in sorted(_SWAP):
            _n0 = np.asarray(NPF[_v], float); _n0 = _n0 / np.linalg.norm(_n0)
            _R = W.LevelSetMulti._rank1_axes(np.asarray(EPS0[_v - 1], float), _n0)
            _a0 = np.asarray(_R[1], float); _a0 = _a0 / np.linalg.norm(_a0)
            P('     V%-2d  rB(n*)=%.4e  rB(a)=%.4e  ⇒ 用 `a`（差 %.1f×）'
              % (_v, _rB(_FV_[_v - 1], _n0), _rB(_FV_[_v - 1], _a0),
                 _rB(_FV_[_v - 1], _n0) / max(_rB(_FV_[_v - 1], _a0), 1e-300)))

    n_hab = np.asarray(NPF[laths[0]], float); n_hab /= np.linalg.norm(n_hab)
    # ★★ 拿 a/w 轴：**直接调静态方法**，不再造一个临时 `LevelSetMulti`
    #   （临时对象会再跑一遍 `_argmin_normal`；实测 4 臂并发时构造 >15 min）。
    _nref0, _, _ = W.argmin_normal_cached(C, np.asarray(EPS0[laths[0] - 1], float))
    _R0 = W.LevelSetMulti._rank1_axes(np.asarray(EPS0[laths[0] - 1], float), _nref0)
    w_ax = np.asarray(_R0[2], float); w_ax /= np.linalg.norm(w_ax)
    a_ax = np.asarray(_R0[1], float); a_ax /= np.linalg.norm(a_ax)
    if laths[0] in _SWAP:                       # ★ R131：对调 n* 与 a（w 不变）
        n_hab, a_ax = a_ax, n_hab

    lt = build_table(laths_eff, a.omega_max_deg, a.omega_mode, a_ax=a_ax,
                     gamma0=a.gamma0, f2_lam=a.f2_pair_gamma)
    P(lt.summary())
    # ★★★ R182（`R30_AUDIT_LEDGER.md` §129 / **P1-45**）：
    #   `--omega-mode perstep` 的诊断 —— 必须**显式打印**它把 `--omega-max-deg`
    #   当成了"逐界面步长"，否则读数的人会以为那还是总张角（硬规则 ⑩）。
    if str(a.omega_mode) == 'perstep':
        _M = len(laths_eff)
        P('★★★ R182（`§129`/P1-45）**ω 改用逐界面步长**：'
          '`Δθ` = **%.4f°**（`--omega-max-deg` 在此模式下是**每步**的取向差，'
          '**不是**总张角）' % a.omega_max_deg)
        P('   ⇒ 相邻同变体对的 `γ_RS(Δθ)` 与 **M 无关**'
          '（M=%d；`ladder` 模式下它是 `θ_max/(M−1)`）' % _M)
        if _M > 1:
            _dth_lad = a.omega_max_deg / (_M - 1)
            P('   ⇒ 与 `ladder` 的差别：ladder 的相邻步长会是 **%.4f°**'
              '（本臂 %.4f°）⇒ 相差 **%.2f 倍**'
              % (_dth_lad, a.omega_max_deg,
                 (a.omega_max_deg / _dth_lad) if _dth_lad > 0 else float('nan')))
        P('   ⚠ 归档臂**全部**是 `ladder`（默认）⇒ 本开关**默认关闭**、'
          '打开即**不是**归档路径，跨模式比较须当**新配置**看待。')
    if a.f2_pair_gamma > 0:
        P('★★★★ R164（`§122`）**F2 的配对依赖已开**：`lambda` = %.3f；'
          '`Δε_ref` = %.6e；填入的 F2 对数 = **%d**'
          % (a.f2_pair_gamma, lt.de_ref, lt.n_f2))
        P('   公式：`γ_F2(v,w) = γ₀·[(1−λ) + λ·min(1, ‖Δε(v,w)‖/Δε_ref)]`')
        P('   ⚠ 记账：这条补法**促进 packet**（同惯习面对便宜），'
          '而 `§94` 的 `k*=6` 自协调要"6 个惯习面各取一个" ⇒')
        P('      **两个目标不同**，必须与 `--f2-pair-gamma 0` 做受控对照，**不预设哪个对**。')
    gmax, g2ab, wets = lt.wetting_report()
    P('润湿判据（(4.6)）：γ_RS 最大 %.4f  vs  2γ_αβ = %.4f  ⇒ %s'
      % (gmax, g2ab, '**润湿**' if wets else '不润湿（C-1）'))
    if a.arm == 'wet':
        P('★ 臂 wet：F3 面能被**规定**为 γ_f=%.4f J/m²（人为亚稳膜）' % a.gamma_film)
        lt.gtab[np.isfinite(lt.gtab)] = float(a.gamma_film)
    elif a.arm == 'gpos':
        lt.gtab[np.isfinite(lt.gtab)] = 100.0
    elif a.arm == 'g0':
        lt.gtab[np.isfinite(lt.gtab)] = 0.0
    # ★★★ `auto`：**面带 ψ 判决臂**（`BLOCK_DERIVATION` §4.6 / 预言 P-2）。
    #   F3 面能按 γ_Σ(ψ) 混合，ψ 在 F3 胞上按局域 Allen–Cahn 演化。
    #   ⚠ `psi0` **不能取 1.0**：ψ≡0 与 ψ≡1 都是 (4.9) 的**精确不动点**
    #     （f'(0)=f'(1)=g'(0)=g'(1)=0）⇒ 从 1.0 出发一步都不动。
    #     取 0.99 等价于给一个无穷小扰动（见 `windowB_film.py` 的记账）。

    eps0 = [np.asarray(EPS0[v - 1], float).copy() for v in laths_eff]
    npref = {i + 1: np.asarray(NPF[v], float) for i, v in enumerate(laths_eff)}
    nv = len(laths_eff)

    # ================= ★★★ R29：athermal 形核律的**钟**（T → 驱动力 → 事件）=========
    #   用户要求：「能否使用类似形核率等等的方式让模型在现有物理公式与框架的基础上
    #   合理运转」。本块把 `windowB_closure` 的 C-2/C-3 闭式接进引擎：
    #     ① 温度钟 `T(t) = T_start − q·t`（`windowB_km.linear_cool`）；
    #     ② 驱动力 `df(T) = drive_of_T(T; T0, DS)` —— 引擎 T6 已有 `set_T` 入口；
    #     ③ 板条数 `n(T) = α_KM·(M_s − T)` —— **`n` 从规定值变成导出量**；
    #     ④ 步长 `dt = cfl·dx/(MOB·ΔG_v(T))` —— 随降温自动变小（速度变大）。
    #   ⚠ 全部 gated 在 `--nuc-law athermal` 上 ⇒ 默认 `cadence` 路径**逐位不变**。
    _athermal = (a.nuc_law == 'athermal')
    _alpha = float(a.alpha_km)
    # ★ 时钟起点默认 = C-2 的 **T_1**（预摆的第 1 片就是第 1 根，见
    #   `windowB_closure.T_start_of_clock`）。从 `M_s` 起会让事件序列整体错位一根。
    _Tstart = (float(a.T_start) if float(a.T_start) > 0
               else CL.T_start_of_clock(_alpha))
    _Tend = float(a.T_end)
    _L_lath = float(a.plate_L) * 1e-9
    _q_source = 'user'
    if _athermal:
        _dG_start = float(KM.drive_of_T(_Tstart, T0_TI64, DS_REF))
        if _dG_start <= 0:
            raise SystemExit('✗ athermal：T_start=%.2f K 必须 < T0=%.1f K'
                             % (_Tstart, T0_TI64))
        _v_worst = CL.v_of_MOB(MOB, _dG_start)
        _q_cap = CL.q_max_ordered(_v_worst, _alpha, _L_lath)
        if float(a.cool_rate) > 0.0:
            _q = float(a.cool_rate)
        else:
            _q = _q_cap * float(a.cool_ratio)
            _q_source = 'C-3 有序性上界 × %.2f' % float(a.cool_ratio)
        _ok_o, _ratio_o, _ = CL.ordered_ok(_q, MOB, _alpha, _L_lath,
                                           dG_worst=_dG_start)
        _n_law = CL.n_lath_int(_Tend, _alpha)
        _T_of_t = KM.linear_cool(_Tstart, _Tend, (_Tstart - _Tend) / _q)
        _dG_of_T = (lambda T: KM.drive_of_T(T, T0_TI64, DS_REF))
        _df_start = float(_dG_of_T(_Tstart))
        P('★★★ R29 athermal 形核律：α_KM=%.4e /K  冷速 q=%.4e K/s（%s）'
          % (_alpha, _q, _q_source))
        P('   时钟起点 T_start = T_1 = M_s − 1/α_KM = %.2f K（**不是 M_s**：'
          'n(M_s)=0 ⇒ t=0 预摆的那片就是第 1 根）' % _Tstart)
        P('   T: %.1f → %.1f K，t_sim=%.4e s；df: %.4e → %.4e J/m³'
          % (_Tstart, _Tend, _T_of_t.t_cool, _df_start, float(_dG_of_T(_Tend))))
        P('   导出板条数 n = floor(α_KM·(M_s − T_end)) = **%d**（当前 nv=%d）'
          % (_n_law, nv))
        P('   形核温度 T_k = M_s − k/α_KM: %s'
          % ' '.join('T%d=%.1f' % (k, CL.T_of_k(k, _alpha)) for k in range(1, _n_law)))
        # ★★★★★ R502：**"块数"口径**的启动横幅（必须打，不许静默）
        _Bt0 = int(getattr(a, 'nuc_block_target', 0) or 0)
        _Af = a.plate_L * 1e-9 * a.plate_W * 1e-9
        _Bmax = (L * L) / max(_Af, 1e-300)
        if _Bt0 > 0:
            _Ntot = _Bt0 * _n_law
            P('   ★★ **块数口径（R502）**：`--nuc-block-target %d`' % _Bt0)
            P('      总根数 = B · n(T_end) = %d × %d = **%d 根**'
              '（C-2 的 `n` 是**每块**根数，不是全盒总数）' % (_Bt0, _n_law, _Ntot))
            P('      几何上界 B_max = L_box²/A_f = %.1f µm² / %.4f µm² = **%.0f**'
              ' ⇒ 本配置 %s'
              % (L * L * 1e12, _Af * 1e12, _Bmax,
                 '在界内 ✅' if _Bt0 <= _Bmax else '**超界 ❌**'))
            P('      ⚠ **块的数目是输入、不是涌现** —— 框架 `limitations()` 第 1 条明写'
              '「面内并列的多个 block…本轮不做」')
            P('      ⚠ 要真拿到 %d 根，`--laths` 必须至少 %d 个（当前 nv=%d）'
              % (_Ntot, _Ntot, nv))
            # ★★★★★ 2026-10-04（**N8**；判定见 `R2_PARAM_VERDICTS.md §0 N8`
            #   与 `R525_TASK5_PARAM_FINDINGS.md §5`；用户拍板"自动推导 + 硬校验"）
            #   ## 缺陷
            #     `--nuc-block-target B`（**目标**块数）与 `--nuc-fresh-every K`
            #     （**实际**建块节奏）是**两个独立旋钮**，此前**无人校验**。
            #   ## 闭式（`_bk_exp.py` 下面的 `_fresh_now = ((n_ath_tgt % K) == 0)`，
            #   ##        `n_ath_tgt` 是**自增前**的值 ⇒ fresh 出现在第 1, K+1, 2K+1… 个事件）
            #     总尝试 `N = B·n(T_end)`；实际块数 `= ceil(N / K)`。要它 `= B`：
            #         ceil(B·n / K) = B   ⇒   **K = n(T_end)**
            #     ⚠ **与 `B` 无关** ⇒ 这是唯一解，不是调出来的。
            #   ## 实测反例（`_r520c`）
            #     `K = 6`、`n(T_end) = 5` ⇒ 实测 fresh 事件号 `[13,19,25,31]` = **4 块**
            #     （目标 8）⇒ `_tgt` 仍按 8 算 ⇒ **多余的尝试全被引擎拒**
            #     （实测 39 次尝试只成功 17 次，**22 次被拒 = 55%**）。
            #   ## 惰性
            #     `--nuc-block-target 0`（**默认**）⇒ 整段不进 ⇒ **归档路径逐位不变**。
            #     `K` 也只在 `--nuc-init > 0` 时才被下面用到（见 `_K > 0 and a.nuc_init > 0`）。
            _K_exp = int(_n_law)
            _K_got = int(getattr(a, 'nuc_fresh_every', 0) or 0)
            if a.nuc_init <= 0:
                P('      ⚠ `--nuc-fresh-every` 只在 `--nuc-init > 0` 时生效'
                  '（当前 `--nuc-init %d`）⇒ 本算例的 fresh/stack 交错**不生效**，'
                  '块数由 `--laths` 的变体分布决定。' % a.nuc_init)
            elif _K_got == 0:
                # **自动推导**：不传 ⇒ 取 `n(T_end)`（用户 2026-10-04 拍板）
                a.nuc_fresh_every = _K_exp
                P('      ★ **N8 自动推导**：`--nuc-fresh-every` 未传 ⇒ '
                  '自动取 **K = n(T_end) = %d**'
                  '（⇒ 实际块数 `ceil(B·n/K) = %d` = `--nuc-block-target %d` ✅）'
                  % (_K_exp, -(-_Ntot // _K_exp), _Bt0))
            elif _K_got != _K_exp:
                raise SystemExit(
                    '❌ **`--nuc-fresh-every %d` 与 `--nuc-block-target %d` 不自洽**（N8）\n'
                    '   闭式：实际块数 = `ceil(B·n(T_end) / K)`，要它等于 `B` ⇒ **`K = n(T_end)`**\n'
                    '     本算例：`B = %d`、`n(T_end) = floor(α_KM·(M_s − T_end)) = %d`\n'
                    '     ⇒ **`K` 必须取 %d**，你传了 %d ⇒ 实际只会建 **%d 个块**\n'
                    '\n'
                    '   ⚠ 最新实测（`_r520c`，`K=6` 而 `n=5`）：实测只建 **4 块**，\n'
                    '     而 `_tgt` 仍按 `B·n` 算 ⇒ 引擎被迫拒绝大量事件\n'
                    '     （39 次尝试只成功 17 次，**22 次被拒 = 55%%**）。\n'
                    '   ⇒ 修法：**去掉 `--nuc-fresh-every`**（自动取 %d），或显式传 `--nuc-fresh-every %d`。\n'
                    '   依据：`R525_TASK5_PARAM_FINDINGS.md §5`（用户 2026-10-04 拍板"自动推导+硬校验"）。'
                    % (_K_got, _Bt0, _Bt0, _K_exp, _K_exp, _K_got,
                       -(-_Ntot // max(_K_got, 1)), _K_exp, _K_exp))
            else:
                P('      ✅ **N8 校验通过**：`--nuc-fresh-every %d` == `n(T_end)` = %d '
                  '⇒ 每块各得 %d 根' % (_K_got, _K_exp, _K_exp))
            if _Bt0 > _Bmax:
                P('   ⚠⚠ **`--nuc-block-target %d` 超过几何上界 %.0f**'
                  '（每块占满一个 A_f 足迹 ⇒ 面内平铺不下这么多）'
                  '⇒ 本算例的"块数"在几何上不成立，**结论不得当成物理**。'
                  % (_Bt0, _Bmax))
        else:
            P('   ★ 块数口径（R502）：`--nuc-block-target 0`（默认）⇒ **沿用旧口径**：'
              '全盒事件上界 = `n(T)`')
            P('      ⚠ 记账：这等于把 C-2 的"**每块**根数"当成了"**全盒总数**"'
              '（`limitations()` 第 1 条的适用范围之外）')
            P('      几何上界 B_max = **%.0f**（若要按"块数 × 每块根数"放开，用它作参考）'
              % _Bmax)
        P('   C-3 有序性：Δt_grow/Δt_nuc = **%.3f**（判据 ≤1）%s'
          % (_ratio_o, '' if _ok_o else '  ⚠ **违反 ⇒ 本次运行处于 burst regime，必须记账**'))
        P('   C-3 步数下界 = %.0f（从 T_1 起）；C-5 β_h 下界 = %.3f（当前 --beta-h %.2f）'
          % (CL.steps_min_ordered(_alpha, _L_lath, dx, 0.15, _Tend, _Tstart),
             CL.beta_h_min(a.steps, dx, a.plate_T * 1e-9), a.beta_h))
        if nv < _n_law:
            P('   ⚠⚠ **表示上限不足**：nv=%d < 导出的 n=%d ⇒ 块会被截断在 nv 根'
              % (nv, _n_law))
        _beta_floor = CL.beta_h_min(a.steps, dx, a.plate_T * 1e-9)
        if _beta_floor > a.beta_h:
            P('   ⚠⚠ **C-5 不满足**：%d 步 / Δx=%.1f nm / t=%.0f nm 需要 β_h ≥ %.3f，'
              '而当前 %.2f ⇒ 板条会增厚 ≈ e^{%.2f}× ⇒ 厚度判据 V-8b 不适用'
              % (a.steps, dx * 1e9, a.plate_T, _beta_floor, a.beta_h,
                 _beta_floor - a.beta_h))
    else:
        _q = float('nan'); _n_law = -1; _T_of_t = None; _dG_of_T = None
        _df_start = float(DF)

    t0 = time.time()
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=a.gamma0, Mob=MOB,
                        df=[0.0] + [_df_start] * nv, workers=a.nthreads,
                        reinit_every=0, reinit_dt=a.reinit_dt,
                        reinit_band_cells=a.reinit_band,
                        dG_of_T=_dG_of_T, T_of_t=_T_of_t,
                        T=(_Tstart if _athermal else None),
                        # ★ N15（2026-10-04）：`phi` 的 dtype —— **解锁 10 µm 盒的杠杆**。
                        #   默认 `'f64'` ⇒ 与原来**逐位相同**。见 `windowB_surface.py:917+`。
                        phi_prec=str(getattr(a, 'phi_prec', 'f64')),
                        # ★★★★★ R561–R568（2026-10-05，**算子优化**）：默认全部 = 归档旧路。
                        #   推荐组合 `--eps0-mode einsum --ed-pair gather`：
                        #   实测 1.44×，且**逐位相同**（`_r568_opverify.py` V2/V3 = 0.0）。
                        #   `--fft-mode rfft` 再快 10%，但**非逐位**（σ 差 2.2e-16）。
                        eps0_mode=str(getattr(a, 'eps0_mode', 'loop')),
                        fft_mode=str(getattr(a, 'fft_mode', 'c2c')),
                        ed_pair_mode=str(getattr(a, 'ed_pair', 'full')),
                        # ★ R578：推进循环只遍历活跃场（`full` = 归档旧路，逐位不变）
                        k_loop_mode=str(getattr(a, 'k_loop', 'full')),
                        # ★ R578：两个"逐位不变"的小项（各自独立开关）
                        act_mode=str(getattr(a, 'act_mode', 'unique')),
                        argmin2_mode=str(getattr(a, 'argmin2_mode', 'legacy')),
                        # ★ R579：`par.gradient` 的切片实现（逐位相同，速度收益未确立）
                        grad_mode=str(getattr(a, 'grad_mode', 'legacy')),
                        eps0_tile=int(getattr(a, 'eps0_tile', 0) or 0),
                        argmin_reuse=bool(getattr(a, 'argmin2_reuse', 0)),
                        ufv_c=bool(getattr(a, 'ufv_c', 0)),
                        bbox_mode=str(getattr(a, 'bbox_mode', 'legacy')),
                        # ★ R579：软指示场不物化（逐位相同；C5 的必要条件之一）
                        pf_phi_mode=str(getattr(a, 'pf_phi', 'materialized')),
                        h_chunk=int(getattr(a, 'h_chunk', 4)))
    g.lath = lt
    # ★★★★★ R208（`§135.7`）：**三项量级直测**的开关（默认关）。
    #   引擎里整块由 `getattr(self, 'diag_terms_on', False)` 门控
    #   ⇒ 默认时**一行都不执行** ⇒ 归档路径逐位不变。
    g.diag_terms_on = bool(getattr(a, 'diag_terms', False))
    # ★ R238（`§135.6`）：逐变体 `ed` 分布的开关（默认关）
    g.diag_edv_on = bool(getattr(a, 'diag_edv', False))
    # ★★★★★ 2026-10-01（`R30_AUDIT_LEDGER.md` **§186**）：面片投影的"排除掩码"开关。
    #   `0`（默认）= 修好的行为（盒子贴合，不张开 β 膜）；
    #   `1` = 旧的 R73 行为（**已知会在每对同变体板条间张开 ≈118 nm 的 β 膜**）。
    #   ⚠ `facet_proj = 0`（默认）时 `facet_project()` 根本不被调用 ⇒ 本行无副作用。
    g.facet_excl = int(getattr(a, 'facet_excl', 0))
    # ★★★ R12：`--arm eng` —— **引擎侧自发形核**的接线。
    #   `vgroup` 告诉引擎哪些场同变体（本臂 6 个场全是变体 1）；
    #   `nfsv` 让同变体形核播进**新的空场**（否则只会加厚第一片）；
    #   `attach` 让新核与源板条**共用一张界面**（C-1 干晶界 regime）。
    n_eng_ev = 0
    _ed_dummy = None
    # ★★ `nuc_cfg` 必须**等 `vmap` 建好之后**再调（`vgroup=vmap`）——
    #   第一版把它放在 `g.lath = lt` 旁边，`vmap` 还没定义 ⇒ UnboundLocalError。
    #   故这里只置一个"待接线"标志，真正的 `nuc_cfg` 在 `vmap` 之后（见下）。
    if a.arm == 'auto':
        # `psi0` 取 0.99（**不能取 1.0**，见上面记账）
        g.film = dict(gamma_f=float(a.gamma_film), W=0.05, L=1.0e8, psi0=0.99)
        P('★ 臂 auto：面带 ψ 开启（γ_f=%.3f, W=0.05, L=1e8, psi0=0.99）'
          % a.gamma_film)
    P('构造 %.1f s（%d 个场；`lath` 已挂上 ⇒ F3 走 γ_RS）' % (time.time() - t0, g.nreg))
    P('   n*=%s  w=%s  a=%s  (n*·a=%.4f)'
      % (np.array2string(n_hab, precision=4), np.array2string(w_ax, precision=4),
         np.array2string(a_ax, precision=4), float(n_hab @ a_ax)))

    # ---------------- 播种：沿 n* 堆叠 M 片 ----------------
    c0 = np.array([L / 2] * 3)
    T, gap = a.plate_T * 1e-9, a.gap_nm * 1e-9
    span = (M - 1) * (T + gap)

    # ================= ★★★ R31（目标第 (2) 项 J-4）：**多块播种** =================
    #   为什么必须新增（`R30_AUDIT_LEDGER.md` 的 **P1-13**，本轮登记）：
    #     原来的播种**一律用 `laths[0]` 的 `n_hab`/`a_ax`/`w_ax`**（`:221-227`）——
    #     对 `--laths 1,1,1,…`（全同变体）这是对的，但一旦变体不同，
    #     就会把**变体 2 的板条也沿变体 1 的惯习面摆**，而惯习面是变体的**身份**。
    #     ⇒ 多块仿真的第一件事就是把它改对。**归档单变体路径逐位不受影响**。
    #   ★ 块的划分（`BLOCK_SELFAC.md §2.2`）：`laths_eff` 里**连续的同一个变体**算一块
    #     （`[1,1,1,2,2,2]` ⇒ 2 块，各 3 根）。
    #   ★ 布局：块心沿**块 0 的长轴 `a_0`** 排开，间距 `--block-gap-nm`（默认 2000 nm）
    #     ⇒ 两块**相向长大**、在盒内相遇（`§7.2` 的 P-SA-2）。
    def _variant_axes(v):
        """变体 v 的 (n*, a, w) —— 与 `:221-227` **同一套定义**，只是按变体取。

        ★ R131（用户裁定 C）：`--rank1-swap invariant` 时，对**判据说该换**的变体
          把 `n*` 与 `a` **对调**（`w` 不变：`cross(a,n) = −cross(n,a)`，同一条线）。
        """
        nv_ = np.asarray(NPF[v], float)
        nv_ = nv_ / np.linalg.norm(nv_)
        nref_, _, _ = W.argmin_normal_cached(C, np.asarray(EPS0[v - 1], float))
        R_ = W.LevelSetMulti._rank1_axes(np.asarray(EPS0[v - 1], float), nref_)
        av_ = np.asarray(R_[1], float); av_ = av_ / np.linalg.norm(av_)
        wv_ = np.asarray(R_[2], float); wv_ = wv_ / np.linalg.norm(wv_)
        if v in _SWAP:                          # ★ R131：对调 n* 与 a
            nv_, av_ = av_, nv_
        return nv_, av_, wv_

    _blk = []                                   # [(variant, [field ids 1-based])]
    for _i, _v in enumerate(laths_eff, start=1):
        if _blk and _blk[-1][0] == int(_v):
            _blk[-1][1].append(_i)
        else:
            _blk.append((int(_v), [_i]))
    _blk_axes = [_variant_axes(v) for v, _ in _blk]

    if a.multi_block:
        nb = len(_blk)
        _gap_blk = (a.block_gap_nm * 1e-9 if a.block_gap_nm > 0 else 2.0e-6)
        # ★★★★★ 2026-10-04（**N6：真·播种前可行性检查**；判定见 `R2_PARAM_VERDICTS.md §0 N6`）
        #   ## 为什么必须加在这里，而不是后面那段报告里
        #   【实测】`_w2_r51_b62r_smoke.log`：`块0：变体…` 在**第 25 行**，
        #     而 `多块：块心间距 …` 在**第 31 行** ⇒ 那段"余量"是**播种之后**才打的
        #     ⇒ **它从来就不是守卫，是事后报告**，物理上不可能拦住任何东西。
        #     证据同向：`_r520b` 的崩溃日志 `_w2_r520b_outer.log` 里
        #     `grep '块心间距'` **为空** —— 崩在报告之前。
        #   ## 这一段的几何（**唯一的真约束**）
        #     块心 `_cb = c0 + _xi·_u`，`_xi = (_b − (nb−1)/2)·_gap_blk`
        #     ⇒ 块心跨度 `(nb−1)·_gap_blk`，两端块心到盒心最远 `0.5·(nb−1)·_gap_blk`；
        #     每个块心还要再装下半长 `0.5·plate_L`（`seed_plate` 的 `elong*R` 检查）。
        #     ⇒ **需要 `0.5·L ≥ 0.5·(nb−1)·_gap_blk + 0.5·plate_L`**。
        #   ## 与旧报告的差别（**为什么它能长期存活**）
        #     旧报告 `0.5·L − 0.5·plate_L − 0.5·block_gap_nm` 有两处**独立**错误：
        #       ① 系数：少乘 `(nb−1)`；⚠ **`nb=2` 时 `0.5·(nb−1)=0.5` 与旧式恰好相等**
        #          ⇒ 旧式**只在 nb=2 上正确**，而归档唯一的 `--multi-block` 臂
        #          （`dry_b62r` / `r51_b62r`）正是 **nb=2**
        #          ⇒ **"唯一用过的那一点恰好对"**，这才是它没被发现的原因。
        #          【实测复核】`r51_b62r`：`gap=3.00 µm`、`L=8 µm`、`plate_L=1000 nm`
        #          ⇒ 旧式 `4.00−1.50−0.50 = +2.00 µm`；新式 `4.00−1.50−0.50 = +2.00 µm`
        #          ⇒ **逐位相同**（日志原文 `沿长轴余量 2.00 µm`）⇒ **归档行为不变**。
        #       ② 变量：旧式读 `a.block_gap_nm`（`--block-gap-nm ≤ 0` 时为 **0**），
        #          而播种用 `_gap_blk`（`≤0` 时默认 **2.0 µm**）
        #          ⇒ 默认配置下旧式**把 2 µm 当成 0**。
        #   ## 实测（`_r520b`：nb=12、默认 gap、L=4 µm）
        #     旧式 ⇒ `2.00 − 0.50 − 0.00 = +1.50 µm`（"余量充裕"）；
        #     真实 ⇒ `2.00 − 11.00 − 0.50 = **−9.50 µm**`
        #     ⇒ `seed_plate` 当即 `ValueError:
        #        elongated seed exceeds domain: elong*R=5e-07 um > margin -9.562e-06 um`。
        #   ## 影响范围（**为什么这不是物理缺陷**）
        #     `seed_plate` 内部有硬检查 ⇒ 结局是**启动期抛错**，不会静默产出错几何
        #     ⇒ 归档**物理结论不受影响**（且归档臂 nb=2，旧式本来就对）。
        #     真正的代价是：**白建一遍 `LathTable`（含 F3 面片对）后才崩**，
        #     且日志里没有任何一行说得出"装不下"。
        #   ⚠ 本段**只做可行性判定**，不做任何几何改动；`line` 布局才适用
        #     （`random` 布局块心散布全盒，由 `seed_plate` 逐核检查兜底）。
        if str(getattr(a, 'block_layout', 'line')) == 'line':
            _need = 0.5 * (nb - 1) * _gap_blk + 0.5 * (a.plate_L * 1e-9)
            if _need > 0.5 * L + 1e-12:
                raise SystemExit(
                    '❌ **播种前可行性检查失败**（N6）\n'
                    '   `--multi-block` 把 %d 个块心沿布局轴排开，间距取 `_gap_blk` = %.3f µm：\n'
                    '     块心跨度 = (nb−1)·gap = %d × %.3f = %.3f µm\n'
                    '     + 板条半长 0.5·plate_L = %.3f µm\n'
                    '     ⇒ **需要半盒 ≥ %.3f µm**，而实际半盒 = 0.5·L = %.3f µm'
                    '（**差 %.3f µm**）\n'
                    '   ⇒ 修法（任选）：① 缩短 `_gap_blk`（显式传 `--block-gap-nm <nm>`；'
                    '默认 %s µm 太大）\n'
                    '                  ② 减少块数（`--laths` 的变体数 = 块数 nb，当前 %d）\n'
                    '                  ③ 放大盒子（`--N`/`--dx-nm`，当前 L = %.2f µm，'
                    '至少需 %.2f µm）\n'
                    '                  ④ 用 `--block-layout random`（块心散布全盒，'
                    '无链式跨度）\n'
                    '   ⚠ 旧版此处**不报**：它把余量算成 %+.3f µm（只算 1 个 gap + '
                    '把默认 gap 当 0）\n'
                    '     ⇒ 一直走到 `seed_plate` 才抛 `ValueError`。'
                    % (nb, _gap_blk * 1e6, nb - 1, _gap_blk * 1e6,
                       (nb - 1) * _gap_blk * 1e6, 0.5 * a.plate_L * 1e-3,
                       _need * 1e6, 0.5 * L * 1e6, (_need - 0.5 * L) * 1e6,
                       ('2.0' if a.block_gap_nm <= 0 else '%.3f' % (a.block_gap_nm * 1e-3)),
                       nb, L * 1e6, 2.0 * _need * 1e6,
                       0.5 * L - 0.5 * (a.plate_L * 1e-9)
                       - 0.5 * a.block_gap_nm * 1e-9))
            P('   ✅ **播种前可行性检查**（N6）：%d 块 × 间距 %.3f µm ⇒ 需半盒 %.3f µm ≤ '
              '半盒 %.3f µm（余量 %+.3f µm）'
              % (nb, _gap_blk * 1e6, _need * 1e6, 0.5 * L * 1e6,
                 (0.5 * L - _need) * 1e6))
        # ★★★★ R52 修（**P1-30**）：把**布局轴**与**长轴**解耦。
        #   原写法 `_cb = c0 - _d * _aa`（`_d` 带符号）**只在两块长轴近乎平行时**
        #   才把它们分到 `c0` 两侧；一旦长轴**反平行**，两个块心就落到**同一个点**。
        #   【实测】`dry_b62r`（`--block-gap-nm 3000`、变体 1&2，长轴仅差 5.26°
        #   且 `a_1·a_0 = -0.996` ⇒ **近乎反平行**）：日志自报"块心间距 3.00 µm"，
        #   而落盘 `region` 实测两块包围盒**中心只差 537 nm**、`t=0` 异变体接触面
        #   **915** ⇒ 完全叠在一起。
        #   一般式：块心间距 = `gap × |a_0 + a_1| / 2` ⇒
        #     平行 ⇒ `gap`（对）；**反平行 ⇒ ≈0（错）**。
        #   修法：块心沿**固定布局轴 `_u`** 排开（间距**精确** = `--block-gap-nm`），
        #   再把每块的**生长方向**翻成指向 `c0` 的那一侧
        #   （板条关于自己的中心对称 ⇒ `along → -along` **等价**，不改变物理）。
        _u = np.sum([_ax[1] for _ax in _blk_axes], axis=0)
        _nu = float(np.linalg.norm(_u))
        if _nu < 1e-6:
            # 长轴两两抵消（典型：一对反平行）⇒ 退回到块 0 的**垂直**方向作布局轴
            _tmp = np.cross(_blk_axes[0][1], _blk_axes[0][0])
            _u = _tmp / (np.linalg.norm(_tmp) + 1e-300)
        else:
            _u = _u / _nu
        # ★★★★★ 2026-10-01（`R30_AUDIT_LEDGER.md` §189，**缺陷②**）：
        #   **`--block-layout random`** —— 块心**盒内随机**，不再排在一条直线上。
        #   ## 为什么
        #     `line`（归档默认）把**全部**块心放在**同一个布局轴 `_u`** 上
        #     （`_cb = c0 + _xi·_u`）⇒ 实测 6 个块心第一主成分方差占比 **0.9998**、
        #     到最佳拟合直线垂距 **≤0.05 µm**、邻居数 `[1,2,2,2,2,1]`
        #     ⇒ 这是**人为规定的一维链**，不是"多个块在盒内相互影响"的涌现构型。
        #   ## 怎么放
        #     块心在**整个周期盒**内均匀随机（引擎是**周期边界** `np.roll`，
        #     没有实体盒壁 ⇒ 铺满整个胞是合法的），带**最小间距**拒绝采样
        #     （默认 = `--block-gap-nm`），用固定 `--block-seed` 保证可复现。
        #   ⚠ `line` 路径**逐字未动** ⇒ 归档逐位不变。
        _layout = str(getattr(a, 'block_layout', 'line'))
        if _layout == 'random':
            _rng_b = np.random.default_rng(int(getattr(a, 'block_seed', 20261001)))
            _dmin = float(getattr(a, 'block_min_dist_nm', 0.0) or 0.0) * 1e-9
            if _dmin <= 0.0:
                _dmin = _gap_blk
            _cens = []
            # ★★ 自纠错（冒烟第一版当场抓到）：`seed_plate` **不做周期折回** ——
            #   它有一条硬检查 `elong*R > margin ⇒ ValueError`
            #   （`windowB_surface.py:2068`）。所以随机块心**必须**留在
            #   "板条 AABB 完全落在盒内"的区域里，不能铺满整个胞。
            #   每块沿轴 i 的半展宽 = (L/2)|a_i| + (W/2)|w_i| + (n_stack·T/2)|n_i|
            #   （最后一项是块沿 n* 的堆叠厚度）⇒ 块心必须落在
            #   `[m_i, Lbox − m_i]` 内。
            _marg = []
            for _b2, (_v2, _fs2) in enumerate(_blk):
                _n2, _a2, _w2 = _blk_axes[_b2]
                _half = (0.5 * a.plate_L * 1e-9) * np.abs(_a2) \
                    + (0.5 * a.plate_W * 1e-9) * np.abs(_w2) \
                    + (0.5 * len(_fs2) * T) * np.abs(_n2)
                _marg.append(_half)
            _marg = np.array(_marg)                       # (nb, 3)
            _lo = _marg.max(0)
            _hi = L - _lo
            if bool((_hi <= _lo).any()):
                raise SystemExit(
                    '✗ 随机布局：盒太小 —— 沿轴 %s 需要半展宽 %s µm，'
                    '而盒只有 %.2f µm ⇒ 装不下。放大 `--N` 或缩小 `--plate-*`。'
                    % (np.array2string(_lo * 1e6, precision=2),
                       np.array2string(_lo * 1e6, precision=2), L * 1e6))
            P('   随机布局的**可用区**：[%s] → [%s] µm（盒 %.2f µm）'
              % (np.array2string(_lo * 1e6, precision=2),
                 np.array2string(_hi * 1e6, precision=2), L * 1e6))
            for _b in range(nb):
                _pick = None
                for _try in range(4000):
                    _c = _lo + _rng_b.random(3) * (_hi - _lo)
                    if all(float(np.linalg.norm(_c - _q)) >= _dmin for _q in _cens):
                        _pick = _c
                        break
                if _pick is None:                      # 拒绝采样失败 ⇒ 明确记账，不静默退化
                    P('   ⚠⚠ 随机布局：第 %d 块在 4000 次尝试内找不到与已有块'
                      '相距 ≥ %.0f nm 的位置 ⇒ 取本次候选（**间距可能不足**）'
                      % (_b, _dmin * 1e9))
                    _pick = _c
                _cens.append(_pick)
            P('★★★ §189 多块播种（**随机布局**）：%d 块（%s）；块心盒内**均匀随机**，'
              '最小间距 ≥ %.0f nm，seed=%d'
              % (nb, ' + '.join('V%d×%d' % (v, len(fs)) for v, fs in _blk),
                 _dmin * 1e9, int(getattr(a, 'block_seed', 20261001))))
            for _b, (_v, _fs) in enumerate(_blk):
                _n, _aa, _ww = _blk_axes[_b]
                _cb = _cens[_b]
                for _j, _fid in enumerate(_fs):
                    _off = (_j - (len(_fs) - 1) / 2.0) * (T + gap)
                    g.seed_plate(_fid, _cb + _off * _n, _n, a.plate_W * 0.5e-9, T,
                                 elong=a.plate_L / a.plate_W, along=_aa,
                                 flat_end=True)
                    n_seeded = _fid
                P('   块%d：变体 V%d，%d 根；n*=%s  块心=%s µm'
                  % (_b, _v, len(_fs), np.array2string(_n, precision=3),
                     np.array2string(_cb * 1e6, precision=2)))
            _cc = np.array(_cens)
            _dev = _cc - _cc.mean(0)
            _ev = np.linalg.eigvalsh(_dev.T @ _dev / max(len(_cc), 1))
            _frac = float(_ev[-1] / max(_ev.sum(), 1e-300))
            _nn = [int(np.count_nonzero(
                (np.linalg.norm(_cc - _q, axis=1) > 1e-12)
                & (np.linalg.norm(_cc - _q, axis=1) <= 1.8 * _dmin))) for _q in _cc]
            P('   ★ 构型自检（**必须与 `line` 明显不同**）：第一主成分方差占比 = **%.4f**'
              '（`line` 实测 0.9998）；邻居数 = %s；最小间距 = %.2f µm'
              % (_frac, _nn,
                 min(float(np.linalg.norm(_cc[i] - _cc[j]))
                     for i in range(len(_cc)) for j in range(i + 1, len(_cc)))
                 if len(_cc) > 1 else float('nan')))
        else:
            P('★★★ R31 多块播种：%d 块（%s）；块心沿**布局轴 u**=%s 排开，'
              '间距 = `--block-gap-nm` = %.0f nm（**精确**）；'
              '每块的生长方向取指向 c0 的一侧'
              % (nb, ' + '.join('V%d×%d' % (v, len(fs)) for v, fs in _blk),
                 np.array2string(_u, precision=3), a.block_gap_nm))
        for _b, (_v, _fs) in enumerate(_blk if _layout != 'random' else []):
            _n, _aa, _ww = _blk_axes[_b]
            _xi = (_b - (nb - 1) / 2.0) * _gap_blk
            _cb = c0 + _xi * _u
            # 生长方向：让 `+along` 指向 c0（板条对称 ⇒ 翻转等价）
            _along = _aa if float(np.dot(_xi * _u, _aa)) < 0 else -_aa
            for _j, _fid in enumerate(_fs):
                _off = (_j - (len(_fs) - 1) / 2.0) * (T + gap)
                g.seed_plate(_fid, _cb + _off * _n, _n, a.plate_W * 0.5e-9, T,
                             elong=a.plate_L / a.plate_W, along=_along,
                             flat_end=True)
                n_seeded = _fid
            P('   块%d：变体 V%d，%d 根；n*=%s  块心=%s µm  生长方向=%s'
              % (_b, _v, len(_fs), np.array2string(_n, precision=3),
                 np.array2string(_cb * 1e6, precision=2),
                 np.array2string(_along, precision=3)))
        g.init_parent()
        # ★ 播种后**实测**两块之间的质心距（不靠推理）：若已经重叠就当场说清楚
        #   （判据 P-SA-2 的前提是"它们能在预算内相遇、且 t=0 是分离的"）。
        if nb >= 2:
            _cc = []
            for _v, _fs in _blk:
                _m = np.zeros(g.region().shape, bool)
                for _fid in _fs:
                    _m |= (g.region() == _fid)
                if _m.any():
                    _cc.append(np.argwhere(_m).mean(0) * dx)
            if len(_cc) >= 2:
                _dist = float(np.linalg.norm(_cc[0] - _cc[1])) * 1e6
                # ⚠ 单位：`--plate-L` 的单位是 **nm** ⇒ 到 µm 要 ×1e-3（第一版写成 1e-6，
                #   于是"半长"被印成 0.00 µm、"分离"判据恒真 —— 本仓库第 5 次 nm/µm 混淆）。
                _half = 0.5 * a.plate_L * 1e-3
                P('   播种后**两块质心距** = %.2f µm（半长 %.2f µm；沿长轴到盒壁余量 %.2f µm）'
                  % (_dist, _half, 0.5 * L * 1e6 - _half))
                if _dist < _half:
                    P('   ⚠⚠ 两块质心距 < 半长（粗判据）⇒ 可能重叠；看下面的**精确判据**')
                # ★★ 精确判据（取代粗判据）：**t=0 有没有 F2（异变体）接触面**。
                #   质心距只是粗判据（两块长轴夹角约 121°，包围盒重叠 ≠ 真接触）。
                #   `F2 面数 == 0` ⟺ 两块在 t=0 **真正分离** —— 这是可证伪的。
                _mA = np.zeros(g.region().shape, bool)
                for _fid in _blk[0][1]:
                    _mA |= (g.region() == _fid)
                _mB = np.zeros(g.region().shape, bool)
                for _fid in _blk[1][1]:
                    _mB |= (g.region() == _fid)
                _f2 = 0
                for _ax in (0, 1, 2):
                    for _sh in (1, -1):
                        _f2 += int((_mA & np.roll(_mB, _sh, axis=_ax)).sum())
                P('   **精确判据**：t=0 的两块异变体接触面 = **%d** 个格面 ⇒ %s'
                  % (_f2, '✅ 真正分离' if _f2 == 0 else '⚠ 已接触（含初始混杂）'))

    P('播种 %d 片（%s nm）沿 n* 堆叠：厚 %.0f nm、间隔 %.0f nm、跨度 %.2f µm；'
      '沿 a 长 %.0f nm、沿 w 宽 %.0f nm'
      % (len(laths_eff), laths_eff, a.plate_T, a.gap_nm, (span + T) * 1e6,
         a.plate_L, a.plate_W))

    # ================= ★★★ G-1 方案 B：**生长中的同变体邻位形核** =================
    #   文献机制（Furuhara 2008）：「A BLOCK IS FORMED BY REPEATED NUCLEATION OF THE
    #   SAME VARIANT OF LATHS ADJACENT TO EACH OTHER」。
    #   ⇒ t=0 **只播第 1 片**；此后每 `--nuc-every` 步，在当前块的**外侧**播下一片
    #     （**同一个变体、新的场**）⇒ 片与片之间自动成为 F3（低角晶界）。
    #   ★ 与"预先把 6 片摆好"的区别：核是**在长大过程中逐个出现**的，且每次出现前
    #     都要**先量当前块的实际延伸**（因为块已经长大了）⇒ 是"生长后堆叠"。
    #   ★ **零引擎改动**：场表 / `LathTable` 在构造时就按 `--laths` 建好，
    #     未播种的场一直是空的（φ=1e3 ⇒ 永远不是 argmin）。
    # ★ R12：`arm=eng` 也要"只播第 1 片 + `init_parent`"，但它**不走驱动层形核**
    #   （`--nuc-every 0`）⇒ 形核由下面的 `g.nucleate()` 负责。
    # ★ R28：**默认走引擎形核**（见下面的 `use_engine`）。
    use_engine = (a.arm == 'eng') or (a.nuc_mode == 'engine') or (
        a.nuc_mode == 'auto' and bool(a.grow_stack) and a.nuc_every <= 0)
    grow = bool(a.grow_stack) or (a.arm == 'eng') or use_engine
    n_seeded = 0

    def _seed_next():
        nonlocal n_seeded
        j = n_seeded + 1
        if j > nv:
            return None
        # ★★ Round 10：**补厚度**（`--nuc-compensate`）。
        #   张力（Round 9 实测）：界面要落在共享平面上 ⇒ 重叠 o 必须 ≥ 1 胞；
        #   但界面落在重叠区**中面** ⇒ 每张被重叠的面被吃 `o/2`，
        #   而**内层片两张宽面都是 F3、`Δf = Δe_el ≡ 0`，没有任何体驱动力**
        #   去补回来（§5.1）⇒ 被削薄就只会继续缩、碎裂
        #   （`gs3` 实测：板条 1 被撕成 20 个碎片，且碎片把 `f3_area` 刷到
        #    7.95 µm²，比预摆对照的 6.77 还大 —— 那是**污染**不是成绩）。
        #   ⇒ 出路不是调 o，而是**把会被咬掉的预先补上**：
        #       片 1..M−1：内外两张面都会被咬 ⇒ 播 `T + o`
        #       片 M     ：只有内面被咬       ⇒ 播 `T + o/2`
        #     这样每片的**稳态厚度都回到 T**，块总厚仍是 M·T。
        #   ⚠ 近端面必须仍在 `edge − o`（否则几何就变了）⇒ 中心相应移到
        #     `edge − o + T_j/2`。多出来的厚度加在**外侧**。
        o = a.nuc_overlap_nm * 1e-9
        _fr = float(a.nuc_compensate_frac)
        Tj = (T + _fr * (o if j < nv else 0.5 * o)) if (o > 0 and a.nuc_compensate) else T
        if j == 1:
            c = c0.copy()
        else:
            sp = _block_span_n(g, n_hab, BM)
            cproj = float(c0 @ n_hab)
            if sp is None:
                c = c0.copy()
            else:
                vlo, vhi = sp
                side = 1.0 if (j % 2 == 0) else -1.0
                edge = (vhi if side > 0 else vlo)
                # ★★ 记账（Round 3 实测更正）：原先放 **1.5 胞（94 nm）** 的间隙，
                #   想让两侧"长到一起"。实测**不会**发生：
                #     间隙里是**母相 β** ⇒ 两侧都是 F1（α′/β）界面，有驱动力，
                #     但**宽面被 β_h 重钉扎** ⇒ 实测宽面推进只有 **0.26 nm/步**
                #     （端板条 Δn=+13 nm/50 步）⇒ 47 nm 要 **~180 步** > 200 步预算。
                #   ⇒ 物理上"sympathetic 邻位形核"本来指**在已有板条的界面上形核**
                #     （Furuhara 2008 的 repeated nucleation adjacent to each other）
                #     ⇒ 新核应当**贴着**已有块放。间隙由 `--nuc-gap-nm` 控制（默认 0）。
                # ★★ Round 9 实测新增（`_bk_pair.py`，gs2 末态）：
                #   "贴着放"**还不够**。`edge` 是**格心**投影，`T=250 nm = 4Δx`，
                #   于是新片的零水平集落在**非格点**位置 ⇒ 两列阶梯错开 ⇒
                #   界面被劈成两半：
                #       1-2 界面：F3 直接接触 0.4601 + **1 胞厚 β 膜 0.9492**
                #                 = 1.4093 µm² ≈ 整片足迹 ⇒ 覆盖率仅 0.33
                #       2-4：0.4081 + 0.9102；4-6：0.5136 + 0.7617（+侧全如此）
                #       而 −侧 3-1、5-3 是满的（1.5477 / 1.4804，几乎无 β）
                #   机理：`seed_plate` 用真 SDF 且把其它场抬到 `-sdf`，`argmin` 把
                #   界面定在**两个零水平集的中面**。所以**只要种子与旧片有重叠**，
                #   界面就是一张完整的阶梯面；**恰好相切**时中面退化成旧片的
                #   零水平集，台阶对不上的地方就留 1 胞 β（阶梯错位伪影，非物理）。
                #   ⇒ 用 `--nuc-overlap-nm` 让新片**咬进**旧片（物理上就是
                #     "在界面上形核"，共用一张界面，不是隔缝相望）。
                c = c0 + ((edge - cproj) + side * (Tj / 2 - o)) * n_hab
                c = c - L * np.floor(c / L)          # 周期折回
        g.seed_plate(j, c, n_hab, a.plate_W * 0.5e-9, Tj,
                     elong=a.plate_L / a.plate_W, along=a_ax, flat_end=True)
        n_seeded = j
        return j

    if grow:
        j0 = _seed_next()
        g.init_parent()
        P('★★ 生长中的同变体邻位形核：t=0 只播第 %d 片（场 %d）；'
          '此后每 %d 步在外侧播下一片（同一变体、新场）⇒ 片间自动成 F3'
          '； 咬入旧片 %.1f nm（`--nuc-overlap-nm`；0=相切，实测 F3 覆盖率仅 0.62）'
          '； 播种厚 %.0f nm = 物理厚 %.0f + 咬入补偿 %.0f（末片再减 %.0f）'
          % (j0, j0, a.nuc_every, a.nuc_overlap_nm, a.plate_T,
             (a.plate_t_physical if a.plate_t_physical > 0 else a.plate_T),
             a.plate_T - (a.plate_t_physical if a.plate_t_physical > 0
                          else a.plate_T),
             a.eng_t_last_reduce_nm))
    elif a.multi_block:
        # ★★★ R31（J-4）：多块播种已在上面完成 ⇒ **跳过**原来的"沿同一个 n* 堆叠"
        #   两支（否则会把刚播好的多块覆盖掉）。
        n_seeded = nv
    elif len(laths_eff) == 1 and M > 1:
        for i in range(M):
            off = (i - (M - 1) / 2.0) * (T + gap)
            g.seed_plate(1, c0 + off * n_hab, n_hab, a.plate_W * 0.5e-9, T,
                         elong=a.plate_L / a.plate_W, along=a_ax, flat_end=True)
        n_seeded = M
        g.init_parent()
    else:
        for i in range(M):
            off = (i - (M - 1) / 2.0) * (T + gap)
            g.seed_plate(i + 1, c0 + off * n_hab, n_hab, a.plate_W * 0.5e-9, T,
                         elong=a.plate_L / a.plate_W, along=a_ax, flat_end=True)
        n_seeded = M
        g.init_parent()
    # ★★★★★ 2026-10-01（`R30_AUDIT_LEDGER.md` **§190**）：**报告口径修复**。
    #   上面第 `:851` 行那句 `P('播种 %d 片（%s nm）沿 n* 堆叠：…跨度 %.2f µm')`
    #   **是无条件打印的"名义堆叠"**，它用的是 `len(laths_eff)` 与 `span`（= M·T），
    #   **完全不反映实际走了哪条播种分支**。
    #   ## 实测后果（**我自己被它误导过**）
    #     `_r425` 探针：24 个场、**不带 `--multi-block`**、带 `--grow-stack`
    #     ⇒ 那句打印 "播种 24 片…**跨度 12.24 µm**"，而真实路径是
    #       `if grow: j0 = _seed_next()` ⇒ **只播了第 1 片**
    #       （落盘实测 `nreg_used = 1`、`Vt = 0.249 µm³` = 1 片板条的体积）。
    #     7 µm 的盒子里"跨度 12.24 µm"看着像硬错误，我据此差点推翻整个 A/B 设计。
    #   ⇒ 修法：**播种分支跑完之后**再打一句**真实**的片数，并标明那是哪条分支。
    #   ⚠ 纯新增打印，不改任何数值。
    P('   ▸ **实际播种**：%d 片（走的是「%s」分支）；'
      '上面那句"播种 %d 片…跨度"是**名义堆叠**口径，**不是**实际播种结果'
      % (int(n_seeded),
         ('`--grow-stack`/引擎：t=0 只播第 1 片，其余靠形核'
          if grow else ('`--multi-block`：按块布置'
                        if a.multi_block else '沿 n* 堆叠全部 %d 片' % nv)),
         nv))
    if a.multi_block:
        # ★★★★★ 2026-10-04（**N6：报告口径修复**；判定见 `R2_PARAM_VERDICTS.md §0 N6`）
        #   ⚠ **先看清楚这一段是什么**：它在**播种之后**才执行
        #     【实测】`_w2_r51_b62r_smoke.log`：`块0：变体…` 第 25 行、
        #       `多块：块心间距…` 第 **31** 行 ⇒ **这是事后报告，不是守卫**。
        #     它**不可能**拦住任何东西 —— 真正的可行性检查已挪到播种前
        #     （本函数内 `_gap_blk` 那句下面的 N6 段）。
        #     所以这里修的是**报告是否说真话**，以及下游 `margin < 0.5 µm`
        #     那条撞壁警告会不会被**错误的余量吞掉**。
        #   ## 旧式错在两处（**独立**，任一处都足以让报告说反话）
        #   旧：`margin = 0.5·L − 0.5·plate_L − 0.5·block_gap_nm`
        #   ① **系数错**：真实块心跨度 = `(nb−1)·_gap_blk`
        #      （本函数播种那段的 `_xi = (_b − (nb−1)/2)·_gap_blk`）
        #      ⇒ 半跨度 `0.5·(nb−1)·_gap_blk`；旧式只算了 **1 个** gap。
        #      ⚠⚠ `nb = 2` 时 `0.5·(nb−1) = 0.5`，**与旧式恰好相等**
        #        ⇒ 旧式**只在 nb=2 这一个点上正确**；而归档里唯一的
        #        `--multi-block` 臂（`dry_b62r` / `r51_b62r`）正是 **nb=2**。
        #      ⇒ **它长期存活的真正原因不是"没被用过"，而是"唯一用过的那一点恰好对"**
        #        （`r51_b62r` 实测 `3.00 µm ⇒ 2.00 µm`，新旧式**逐位相同**）。
        #   ② **变量错**：旧式读 `a.block_gap_nm`（`--block-gap-nm ≤ 0` 时为 **0**），
        #      而播种实际用的是 `_gap_blk`（`≤0` 时默认 **2.0 µm**）
        #      ⇒ 默认配置下旧式**把 2 µm 当成 0**。
        #   ## 实测（`_r520b`，nb=12、默认 gap、L=4 µm）
        #     旧式 ⇒ `margin = 2.00 − 0.50 − 0.00 = +1.50 µm` 且打"余量充裕"；
        #     真实 ⇒ `2.00 − 11.00 − 0.50 = **−9.50 µm**`
        #     ⇒ `seed_plate` 当即
        #       `ValueError: elongated seed exceeds domain:
        #        elong*R=5e-07 um > margin -9.562e-06 um`
        #   ## 影响范围（**为什么这不是物理缺陷**）
        #     `seed_plate` 内部有硬检查 ⇒ 结局是**启动期抛错**，
        #     不会静默产出错几何 ⇒ 归档的**物理结论不受影响**（且归档臂 nb=2，旧式本来就对）。
        #     但报告"算出 +1.5 µm 却真实 −9.5 µm"会让 `margin < 0.5 µm`
        #     那条**撞壁警告被吞掉** ⇒ **警告不可信**，这才是要修的。
        #   ⚠ `--block-layout random` 下块心不排在一条线上 ⇒ 链式余量**不适用**，另打。
        #   ⚠ 本段**只影响打印与警告阈值**，不参与任何求解/几何 ⇒ 数据字段零风险。
        if str(getattr(a, 'block_layout', 'line')) == 'random':
            margin = 1.0e-6
            P('   多块：%d 块，`--block-layout random` ⇒ 块心散布全盒，'
              '**沿布局轴的链式余量不适用**（由 `seed_plate` 的逐核边界检查兜底）' % nb)
        else:
            _half_span = 0.5 * (nb - 1) * _gap_blk
            margin = 0.5 * L - _half_span - 0.5 * (a.plate_L * 1e-9)
            P('   多块：%d 块；块心间距（**实际**，`_gap_blk`）= %.2f µm ⇒ '
              '块心半跨度 %.2f µm；再加板条半长 %.2f µm ⇒ **沿长轴余量 %.2f µm**'
              % (nb, _gap_blk * 1e6, _half_span * 1e6,
                 0.5 * a.plate_L * 1e-3, margin * 1e6))
    elif grow:
        # ★★★★★ 2026-10-01（`R30_AUDIT_LEDGER.md` **§199**）：**报告口径修复**。
        #   `grow`（引擎路径）下 t=0 **只播 1 片**（`if grow: _seed_next()`），
        #   其余靠形核**撒在随机位点**上 ⇒ 「沿 n* 堆叠全部 nv 片」这个**名义**假设
        #   **完全不成立**。
        #   而下面那条 `margin` 是用**名义 `span = M·T`** 算的：
        #     实测（`§199`，24 片 × 510 nm = 12.24 µm 的"名义跨度" vs 7 µm 的盒）
        #     ⇒ 打出「沿 n* 余量 **−2.62 µm**、沿 a 余量 **−3.12 µm**」
        #       与「⚠⚠ **本算例会在中期撞盒壁**」。
        #   ⇒ **这是假警报**（与 `§190.3` 的"播种 24 片…跨度 12.24 µm"是**同一个根因**：
        #     都拿名义 `span`/`len(laths_eff)` 当实际）。
        #   ⇒ 改成打**真正约束**：**盒体积能装多少根板条**（与堆叠方向无关）。
        _v_lath = (a.plate_L * 1e-9) * (a.plate_W * 1e-9) * (a.plate_T * 1e-9)
        _n_vol = int(0.30 * L ** 3 / max(_v_lath, 1e-300))
        P('   **引擎路径**（`--grow-stack`）：t=0 只播 1 片，其余靠形核撒在**随机位点**'
          ' ⇒ 「沿 n* 堆叠 %d 片」的**名义余量不适用**（不再据此发撞壁警告）' % nv)
        P('   真正约束是**盒体积**：%.2f µm³ / 单根 %.4f µm³ ⇒ 30%% 转变分数下可容 '
          '**%d 根**（本算例 nv=%d）⇒ %s'
          % (L ** 3 * 1e18, _v_lath * 1e18, _n_vol, nv,
             '✅ 体积不是瓶颈' if _n_vol >= nv else '❌ **体积是瓶颈**'))
        margin = 1.0e-6          # 名义余量不适用 ⇒ 不触发下面的撞壁警告
    else:
        margin = 0.5 * L - 0.5 * (span + T) - 0.5 * a.plate_L * 1e-9
        P('   沿 n* 到盒壁余量 %.2f µm；沿 a 余量 %.2f µm（标量估计，%s）'
          % ((0.5 * L - 0.5 * (span + T)) * 1e6, margin * 1e6,
             '余量充裕' if margin > 1.0e-6 else
             '⚠ 余量偏紧：归档几何下 700 步长跑会撞壁（见 §4.1）'))
    if margin < 0.5e-6:
        P('   ⚠⚠ 沿 a 余量 < 0.5 µm ⇒ **本算例会在中期撞盒壁**（`box_touch` 会置 1）')
    # ⚠ `span` 假设**所有板条沿同一个 n* 排成一列** —— 对 `--nuc-init > 0`
    #   （新核撒在随机位点上）这个假设不成立 ⇒ 那条硬检查**不适用**。
    # ★ §199：`grow`（引擎路径）同样是"只播 1 片 + 随机位点形核" ⇒ 也**不适用**。
    #   ⚠ 原先漏了 `grow`：`--grow-stack` 但**不传** `--nuc-init` 的算例会被这条
    #     **假检查**直接 `SystemExit`（而它其实播得下）。
    if (span + T > L) and not a.multi_block and a.nuc_init <= 0 and not grow:
        raise SystemExit('✗ 堆叠跨度 %.2f µm > 盒 %.2f µm —— 播不下'
                         % ((span + T) * 1e6, L * 1e6))

    vmap = {i + 1: laths_eff[i] for i in range(nv)}
    # ★★★ R12：`--arm eng` —— **引擎侧自发形核**的接线（放在 `vmap` 之后）。
    #   `vgroup` 告诉引擎哪些场同变体（本臂 6 个场全是变体 1）；
    #   `nfsv` 让同变体形核播进**新的空场**（否则只会加厚第一片）；
    #   `attach` 让新核与源板条**共用一张界面**（C-1 干晶界 regime）。
    if use_engine:
        # ★ R28：**自动补厚度** —— 界面落在重叠区中面 ⇒ 每片被吃 `o/2`
        #   （两侧被吃的片吃 `o`）⇒ 引擎路径下把 `o` 加回 `t_nuc`。
        #   这样「只给 `--grow-stack`」的最简命令行也能复现 `eng12`。
        _t_nuc = a.eng_t_nm * 1e-9
        if use_engine and a.eng_t_nm <= 250.0 and a.nuc_overlap_nm > 0:
            _t_nuc = (250.0 + a.nuc_overlap_nm) * 1e-9
        g.nuc_cfg(a.eng_r_nm * 1e-9, _t_nuc, gamma=a.gamma0,
                  n_init=int(getattr(a, 'nuc_init', 0)),
                  # ⚠⚠⚠ **R581-R17 记账：我差点在这里加重复的 `seed=`（留痕）**
                  #   我此前断言「`nuc_cfg` 的 `seed` 是硬编码 11、CLI 没旋钮」（缺口 **A22**），
                  #   并动手加了 `seed=int(getattr(a,'nuc_seed',11))` + 新开关 `--nuc-seed`。
                  #   **实测报错**：`SyntaxError: keyword argument repeated: seed`
                  #   —— 因为 **`nuc_cfg(...)` 的调用里本来就有 `seed=a.eng_seed`**
                  #   （在本段下方，我第一遍 `grep` 只搜了 `--seed`/`nuc_seed`，**漏了 `eng_seed`**）。
                  #   ⇒ **A22 里"CLI 没有旋钮"这半句是错的**：旋钮是 **`--eng-seed`**。
                  #   ⇒ 我已**撤回**那两处改动（本行的 `seed=` 与 `--nuc-seed` 参数定义），
                  #     并改正文档。**教训见 `R581_DISCIPLINES.md` P28**：
                  #     **"grep 没搜到" ≠ "代码里没有"** —— 先搜**语义**（`seed`），
                  #     不要只搜**你以为的那个拼写**（`nuc_seed`）。
                  p_auto=0.0, harden_f=1.0, sym_gap_cells=0,
                  # ★★★★★ R483（2026-10-01，**任务(2) 的 S5**）：`max_per_step` **接到 CLI**。
                  #   ## 病灶（`R2_PARAM_VERDICTS.md` S5）
                  #     引擎的 `nucleate()` 里每调用**最多放 `cap = max_per_step` 个事件**，
                  #     而这里**硬编码 1**（引擎默认也是 1，`windowB_surface.py:1231`）
                  #     ⇒ **一次调用最多 1 个核**。
                  #   ## 物理依据（为什么要放开）
                  #     文献（Bhadeshia，已读原文）：burst 是"**一次触发一串**板条"
                  #     （autocatalysis ⇒ "a **rapid sequence** of many other plates"）。
                  #     而 athermal 律在温度档内要求的是 `Δn = α_KM·ΔT` 个核
                  #     （准静态钟下默认 `ΔT = 1/α_KM` ⇒ **Δn = 1**，见 `R477_QS_CLOCK.md`）
                  #     ⇒ **默认档宽下 cap=1 恰好够用**；**只有把 `ΔT` 取粗**（一档放多根）
                  #       或**跑旧的"时间积分"路径**时，`cap=1` 才会成为瓶颈。
                  #   ⚠ 所以本开关**不是**在"造 burst 律" —— 它只是把"一次调用能放几个"
                  #     这个**表示上限**暴露成参数。**burst 的定量率律仍然没有**（§改 3 纪律）。
                  #   ⚠ 同仓 `T24/T27/_chk_w13/_chk_w14/_probe_nuc_switches` 都传 **8**。
                  #   ⚠ 默认 **1** ⇒ 归档路径逐位不变。
                  max_per_step=int(getattr(a, 'nuc_max_per_step', 1) or 1),
                  seed=a.eng_seed,
                  # ★ R31（J-5）：**变体选择规则**暴露到驱动。
                  #   `ed`（默认）= 按弹性能变化最小选（Du 2017）——**可以是涌现的**；
                  #   `random` = 均匀随机（`BLOCK_SELFAC.md §7.1 P-SA-1` 的**负对照臂**）。
                  #   ⚠ 默认仍是 `ed` ⇒ 归档逐位不变。
                  var_rule=a.var_rule,
                  # ★ R31（P1-17）：新核的**长轴按变体取**（`atab[k]`），
                  #   且 `fresh` 通道也播**长条**（原来播圆盘）。
                  #   ⚠ 只在 `--nuc-init > 0`（走 fresh）时打开 ⇒ 归档逐位不变。
                  along_per_variant=(a.nuc_init > 0),
                  # ★★★★★ 2026-10-01（`R30_AUDIT_LEDGER.md` **§192**）：把**框架自带的
                  #   `f_nuc^crit = 4γ/d` 判据（Du 2017 / `WINDOWB_AUDIT_REGISTER` §9 D1）
                  #   接到 CLI 上。
                  #   ## 为什么这是一条**接线缺陷**（不是新功能）
                  #     `windowB_surface.nucleate()` 里那条判据**早就实现了**，注释还写着
                  #     "✅ W1-4（2026-09-28）：本判据**已接线**"，但它**只接在引擎内部**——
                  #     `_bk_exp.py` 里 `use_fcrit` **只出现在注释里**（3 处全是注释），
                  #     **从未**传给 `nuc_cfg()`，也**没有** CLI 开关
                  #     ⇒ 从驱动层的角度它是**死代码**，**永远打不开**。
                  #     这正是目标第 (1) 项要查的"该有的模块是否正常接线"。
                  #   ## 判定式（引擎里已写死）
                  #     `(df + max_k ed_k) > fcrit`，`fcrit = 4γ/t`；
                  #     被拒的位点计入 `dbg['fcrit']`（**显式可诊断**）。
                  #   ⚠ **只覆盖 `fresh` 通道**；`stack`（sympathetic）通道**未**加该判据
                  #     —— 这是**已知的范围缺口**，不得说成"两条通道都过了驱动力判据"。
                  #   ⚠ 默认 **0**（关）⇒ 归档路径**逐位不变**。
                  use_fcrit=bool(int(getattr(a, 'nuc_fcrit', 0))),
                  # ★★★★★ R479（2026-10-01，**任务(2) ②：超临界判据**）。
                  #   判据：`ΔG_v(T) + ed_face > 2γ/t`（薄板两个宽面的界面能/体积）。
                  #   实现方式：**试放**（造一个试放 `region` 跑一次弹性求解，**不改任何场**）。
                  #   与上面 `use_fcrit` 的根本区别见 `nuc_cfg` 里的长注释。
                  #   ⚠ 同样**只覆盖 `fresh` 通道**（范围缺口与 `use_fcrit` 相同，必须随结论给）。
                  #   ⚠ 默认 **0**（关）⇒ 归档路径**逐位不变**。
                  supercrit=bool(int(getattr(a, 'nuc_supercrit', 0))),
                  # ★★★★★ R508（2026-10-01）：**核的形状**。
                  #   'disc'（默认）= 现行为 `sdf = max(|d|−t/2, rperp−R)` ⇒ **带尖边圆柱**；
                  #   'ellipsoid' = 光滑椭球。
                  #   依据（`R507_fullclosure`）：尖边圆盘的弹性罚实测比椭球**高 52%**
                  #   （3.1818e8 vs 2.0873e8）⇒ 超临界门槛从 641.7 K 抬到 377.7 K
                  #   ⇒ **形核窗口从 344 K 压到 80 K** ⇒ 五约束联立后**交集为空**
                  #     （C3 要 α_KM ≥ 0.0251，块厚带要 α_KM ≤ 0.0205）。
                  #   换椭球 ⇒ 交集 [0.0058, 0.0205]，框架参考 0.011 正落在里面 ✅
                  #   ⚠ 默认 'disc' ⇒ 归档路径逐位不变。
                  shape=str(getattr(a, 'nuc_shape', 'disc') or 'disc'),
                  # ★★★★★ R481（2026-10-01，**任务(2) ③：位点持续可用**）。
                  #   病灶：位点池 t=0 撒一次、`sites.pop(i)` 用过即移除
                  #   ⇒ 池子耗尽后**再也形不了核**，而 athermal 律还在要求新核
                  #     （"定律要核、池子没有"的静默缺口）。
                  #   物理：位点是母相里**预先存在**的异质位置（晶界/位错），
                  #     是**密度**意义的、**不随激活而消失** ⇒ 见底时应按同一分布继续抽。
                  #   ⚠ 记账：本开关**不声称**位点密度是物理值（本项目未标定数密度/空间关联），
                  #     它只保证"**不会因为池子空而停**"。
                  #   ⚠ 默认 **0** ⇒ 归档路径逐位不变。
                  sites_refill=bool(int(getattr(a, 'nuc_sites_refill', 0))),
                  # ★★★★★ 2026-10-01（`R30_AUDIT_LEDGER.md` **§200**）：
                  #   **接线缺口 #3 的修复** —— 把 `dG` 接到"选哪个块做 sympathetic 源"上。
                  #   `§195` 实测：sympathetic 形核**继承源块的命运** ——
                  #   4 条"长了"的 `attach` 全部接在 V7/V9 的块上、6 条"不长"的全部接在
                  #   V1 的块上。而现行写法是 `ks[rng.integers(...)]` **均匀随机挑块**。
                  #   引擎里 `dG = df + ed` **早就在算**（落盘成 `series.csv` 的
                  #   `dG_tip`/`dG_side`），**只是没接到选块逻辑上**。
                  #   ⚠ 默认 **0**（关）⇒ 归档路径**逐位不变**。
                  stack_pick_dg=bool(int(getattr(a, 'stack_pick_dg', 0))),
                  vgroup=vmap, nfsv=True, attach=True,
                  # ★ 2026-10-04（**N11**）：`--nfsv-diag 1` ⇒ 在**拒绝路径**上
                  #   记录"同变体场总数 / 其中被判非空的个数 / 那些场的胞数分布
                  #   / 全盒非空场总数"。用来**取证** `nfsv_nofield` 的真实成因
                  #   （`--laths` 72→120 没能动它 ⇒ 原假设已被否，见 `R525 §4`）。
                  #   ⚠ 默认 **0**（关）⇒ 归档路径**逐位不变**。
                  nfsv_diag=bool(int(getattr(a, 'nfsv_diag', 0) or 0)),
                  # ★★★★★ 2026-10-04（**N13：播种非周期 vs 动力学周期**）
                  #   开 ⇒ ① `seed_plate` 取**最小镜像** ② **跳过"有界盒"越界拒绝**
                  #   （两条落位通道共用同一个开关，**必须配套**）。
                  #   动机（实测）：`_r541` b4 臂 `oob = 122` 次 vs `ok = 13` 次
                  #   —— 绝大多数落位尝试死在**边界**上，而那些位点在周期盒里
                  #   与盒心**完全等价**。代码自己也记过"Round 65 实测的 90% 越界"。
                  #   ⇒ 直接卡住 `blocks` 的数目 ⇒ 卡住 C5（填满盒子）。
                  #   ⚠ 默认 **0**（关）⇒ 归档路径**逐位不变**。
                  periodic_seed=bool(int(getattr(a, 'nuc_periodic_seed', 0) or 0)),
                  attach_overlap=a.nuc_overlap_nm * 1e-9,
                  elong=((a.eng_elong if a.eng_elong > 1.0
                          else (a.plate_L / a.plate_W if use_engine else 1.0))),
                  along=(a_ax if (a.eng_elong > 1.0 or use_engine) else None),
                  # ★ R23：默认**不传** ⇒ 由引擎自动决定（attach 下 = False）。
                  #   `--eng-force-reinit` 可强制打开（用于复现 eng5–eng10）。
                  force_reinit_after_event=(True if a.eng_force_reinit else None),
                  t_last_reduce=((a.eng_t_last_reduce_nm if a.eng_t_last_reduce_nm > 0
                                  else (a.nuc_overlap_nm * 0.5 if use_engine else 0.0))
                                 * 1e-9))
    # ★★★ R31（**P1-16**）：`--arm eng` 一直把**零数组**当 `ed` 传给 `nucleate()`。
    #   本来无害（`stack` 通道根本不读 `ed`，所以 eng12/cl1b/cln11 全跑得通），
    #   但只要有人用 `fresh` 通道（`--nuc-init > 0`）或 `use_fcrit`，就会
    #   **崩在 `IndexError`**（实测：`ed` 形状 (nreg,1,1,1)，而 `nucleate` 用
    #   `ed[1:, ci0, ci1, ci2]` 索引真实格点）—— 或者更糟：静默按**全零驱动**
    #   做 `argmax`（⇒ 永远选第一个变体）。
    #   ⇒ 修法：**只有在真要 `fresh` 的时候**才算真实弹性驱动（它占单步 13.5%，
    #     不该为 `stack` 通道白付）。
    _ed_dummy = np.zeros((g.nreg, 1, 1, 1)) if use_engine else None

    def _ed_for_nuc():
        if a.nuc_init > 0:
            return g.elastic_driving()
        if _ed_dummy is not None:
            return _ed_dummy
        return g.elastic_driving()

    if use_engine:
        P('★★★ 臂 eng：**形核交给引擎**（`nucleate` 的 stack 通道 + attach + nfsv）'
          '；R=%.0f nm t=%.1f nm（**含自动补厚**），咬入 %.1f nm，节奏 %s，seed=%d'
          % (a.eng_r_nm, _t_nuc * 1e9, a.nuc_overlap_nm,
             ('每步' if a.eng_cadence == 0 else '每 %d 步' % a.eng_cadence),
             a.eng_seed))
        P('   %s'
          % ('✅ **速率由 athermal 律给出**（`--nuc-law athermal`）：'
             '`n(T) = α_KM(M_s − T)` ⇒ 事件温度 `T_k` 由 `α_KM` 与冷却给出，'
             '**不再是驱动层的节奏**。'
             if _athermal else
             '⚠ 记账：**速率仍由驱动层的节奏规定** —— 引擎的 sympathetic 通道'
             '在没有 `--nuc-law athermal` 时**没有速率律**（`use_fcrit` 只覆盖 `fresh`）。'))
        P('   核形状：%s'
          % ('**长条** elong=%.2f 沿 a 轴（与驱动层一致）' % a.eng_elong
             if a.eng_elong > 1.0 else
             '**圆盘**（引擎原行为）—— 实测足迹只有长条板的 1/5，'
             'F3 面积会小 ~7 倍'))
    np.savez_compressed(
        os.path.join(outdir, 'seeds.npz'), phi=g.phi.astype(np.float32),
        region=g.region(), n_hab=n_hab, w_ax=w_ax, a_ax=a_ax,
        vmap_keys=np.array(sorted(vmap)), vmap_vals=np.array([vmap[k] for k in sorted(vmap)]),
        N=N, L=L, arm=a.arm, laths=np.array(laths_eff))

    # ★★★ R56（**P1-31 的定位实验**）：把**速度扩展带宽**暴露成开关。
    #   为什么：引擎自己的注释记着「无扩展 band=2dx → 0.250；6dx → 0.750；
    #   **20dx → 1.0000**；带太窄时带外剖面不动 ⇒ 带边折点累积 ⇒ **有效速度塌**」。
    #   但那条对照是**平界面 + 常数驱动**（**各向同性**）⇒ 它**看不到角各向异性**
    #   （`AGENTS.md §3` 教训 14）。而 P1-31 实测：解析各向异性 9.90、引擎实际 1.24。
    #   ⇒ 需要扫带宽看 `v_a/v_w` 会不会动。
    #   ⚠ 默认 **20**（= T 系列验证过的值）⇒ `--band-cells` 不传时**逐位不变**。
    kw = dict(aniso=0.4, npref=npref, band_cells=int(a.band_cells),
              mob_beta=a.beta_h,
              mob_beta_w=a.beta_w, adv_grad=a.adv, norm_smooth=a.norm_smooth,
              facet_lam=a.facet_lam, facet_eps=a.facet_eps,
              # ★★★★★ R61（**P1-31 的实现**）：Wulff 凸化速度律（刻面机制）。
              #   `--mob-wulff` 默认 **off**、`--mob-dip` 默认 **0** ⇒
              #   **归档路径逐位不变**（由 `_r30_regress.sh` 把关）。
              mob_wulff=bool(a.mob_wulff), mob_dip=float(a.mob_dip),
              # ★★★★★ R64（§52）：**椭圆面内极曲线**（凸 ⇒ 凸化恒等 ⇒ 无两难）
              mob_iform=str(a.mob_iform), mob_ratio=float(a.mob_ratio),
              # ★★★★★ R64（§53）：**弹性驱动缩放旋钮**（1.0 = 全量 ⇒ 逐位不变）
              el_scale=float(a.el_scale),
              # ★★★★★ R69（`BLOCK_SELFAC.md §8 C`）：**周期性面片投影**（保面机制）。
              #   算子已过正对照（解析长方体幂等、体积 0.0%）。默认 0 ⇒ 逐位不变。
              facet_proj=int(a.facet_proj),
              # ★★★★★ R581-L1（goal §(3) L1）：`adv.extend` 的 EDT 分支档。
              #   默认 `legacy` ⇒ **归档路径逐位不变**（由 `_r576_regress.sh` 把关）。
              extend_mode=str(a.extend_mode))
    # ⚠ 自纠错：`facet_excl` **不能**放进 `kw` —— `kw` 是 `g.advance(**kw)` 的实参，
    #   而 `advance()` 没有这个形参 ⇒ `TypeError`（冒烟第一版实测抓到）。
    #   `facet_project()` 是从 `self` 读属性的，所以只在**构造后**挂到 `g` 上即可。
    dt = 0.15 * dx / (MOB * DF)
    if _athermal:
        # ★ athermal 路径**逐步**按当前 ΔG_v 定 dt（见主循环）⇒ 这里打的是**首步**值。
        #   原先无条件打 `dt = 0.15·dx/(MOB·DF)`（DF=3.5e8 的常数），
        #   对 athermal 是**误导**（真实首步 dt = 0.15·dx/(MOB·ΔG_v(T_1))）。
        dt = 0.15 * dx / (MOB * max(_df_start, 1e-300))
        P('dt **首步** = %.4e s（%d 步 ⇒ 名义 t_sim=%.3e s，实际随 ΔG_v(T) 逐步缩小）；'
          'norm_smooth=%d' % (dt, a.steps, a.steps * dt, a.norm_smooth))
    else:
        P('dt=%.4e s（标称 %.2f nm/步）；%d 步 ⇒ t_sim=%.3e s；norm_smooth=%d'
          % (dt, 0.15 * dx * 1e9, a.steps, a.steps * dt, a.norm_smooth))
    P('-' * 104)

    if a.dry_run:
        mm = BM.measure_state(g.region(), dx, n_hab, w_ax, a_ax, vmap)
        P('--dry-run：初始测量 ' + json.dumps(
            {k: (round(v, 6) if isinstance(v, float) else v)
             for k, v in mm.items()}, ensure_ascii=False))
        return 0

    csvf = open(os.path.join(outdir, 'series.csv'), 'w', newline='')
    cw = csv.writer(csvf); cw.writerow(COLS)
    with open(os.path.join(outdir, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(arm=a.arm, tag=tag, N=N, L=L, dx_nm=dx * 1e9, steps=a.steps,
                       laths=laths_eff, nv=nv, vmap=vmap,
                       omega_max_deg=a.omega_max_deg, omega_mode=a.omega_mode,
                       theta_deg={('%d-%d' % (i + 1, j + 1)):
                                  float(np.degrees(lt.theta[i + 1, j + 1]))
                                  for i in range(nv) for j in range(i + 1, nv)},
                       gamma_RS={('%d-%d' % (i + 1, j + 1)):
                                 (float(lt.gtab[i + 1, j + 1])
                                  if np.isfinite(lt.gtab[i + 1, j + 1]) else None)
                                 for i in range(nv) for j in range(i + 1, nv)},
                       plate=dict(L=a.plate_L, W=a.plate_W, T=a.plate_T,
                                  T_physical=(a.plate_t_physical
                                              if a.plate_t_physical > 0
                                              else a.plate_T)),
                       gap_nm=a.gap_nm, norm_smooth=a.norm_smooth,
                       beta_h=a.beta_h, beta_w=a.beta_w, adv=a.adv,
                       reinit_band=a.reinit_band, nthreads=a.nthreads,
                       # ★★ 2026-09-29 补：这几个**决定这次跑的到底是什么**的开关
                       # 原先**没写进 meta.json**（`reinit_dt` / `grow_stack` /
                       # `nuc_every` / `nuc_gap_nm` / `phi_every`），
                       # 直接违反用户「全过程数据要能事后重测」的要求：
                       # 光看 meta 无法判断一个臂是"预装 6 根"还是"长出来的"。
                       # 除了逐个列出，还整份 dump `vars(a)`（argparse 命名空间），
                       # **今后任何新增的 CLI 开关都会自动进 meta**，不再依赖记得加。
                       reinit_dt=a.reinit_dt, reinit_every=0,
                       grow_stack=bool(a.grow_stack), nuc_every=a.nuc_every,
                       nuc_gap_nm=a.nuc_gap_nm, phi_every=a.phi_every,
                       nuc_overlap_nm=a.nuc_overlap_nm,
                       nuc_compensate=bool(a.nuc_compensate),
                       snap_every=a.snap_every, every=a.every,
                       out_root=a.out, exp_args=vars(a),
                       gamma0=a.gamma0, DF=DF, Mob=MOB, dt=dt, t_sim=a.steps * dt,
                       df_const=(None if _athermal else float(DF)),
                       df_start=(float(_df_start) if _athermal else None),
                       n_hab=n_hab.tolist(), w_ax=w_ax.tolist(), a_ax=a_ax.tolist(),
                       sha_windowB_surface=sha256(os.path.join(_HERE, 'windowB_surface.py')),
                       sha_windowB_lath=sha256(os.path.join(_HERE, 'windowB_lath.py')),
                       sha_windowB_par=sha256(os.path.join(_HERE, 'windowB_par.py')),
                       sha_exp=sha256(os.path.abspath(__file__)),
                       sha_measure=sha256(os.path.join(_HERE, '_bk_measure.py')),
                       git=subprocess_out(['git', '-C', os.path.dirname(
                           os.path.dirname(_HERE)), 'rev-parse', 'HEAD'])),
                  f, ensure_ascii=False, indent=1)

    P0, t_sim, wall0, tstep = None, 0.0, time.time(), []
    # ★★★★★ R477（2026-10-01，**任务(2) ①：准静态钟（路线 1B）**）：
    #   ## 为什么（物理依据，不是拍脑袋）
    #     文献（Bhadeshia，已读原文）：马氏体生长速度**上限 1100 m/s**
    #     ⇒ 生长时间/冷却时间 = (1 µm/1100 m/s)/234 µs ≈ **4×10⁻⁶**
    #     ⇒ **生长相对冷却是"瞬间"的 ⇒ 必须按准静态处理，不能当时间积分。**
    #   ## 旧语义错在哪（`§R2_PARAM_VERDICTS` S12）
    #     旧主循环 `g.t += dt` 里的 `dt` 是 **CFL 步长**（`0.15·dx/(MOB·ΔG)`），
    #     而 `MOB = 1e-9` 是**占位值**（比真实小 ~10⁴ 倍）
    #     ⇒ **"物理时刻"由数值稳定性 + 一个占位参数累加而成。**
    #     后果实测：`abA` 只走完冷却 46.4%、`r464` 只走完 16.9%（`_r465`）；
    #     而门槛 `T* = 641.7 K`（`_r470`）意味着**大部分时间驱动力压不过弹性罚**
    #     ⇒ 板条"播一片溶一片"（`§203`）。
    #   ## 新语义（1B）
    #     **不对 `t` 积分，而是对 `T` 求不动点**：每个温度档内把 T **钉住**、
    #     做**伪时间弛豫**直到 `dG_max` 衰减到 `qs_tol × 阶段初值`，**再降 T 一档**。
    #     · `M` 只决定伪时间的快慢，**不出现在不动点方程里** ⇒ **末态与 `M` 无关**
    #       （前提：速度律对 `M` 线性，现在是）；
    #     · `dt` 在阶段内**固定**（由阶段初的 `dG_max` 定）⇒ 界面位移随 `dG` 衰减
    #       ⇒ 自然收敛；旧写法每步重定 `dt` 使其恒为 0.15 胞 ⇒ **永不收敛**。
    #   ## 惰性
    #     `--qs-clock 0`（**默认**）⇒ 下面所有分支都不进 ⇒ **归档路径逐位不变**
    #     （已由 `_r30_regress.sh` 的"共有列逐位一致"把关）。
    _qs_clock = bool(int(getattr(a, 'qs_clock', 0) or 0)) and _athermal
    #   温度档步长 `ΔT`：默认 `1/α_KM` ⇒ **每档恰好放 1 根核**，共 `n(T_end)` 根。
    #   ★ 这不是拍的：`n(T) = α_KM(M_s − T)` ⇒ 相邻两根核的温度间隔**定义**就是 `1/α_KM`
    #     ⇒ 它**原样复现 C-2 的 `T_k = M_s − k/α_KM` 序列**（见 `PHYSICS_FIRST_SPEC §6.6 选项 A`）。
    _qs_dT = (float(getattr(a, 'qs_dT', 0.0) or 0.0) if _qs_clock else 0.0)
    _qs_dT_auto = _qs_clock and _qs_dT <= 0.0
    if _qs_dT_auto:
        _qs_dT = 1.0 / _alpha
    # ★★★★★ 2026-10-04（**用户拍板：方案 A**；判定与证据见 `R525_TASK5_PARAM_FINDINGS.md §2`）
    #   ## 拍的是什么
    #     `PHYSICS_FIRST_SPEC §6.6` 把"温度档 `ΔT` 取 A（`1/α_KM`）还是 C（用户给）"
    #     留给用户。**用户 2026-10-04 拍板 A。**
    #   ## 为什么 A 是**唯一自洽**的（不是"可以接受"）
    #     `n(T) = α_KM(M_s − T)` 是**每块**的板条数。一档从 `T_k` 降到 `T_{k+1}`：
    #       每块涨   `α_KM·ΔT`
    #       全盒涨   `B·α_KM·ΔT`
    #     ⇒ 取 `ΔT = 1/α_KM` ⇒ 每块涨 **1**、全盒涨 **`B`**
    #        ⇒ **每档每个块各形核 1 根**，逐根可分辨，且**没有引入任何新率律**。
    #     ⇒ `ΔT < 1/α_KM` ⇒ 每块涨不到 1 根 ⇒ 整档**没有任何事件**（白烧机时）；
    #        `ΔT > 1/α_KM` ⇒ 同一档内多根同时形核、**彼此无时序** ⇒ 那正是"burst 当输入"，
    #        而**框架里没有"同档内谁先谁后"的律** ⇒ 必须有额外论证才允许。
    #   ## 实测支持（`_r520c`，`_r523_nucschedule.py`）
    #     5 档反解 `(M_s−T)·α_KM` = `1.000 / 2.000 / 3.000 / 4.000 / 4.999`
    #     ⇒ 档温**精确**落在 `T_k` 上；每档尝试数 `[8,8,8,8,8] = B` ✅
    #   ## 所以这里**硬校验**（用户要求"写成启动断言"）
    #     ⚠ 实测：**没有任何脚本/归档臂显式传过 `--qs-dT`**
    #       （`grep -rn 'qs-dT' *.sh` 为空；60 个 `meta.json` 的 `exp_args.qs_dT` 全为 0）
    #       ⇒ 本断言**不会改变任何既有算例的行为**。
    #     ⚠ `--qs-clock 0`（**默认**）⇒ 整段不进 ⇒ 归档路径逐位不变。
    if _qs_clock and (not _qs_dT_auto):
        _dT_ref = 1.0 / _alpha
        if abs(_qs_dT - _dT_ref) > 1e-9 * max(_dT_ref, 1.0):
            raise SystemExit(
                '❌ **温度档 `ΔT` 与已拍板的方案 A 不符**\n'
                '   你传了 `--qs-dT %.6g`，但方案 A 要求 `ΔT = 1/α_KM = %.6g K`\n'
                '   （α_KM = %.6g /K）\n'
                '\n'
                '   为什么 A 是唯一自洽的：\n'
                '     `n(T) = α_KM·(M_s − T)` 是**每块**的板条数 ⇒ 一档降 ΔT：\n'
                '       每块涨 α_KM·ΔT，全盒涨 B·α_KM·ΔT\n'
                '     ⇒ ΔT = 1/α_KM ⟺ **每档每个块各形核 1 根**（逐根可分辨）\n'
                '     ⇒ ΔT < 1/α_KM ⇒ 整档**无任何事件**（白烧机时）\n'
                '     ⇒ ΔT > 1/α_KM ⇒ 同档内多根同时形核、**彼此无时序**\n'
                '        —— 那是"burst 当输入"，而**框架里没有"同档内谁先谁后"的律**。\n'
                '\n'
                '   若你确实要方案 C（burst 当输入）：**必须先补上物理论证**，\n'
                '   并在文档里登记"同档内时序未解析"。\n'
                '   证据见 `R525_TASK5_PARAM_FINDINGS.md §2`（用户 2026-10-04 拍板 A）。'
                % (_qs_dT, _dT_ref, _alpha))
    _qs_tol = float(getattr(a, 'qs_tol', 2e-3) or 2e-3)
    _qs_max_relax = int(getattr(a, 'qs_max_relax', 400) or 400)
    _qs_win = max(int(getattr(a, 'qs_win', 20) or 20), 1)
    # ★★★★★ R498（2026-10-01，**任务(5) 的"纯溶解档"早退**）：
    #   ## 动机（`_r497_stageinert.py` 实测，只读归档）
    #     `dry_r492on` 的**档 1**（T=849 K）里，t=0 播的初始板条体积
    #     `0.2495 → 0.006836 µm³`（**溶掉 97.3%**），而 `nreg_used` **+0**
    #     （超临界判据把所有核都拒了）⇒ **那一档不是"惰性"，而是"只在溶解"**。
    #     `R470`/`R479` 的两个门槛（`T*=641.7 K` 生长窗口、`377.7 K` 形核门槛）
    #     解释了为什么：`T` 太高 ⇒ 没有东西能长大。
    #   ## ⚠ 为什么**不能**简单跳过这些档（**我原本的建议被 `_r497` 推翻**）
    #     跳过 ⇒ 初始板条**不会溶解** ⇒ 末态**多一根** ⇒ **不等价**。
    #     ⇒ 必须**照跑**；但**不需要"弛豫到收敛"** —— 纯溶解**没有不动点**，
    #       收敛判据（窗口内 `Σ|ΔV|/V < tol`）**原理上永远不满足**
    #       ⇒ 每档都撞 `--qs-max-relax`（实测 400 步）⇒ **白烧 20×400 步**。
    #   ## 判据（**保守：只砍"确定在溶"的档**）
    #     若本档**从头到现在 `V` 每一步都在减少**（纯溶解、无任何增长迹象），
    #     且已跑够 `--qs-shrink-cap` 步 ⇒ **本档提前结束、降 T**。
    #     ⚠ `--qs-shrink-cap 0`（**默认**）⇒ 完全关闭 ⇒ 归档行为逐位不变。
    #     ⚠ 这是**数值优化、不是物理**：它只改"纯溶解段跑多少步"。
    #       **必须**用对照实验确认末态在容差内一致（不得只靠论证）。
    _qs_shrink_cap = int(getattr(a, 'qs_shrink_cap', 0) or 0)
    _qs_shrink_n = 0                 # 本档连续"V 在减少"的步数
    _qs_shrink_v = None              # 上一步的转变胞数
    _qs_shrink_used = 0              # 因早退省下的档数（记账）
    _qs_T = float(_Tstart)          # 当前档的温度（阶段内**不变**）
    _qs_stage = 0                   # 已完成的温度档数
    _qs_ref = None                  # 本阶段初的 `dG_max`（**只作诊断**，不作判据）
    _qs_relax = 0                   # 本阶段已做的弛豫步数
    _qs_dt = None                   # 本阶段**固定**的弛豫步长
    _qs_conv = True                 # "可以降 T 了"（首档进来就是 True）
    _qs_stop = False                # 到 T_end 或步数用尽
    _qs_V = None                    # 上一步的转变胞数
    _qs_dV = []                     # 滑动窗口内的 |ΔV|（胞）
    _qs_dg = []                     # 各档收敛时的 dG_max/dG_ref（诊断）
    # ★★★★★ R581-ckpt 审计发现（判据⑩ 的样本）：**`_qs_rel_last` 是**只写不读**的死变量**
    #   实测：全仓 `grep -n '_qs_rel_last'` **只有 1 处赋值**（本循环内
    #   `_qs_rel_last = _rel`），**零处读取**。
    #   ⇒ 它长得像"必须随检查点保存的状态"（goal 任务(1) 的 1j 列了它），
    #     实则**与动力学无关**。
    #   ⇒ 这里**只加一个初始值**，让检查点采集器能安全读它（**数值零影响**：
    #     既有的唯一赋值点照旧覆盖它，且没有任何读取点）。
    _qs_rel_last = None             # ⚠ **只写不读**（留档用；见上注）
    if _qs_clock:
        P('★★★★★ **准静态钟（1B）已启用**：ΔT = %.3f K（= 1/α_KM，**方案 A**，'
          '用户 2026-10-04 拍板；%s）⇒ 每档每块各 1 根；'
          '收敛判据：窗口 %d 步内 Σ|ΔV|/V < %.4g；每档最多 %d 步'
          % (_qs_dT, '**自动取默认**' if _qs_dT_auto else '**显式传入且已通过断言**',
             _qs_win, _qs_tol, _qs_max_relax))
        P('   物理依据：文献生长上限 1100 m/s ⇒ t_grow/t_cool ≈ 4e-6 ⇒ 生长是"瞬间"的；')
        P('   旧路径把 CFL 步长 `0.15dx/(MOB·ΔG)` 当物理时间 ⇒ 已弃用（本开关下）。')
    # ★ R208（`§135.7`）：三项量级的逐步记录（`--diag-terms` 关时恒为空表）。
    diag_terms_rec = []
    # ★ R238（`§135.6`）：逐变体 `ed` 分布的逐步记录（`--diag-edv` 关时恒为空表）。
    diag_edv_rec = []
    nfail = 0
    # ★★★ R29：athermal 钟的逐步状态（`--nuc-law cadence` 下**全部不参与**）
    n_ath_ev = 0                 # 由 athermal 律触发的形核次数
    n_ath_tgt = 0                # 当前的累计根数（不含预摆的第 1 片）
    T_hist = []                  # 每次事件时的 (step, t, T, df)
    # ★ §189（缺陷③）：fresh/stack 的**实际分配**记账（必须留在日志里，不是内部变量）
    n_mode = {}                  # {'fresh': n, 'stack': n}
    n_fresh_fallback = 0         # 要 fresh 却被拒、退回 stack 的次数
    if _athermal:
        # 预摆的第 1 片视为"在 M_s 处形核" ⇒ 累计计数从 1 起算
        n_ath_tgt = 1

    # ============ ★★★★★ R146（**P1-43**）：**块内界面完整性自检**（`§99` 的缺口）============
    #   位置：**主循环之前、全部播种路径都跑完之后**。
    #   ⚠ 第一版放在"播种 N 片"那句打印之后 ⇒ `g.region()` **还是全 0**
    #     （实测 `n_occ = 0`、`cov = nan`，与"空 region"的负对照**逐位一致**）
    #     ⇒ 已移到此处。**这一条也说明"打印顺序 ≠ 状态就绪"**。
    #   ⚠ 纯诊断：只读 `region`，**不改任何数值**；失败只打警告。
    #   ⚠ `cov` 有 **`L` 依赖**（`§100`：L=450 ⇒ 0.44；L=1600 ⇒ 1.08）
    #     ⇒ 判据用 `cov_norm = cov / cov_baseline(L)`（阈值 0.95）。
    try:
        _vmap_local = {i + 1: int(laths_eff[i]) for i in range(len(laths_eff))}
        _reg0 = g.region()
        _zc = dict(region=_reg0, L=L, n_hab=n_hab,
                   vmap_keys=np.array(sorted(_vmap_local)),
                   vmap_vals=np.array([_vmap_local[k]
                                       for k in sorted(_vmap_local)]))
        _cv = BM.snapshot_coverage(_zc)
        _cov = float(_cv.get('cov', float('nan')))
        _bf = _cv.get('beta_frac', {}) or {}
        _mb = max(_bf.values()) if _bf else float('nan')
        _cn, _cb, _cn_n, _cn_ex = BM.cov_norm(_cov, a.plate_L * 1e-9)
        _nocc = int(_cv.get('n_occ', 0))
        # ★★★ R152 修（**R30 回归的 `①a2` 抓到的**）：**先问判据适不适用**（硬规程④）。
        #   实测：`--grow-stack` 路径 **t=0 只播 1 片** ⇒ `n_occ = 1`
        #   ⇒ `exp_int = tot_broad·(n_occ−1)/n_occ = **0**` ⇒ `cov = nan`。
        #   而第一版会对 `nan` 直接打 ❌「本几何的块内判据没过」——
        #   **那是误报**：**1 根板条根本没有"同变体界面"这个东西**，判据**不适用**。
        #   ⇒ 单场/单根的情形**明说"不适用"**，不打 ❌。
        if _nocc < 2:
            P('★★ **块内界面自检（R146）**：`n_occ` = %d/%d ⇒ **判据不适用**'
              '（t=0 只有 %d 根在场 ⇒ **没有"同变体界面"这个东西**）'
              % (_nocc, len(laths_eff), _nocc))
            P('   （`--grow-stack` 等"只播 1 片、随后邻位形核"的路径就是这一档；'
              '不是缺陷，是**判据的适用域**问题。）')
        else:
            _ok_cov = (_cn == _cn) and (_cn >= 0.95)
            _ok_b = (_mb == _mb) and (_mb <= 0.25)
            P('★★ **块内界面自检（R146 / `§99` 的缺口）**：`cov(t=0)` = **%.3f**，'
              '各对 β 占比 max = **%.2f**，`n_occ` = %d/%d'
              % (_cov, _mb, _nocc, len(laths_eff)))
            P('   `cov_norm` = %.3f（基线 `cov_base(L=%.0f nm)` = %.3f，该档 n=%d%s）⇒ %s'
              % (_cn, a.plate_L, _cb, _cn_n,
                 '' if _cn_ex else '，**表里没有正好这个 L，用了最近档**',
                 '✅ ≥0.95' if _ok_cov else '❌ **低于 0.95**'))
            P('   β 占比判据（≤0.25）⇒ %s' % ('✅' if _ok_b else '❌ **超出**'))
            if not (_ok_cov and _ok_b):
                P('   ⚠⚠ **本几何的"块内"判据没过** —— 播种阶段就可能把 F3（低角晶界）播坏了。')
                P('      参照：合格的 L=1600 档 `cov` = 1.079；L=600 档最好的只有 0.532。')
                P('      （`§99` 规程⑧：多块几何必须**块间** `nf2(t=0)==0` **且** 本条过。）')
    except Exception as _e:                                     # pragma: no cover
        P('⚠ 块内界面自检失败（不影响仿真）：%s' % _e)

    for it in range(0, a.steps + 1):
        # ★ R477（1B）：到 T_end **且该档已弛豫收敛** ⇒ 正常收工（不是步数用尽）。
        if _qs_clock and _qs_stop and _qs_conv:
            P('   ★ 准静态钟：T 已到 T_end 且本档收敛 ⇒ 提前结束于 step %d'
              '（预算 %d 步，实际用 %d）' % (it, a.steps, it))
            break
        if it > 0:
            tw = time.time()
            if _athermal:
                if _qs_clock:
                    # ★ 1B：阶段内 **T 不动**，只有"收敛"后才降一档。
                    if _qs_conv and not _qs_stop:
                        if _qs_stage > 0:
                            _qs_T -= _qs_dT
                        if _qs_T <= float(_Tend) + 1e-9:
                            _qs_T = float(_Tend)
                            _qs_stop = True
                            P('   ★ 准静态钟：到达 T_end = %.1f K ⇒ 本步后停止'
                              '（共 %d 档）' % (_Tend, _qs_stage))
                        g.set_T(_qs_T)
                        # 物理时刻由**温度**反推（冷却时间表是物理的）
                        g.t = (_qs_T - float(_Tstart)) / (-_q)
                        t_sim = g.t
                        _qs_ref, _qs_relax, _qs_dt = None, 0, None
                        # ★ R498：新档开始 ⇒ 重置"纯溶解"计数（保守：每档独立判）
                        _qs_shrink_n, _qs_shrink_v = 0, None
                        _qs_stage += 1
                    _df_now = float(g.df[1])
                    if _qs_dt is None:
                        # 本阶段固定 dt（由**阶段初**的 dG 定）⇒ 之后位移随 dG 衰减
                        _qs_dt = 0.15 * dx / (MOB * max(_df_now, 1e-300))
                    dt = _qs_dt
                else:
                    # ★ 钟：先走时间、再把 T 换成驱动力，然后才推进几何。
                    #   （语义与 `LevelSetMulti.advance_T` 一致；这里显式写开是为了
                    #     让 `dt` 能按**当前** ΔG_v 自适应 —— 降温 ⇒ ΔG_v 涨 ⇒ dt 变小。）
                    g.t += dt
                    g.set_T(g.T_of_t(g.t))
                    _df_now = float(g.df[1])
                    dt = 0.15 * dx / (MOB * max(_df_now, 1e-300))
            # ★★★★★ R74（`R30_AUDIT_LEDGER.md` §77）：把"场→变体"映射挂到引擎对象上。
            #   为什么：`LevelSetMulti.facet_project()` 需要它来构造"同变体的其他场"
            #   排除掩码（只投影外侧，保根数）。引擎**没有**这个属性，也没从构造
            #   函数收到变体信息（`__init__` 里全部按**场号**索引）⇒ `excl` 曾恒为
            #   `None`，导致 §76 的"只投影外侧已生效"是**错的**（§77 已更正）。
            #   ⚠ 只新增属性 ⇒ 不影响任何既有路径。
            g.vmap = dict(vmap)
            g.advance(dt, **kw)
            # ★ R477（1B）：本阶段的**收敛判据**。
            #   ## 为什么不用 `dG_max`（第一版就是它，**实测失败，留痕**）
            #     第一版判据：`dG_max ≤ qs_tol × 阶段初值`。
            #     **实测（`_r478` 冒烟，`--qs-tol 0.02 --qs-max-relax 400`）**：
            #       900 步只走完 **~2 档**（末温 801 K，预期 10.4 档）⇒ **每档都撞 400 步上限**。
            #     根因：`dG_max` 是**全场最大值** ⇒ 被**最尖的那个胞**（尖端/1 胞孤儿，
            #       其曲率 ~1/Δx）主导，而那一项**永远不衰减** ⇒ 判据**原理上到不了**。
            #       （与 `windowB_surface.py:3832` 记的"1 胞孤儿压低全场 dt"是同一件事。）
            #   ## 改用什么：**窗口内的相对体积变化**
            #     `Σ_窗口 |ΔV| / V < qs_tol`，其中 `V` = 已转变胞数。
            #     物理含义直白：**"形状不再变了"**；而且它对单个胞的抖动不敏感
            #     （窗口求和）⇒ 与"弛豫到不动点"的定义一致。
            #     ⚠ 代价：每步多一次 `region()`（一次 N³ argmin，约与 `advance` 同量级，
            #       但**只在 `--qs-clock 1` 下付**）。
            if _qs_clock:
                _qs_relax += 1
                _dgm = float(getattr(g, 'dG_max', float('nan')))
                if _qs_ref is None and np.isfinite(_dgm):
                    _qs_ref = _dgm
                _Vnow = int((g.region() != 0).sum())
                if _qs_V is not None:
                    _qs_dV.append(abs(_Vnow - _qs_V))
                    if len(_qs_dV) > _qs_win:
                        del _qs_dV[0]
                _qs_V = _Vnow
                _rel = (sum(_qs_dV) / max(_Vnow, 1)) if len(_qs_dV) >= _qs_win else 1.0
                _qs_rel_last = _rel
                _qs_conv = bool((len(_qs_dV) >= _qs_win and _rel < _qs_tol)
                                or _qs_relax >= _qs_max_relax)
                # ★ R498：**纯溶解档早退**（默认关）。判据见主循环前的长注释。
                if _qs_shrink_cap > 0:
                    if _qs_shrink_v is not None and _Vnow < _qs_shrink_v:
                        _qs_shrink_n += 1
                    else:
                        _qs_shrink_n = 0        # 出现"没在减少" ⇒ 计数清零（保守）
                    _qs_shrink_v = _Vnow
                    if (not _qs_conv) and _qs_shrink_n >= _qs_shrink_cap:
                        _qs_conv = True
                        _qs_shrink_used += 1
                        P('   [qs] 档 %d **纯溶解早退**：V 连续 %d 步减少'
                          '（%.0f→%.0f 胞），按 --qs-shrink-cap %d 提前降 T'
                          % (_qs_stage, _qs_shrink_n, float(_qs_shrink_v),
                             float(_Vnow), _qs_shrink_cap))
                if _qs_conv and _qs_relax > 1:
                    # ★ 逐档记账（落在 stdout/log 里，便于事后核"每档用了多少步"）
                    P('   [qs] 档 %d 收敛：T=%.2f K  用了 %d 步  窗口 Σ|ΔV|/V=%.3g'
                      '  dG_max/dG_ref=%.3g'
                      % (_qs_stage, _qs_T, _qs_relax, _rel,
                         (_dgm / _qs_ref) if (_qs_ref and np.isfinite(_dgm)
                                              and _qs_ref > 0) else float('nan')))
            tstep.append(time.time() - tw)
            if not _qs_clock:
                t_sim += dt
            # ★★★★★ R208（`§135.7`）：**三项量级的逐步记录**（默认关）。
            #   只读 `g.diag_terms`（引擎在 `advance` 里算好的），**不改任何数值**。
            #   动机见 `--diag-terms` 的 help 与 `windowB_surface.py:3348` 的注释。
            if bool(a.diag_terms) and getattr(g, 'diag_terms', None):
                _dt_ = g.diag_terms
                if _dt_.get('error'):
                    if it == 0:
                        P('   ⚠ `--diag-terms` 出错（不影响仿真）：%s'
                          % _dt_['error'])
                else:
                    _rec = dict(step=int(it), t_s=float(t_sim),
                                vmap_split=bool(_dt_.get('vmap_split')))
                    for _cls in ('vv', 'f3', 'vb'):
                        _c = _dt_.get(_cls) or {}
                        _rec[_cls] = _c
                    # ★ R353（`§170` 的**存疑复核**）：把引擎的 `dbg` 中间计数也落盘。
                    #   动机：`§170` 引用了 `vv.n ≡ 0`（400/400 步）来判"`advance` 的
                    #   `(karr,larr)` 基里没有异变体面片"，但 `_r353` 用归档 `band_*`
                    #   重建亚军，实测**几何 F2 胞上有 88.9% 的亚军是异变体邻居**
                    #   ⇒ **两者矛盾，必须让引擎自己把 `larr` 的分布吐出来**。
                    #   ⚠ **纯附加字段**：`dbg` 是引擎在 `windowB_surface.py:3427-3451`
                    #   已经算好的只读统计，这里只是**多抄一份进 JSON**
                    #   ⇒ 不改任何数值、不改任何分支（仍由 `--diag-terms` 门控）。
                    _rec['dbg'] = _dt_.get('dbg') or {}
                    diag_terms_rec.append(_rec)
                    if it % max(int(a.every), 1) == 0 or it == a.steps:
                        # ⚠ 记账（硬规则⑫ 的同类）：**不能用 `x or 0.0`** ——
                        #   `med_df`/`med_ed` 会**恰好是 0.0**，`0.0 or d` 会把它
                        #   悄悄换成 `d`（第一版就踩了这个，把"恰好 0"印成了别的数）。
                        def _f(v):
                            return float(v) if isinstance(v, (int, float)) else float('nan')
                        _pv = _rec.get('vv') or {}
                        _pf = _rec.get('f3') or {}
                        P('   ★★ **三项量级**（`§135.7`）@step %d  vmap 拆分=%s'
                          % (it, _rec['vmap_split']))
                        for _lab, _p in (('F2 异变体', _pv), ('F3 同变体', _pf),
                                         ('F1 含母相', _rec.get('vb') or {})):
                            if not _p or 'med_ed' not in _p:
                                P('      %-9s 胞数 %-7s（不足，跳过）'
                                  % (_lab, _p.get('n', 0)))
                                continue
                            P('      %-9s 胞数 %-7d `|Δed|` 中位 **%.3e**'
                              '（`Δed`≡0 占 %.1f%%）  `|stk·κ|` 中位 **%.3e**'
                              '  **比值中位 %.3f%%**（99 分位 %.3f%%）'
                              % (_lab, _p['n'], _f(_p['med_ed']),
                                 100 * _f(_p.get('frac_ed0', 0.0)),
                                 _f(_p['med_sk']),
                                 100 * _f(_p.get('med_ratio', float('nan'))),
                                 100 * _f(_p.get('p99_ratio', float('nan')))))
                        P('      `|df_k−df_l|` 中位 = %.3e（**必须恰好 0**：'
                          '所有 α′ 变体共用同一个 `df`）' % _f(_pv.get('med_df', 0.0)))
                        # ★ R229（Q-16 定位）：打印**逐步放开的掩码计数**
                        _dbg = _dt_.get('dbg') or {}
                        if _dbg:
                            P('      【Q-16 定位】变体-变体胞(原始)=%s  其中同变体=%s  '
                              '通过 `_fin` 的变体-变体=%s  全 `_fin`=%s'
                              % (_dbg.get('n_vv_raw'), _dbg.get('n_samev'),
                                 _dbg.get('n_fin_vv'), _dbg.get('n_fin')))
                            P('        有限计数：`phb`=%s `stk·κ`=%s `Δed`=%s `df`=%s'
                              % (_dbg.get('fin_phb'), _dbg.get('fin_skt'),
                                 _dbg.get('fin_edt'), _dbg.get('fin_dft')))
                            # ⚠ R231 修：原来把这三行放在 `if it == 0 or n_samev:`
                            #   里面，而诊断**首次触发是在 `it == 1`**（it=0 的那次
                            #   `advance` 走的是另一条早退路径）⇒ **一行都没打印**。
                            #   ⇒ 改成**无条件打印**（诊断本身已按 `--every` 节流）。
                            if _dbg.get('n_kpos') is not None:
                                P('        `karr>0` 的胞数 = %s；`karr` 取值 = %s'
                                  % (_dbg.get('n_kpos'), _dbg.get('karr_uniq')))
                                P('        `karr>0` 处 `larr` 的取值分布 = %s'
                                  % (_dbg.get('larr_where_kpos'),))
                                P('        `larr` 全局取值分布（前 20）= %s'
                                  % (_dbg.get('larr_uniq'),))
                                P('        `vmap` 键=%s 值=%s'
                                  % (_dbg.get('vmap_keys'), _dbg.get('vmap_vals')))
                                _vt = _dbg.get('var_tab')
                                if _vt:
                                    P('        场→变体表（索引 0..nreg−1）= %s' % _vt)
            # ★★★★★ R238（`§135.6` / 条件③主线）：**逐变体 `ed` 分布**的逐步记录。
            #   只读 `g.diag_edv`（引擎算好的），**不改任何数值**。
            if bool(a.diag_edv) and getattr(g, 'diag_edv', None):
                _de = g.diag_edv
                if _de.get('error'):
                    if it == 0:
                        P('   ⚠ `--diag-edv` 出错（不影响仿真）：%s' % _de['error'])
                else:
                    # ⚠ 修（**第 21 个自查错误**）：引擎返回的 `_de` **自己也含 `step`**
                    #   ⇒ `dict(step=..., **_de)` 会 `TypeError: dict() got multiple
                    #   values for keyword argument 'step'`。
                    #   ⇒ 先拷贝、再**覆盖**，不靠 `**` 展开去撞键。
                    _rec_e = dict(_de)
                    _rec_e['step'] = int(it)
                    _rec_e['t_s'] = float(t_sim)
                    diag_edv_rec.append(_rec_e)
                    if it % max(int(a.every), 1) == 0 or it == a.steps:
                        _pf = _de.get('per_field') or {}
                        P('   ★★ **逐变体 `ed`**（`§135.6`）@step %d：%d 个变体在场'
                          % (it, _de.get('n_field', 0)))
                        for _k in sorted(_pf, key=lambda x: int(x)):
                            _v = _pf[_k]
                            P('      场%-3d V%-4d 体积 %-9.4f µm³  `ed` 中位 **%+.4e**'
                              '（均值 %+.4e；10–90 分位 %+.3e … %+.3e）'
                              % (_v['field'], _v['variant'], _v['vol_um3'],
                                 _v['med'], _v['mean'], _v['p10'], _v['p90']))
                        if 'med_spread' in _de:
                            P('      ⇒ 跨变体：`ed` 中位的**极差 %.4e**、'
                              '**标准差 %.4e**（均值 %+.4e）；体积 CV = %.3f'
                              % (_de['med_spread'], _de['med_std'],
                                 _de['med_mean'], _de.get('vol_cv', float('nan'))))
            if not np.all(np.isfinite(g.phi)):
                P('✗✗ `phi` 非有限 @ step %d —— 立即中止并**保留现场**' % it)
                np.savez_compressed(os.path.join(outdir, 'CRASH_phi.npz'),
                                    phi=g.phi, step=it)
                nfail = 4
                break
        # ★★★ G-1 方案 B：**生长中的邻位形核**（在推进之前播下一片）
        if grow and a.nuc_every > 0 and it > 0 and (it % a.nuc_every == 0):
            _j = _seed_next()
            if _j is not None:
                P('   ★★ 形核事件 @ step %d：新核进入**新场 %d**（变体 %d）'
                  % (it, _j, laths_eff[_j - 1]))
        # ★★★ R12：**引擎侧自发形核**（`--arm eng`）。与上面 `_seed_next` 的区别：
        #   `_seed_next` 由**驱动层**决定"哪一步、放在哪、进哪个场"；
        #   这里把**位置与场的选择**交给引擎的 `nucleate()`（`attach` + `nfsv`），
        #   驱动层只保留**节奏**（`--eng-cadence`；0 = 每步都问一次）。
        #   ⇒ 记账：**速率仍然是被规定的** —— 引擎的 sympathetic 通道目前
        #     **没有速率律**（`use_fcrit` 只覆盖 `fresh` 通道）。这一点不得含糊。
        if use_engine and it > 0 and a.eng_cadence >= 0 and not _athermal:
            if a.eng_cadence == 0 or (it % a.eng_cadence == 0):
                _reg_e = g.region()
                _fnow = 1.0 - float((_reg_e == 0).sum()) / g.N ** 3
                # ★★ R31：`--nuc-init > 0` ⇒ 走 **`fresh`（独立形核）** 通道，
                #   那条通道才是**按 `--var-rule` 选变体**的那一条（`stack` 通道是
                #   "同变体、新场"，与变体选择无关）。MB-2 的 P-SA-1 必须走这条。
                _nf = 1 if a.nuc_init > 0 else 0
                _ev = g.nucleate(_ed_for_nuc(),
                                 f_now=_fnow, n_fresh=_nf, n_stack=1,
                                 df=float(g.df[1]))       # §196 同上
                n_eng_ev += len(_ev)
                if _ev:
                    _kk, _md = _ev[0][0], _ev[0][1]
                    P('   ★★ **引擎形核** @ step %d：场 %d（变体 V%d），模式 %s'
                      '（累计 %d 次）'
                      % (it, _kk, vmap.get(_kk, -1), _md, n_eng_ev))
        # ★★★ R29：**athermal 律触发的形核**（`--nuc-law athermal`）。
        #   判据不是"第几步"，而是**累计核数**：
        #       `n_target(T) = floor(α_KM·(M_s − T))`，`T = T_of_t(t)`。
        #   ⇒ 事件出现在 `T_k = M_s − k/α_KM`，与步数无关 ⇒ **速率由物理给出**。
        #   ⚠ 与 `cadence` 路径**互斥**（上面那条已加 `not _athermal`）⇒ 默认逐位不变。
        if _athermal and use_engine and it > 0:
            _Tnow = float(g.T)
            # ★★★★★ R502（2026-10-01，**"块数"口径的框架缺口**，见 `R502_BLOCKCOUNT.md`）：
            #   `CL.alpha_km_n_lath(T)` 是 **C-2 导出的「一个块里堆叠的板条数」**
            #   （块厚 `W_block = n·t`），而 `limitations()` 第 1 条明写
            #   「面内并列的多个 block 需要在面内做分割，**本轮不做**」
            #   ⇒ **框架里没有"块数"这条律**。
            #   而本行原来把它当成了**全盒的事件上界** ⇒ 全盒最多 `n(T_end)` 次事件，
            #   且 `B>1` 时每个块都拿不到 C-2 说的那个 `n`。
            #   ⇒ 正确的总量是 `N_tot = B · n(T)`，其中 `B`（块数）是**输入**。
            #   ⚠ **`B` 不是新编的律**：与 `--plate-L`/`--nuc-init` 同类的输入；
            #     它还有一个**几何导出的上界** `B_max = L_box²/A_f`（每块占满一个足迹）。
            #   ⚠ `--nuc-block-target 0`（**默认**）⇒ 完全走原路径 ⇒ 归档逐位不变。
            _Bt = int(getattr(a, 'nuc_block_target', 0) or 0)
            _n_blk = int(np.floor(CL.alpha_km_n_lath(_Tnow, _alpha) + 1e-12))
            if _Bt > 0:
                _tgt = min(_Bt * _n_blk, nv)
            else:
                _tgt = min(_n_blk, nv)
            while n_ath_tgt < _tgt and n_ath_tgt < nv:
                _reg_e = g.region()
                _fnow = 1.0 - float((_reg_e == 0).sum()) / g.N ** 3
                # ★★★★★ 2026-10-01（`R30_AUDIT_LEDGER.md` §189，**缺陷③**）：
                #   **fresh / stack 交错**（`--nuc-fresh-every K`）。
                #   ## 为什么必须交错
                #     引擎的 `nucleate()` 里 **fresh 通道先跑、且 `cap = max_per_step = 1`**
                #     （`windowB_surface.py:1500+` / `:1645+`）⇒ 只要 `--nuc-init` 的待机
                #     位点还没用完，**每一次事件都走 fresh、`stack` 一次也拿不到名额**。
                #     而 `fresh` = **新块**（随机位点、按 `--var-rule` 选变体），
                #     `stack` = **同变体、新场、贴在块外缘**（块内板条）。
                #   ⇒ 现状只能二选一：
                #       `--nuc-init > 0` ⇒ 一堆**单板条块**（有块、无块内堆叠）；
                #       `--nuc-init = 0` ⇒ 只有 `stack` ⇒ **永远只有一个块**
                #         （`_seed_next` 用顺序场号 + 块 0 的轴，见 `:785`）。
                #     **两条都给不出「多块 × 每块多根板条」。**
                #   ## 规则（先在文档里写死，再实现）
                #     第 `k` 个 athermal 事件：`k % K == 1` ⇒ **fresh**（建新块），
                #     否则 ⇒ **stack**（往已有块里加板条）。
                #     ⇒ `K=1` ⇒ 全 fresh（= 旧行为）；`K=4` ⇒ 每 4 个事件建 1 个新块。
                #   ⚠⚠ **R494 更正（自查错误 #92/#93 的连带）**：
                #     上面的"规则"与**下面的代码差一个相位**：
                #       文档写 `k % K == 1`（⇒ 首个 fresh 是**事件 1**）
                #       代码是 `n_ath_tgt % K == 0`（⇒ 首个 fresh 是**事件 K**）
                #     两者都满足"每 K 个事件建 1 个新块"，只是**整体平移**。
                #     **实测确认代码是对的、且没有死锁**（`_r494`，`_r482` 两臂）：
                #       A 臂 5 个事件 = attach×3, **fresh(决策序号 4)**, attach×1；
                #       B 臂 6 个事件，同样规律。
                #     ⇒ **本条不是缺陷**（我一度登记成 "F1 死锁"，那是我 grep 错了串，见 `_r494`）。
                #     ⚠ 但**文档与代码不一致这件事本身要修**：以**代码**为准，
                #       因为归档臂（`abB` 用了 `--nuc-fresh-every 4`）跑的是代码的行为。
                #       ⇒ 下面这行注释保留原文以便溯源，**但请按代码理解**。
                #   ## 物理依据（框架内，不是拍脑袋）
                #     `windowB_closure.alpha_km_n_lath` 的 C-2 推导**只对"堆叠型块"成立**
                #     （`limitations()` 第 1 条明写："面内并列的多个 block 需要在面内
                #     做分割，本轮不做"）⇒ **框架里本来就没有"块的数目"这条律**。
                #     本开关**不发明新律**，只把"块数 vs 块内板条数"的**分配**暴露出来，
                #     并且**必须**在 `meta.json` 里留痕（`--nuc-fresh-every` 经 `vars(a)` 入档）。
                #     ⚠ 所以：**本开关下的"块数"是规定的，不是涌现的**，不得当成物理结论。
                #   ## 惰性
                #     `K = 0`（默认）⇒ 走**原来的** `n_fresh=(1 if nuc_init>0 else 0)` 一行
                #     ⇒ 归档路径**逐位不变**。
                _K = int(getattr(a, 'nuc_fresh_every', 0) or 0)
                if _K > 0 and a.nuc_init > 0:
                    _fresh_now = ((n_ath_tgt % _K) == 0)
                    _nf, _ns = (1, 0) if _fresh_now else (0, 1)
                else:
                    _nf, _ns = (1 if a.nuc_init > 0 else 0), 1
                # ★★★★★ 2026-10-01（`R30_AUDIT_LEDGER.md` **§196**）：**接线缺口修复**。
                #   `nucleate()` 的签名是
                #     `nucleate(ed, …, df=0.0)`（`windowB_surface.py:1450`），
                #   而**驱动层三处调用一次都没传 `df`** ⇒ `df` 恒为 **0.0**
                #   ⇒ 引擎里那条判据实际算的是
                #       `(0 + max_k ed_k) > 4γ/t`
                #   而注册表 §9 / `windowB_surface` 的注释写的是
                #       `(df + max_k ed_k) > 4γ/t`（`df = ΔG_v(T)`）
                #   ⇒ **化学驱动力项整个丢了**（该项量级 1.2e8–3.5e8，
                #     而阈值 `4γ/t = 2.4e6` ⇒ 丢掉的是**最大的那一项**）。
                #   ⚠ **惰性**：`df` 只在 `use_fcrit=True` 分支里被读
                #     ⇒ `--nuc-fcrit 0`（默认）下**逐位不变**。
                _ev = g.nucleate(_ed_for_nuc(),
                                 f_now=_fnow, n_fresh=_nf, n_stack=_ns,
                                 df=float(g.df[1]))
                # ★ 记账（不静默）：要 `fresh` 却被挡（待机位点用尽 / 落位失败）
                #   ⇒ 当场退回 `stack`，并把退回**计数**（`meta` 里查得到）。
                if _nf > 0 and not _ev and _ns == 0:
                    _ev = g.nucleate(_ed_for_nuc(),
                                     f_now=_fnow, n_fresh=0, n_stack=1,
                                     df=float(g.df[1]))   # §196 同上
                    if _ev:
                        n_fresh_fallback += 1
                        P('   ⚠ athermal 事件 #%d：`fresh` 被拒 ⇒ **退回 `stack`**'
                          '（本算例累计 %d 次）'
                          % (n_ath_tgt + 1, n_fresh_fallback))
                n_ath_tgt += 1
                if _ev:
                    n_eng_ev += len(_ev)
                    n_ath_ev += 1
                    n_mode[_ev[0][1]] = n_mode.get(_ev[0][1], 0) + 1
                    # ★★★★★ 2026-10-04（**N7：报告口径修复**；判定见
                    #   `R2_PARAM_VERDICTS.md §0 N7`）
                    #   ## 错在哪
                    #     `CL.T_of_k(k)` 的定义是 `T_k = M_s − k/α_KM`，而它反演的
                    #     `alpha_km_n_lath` 是 **C-2 导出的「一个块里堆叠的板条数」**
                    #     （该函数自己的 docstring：「本条**只对"堆叠型块"成立**…
                    #      平面上并列的块…本轮**不做**」）
                    #     ⇒ **`T_of_k` 的 `k` 是「块内序号」，不是「全盒序号」。**
                    #     而这里原来传的是 `n_ath_tgt` = **全盒累计事件数**
                    #     （判据是 `n_ath_tgt < _tgt`，`_tgt = B·n(T)`，见上面 `:1807`）
                    #     ⇒ **拿全盒序号去喂块内公式，大了整整 `B` 倍。**
                    #   ## 症状（**一眼可辨的物理不可能值，这就是"tell"**）
                    #     `_r520c`（B=8、α_KM=0.011、M_s=873 K）实测打印：
                    #       `T_25 理论 = −1399.7 K`、`T_34 理论 = −2217.9 K`
                    #     —— **负的绝对温度**。`M_s − 25/0.011 = 873 − 2272.7 = −1399.7` ✅ 对得上。
                    #   ## 正确的块内序号
                    #     全盒第 `k` 个事件、共 `B` 个块 ⇒ 均摊到每块是第 `ceil(k/B)` 根
                    #     ⇒ `T_of_k(ceil(k/B))`。
                    #   ## ★★ 自验证（**这就是"修对了"的证据，不是推理**）
                    #     `ceil(25/8) = 4` ⇒ `T_4 = 873 − 4/0.011 = **509.36 K**`
                    #       —— 而事件 #25 实测就发生在 **T=509.4 K**（`_w2_r520_param.log:2636`）✅
                    #     `ceil(34/8) = 5` ⇒ `T_5 = 873 − 5/0.011 = **418.45 K**`
                    #       —— 事件 #34 实测 **T=418.5 K** ✅（`:2651`）
                    #     ⇒ **修后的打印与实测温度吻合到 0.1 K**。
                    #   ## 影响范围
                    #     ⚠ `T_of_k` **只出现在这一句打印里**，**不参与判据**
                    #       （判据是 `while n_ath_tgt < _tgt`，`:1810`，本来就对）
                    #     ⇒ **这是纯报告缺陷**：不改任何数值、不改进程
                    #     ⇒ 归档结论不受影响（`dry_*` 的 CSV 里没有这一列）。
                    #   ⚠ 但它**误导性极强**：读日志的人会以为"时钟坏了、事件提前了几千 K"，
                    #     而真相是**判据正确、只有这一行数字错**。本轮我自己就先信了它。
                    _B_eff = max(int(_Bt), 1)
                    _kpb = int(np.ceil(n_ath_tgt / _B_eff))
                    T_hist.append(dict(step=it, t=float(g.t), T=_Tnow,
                                       df=float(g.df[1]), field=int(_ev[0][0]),
                                       n_target=int(_tgt), k=int(n_ath_tgt),
                                       k_in_block=int(_kpb),
                                       mode=str(_ev[0][1])))
                    P('   ★★ **athermal 形核** @ step %d：T=%.1f K'
                      '（T_%d 理论=%.1f K；块内第 %d 根 / 共 %d 块）'
                      '，df=%.4e，场 %d（累计 %d/%d；模式 **%s**；累计 fresh=%d stack=%d）'
                      % (it, _Tnow, _kpb, CL.T_of_k(_kpb, _alpha), _kpb, _B_eff,
                         float(g.df[1]), _ev[0][0], n_ath_tgt, _n_law,
                         _ev[0][1], n_mode.get('fresh', 0), n_mode.get('stack', 0)))
                else:
                    P('   ⚠ athermal 事件 #%d 被引擎拒（无可用空场/落位失败）@ step %d'
                      % (n_ath_tgt, it))
        # ★★★ R49（**口径修复：`--snap-every` 原先藏在 `--every` 门后面**）
        #   原写法把**整块 CSV + 快照**都放在 `if (it % a.every) ... continue` 之后
        #   ⇒ 快照的**实际**间隔 = `lcm(every, snap_every)`，而不是 `snap_every`。
        #   实测命中（`_r49_cadence.py` 逐臂扫过）：
        #     `--every 40 --snap-every 250` 的臂只拿到 **1000 步**的间隔
        #     ⇒ `dry_mb1L` / `dry_mb1Ls` / `dry_mb1s62` 三条都中招。
        #   ⚠ 为什么这条是 P 级而不是"参数没生效"的小事：**快照是"事后重测"的
        #     唯一载体**（用户要求"全过程数据留 F 盘，量具有 bug 也能重测"）。
        #     间隔被悄悄放大 4× ⇒ 长大速率的**时间基线**比设计值粗 4 倍，
        #     而 0→首快照这一段的初始瞬态无法与稳态段分开。
        #   修法：给快照**单开一条路径**。⚠ 当 `_every_now` 与 `_snap_now` **同时**
        #   命中时，仍走**原来的**代码顺序（快照留在 CSV 块内、`P0` 已更新）
        #   ⇒ **归档快照逐位不变**（由 `_r30_regress.sh` 验收）。
        _every_now = (it % a.every == 0) or (it == a.steps)
        _snap_now = (it % a.snap_every == 0) or (it == a.steps)
        if _snap_now and not _every_now:
            # 独立快照：只需 `region`（+ 带内 φ / ψ），**不需要** `measure_state`
            # （那套逐分量连通标注是 CSV 行的成本，快照不该付）。
            _reg_s = g.region()
            _ds = dict(region=_reg_s, step=it, t_s=float(t_sim),
                       n_hab=n_hab, w_ax=w_ax, a_ax=a_ax,
                       N=N, L=L, arm=a.arm,
                       vmap_keys=np.array(sorted(vmap)),
                       vmap_vals=np.array([vmap[k] for k in sorted(vmap)]),
                       f3_pos_p0_m=(float(P0) if P0 is not None else np.nan))
            if getattr(a, 'phi_band_every', 0) >= 0 and (
                    a.phi_band_every == 0 or it % a.phi_band_every == 0
                    or it == a.steps):
                _ds.update(_sparse_band(g.phi, dx, int(a.phi_band_cells)))
            if getattr(g, 'psi', None) is not None:
                _ds['psi'] = np.asarray(g.psi, np.float32)
            if a.phi_every > 0 and (it % a.phi_every == 0 or it == a.steps):
                _ds['phi'] = g.phi.astype(np.float32)
            np.savez_compressed(os.path.join(outdir, 'snap_%05d.npz' % it), **_ds)
            P('  [snap %4d] 独立快照落盘（本步不含 CSV 行）' % it)
            continue
        if not _every_now:
            continue
        reg = g.region()
        mm = BM.measure_state(reg, dx, n_hab, w_ax, a_ax, vmap)
        # ψ 的带（只在 F3 胞上；`g.psi is None` 时不算）
        if g.psi is not None:
            karr_m, larr_m = g.par.argmin2(g.phi)
            karr_m = karr_m.astype(np.intp); larr_m = larr_m.astype(np.intp)
        else:
            karr_m = larr_m = None
        pm = mm['f3_pos_n']
        if P0 is None and np.isfinite(pm):
            P0 = pm
        nc = [mm['ncomp_%d' % k] for k in range(1, nv + 1)]
        ncb = [mm['ncompbig_%d' % k] for k in range(1, nv + 1)]
        # ★★ Round 10 修：中位数**必须只统计非空场**。
        #   原写法对**所有** `k=1..nv` 取中位数，而生长臂早期大部分场是空的
        #   （`n_k = 0`）⇒ 中位数被 0 绑架。实测 `dry_gs3` 在 step 0–50 打出
        #   `n/w/a=0/0/0 nm`（那时明明有 1–2 根 250/619/2400 nm 的板条），
        #   到 step 60 又跳成 124 —— 全是空场把中位数拉到 0 的假象。
        #   ⇒ 只对 `vol_k > 0` 的场取中位数；全空则给 0（`vols` 列可辨）。
        _occ = [k for k in range(1, nv + 1) if mm['vol_%d' % k] > 0]
        _med = (lambda f: float(np.median([f(k) for k in _occ])) if _occ else 0.0)

        # ★ R18：逐对 F3 面积（只在命中 `--pair-every` 时算）
        _pair_now = bool(a.pair_every > 0 and it % a.pair_every == 0)

        def _pair_str(reg_, mm_):
            out_ = []
            for _ii, _i in enumerate(_occ):
                for _j in _occ[_ii + 1:]:
                    if vmap[_i] != vmap[_j]:
                        continue
                    _A = BM._area_from_faces(
                        BM._faces_between(reg_ == _i, reg_ == _j), n_hab, dx)
                    if _A > 0:
                        out_.append('%d-%d:%.6g' % (_i, _j, _A * 1e12))
            return '/'.join(out_)

        def _pairpos_str(reg_):
            """★★★ R29（Round 18）：**逐对界面位置**（沿 `n*`，单位 **Δx**）。

            为什么必须有这一列（而不是继续用汇总的 `f3_pos_dx`）：
              `f3_pos_dx` 是**所有 F3 胞**在 `n*` 上的平均位置 —— 一个**汇总量**。
              块里有 k 张界面时，它的漂移有两个来源：
                (a) 某张界面真的在迁移；
                (b) **各张界面之间的权重变了**（某一对面积涨、另一对掉）。
              ⇒ `V-3g`（用它下判）在"各对面积悬殊且在变"时会给出**假 FAIL**。
              实测（`dry_cl1b`）：逐对面积 `5.29/5.34 → 3.81/3.36`（权重变 ~30%），
              而**逐对粗糙度没变**（0.071 × 板条厚，见 `_bk_f3flat.py`）；
              归档 `eng12` 的各对面积齐平（1.50–1.60，±3%）⇒ 它的 `V-3g` 才稳。
              ⇒ 要判"界面有没有迁移"，必须**逐对**看。
            ⚠ **本列只做数据落盘**：对应的"逐对 V-3g"判据**尚未实现、尚未验证**
              （本轮已在同一问题上错三次 ⇒ **不再交付未验证的判据**）。
            ⚠ 只在 `--pair-every` 命中时算（默认 0 ⇒ 不算、列是空串 ⇒ 归档逐位不变）。
            """
            out_ = []
            for _ii, _i in enumerate(_occ):
                for _j in _occ[_ii + 1:]:
                    if vmap[_i] != vmap[_j]:
                        continue
                    _mi = (reg_ == _i)
                    _mj = (reg_ == _j)
                    _adj = np.zeros_like(_mi)
                    for _ax in (0, 1, 2):
                        for _sh in (1, -1):
                            _adj |= _mi & np.roll(_mj, _sh, axis=_ax)
                    if not bool(_adj.any()):
                        continue
                    _idx = np.argwhere(_adj).astype(float) + 0.5
                    _p = float((_idx.mean(0) @ n_hab) * dx / dx)      # 单位 Δx
                    out_.append('%d-%d:%.5g' % (_i, _j, _p))
            return '/'.join(out_)

        row = dict(
            step=it, t_s=round(t_sim, 12), wall_s=round(time.time() - wall0, 2),
            dt=dt, V0=mm['vol_0'], Vt=sum(mm['vol_%d' % k] for k in range(1, nv + 1)),
            M=M, nreg_used=mm['nreg_used'], nslab_n=mm['nslab_n'],
            nf3_col=mm['nf3_col'], runs=mm['runs'].replace(',', '/'),
            ncomp_min=int(np.min(nc)), ncomp_max=int(np.max(nc)),
            # ★ 显著分量数（≥32 体素）：`ncomp_max` 会把 1–2 体素的离散孤儿算成
            #   "碎裂"（`dry_gs2` 实测 ncomp_max=4，实际是 1 根完整板条 + 3 个孤儿）。
            #   两个口径**都存**，判决用新的、原始值留档，任何人都能自己重判。
            ncompbig_max=int(np.max(ncb)),
            vols='/'.join('%.6g' % (mm['vol_%d' % k] * 1e18)
                          for k in range(1, nv + 1)),
            ths='/'.join('%.6g' % (mm['n_%d' % k] * 1e9)
                         for k in range(1, nv + 1)),
            # ★ R18：逐对 F3 面积。只在 `--pair-every` 命中时算（它要按对做
            #   6 次 `np.roll`，N=96 时约 2–3 s ⇒ 不能每步都算）。
            f3_pairs=('' if not _pair_now else _pair_str(reg, mm)),
            f3_pairs_pos=('' if not _pair_now else _pairpos_str(reg)),
            nf3=mm['f3_faces'], f3_area_m2=mm['f3_area'],
            # ★★ R31：**F2 面（异变体界面）** —— "块与块相遇"的签名（原来没有量具）
            nf2=mm['f2_faces'], f2_area_m2=mm['f2_area'],
            # ★★★★★ R218（`§137.7`）：**F1 聚合面积**（含母相）⇒ 三类占比可算
            nf1=mm['f1_faces'], f1_area_m2=mm['f1_area'],
            f1_area_stair=mm['f1_area_stair'],
            f3_area_stair=mm['f3_area_stair'], f3_pos_m=pm,
            f3_pos_dx=((pm - P0) / dx if (np.isfinite(pm) and P0 is not None)
                       else float('nan')),
            f3_std_m=mm['f3_std_n'],
            # ★★ Round 10 修：中位数**必须只统计非空场**（见上面 `_occ` 的记账）。
            n_lath=_med(lambda k: mm['n_%d' % k]),
            w_lath=_med(lambda k: mm['w_%d' % k]),
            a_lath=_med(lambda k: mm['a_%d' % k]),
            box_touch=int(mm['box_touch']),
            # ★★★ R38（**P1-22**）：**孤儿免疫**的撞壁判据 + 核心/分量记账。
            #   旧 `box_touch` 判"任一已转变胞落在盒面" ⇒ 一个 1 胞孤儿就置 1；
            #   实测 MB-1 的 mb1 报了 27 行，而核心 a 跨度只有 2654 nm（盒 12 µm）。
            box_touch_core=int(mm.get('box_touch_core', 0)),
            core_vox=mm.get('core_vox', -1), ncomp_all=mm.get('ncomp_all', -1),
            # ★★★ R41（**P1-25** 的决定性诊断）：`dG_max` 是不是被极少数异常胞绑架？
            #   `dG_max/p99.9 ≫ 1` 或 `dG_near_max` 极小 ⇒ 最大值是**离群点**
            #   ⇒ `dt`（按 `dG_max` 定）被整体压低 ⇒ **全场都慢，含物理时间轴**。
            dG_max_Jm3=getattr(g, 'dG_max', float('nan')),
            dG_p999=getattr(g, 'dG_p999', float('nan')),
            dG_ratio=(getattr(g, 'dG_max', float('nan'))
                      / max(getattr(g, 'dG_p999', float('nan')), 1e-300)),
            dG_near_max=getattr(g, 'dG_nmax', -1),
            # ★★★ R45（P1-25 直测）：按界面法向分档的 `ed` / `dG` 中位数
            #   （把 "弹性偏袒侧面、压制尖端" 从**反解**升级为**直测**）
            ed_tip=_ebf(g, 'tip', 0), ed_side=_ebf(g, 'side', 0),
            ed_wide=_ebf(g, 'wide', 0),
            dG_tip=_ebf(g, 'tip', 1), dG_side=_ebf(g, 'side', 1),
            dG_wide=_ebf(g, 'wide', 1),
            # ★★★ R49（R48 遗留的受控检验）：**同一算例上**同时落盘 tip/side 的
            #   `dG` 的 **p90 / max** —— 用来判"面运动到底被哪个统计量驱动"。
            #   动机：R48 发现朴素预言差 68×，其中 12× 是"用了 `ΔG_max` 而不是
            #   面上的 `dG`"造成的口径差；而 R46b 又实测**中位数不预测面运动**。
            #   两者合起来说明：**统计量没定对**，此前任何"差 N 倍"的说法都悬空。
            dG_tip_p90=_ebf(g, 'tip', 4), dG_side_p90=_ebf(g, 'side', 4),
            dG_tip_max=_ebf(g, 'tip', 5), dG_side_max=_ebf(g, 'side', 5),
            ed_tip_p90=_ebf(g, 'tip', 3), ed_side_p90=_ebf(g, 'side', 3),
            # ★★★ R49：**直接可比的速率预言**（`<M(n)·dG>_面 · dt`，nm/步）。
            #   `*_nabs` 用 `|v|` 平均（粗糙面的**面位置**推进看这个）；
            #   `*_nsgn` 用带符号平均（看净方向）。
            v_tip_nsgn=_vbf(g, 'tip', 0, dt), v_tip_nabs=_vbf(g, 'tip', 1, dt),
            v_side_nsgn=_vbf(g, 'side', 0, dt), v_side_nabs=_vbf(g, 'side', 1, dt),
            v_wide_nabs=_vbf(g, 'wide', 1, dt), v_obl_nabs=_vbf(g, 'oblique', 1, dt),
            # ★★★ R49：**F1（变体-母相）only** 的面速度 + F1 占比守卫。
            #   3 根同类板条堆叠 ⇒ 板条间是 F3（驱动逐位为 0）⇒ 混在一起会低估。
            v_tip_f1=_vbf_f1(g, 'tip', dt), v_side_f1=_vbf_f1(g, 'side', dt),
            v_wide_f1=_vbf_f1(g, 'wide', dt),
            f1_tip=_vbf_f1frac(g, 'tip'), f1_side=_vbf_f1frac(g, 'side'),
            f1_wide=_vbf_f1frac(g, 'wide'),
            # 面分类的**胞数**（守卫：档位退化时必须能从 CSV 看出来，不能静默为空）
            n_tip=((getattr(g, 'ed_by_face', None) or {}).get('tip') or (0, 0, 0))[2],
            n_side=((getattr(g, 'ed_by_face', None) or {}).get('side') or (0, 0, 0))[2],
            n_wide=((getattr(g, 'ed_by_face', None) or {}).get('wide') or (0, 0, 0))[2],
            # ★ R45b：第四档（斜法向）—— H-ε 的判据量
            ed_obl=_ebf(g, 'oblique', 0), dG_obl=_ebf(g, 'oblique', 1),
            n_obl=(getattr(g, 'ed_by_face', None) or {}).get(
                'oblique', (0, 0, 0))[2]
            if (getattr(g, 'ed_by_face', None) or {}).get('oblique') else '',
            finite=int(np.all(np.isfinite(g.phi))),
            psi_mean=(float(g.psi[np.isfinite(
                lt.gtab[np.clip(karr_m, 0, g.nreg - 1),
                        np.clip(larr_m, 0, g.nreg - 1)])].mean())
                if (g.psi is not None) else float('nan')),
            # ★ R29：CFL 实际用量（胞/步）。`advance` 每步把总驱动的最大值写在
            #   `g.dG_max`（第 0 步还没 advance ⇒ 没有该属性 ⇒ 记 nan，不假装是 0）。
            cfl_used=(float(dt) * MOB * float(getattr(g, 'dG_max', float('nan')))
                      / dx),
            # ★ R31（J-3）：**全局弹性能**落盘。`BLOCK_SELFAC.md §7.1 P-SA-1` 的判据
            #   （`ed` 臂 vs `random` 臂的末态 `E_el`）需要它，而此前**从未落盘**
            #   （S5 的 G-8）。`g.pf` 是 FFT 谱法弹性求解器 ⇒ `E_el()` 是一次求和，便宜。
            E_el_J=(float(g.pf.E_el()) if getattr(g, 'pf', None) is not None
                    else float('nan')),
            # ★ R31（J-1）：**块表**（块数 / 每块板条根数 / 变体分数 / 实测自协调残差 /
            #   实测惯习面数）。⚠ `blocks()` 要对每个变体做一次 3D 连通标注
            #   （scipy.ndimage.label），N=96 时约 0.1 s/变体 ⇒ 只在 `--pair-every`
            #   命中时算（与逐对 F3 面积同一个节流阀）。
            **(_blk_cols(g, reg, dx, vmap) if _pair_now else _BLK_EMPTY),
            # ★★★ R47：**三个面族的面间距**（「长大速率」的金标准口径）
            **(_facesep_cols(g, dx, vmap) if _pair_now
               else dict(tip_sep_nm='', side_sep_nm='', wide_sep_nm='')),
            # ★ R30（P0-1）：柱剖面的修正口径 + 可见性守卫
            nslab_n1=mm['nslab_n1'], runs1=mm['runs1'].replace(',', '/'),
        # ★★★ R50（P1-29）：**去重场数**（柱里真正穿过几根板条）+ 多读比
        nslab_nu=_nslab_dedup(mm['runs']),
        nslab_nu1=_nslab_dedup(mm['runs1']),
            nf3_col1=mm['nf3_col1'], r_col_nm=round(mm['r_col_nm'], 1),
            col_cover_min=round(mm['col_cover_min'], 4))
        # ★ 防御：`cw.writerow([row[c] for c in COLS])` 里少一个键就是 KeyError，
        #   而它出现在**第 0 步写第一行**时 —— 那时构造已经花掉 60 s，
        #   且发生在长跑开头而不是起跑前。这里提前硬失败，把话说明白。
        _miss = [c for c in COLS if c not in row]
        if _miss:
            raise KeyError('series.csv 的 COLS 与 row 不一致，row 里缺: %s' % _miss)
        cw.writerow([row[c] for c in COLS]); csvf.flush()
        if (it % a.snap_every == 0) or (it == a.steps):
            # ★★ 落盘策略（用户要求"全过程数据留 F 盘，量具有 bug 也能事后重测"）：
            #   · **`region`（int16，R474 起；原 int8）每个快照都存** —— 这是 `_bk_measure.measure_state`
            #     的**唯一输入**（体积/分量/nslab/nf3col/三轴尺寸/面积/位置全都只吃它）
            #     ⇒ **只靠 region 的那些量可完全事后重测**（S5 已端到端实测：0 处不一致）。
            #   · **带内稀疏 `φ`（R30 新增）默认每个快照都存** ⇒ 界面剖面/法向/κ/
            #     亚胞厚度也能事后重测。⚠ 记账：**只存 `|φ| ≤ band·Δx` 的胞**。
            #   · **整场 `phi`（+164.7 MB/快照、+10.5 s @N=192）** 仍由 `--phi-every`
            #     单独控制；语义是 **`>0` 才存**（`0` = **从不**）—— R30 修正了
            #     原来与代码相反的 help 文字。
            d = dict(region=reg, step=it, t_s=float(t_sim),
                     n_hab=n_hab, w_ax=w_ax, a_ax=a_ax,
                     N=N, L=L, arm=a.arm,
                     vmap_keys=np.array(sorted(vmap)),
                     vmap_vals=np.array([vmap[k] for k in sorted(vmap)]),
                     # ★ R30：`Δpos` 的基准必须落盘 —— 否则 `f3_pos_dx` 无法离线复算
                     #   （它是在**中间某一步**被钉下的，而那一步常常没有快照；
                     #    S5 实测第一版重算差 1.31 Δx 就是这个原因）。代价 ≈ 0。
                     f3_pos_p0_m=(float(P0) if P0 is not None else np.nan))
            if getattr(a, 'phi_band_every', 0) >= 0 and (
                    a.phi_band_every == 0 or it % a.phi_band_every == 0
                    or it == a.steps):
                d.update(_sparse_band(g.phi, dx, int(a.phi_band_cells)))
            if getattr(g, 'psi', None) is not None:
                d['psi'] = np.asarray(g.psi, np.float32)
            if a.phi_every > 0 and (it % a.phi_every == 0 or it == a.steps):
                d['phi'] = g.phi.astype(np.float32)
            np.savez_compressed(os.path.join(outdir, 'snap_%05d.npz' % it), **d)
        # ══════════════════════════════════════════════════════════════════════
        # ★★★★★ R581-ckpt（goal「原生精度断点续跑」）：**可续跑检查点**
        #
        #   ⚠ **默认关**（`--ckpt-every 0`）⇒ 下面**一个字节都不执行**
        #     ⇒ `snap_*.npz` 与 `series.csv` 逐位不变（**门 4**）。
        #
        #   ## 为什么放在这里
        #   它在"本步的 `advance` 已完成 + 观测量已落盘"之后 ⇒
        #   检查点里的状态 = **下一步开始时**的状态 ⇒ 恢复时从 `it + 1` 续跑即可。
        #
        #   ## 与快照的关系（**两套东西，各有用途**）
        #   * 快照（`snap_*.npz`，1–3 MB）：**事后分析**用（`region` + 带内 φ）；
        #   * 检查点（`ckpt/`，26–39 MB@N=160）：**续跑**用（完整 φ + 全部状态）。
        #   ⚠ 检查点**不替代**快照；两者并存。
        # ══════════════════════════════════════════════════════════════════════
        if int(getattr(a, 'ckpt_every', 0) or 0) > 0:
            _ck = int(a.ckpt_every)
            _ckms = int(getattr(a, 'ckpt_milestone_every', 0) or 0)
            _is_ms = bool(_ckms > 0 and it > 0 and it % _ckms == 0)
            if (it % _ck == 0) or (it == a.steps) or _is_ms:
                _cdir = (a.ckpt_dir or os.path.join(outdir, 'ckpt'))
                try:
                    _st = _ckpt_gather(
                        g, it, t_sim,
                        dict(_qs_T=_qs_T, _qs_stage=_qs_stage, _qs_dt=_qs_dt,
                             _qs_stop=_qs_stop, _qs_conv=_qs_conv, _qs_ref=_qs_ref,
                             _qs_relax=_qs_relax, _qs_V=_qs_V,
                             _qs_dV=list(_qs_dV), _qs_rel_last=_qs_rel_last,
                             _qs_shrink_n=_qs_shrink_n, _qs_shrink_v=_qs_shrink_v,
                             _qs_shrink_used=_qs_shrink_used,
                             _qs_win=_qs_win, _qs_tol=_qs_tol,
                             n_ath_ev=n_ath_ev, n_ath_tgt=n_ath_tgt,
                             n_eng_ev=n_eng_ev, n_fresh_fallback=n_fresh_fallback,
                             n_mode=dict(n_mode)),
                        N, L, nv, int(getattr(g, 'nreg', nv + 1)), vmap, tstep=tstep)
                    _cp = _ckpt_write(_cdir, _st, keep=int(a.ckpt_keep),
                                      atomic=bool(int(a.ckpt_atomic)),
                                      milestone=_is_ms)
                    if it % max(_ck, 1) == 0 or _is_ms:
                        P('  [ckpt %4d]%s 检查点落盘 %s（%.1f MB）'
                          % (it, ' **里程碑**' if _is_ms else '',
                             os.path.basename(_cp), os.path.getsize(_cp) / 1048576.0))
                except Exception as _ce:
                    # ★ 检查点失败**绝不影响仿真**（与 `nuc_dbg.json` 的 N12 教训同源：
                    #   一份辅助产物不该毁掉整轮）
                    P('  ⚠ [ckpt %4d] 检查点落盘失败（**不影响仿真**）：%s' % (it, _ce))
        P('  [%4d] Vt=%.4f µm³ | **nslab=%d** nf3col=%d runs=%-13s | F3面=%-6d '
          '面积=%.4f µm² | Δpos=%+7.3f dx std=%5.1f nm | nc=%d..%d(显著%d) | '
          '厚度(在位的场) %s nm | 壁=%d | %.2fs/步'
          % (it, row['Vt'] * 1e18, mm['nslab_n'], mm['nf3_col'], row['runs'],
             mm['f3_faces'], mm['f3_area'] * 1e12,
             (row['f3_pos_dx'] if np.isfinite(row['f3_pos_dx']) else float('nan')),
             (mm['f3_std_n'] * 1e9 if np.isfinite(mm['f3_std_n']) else float('nan')),
             row['ncomp_min'], row['ncomp_max'], row['ncompbig_max'],
             ' '.join('%d:%.0f' % (k, mm['n_%d' % k] * 1e9)
                      for k in range(1, nv + 1) if mm['vol_%d' % k] > 0)
             or '（无）',
             row['box_touch'],
             (np.mean(tstep[-a.every:]) if tstep else 0.0)))
    csvf.close()

    # ★★★ R15：把**形核通道的诊断计数落盘**。原先 `g._nuc['dbg']` 只在内存里，
    #   于是"`nfsv` 到底有没有因为没空场而拒绝事件"这类判据（本轮预登记的 G-5）
    #   **无法从落盘数据复核** —— 而用户的要求正是"全过程数据留盘、量具/判据
    #   有 bug 也能事后重测"。⇒ 写成 `nuc_dbg.json`（只在 `arm=eng` 时）。
    if use_engine and getattr(g, '_nuc', None) is not None:
        # ★★★★★ 2026-10-04（**N12：诊断落盘的"一个键毁掉整份文件"**）
        #   ## 实测（`_r535_diagrun.sh`，`--nfsv-diag 1`）
        #     日志原话：
        #       `⚠ nuc_dbg.json 落盘失败（不影响仿真结果）:
        #         int() argument must be a string, a bytes-like object or a real number, not 'list'`
        #     而落盘结果是 **`nuc_dbg.json` = 0 字节**（`closure.json` 13 KB、
        #     `series.csv` 49 KB 都正常）⇒ **整份形核诊断全丢**。
        #   ## 根因
        #     原写法 `dbg={k: int(v) for k, v in ...}` **对每个值无条件 `int()`**
        #     —— 那是为了把 `np.int64` 之类转成 JSON 可序列化的原生类型。
        #     但**只要有一个键不是标量**（我新加的 `nfsv_diag_occ_sizes` 是 `list`）
        #     就抛异常 ⇒ 被下面的 `except` 吞掉 ⇒ **写出一份 0 字节的文件**。
        #   ## 为什么这是**真缺陷**（不是"我加错了键"就完了）
        #     * 用户硬要求：「**全过程数据留盘，量具/判据有 bug 也能事后重测**」。
        #       一个**能被单个键毁掉**的诊断文件**违背这条**。
        #     * 与 `R30_AUDIT_LEDGER.md §R31` 记的**同一类**（当时是"嵌套 ndarray
        #       漏转 ⇒ 静默落盘失败"，已修过一次）⇒ **这次是"非标量/标量混用"再来一遍**。
        #     * 而且它在**跑完 601 步之后**才发生 ⇒ 白跑一整轮才发现没数据。
        #   ## 修法（**两条**，都要）
        #     ① **类型感知**地转（`list/tuple/dict/bool/int/float/ndarray/其他→str`）；
        #     ② **逐键降级**：某个键转不动时**只把那个键变成 `str`** 并**记进
        #        `dbg_coercion_notes`**，**绝不**让整份文件写不出来。
        #   ★ 转换器已提取到**模块级**（`_js_diag` / `_js_diag_key`）⇒ 可被
        #     `_r538_n12check.py` **用解析已知答案直接单测**，不必跑 601 步。
        #   ⚠ 本段只在 `use_engine` 且落盘诊断时执行 ⇒ **不碰任何数值路径**。
        _coerce_notes = []

        def _js_key(k, v):
            return _js_diag_key(k, v, _coerce_notes)

        try:
            with open(os.path.join(outdir, 'nuc_dbg.json'), 'w',
                      encoding='utf-8') as f:
                json.dump(dict(n_eng_ev=n_eng_ev,
                               nuc_law=a.nuc_law,
                               n_athermal_ev=n_ath_ev,
                               n_target_final=n_ath_tgt,
                               # ★ §189（缺陷③）：fresh/stack 交错的实际分配 + 退回次数。
                               #   `nuc_fresh_every = 0` ⇒ 未启用交错（归档行为）。
                               nuc_fresh_every=int(getattr(a, 'nuc_fresh_every', 0) or 0),
                               n_events_by_requested_mode=dict(n_mode),
                               n_fresh_fallback_to_stack=int(n_fresh_fallback),
                               T_events=T_hist,
                               n_events_by_mode={
                                   m: sum(1 for _k, mm in g._nuc_events if mm == m)
                                   for m in sorted(set(mm for _k, mm
                                                       in g._nuc_events))},
                               # ★ N12：类型感知 + 逐键降级（原为无条件 `int(v)`）
                               dbg={k: _js_key(k, v) for k, v in
                                    g._nuc.get('dbg', {}).items()},
                               # ★ N12：记下**哪些键被降级**（不静默）
                               dbg_coercion_notes=_coerce_notes,
                               nuc_cfg={k: _js_key(k, v) for k, v in g._nuc.items()
                                        if k not in ('rng', 'dbg')}),
                          f, ensure_ascii=False, indent=1,
                          # ★ R31：`_nuc['sites']` 是 `[(k, ndarray), …]`
                          #   ⇒ 原来的"只把顶层 ndarray 转 list"漏掉了**嵌套** ⇒
                          #   `nuc_dbg.json` **静默落盘失败**（被 try/except 吞掉）。
                          # ★ N12：`default` 只作**兜底**（`_js_key` 已覆盖绝大多数）
                          default=lambda o: (o.tolist() if isinstance(o, np.ndarray)
                                             else str(o)))
            P('★ 形核诊断已落盘: nuc_dbg.json（n_eng_ev=%d, dbg=%s）'
              % (n_eng_ev, g._nuc.get('dbg', {})))
            if _coerce_notes:
                P('   ⚠ N12：有 %d 个诊断键**降级成字符串**（其余字段完好）：%s'
                  % (len(_coerce_notes), '; '.join(_coerce_notes[:5])))
        except Exception as exc:
            # ★ N12：**不许静默**。原来只打一句普通告警，7000 行日志里根本看不见。
            P('❌❌❌ **`nuc_dbg.json` 落盘失败 ⇒ 本算例的形核诊断全丢**'
              '（仿真结果本身不受影响）：%s' % exc)
            P('   ⇒ 这是 N12 那一类（一个键毁掉整份文件）。'
              '**该文件是"事后重测"的唯一载体**（用户硬要求）⇒ **报出来，别吞**。')

    # ★★★ R29：把**这一次到底用了哪些闭环参数**整份落盘（`closure.json`）。
    #   用户的硬要求是"全过程数据留盘、量具/判据有 bug 也能事后重测"。
    #   `--nuc-law cadence`（默认）时只写 `nuc_law` 一个字段，**不改任何归档产物**。
    try:
        _rec = CL.recommend(N=N, t_lath_nm=float(a.plate_T),
                            aspect=float(a.plate_L) / float(a.plate_T),
                            alpha_KM=_alpha, T_f=_Tend, MOB=MOB, cfl=0.15,
                            ratio_target=float(a.cool_ratio))
        _cl = dict(nuc_law=a.nuc_law,
                   alpha_KM=_alpha,
                   Ms=float(M_S_TI64), T0=float(T0_TI64), DS=float(DS_REF),
                   dG_crit=float(DG_CRIT_REF),
                   T_start=_Tstart, T_end=_Tend,
                   T_start_kind=('T_1 = M_s − 1/α_KM（预摆片 = 第 1 根）'
                                 if float(a.T_start) <= 0 else 'user'),
                   q=(None if not _athermal else float(_q)),
                   q_source=_q_source,
                   q_cap=(None if not _athermal else float(_q_cap)),
                   n_law_float=CL.alpha_km_n_lath(_Tend, _alpha),
                   n_law=int(_n_law),
                   T_k=[float(CL.T_of_k(k, _alpha)) for k in range(1, max(_n_law, 1) + 1)],
                   steps_min_ordered=CL.steps_min_ordered(_alpha, _L_lath, dx, 0.15,
                                                          _Tend, _Tstart),
                   beta_h_floor=CL.beta_h_min(a.steps, dx, a.plate_T * 1e-9),
                   beta_h_T=CL.beta_h_of_T(0.5 * (float(M_S_TI64) + _Tend)),
                   beta_h_used=float(a.beta_h),
                   geometry=dict(N=N, dx_nm=dx * 1e9, L_box=dx * N,
                                 plate_L_nm=a.plate_L, plate_W_nm=a.plate_W,
                                 plate_T_nm=a.plate_T,
                                 plate_T_physical_nm=(a.plate_t_physical
                                                      if a.plate_t_physical > 0
                                                      else a.plate_T),
                                 t_over_dx=float(a.plate_T) * 1e-9 / dx),
                   params=CL.params())
        _cl['n_lath_derived'] = dict(L_lath_um=_rec.get('L_lath', 0) * 1e6,
                                     W_lath_um=_rec.get('W_lath', 0) * 1e6,
                                     dx_nm_rec=_rec.get('dx_nm'),
                                     q_rec=_rec.get('q'),
                                     steps_rec=_rec.get('steps'),
                                     beta_h_rec=_rec.get('beta_h_use'),
                                     n_geo_cap=_rec.get('n_geo_cap'),
                                     ordered_ratio=_rec.get('ordered_ratio'),
                                     ok=_rec.get('ok'))
        with open(os.path.join(outdir, 'closure.json'), 'w', encoding='utf-8') as f:
            json.dump(_cl, f, ensure_ascii=False, indent=1)
        P('★ 闭环参数已落盘: closure.json（nuc_law=%s, α_KM=%.4e, q=%s, n=%d）'
          % (a.nuc_law, _alpha,
             ('%.4e' % _q) if _athermal else 'n/a', _n_law))
    except Exception as exc:                                    # pragma: no cover
        P('⚠ closure.json 落盘失败（不影响仿真结果）: %s' % exc)

    # ★★★★★ R208（`R30_AUDIT_LEDGER.md` **§135.7**）：三项量级**逐步记录**落盘。
    #   为什么单独落盘：用户硬要求「全过程数据保存在 F 盘，之后能用新量具重测」。
    #   本节的数据支撑本轮最重要的三条结论 ⇒ **必须留原始记录**，不能只留在日志里。
    if diag_terms_rec:
        try:
            _p = os.path.join(outdir, 'diag_terms.json')
            with open(_p, 'w', encoding='utf-8') as f:
                json.dump(dict(
                    n_rec=len(diag_terms_rec),
                    note='速度律 dG=(df_k-df_l)+(ed_k-ed_l)-stk*kappa 的逐胞三项量级；'
                         '只在**界面胞**上统计；vv=变体-变体(k>0&l>0)，'
                         'vb=含母相(k>0&l==0)。med_ratio=|stk*kappa|/|ded| 的中位。',
                    rec=diag_terms_rec), f, ensure_ascii=False, indent=1)
            _last = diag_terms_rec[-1]
            _lv = _last.get('vv') or {}
            P('★★ **三项量级已落盘**: diag_terms.json（%d 条记录）' % len(diag_terms_rec))
            if 'med_ed' in _lv:
                # ⚠ 同样**不用 `or 0.0`**：这些数可能**恰好是 0**。
                _g = lambda k, d=float('nan'): (
                    float(_lv[k]) if isinstance(_lv.get(k), (int, float)) else d)
                P('   末条 @step %d：**F2 异变体** 胞数 %d；`|Δed|` 中位 **%.4e**，'
                  '`|stk·κ|` 中位 **%.4e** ⇒ **比值中位 %.4f%%**（99 分位 %.4f%%）'
                  % (_last['step'], int(_lv.get('n', 0)), _g('med_ed'),
                     _g('med_sk'), 100 * _g('med_ratio'), 100 * _g('p99_ratio')))
        except Exception as exc:                                # pragma: no cover
            P('⚠ diag_terms.json 落盘失败（不影响仿真结果）: %s' % exc)

    # ★★★★★ R238（`§135.6` / 条件③主线）：**逐变体 `ed` 分布**落盘。
    if diag_edv_rec:
        try:
            with open(os.path.join(outdir, 'diag_edv.json'), 'w',
                      encoding='utf-8') as f:
                json.dump(dict(
                    n_rec=len(diag_edv_rec),
                    note='逐变体 ed（弹性自项）：在每个变体"winner 是它"的胞上统计。'
                         'med_spread/std = 跨变体 ed 中位的极差/标准差；'
                         'vol_cv = 各变体体积的变异系数。'
                         '速度律 dG = 0(化学) + Δed − stk·κ ⇒ ed 是变体选择的主杠杆。',
                    rec=diag_edv_rec), f, ensure_ascii=False, indent=1)
            _le = diag_edv_rec[-1]
            P('★★ **逐变体 `ed` 已落盘**: diag_edv.json（%d 条记录）' % len(diag_edv_rec))
            if 'med_spread' in _le:
                P('   末条 @step %d：%d 个变体；`ed` 中位极差 **%.4e**、'
                  '标准差 **%.4e**；体积 CV = %.3f'
                  % (_le['step'], _le.get('n_field', 0), _le['med_spread'],
                     _le['med_std'], _le.get('vol_cv', float('nan'))))
        except Exception as exc:                                # pragma: no cover
            P('⚠ diag_edv.json 落盘失败（不影响仿真结果）: %s' % exc)

    s = read_series(os.path.join(outdir, 'series.csv'))
    P('-' * 104)
    P('判决 臂=%-5s  M=%d  nslab_n %d→%d（应 == M=%d）  nf3_col %d→%d  '
      'F3 面积 %.4f→%.4f µm²  Δpos %s dx  nc_max %d→%d（显著 %s）'
      % (a.arm, M, s['nslab_n'][0], s['nslab_n'][-1], M, s['nf3_col'][0],
         s['nf3_col'][-1], s['f3_area_m2'][0] * 1e12, s['f3_area_m2'][-1] * 1e12,
         ('%+.3f' % s['f3_pos_dx'][-1]) if np.isfinite(s['f3_pos_dx'][-1]) else 'NaN',
         s['ncomp_max'][0], s['ncomp_max'][-1],
         ('%d→%d' % (s['ncompbig_max'][0], s['ncompbig_max'][-1]))
         if 'ncompbig_max' in s else '本臂无此列（旧版跑的数据）'))
    if a.arm == 'gneg':
        P('  负对照判据：**nf3 必须恒为 0** ⇒ 实测 %d→%d  %s'
          % (s['nf3'][0], s['nf3'][-1],
             '✓' if (s['nf3'][0] == 0 and s['nf3'][-1] == 0) else '✗✗ 量具失效'))
    else:
        _blk_verdict(s, M, a, P)
    return nfail


def _ints(txt):
    """`'3/3'` -> `[3, 3]`（CSV 里的逐块列都是这种斜杠串）。"""
    return [int(float(t)) for t in str(txt or '').split('/') if t.strip()]


def _blk_verdict(s, M, a, P):
    """★★★ R76（**P1-34**）：**判决口径**必须随构型切换。

    为什么：`nslab_n` 是**单柱**剖面，柱心 = `allowed`（= vmap 里的**全部**场）的
    质心、柱轴 = `laths[0]` 的 n*。**多块构型下这两条都不成立**：
      * 两个块沿布局轴分开 ⇒ **并集质心落在两块之间的空隙里**
        （R75 实测：块心 y=1.75/4.25 µm ⇒ 柱心 y=3.0 µm）；
      * 块 1 是**镜面变体**，它的 n* 与块 0 不同 ⇒ 沿块 0 的 n* 投影必然弥散。
    ⇒ 多块下 `nslab_n` **结构性无效**，R75 的 `nslab_n 1→1 ✗` **不是物理失败**
      （离线重测 `_r76_remeasure.py`：逐块口径 31/31 快照全为 `3/3`）。

    多块主判据（**逐块、沿该块自己的 n***）：
      `blk_nprof == blk_laths`（块内每根板条都在该块的柱剖面里当过众数）
      **且** `nblk_sig == 期望块数`。
    `blk_nlath` 作**上界**（场只要有一个胞在分量里就计数 ⇒ 层并成一片也报满），
    `blk_nruns` 只作诊断（分箱众数抖动会**多读**，实测 `mb1s` 真值 3 → 5~6）。
    ⚠ `read_series()` 返回的是 **`{列: np.ndarray}`**（不是 list）
      ⇒ 第一版这里写 `s['blk_nprof'] and ...` 直接抛
      `ValueError: The truth value of an array with more than one element is
      ambiguous`（**`_r30_regress.sh` 抓到**；它只在**终态判决**处炸，
      CSV 已经写完 ⇒ 逐位比较仍然 PASS ⇒ **只有日志里那一行 Traceback 能看出来**）。
      ⇒ 一律走 `_last()`，**不**对数组做真值判断。
    ⚠ `P` **必须显式传参**：它原本是 `run()` 里的**局部 lambda**（`_bk_exp.py:407`），
      R76 第一版把这个判决块抽成模块级函数后 `P` 就成了未定义名
      （`NameError`，被上面那个 `ValueError` 挡在前面没露出来）——
      **同一个改动里两个错，回归脚本只报出了先到的那个**。
    """
    def _last(col):
        """取某列**末行**的值；列缺失/为空 ⇒ `None`。对 ndarray/list/标量都安全。"""
        v = s.get(col) if hasattr(s, 'get') else None
        if v is None:
            return None
        if isinstance(v, (str, bytes)):
            return v or None
        try:
            n = len(v)
        except TypeError:
            return v
        return None if n == 0 else v[-1]

    def _int_of(x, dflt=0):
        try:
            return int(float(x))
        except (TypeError, ValueError):
            return dflt

    nblk = _int_of(_last('nblk_sig'))
    _npr_last = _last('blk_nprof')
    have_new = (_npr_last is not None and str(_npr_last).strip() != '')
    if nblk >= 2 and have_new:
        tgt = _ints(_last('blk_laths'))
        npr = _ints(_npr_last)
        nrn = _ints(_last('blk_nruns'))
        nlt = _ints(_last('blk_nlath'))
        ok_n = (len(npr) == len(tgt) and len(tgt) > 0
                and all(x == y for x, y in zip(npr, tgt)))
        ok_nn = (len(nrn) == len(npr) and all(x == y for x, y in zip(nrn, npr)))
        P('  ⚠ **多块构型（nblk_sig=%d）** ⇒ 全局 `nslab_n` **结构性无效**'
          '（柱心 = 并集质心，落在两块之间的空隙里；柱轴只用 `laths[0]` 的 n*）'
          ' —— **不作判据**（`_r76_remeasure.py` 有离线复核）。' % nblk)
        P('  主判据（**逐块、沿该块自己的 n***）：'
          '`blk_nprof == blk_laths`（每块内每根板条都在该块的柱剖面里当过众数）'
          ' **且** `blk_nruns == blk_nprof`（剖面无噪声）')
        P('     每块板条数(定义) blk_laths = %s' % tgt)
        P('     逐块柱剖面**不同场数** blk_nprof = %s   ← **主口径**' % npr)
        P('     逐块柱剖面**段数**     blk_nruns = %s   （诊断；抖动会多读）%s'
          % (nrn, '' if ok_nn else ' ⚠ **与 nprof 不等 ⇒ 剖面有噪声**'))
        P('     该块分量覆盖的场数     blk_nlath = %s   （**上界**，会退化）' % nlt)
        P('     ⇒ **%s**' % ('✓ 每块内板条全部可分辨且剖面无噪声'
                            if (ok_n and ok_nn) else
                            ('⚠ 板条可分辨但剖面有噪声（只按主口径通过）'
                             if ok_n else '✗ 有块内的板条在柱剖面里看不见')))
        return
    if a.multi_block and not have_new:
        P('  ⚠ 本算例的 `series.csv` **没有** `blk_nprof` 列（早于 R76 接线，**P1-33**）'
          ' ⇒ 逐块判据**无法**在本文件上做；请用 `_r76_remeasure.py` 从快照离线重测。')
        # ★ 关键：**不要**在这种情况下接着打原来的单柱判据 ——
        #   多块下它是**无效**的，打出来只会像 R75 那样把"通过"读成"失败"。
        P('  ⇒ **本文件不给判据**（避免用无效口径误判）。')
        return
    _ns, _n3 = _last('nslab_n'), _last('nf3_col')
    P('  主判据：**nslab_n == M** 且 **nf3_col == M-1**（低角晶界把每根都分开）'
      ' ⇒ %s' % ('✓' if (_int_of(_ns, -1) == M and _int_of(_n3, -2) == M - 1)
                 else '✗ 见逐步读数'))


def subprocess_out(cmd):
    import subprocess
    try:
        return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    except Exception:
        return ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', default='dry',
                    choices=['dry', 'wet', 'gpos', 'gneg', 'g0', 'auto', 'eng'])
    ap.add_argument('--N', type=int, default=96)
    ap.add_argument('--dx-nm', type=float, default=62.5)
    ap.add_argument('--steps', type=int, default=400)
    ap.add_argument('--every', type=int, default=10)
    ap.add_argument('--snap-every', type=int, default=100)
    ap.add_argument('--phi-every', type=int, default=0,
                    help='存**整场** phi 的间隔；**必须 >0 才存**（0 = 从不存）。'
                         '⚠ R30 修正：原文案写"0 = 与 snap-every 相同"，与代码'
                         '（`>0` 才存）相反，导致 297 个归档快照里 phi 出现 0 次'
                         '（`R30_AUDIT_LEDGER` P0-4）。整场 φ 在 N=192/7 场是'
                         '+164.7 MB/快照、+10.5 s/次；一般**不需要**它，'
                         '用下面的 `--phi-band-every` 就够。')
    ap.add_argument('--phi-band-every', type=int, default=0,
                    help='存**带内稀疏** phi 的间隔；**0 = 每个快照都存**（默认，'
                         '代价 ~1 MB/快照）；-1 = 关闭。'
                         '带内稀疏 φ 是"新量具事后重测界面几何/曲率"的唯一来源。')
    ap.add_argument('--phi-band-cells', type=int, default=6,
                    help='带内稀疏 φ 的判定带：存 |phi| <= 本值·dx 的胞（默认 6）')
    # ══════════════════════════════════════════════════════════════════════
    # ★★★★★ R581-ckpt（goal「原生精度断点续跑」）—— **五个开关，全部默认关**
    #   门 4：**不传任何 `--ckpt-*`** 时，`snap_*.npz` 与 `series.csv` 逐位不变。
    # ══════════════════════════════════════════════════════════════════════
    ap.add_argument('--ckpt-every', type=int, default=0,
                    help='**[默认 0 = 关]** 每 K 步写一个**可续跑检查点**'
                         '（`<outdir>/ckpt/`）。'
                         '★ 检查点含**完整 φ（f64）**+ RNG 状态 + `_nuc` 整字典 + '
                         '引擎节拍 + 驱动层准静态钟状态 ⇒ 可**原生精度续跑**。'
                         '⚠ 成本实测：N=160 跑到 600 步时约 **26–39 MB/帧**'
                         '（活跃场 6–9；见 `R581_RESUME_DESIGN.md` §4\'）。'
                         '不传它 ⇒ 一行检查点代码都不会执行 ⇒ 归档逐位不变。')
    ap.add_argument('--ckpt-keep', type=int, default=2,
                    help='**滑动窗口**保留的帧数（默认 **2**）。'
                         '★ `2` ⇒ **A/B 交替**（`ckpt_A.npz`/`ckpt_B.npz`）'
                         '⇒ **磁盘恒定、且完全不需要删除**（goal 推荐做法）；'
                         '`>2` ⇒ 步号命名 + 多余帧滚进 `_superseded/`'
                         '（**滚动名 `os.replace` 覆盖，不用 `rm`**）；'
                         '`1` ⇒ 单文件（**没有退路**，不推荐）。')
    ap.add_argument('--ckpt-atomic', type=int, default=1, choices=(0, 1),
                    help='**[默认 1 = 开]** 先写 `<name>.tmp` 再 `os.replace()` 原子改名'
                         '⇒ 被 kill 时**任何时刻都有一帧是完整的**。'
                         '⚠ 关掉它就没有这个保证（只用于做**负对照**）。')
    ap.add_argument('--ckpt-milestone-every', type=int, default=0,
                    help='[默认 0 = 关] 每 M 步另存一个**里程碑**'
                         '（`ckptms_%06d.npz`，**不参与滑动窗口**）'
                         '⇒ 给"想往回退一大截"留一条路。')
    ap.add_argument('--ckpt-dir', default='',
                    help='检查点目录（默认 `<outdir>/ckpt`）。')
    ap.add_argument('--laths', default='1,1,1,1,1,1')
    # ★★★ R31（目标第 (2) 项 J-4）：**多块播种**。
    #   `--laths 3,3` ⇒ 2 块（变体 1 的 3 根 + 变体 2 的 3 根）。
    #   块内沿**该变体自己的** n* 堆叠；块心沿**块 0 的长轴 a** 排开 `--block-gap-nm`。
    #   ⚠ 不传 `--multi-block` ⇒ 归档路径**逐位不变**（原来的"沿同一个 n* 堆叠"）。
    ap.add_argument('--multi-block', action='store_true',
                    help='按 laths 里**连续的同一个变体**分块；每块用该变体自己的 '
                         'n*/a/w 播种，块心沿块 0 的长轴排开 --block-gap-nm')
    ap.add_argument('--block-gap-nm', type=float, default=2000.0,
                    help='多块播种时**块心间距**（nm）；<=0 ⇒ 用默认 2000 nm')
    # ★★★★★ 2026-10-01（`R30_AUDIT_LEDGER.md` §189，**缺陷②**）：块心**布局**。
    #   `line`（**归档默认**）⇒ 全部块心排在同一个布局轴 `_u` 上 ⇒ 实测 6 块
    #     第一主成分方差占比 **0.9998**、到最佳拟合直线垂距 ≤0.05 µm、
    #     邻居数 `[1,2,2,2,2,1]` ⇒ **一维链**，是人为规定而非涌现。
    #   `random` ⇒ 块心在**周期盒**内均匀随机（引擎是周期边界，没有实体盒壁），
    #     带最小间距拒绝采样；用 `--block-seed` 保证可复现。
    #   ⚠ 只新增分支 ⇒ `line` 路径**逐字未动** ⇒ 归档逐位不变。
    ap.add_argument('--block-layout', choices=['line', 'random'], default='line',
                    help='多块布置：line=排成一条直线（归档默认）；random=盒内随机位点')
    ap.add_argument('--block-seed', type=int, default=20261001,
                    help='`--block-layout random` 的 RNG 种子（可复现）')
    ap.add_argument('--block-min-dist-nm', type=float, default=0.0,
                    help='随机布局的**最小块心距**（nm）；<=0 ⇒ 取 `--block-gap-nm`')
    # ★ R31（J-5）：变体选择规则。`ed`（默认，归档）⇒ 逐位不变；
    #   `random` 是 `BLOCK_SELFAC.md §7.1 P-SA-1` 的负对照臂。
    ap.add_argument('--var-rule', default='ed', choices=['ed', 'random', 'doublet'],
                    help='新核的**变体选择规则**：ed（按弹性能，默认）/ random / doublet')
    # ★ R31（J-4 的第二半）：`fresh`（独立形核）通道需要**待机位点**；
    #   位点由引擎在 t=0 随机撒下（`_nuc_place_initial`）。>0 才会走 `fresh` 通道，
    #   而**只有 `fresh` 通道才按 `--var-rule` 选变体**（`stack` 是"同变体、新场"）。
    ap.add_argument('--nuc-init', type=int, default=0,
                    help='t=0 撒下的**待机形核位点**数；>0 ⇒ 走 fresh 通道（按 --var-rule 选变体）')
    # ★★★★★ 2026-10-01（`R30_AUDIT_LEDGER.md` §189，**缺陷③**）：**fresh/stack 交错**。
    #   `0`（**默认**）⇒ 原行为：`n_fresh=(1 if nuc_init>0 else 0), n_stack=1`
    #     ⇒ 引擎里 fresh 先跑且 `cap=1` ⇒ **全部事件都是 fresh** ⇒ 一堆**单板条块**。
    #   `K > 0` ⇒ 第 `k` 个 athermal 事件：`k % K == 1` 走 **fresh**（建新块），
    #     其余走 **stack**（同变体、新场、贴块外缘 ⇒ **块内板条**）。
    #   ⚠ **物理记账（硬约束，不得含糊）**：`windowB_closure.limitations()` 第 1 条明写
    #     C-2 的 `n = α_KM(M_s − T)`"只在堆叠型块上成立；面内并列的多个 block
    #     需要在面内做分割，**本轮不做**" ⇒ **框架里本来没有"块的数目"这条律**。
    #     本开关**不发明新律**，它把"块数 vs 块内板条数"的**分配**暴露成显式输入
    #     ⇒ **本开关下的"块数"是规定的、不是涌现的**，不得当成物理结论。
    ap.add_argument('--nuc-fresh-every', type=int, default=0,
                    help='athermal 事件里每 K 个走一次 fresh（建新块），其余走 stack'
                         '（块内板条）；0=关（归档行为，全 fresh）')
    # ★★★★★ 2026-10-01（`R30_AUDIT_LEDGER.md` **§192**）：**接线修复** ——
    #   把引擎里**早已实现**的临界核判据 `f_nuc^crit = 4γ/d` 接到 CLI。
    #   ## 为什么这是"修接线"而不是"加功能"
    #     `windowB_surface.nucleate()` 的注释写着
    #     "✅ W1-4（2026-09-28）：本判据**已接线**"，但 `_bk_exp.py` 里
    #     `use_fcrit` **只出现在 3 处注释里**，从未传给 `nuc_cfg()`，也没有 CLI 开关
    #     ⇒ 从驱动层看它是**死代码**。目标第 (1) 项要求查"该有的模块是否正常接线"，
    #     这就是一条。
    #   ## 判据（引擎里已写死，此处只是让它可达）
    #     `(df + max_k ed_k) > fcrit`，`fcrit = 4γ/t`（`d` 取核厚 `t`）。
    #     被拒的位点计入 `nuc_dbg.json` 的 `dbg['fcrit']`。
    #   ## 本轮要回答的**可证伪问题**（`§191.4`）
    #     `§191` 查明：冷却前段 `ΔG_v(T_k) < |ed|` ⇒ 播下去的那片**亚临界、会溶解**。
    #     那么这条判据**能不能拦住**这些注定溶解的事件？
    #     量级预估（**待实测**）：`fcrit = 4×0.15/250e-9 = 2.4e6 J/m³`，
    #     而实测典型界面 `|dG| ≈ 1.3e8` ⇒ 判据阈值比实际弹性罚**小 ~54 倍**
    #     ⇒ **很可能拦不住**。**但必须实测，不得只靠量级估计下结论。**
    #   ⚠ **只覆盖 `fresh` 通道**；`stack` 通道**未**加该判据（已知范围缺口）。
    #   ⚠ 默认 **0** ⇒ 归档路径逐位不变。
    ap.add_argument('--nuc-fcrit', type=int, default=0, choices=(0, 1),
                    help='是否启用引擎自带的临界核判据 f_nuc^crit=4γ/d'
                         '（0=关，归档行为；1=开，**只作用于 fresh 通道**）')
    # ★★★★★ R479（2026-10-01，**任务(2) ②：超临界判据**）：
    #   判据 `ΔG_v(T) + ed_face > 2γ/t`，**试放**实现（不改任何场，见 `_supercrit_probe`）。
    #   与 `--nuc-fcrit` 的根本区别：后者用"位点上、**放核前**"的 `ed`
    #   （只是与已有板条的**相互作用**，实测 +1.9e8，可正可负），
    #   而放核**后** `ed` 含**自身弹性能**（实测 −2.5e8）⇒ **符号都不同**
    #   ⇒ 用前者判"放下去站不站得住"**原理上无效**（这正是 `--nuc-fcrit` 恒为真的原因：
    #     `4γ/t = 2.4e6` 远小于 `df + max_k ed_k ≳ 1.2e8`，51 倍余量）。
    #   ⚠ 默认 **0** ⇒ 归档路径逐位不变；且**只覆盖 fresh 通道**（范围缺口同上）。
    ap.add_argument('--nuc-supercrit', type=int, default=0, choices=(0, 1),
                    help='超临界判据 ΔG_v+ed_face>2γ/t，用**试放**实现'
                         '（0=关，归档行为；1=开，**只作用于 fresh 通道**）')
    # ★ R508：核的形状。默认 disc = 归档行为；ellipsoid = 光滑椭球。
    #   依据见 `nuc_cfg` 调用处的长注释与 `R507_fullclosure`。
    ap.add_argument('--nuc-shape', default='disc', choices=('disc', 'ellipsoid'),
                    help="核的形状：'disc'（默认，带尖边圆柱 = 归档行为）或 "
                         "'ellipsoid'（光滑椭球）。实测椭球的弹性罚低 52%% ⇒ "
                         '超临界门槛 377.7 K → 641.7 K')
    # ★★★★★ R481（2026-10-01，**任务(2) ③**）：
    #   位点池"持续可用"。默认 0 ⇒ 归档行为（池子用尽即止、逐位不变）。
    #   ⚠ 只在 `--nuc-init > 0`（已建池）下有意义。
    ap.add_argument('--nuc-sites-refill', type=int, default=0, choices=(0, 1),
                    help='形核位点池用尽时按同一分布继续抽（位点代表'
                         '**预先存在的异质位置**，物理上不应"用尽"）')
    # ★★★★★ 2026-10-04（**N11**）：`nfsv_nofield` 的**取证**开关。
    #   背景：`--laths` 从 `12×6=72` 抬到 `12×10=120`（`nv` **+67%**），
    #   而 `nfsv_nofield` 只从 **22 → 21** ⇒ **"变体碰撞/场不够"这个假设被 A/B 否掉**。
    #   ⇒ 不再猜：在**拒绝现场**把占用分布打出来。
    #   落盘到 `nuc_dbg.json` 的 `dbg`：
    #     `nfsv_diag_v`        源场的变体组号
    #     `nfsv_diag_nfields`  **同变体**的场**总数**
    #     `nfsv_diag_nocc`     其中被判为"非空"的个数
    #     `nfsv_diag_occ_sizes` 那些"非空"场的**胞数**（降序前 12）
    #     `nfsv_diag_occ_min`  最小非空场的胞数（**碎点探测**）
    #     `nfsv_diag_tot_occ`  全 `nv` 个场里非空的总数
    #     `nfsv_diag_nv`       引擎侧的 `nv`
    #   ⚠ 默认 **0**（关）⇒ 归档路径**逐位不变**（只在拒绝路径上多算一点诊断）。
    ap.add_argument('--nfsv-diag', type=int, default=0, choices=(0, 1),
                    help='在 `nfsv_nofield` 拒绝现场记录占用分布（取证 N11；'
                         '默认 0 = 不算，归档逐位不变）')
    # ★★★★★ 2026-10-04（**N13**）：**周期播种**。
    #   开 ⇒ ① `seed_plate` 取最小镜像（`rel -= L*round(rel/L)`）
    #        ② 跳过两条"有界盒越界"拒绝（`attach` 与 `fresh/stack`）
    #   —— **两件事必须配套**：只做②会让种子被盒面截断（`EXPERT-#1` 记的老问题）。
    #   动机（实测 `_r541` b4）：`oob = 122` 次 vs `ok = 13` 次 ⇒
    #     绝大多数落位尝试**死在边界上**，而那些位点在**周期盒里与盒心等价**。
    #   ⇒ 这正是"块数上不去 ⇒ C5 填不满盒子"的一个直接人为瓶颈。
    #   ⚠ 默认 **0**（关）⇒ 归档路径逐位不变。
    ap.add_argument('--nuc-periodic-seed', type=int, default=0, choices=(0, 1),
                    help='周期播种：播种取最小镜像 + 不再因"靠近盒面"拒绝位点'
                         '（默认 0 = 归档行为，逐位不变）')
    # ★★★★★ 2026-10-04（**N15**）：`phi` 的 dtype。
    #   实测内存定律（`R550_MEMORY_ENVELOPE.md §2`）：
    #     `数组合计(MB) = 9.01·nv·N³/2²⁰ + 311.8·N³/2²⁰`（留一法误差 0.13%）
    #   其中 `g.phi`（float64 = 8 B/胞）占**边际项**的 89%
    #   ⇒ 改 float32 ⇒ N=160 的 `nv_max` 从 **604 → ≈1087**
    #   ⇒ 10 µm 盒的转变分数上限从 **15.4% → ≈27.7%**（C5 要求"填满"≈30%）。
    #   ⚠ **固定项（311.8 B/胞，94% 是 `pf.Lam`）砍不动** —— 仓库 `:1052-1060`
    #     早已实测否掉其 float32；`_r551` 也证"砍 75% 只让 `nv_max` +4.5%"。
    #   ⚠ 默认 `'f64'` ⇒ **逐位不变**（用户纪律：新开关、默认关、过回归）。
    ap.add_argument('--phi-prec', type=str, default='f64',
                    choices=('f64', 'f32', 'float64', 'float32'),
                    help='`phi` 的精度（默认 f64 = 归档行为）。f32 省一半内存，'
                         '是上 10 µm 盒的前提；必须过 P1–P5 精度判据')
    ap.add_argument('--nuc-max-per-step', type=int, default=1,
                    help='每次 nucleate() 调用最多放几个核（默认 1 = 归档行为）。'
                         '准静态钟默认档宽下 Δn=1，cap=1 恰好够；'
                         '只有把 --qs-dT 取粗或跑时间积分路径时才需要放开。')
    # ★★★★★ R561–R568（2026-10-05，**算子优化**）：三个新开关，**默认全部 = 归档旧路**。
    #   实测（生产宿主 WSL/conda ml/numpy 2.5.3，N=64 nv=24 workers=4，`_r568_opverify.py`）：
    #     baseline(c2c/loop/full)  0.4052 s/步   1.00×
    #     einsum                   0.3507        1.16×
    #     einsum+gather            0.2810        1.44×   ← **与 baseline 逐位相同**
    #     rfft+einsum+gather       0.2524        1.61×   ← σ 差 2.2e-16（已做 Nyquist 修正）
    #   ⇒ 推荐 `--eps0-mode einsum --ed-pair gather`：**零物理代价**（逐位相同，判据 V2/V3 = 0.0）。
    #     `--fft-mode rfft` 再快 10%，但**不是逐位**（差 1–2 ulp，长轨迹会因混沌分叉）
    #     ⇒ 归档复现必须用默认 `c2c`。
    ap.add_argument('--eps0-mode', type=str, default='loop',
                    choices=('loop', 'einsum', 'gemm'),
                    help='ε⁰ 场装配算子。loop=归档旧路；einsum **逐位相同**且 1.76×；'
                         'gemm 最快但差 1–2 ulp（且实测在本引擎里被 BLAS 线程争用拖慢）')
    ap.add_argument('--fft-mode', type=str, default='c2c',
                    choices=('c2c', 'rfft'),
                    help='弹性 FFT。c2c=归档旧路；rfft=实数 FFT 半谱（整链 1.71×，'
                         'Λ 常驻 288→144 B/胞），带 Nyquist 面 Hermite 修正 ⇒ 与 c2c '
                         '等价到 2.2e-16（**非逐位**）')
    ap.add_argument('--ed-pair', type=str, default='full',
                    choices=('full', 'gather'),
                    help='`elastic_driving_pair` 的读出。full=归档旧路（造 (nreg,N³) '
                         '+ nreg 次 einsum）；gather=只算 winner/runner-up 两行，'
                         '实测 4.92× 且**逐位相同**')
    # ★★★★ R578（**算子优化第二轮**）：推进循环的**遍历集合**。
    #   `full` = `range(nreg)`（归档旧路）；`act` = `unique(karr) ∪ unique(larr)`。
    #   **等价性可证**（`windowB_surface.LevelBSetMulti.__init__` 的记账）：
    #     `k ∉ act ⇒ (karr==k) ≡ (larr==k) ≡ False ⇒ vnk ≡ ±0.0 ⇒ 必定 return，不写任何场`。
    #   实测（`_r578_kloop.py`，N=48/nv=8，两种构型各 5 步）：
    #     两臂 `g.phi` **逐位相同 0.000e+00**；负对照（`act` 臂丢一个活跃场）**8.3e-08** ⇒ 量具有分辨力。
    #   实测（`_r578_kloop_ab.sh`，N=64/nv=24，交错 3 轮）：
    #     计数回归 `adv.step.vnk` **25.00 → 4.00 次/步**（nreg=25、活跃场=4）；
    #     墙钟**中位 1.064×**（区间 1.025–1.067）。
    ap.add_argument('--k-loop', type=str, default='full',
                    choices=('full', 'act'),
                    help='推进循环 for_each 的遍历集合。full=归档旧路（所有 nreg 个场）；'
                         'act=只遍历 winner/runner-up 出现过的场（**逐位相同**，'
                         '实测 1.064×，因为空场那一步"什么也不做"）')
    # ★★★★ R578（goal §3①/③）：两个"逐位不变"的小项，各自独立开关。
    ap.add_argument('--act-mode', type=str, default='unique',
                    choices=('unique', 'bincount'),
                    help='活跃场集合的算法。unique=归档旧路（三次排序）；'
                         'bincount=线性计数，**同一个升序集合**，实测 6.12×')
    ap.add_argument('--argmin2-mode', type=str, default='legacy',
                    choices=('legacy', 'copyto'),
                    help='argmin2 的 runner-up 扫描。legacy=归档旧路（布尔花式索引）；'
                         'copyto=np.copyto(where=)，**逐位相同**，实测 1.265×')
    # ★★★★ R579（goal §6）：`par.gradient` 的实现。
    ap.add_argument('--grad-mode', type=str, default='legacy',
                    choices=('legacy', 'sliced'),
                    help='`par.gradient` 的实现。legacy=归档旧路（对带 halo 的子盒调 '
                         'np.gradient）；sliced=**逐行照抄 numpy 的 edge_order=2 边界公式** '
                         '的切片版，与 np.gradient **逐位相同**（判据 `_r579_grad.py`）；'
                         '⚠ 速度收益未确立（微基准中位 1.143×，区间 [0.487, 2.501]）')
    # ★★★★★ R579（goal §4）：`pf.phi`（软指示场）是否常驻 —— **C5 的必要条件之一**。
    ap.add_argument('--pf-phi', type=str, default='materialized',
                    choices=('materialized', 'onfly'),
                    help='软指示场 `pf.phi` 的处理。materialized=归档旧路（写进 pf.phi 再读，'
                         'float64 = 8 B/胞·nv）；onfly=**不物化**，`eps0_fields` 按 '
                         '--h-chunk 分块现算 ⇒ 常驻降到 bool 的 1 B/胞·nv。'
                         '**与 materialized 逐位相同**（`_r579_pfphi.py` D2 = 0.000e+00）；'
                         'N=160 实测 a 从 16.000 → 9 B/胞 —— C5（需 a ≤ 6.8）**仍差一步**，'
                         '必须再叠加 `--phi-prec f32`（a → 5）')
    ap.add_argument('--h-chunk', type=int, default=4,
                    help='`--pf-phi onfly` 时软指示场的分块份数（每份 N³ float64）。'
                         '决定**峰值**上界：chunk×8 B/胞 + 输出 48 B/胞（判据 D4）')
    # ★★★★★ R581-L2（goal §(4)）：`eps0_fields_stream` 的**首轴空间分块**。
    ap.add_argument('--eps0-tile', type=int, default=0,
                    help='`--pf-phi onfly` 下 `eps0_fields_stream` 的**首轴空间分块**'
                         '（每块几个首轴切片）。0=归档旧路（整场 axpy）。'
                         '为什么：生产实测 `el.epsh` = **47.5% 单步**，其中 1.10 s 是它；'
                         '根因是 `e`(48 B/胞) 溢出 cache（288 次整场 axpy ≈ 4.1 GB/步 DRAM）。'
                         '分块后 `e` 的切片留在 L2/L3 ⇒ 微基准 **1.81–1.89×**，'
                         '**42 档组合全部逐位**（`_r581_L2_sweep.py`）。建议 2–4')
    # ★★★★★ R581-L5（goal §(7) ①）：复用 `region()` 的 winner，省一次 argmin/步。
    ap.add_argument('--argmin2-reuse', type=int, default=0, choices=(0, 1),
                    help='`advance()` 里 `reg0 = region()` 与 `argmin2(self.phi)` 是'
                         '**同一个 argmin**（两者之间 phi 未被修改）⇒ 复用 reg0，'
                         '省掉一次 argmin/步（每步 argmin 次数 3→2）。'
                         '**逐位相同**（论证见 `ParCtx.argmin2` 的 docstring）。'
                         '⚠ 计数回归的**实测**变化：`argmin2.winner` 1→0（workers=1），'
                         '每步**总 argmin 次数 4→3**（`region()` 本身仍是 3 次/步）')
    # ★★★★★ R581-L6（goal §(8)⑤）：`upwind_flux_vec` 的**整轴融合 C 核**（默认关）。
    ap.add_argument('--ufv-c', type=int, default=0, choices=(0, 1),
                    help='`upwind_flux_vec` 用 C 融合核（`_r581_ufv.so`）。'
                         '需先 `bash _r581_buildc.sh`。'
                         '实测（N=96 交错 7 轮）**2.122×**，折算省 **8.94%** 单步；'
                         '**逐位**（order 1/2 × V 三种形态，NaN 感知 + 符号位比较）。'
                         '⚠ 记账：C 档下 op.ufv.* / op._minmod 的打点计数都变 0（融合核内部不打点）')
    # ★★★★★ R581-L4（goal §(6) ②）：`_bbox_pad` 的实现档。
    ap.add_argument('--bbox-mode', type=str, default='legacy',
                    choices=('legacy', 'axis'),
                    help='`_bbox_pad` 的实现。legacy=np.argwhere（造 (M,3) int64 索引）；'
                         'axis=逐轴 any+flatnonzero（无大临时量）。'
                         '**18 组（6 掩模 × 3 pad）包围盒完全一致**（含贴盒面的 wrap 分支）；'
                         '实测 `_bbox_pad` 本身 **15.362×**。'
                         '⚠ 天花板：折算仅约 **0.4% 单步**（mask_bbox 只占 0.80%）')
    # ★★★★★ R581-L1（goal §(3) L1）：`adv.extend` 的 EDT 分支档。
    ap.add_argument('--extend-mode', type=str, default='legacy',
                    choices=('legacy', 'merged', 'near'),
                    help='`adv.extend` 的 EDT 分支实现（**生产走的就是这一支**，'
                         '因为 `pair_kernel` 默认 False）。'
                         'legacy=归档旧路（对 `~iface` **调两次** distance_transform_edt）；'
                         'merged=合成一次（return_distances+return_indices），'
                         '**逐位相同**，实测 1.56–1.61×；'
                         'near=merged + 只在 `dist<=band_cells` 的胞上 gather，'
                         '**逐位相同**，实测 1.91–2.11×。判据 `_r581_L1b_edt.py`')
    # ★★★★★ R502（2026-10-01，**"块数"口径**，见 `R502_BLOCKCOUNT.md`）：
    #   C-2 的 `n(T) = α_KM(M_s − T)` 是**一个块里堆叠的板条数**（块厚 `W_block = n·t`），
    #   而驱动原来把它当成**全盒的事件上界** ⇒ 全盒最多 `n(T_end)` 次事件。
    #   正确的总量是 `N_tot = B · n(T)`，`B`（块数）是**输入**（框架没有这条律）。
    #   ⚠ 默认 0 ⇒ 走原路径 ⇒ 归档逐位不变。
    ap.add_argument('--nuc-block-target', type=int, default=0,
                    help='块数 B（输入，不是涌现）。>0 时全盒事件上界 = B·n(T)；'
                         '0（默认）= 旧口径（上界 = n(T)）。'
                         '几何上界 B_max = L_box²/(plate_L·plate_W)')
    # ★★★★★ 2026-10-01（`R30_AUDIT_LEDGER.md` **§200**，**接线缺口 #3**）：
    #   **sympathetic 形核"接到哪个块上"是否看驱动力**。
    #   ## 缺口
    #     `windowB_surface.nucleate()` 的 stack 通道原先写
    #       `k = int(ks[rng.integers(0, len(ks))])`   ← **均匀随机挑一个已有场**
    #     **完全不看驱动力**。而 `§195` 实测：sympathetic 形核**继承源块的命运** ——
    #     4 条"长了"的 `attach` **全部**接在 V7/V9 的块上（正在长），
    #     6 条"不长"的**全部**接在 V1 的块上（正在溶）。
    #   ## 打开后做什么
    #     对每个已有场取"**与母相相邻的胞**"（自由外侧面），算 `mean(df + ed_k)`，
    #     **接到平均驱动力最大的那个块上**。没有自由面的场不参选。
    #   ## 记账
    #     `dG = df + ed` 是引擎**已经在算**的量（`series.csv` 的 `dG_tip`/`dG_side`
    #     就是它的分面统计）⇒ 本开关**不引入新的物理量**，只是**接线**。
    #     ⚠ 但它**会改变数值**（选块规则变了）⇒ 必须与 `0` 做**受控对照**。
    #   ⚠ 默认 **0**（关）⇒ 归档路径**逐位不变**。
    ap.add_argument('--stack-pick-dg', type=int, default=0, choices=(0, 1),
                    help='sympathetic 形核选源块：0=均匀随机（归档）；'
                         '1=接到"外侧面平均 dG 最大"的块（§200 接线修复）')
    ap.add_argument('--omega-max-deg', type=float, default=5.0,
                    help='ladder/random 模式下是**总张角** θ_max；'
                         'perstep 模式下是**逐界面步长** Δθ（见 §129/P1-45）')
    # ★★★ R182（`§129` / **P1-45**）：新增 `perstep` 模式。
    #   ## 为什么
    #     `ladder` 把总张角 θ_max **均分**给 M−1 个间隔 ⇒ 相邻同变体对的取向差
    #     Δθ = θ_max/(M−1) **随 M 变** ⇒ 实测块内界面能**跨 M=2…20 变化 7.91 倍**
    #     （M=2 时 γ=1.108×γ₀ **倒挂**，M=20 时 0.140×γ₀）⇒ 它**不是材料常数**。
    #     而"块 = 多根同类板条堆叠 + 低角晶界分隔"这个前提里，
    #     物理上可控的是**逐条界面的取向差**，不是"一个块总共转多少度"。
    #   ## 惰性保证
    #     默认仍是 `ladder` ⇒ **归档路径逐位不变**（回归第 19 次必须过）。
    #   ## 不预设哪个对
    #     沿用 `§102` 的 C 方案先例：**两条都跑、作受控对照**，
    #     不假定位移步长一定比均分好（真实块内确实可能存在转动梯度）。
    ap.add_argument('--omega-mode', default='ladder',
                    choices=['ladder', 'perstep', 'random'],
                    help='ladder=总张角均分（**归档默认**）；'
                         'perstep=逐界面步长 Δθ 固定（P1-45 的修法，**默认关**）；'
                         'random=负对照')
    # ★★★★★ R208（`R30_AUDIT_LEDGER.md` **§135.7 的决定性检验**）：**逐胞直测
    #   速度律三项** `|df_k−df_l|`、`|ed_k−ed_l|`、`|stk·κ|` 的量级。
    #
    #   ## 为什么
    #     `§135.5` 断言"界面能项 ≤ 0.88% 的弹性项"（用 `κ=1/Δx` 的**上限**推的），
    #     该结论支撑 R165 否定结果、`§132.5`（`ncmp` 量不到）、`§112`（自协调 FAIL）
    #     三条**重要**结论 ⇒ **必须从【推理】升为实测**。
    #
    #   ## 口径
    #     只在**界面胞**上统计；**变体-变体**（F2/F3）与**含母相**（F1）**分开报**。
    #     输出：中位/90 分位的 `|Δed|`、`|stk·κ|`，以及**比值** `|stk·κ|/|Δed|`。
    #
    #   ## 惰性
    #     默认 **False** ⇒ 引擎里整块被 `getattr(..., False)` 门控跳过 ⇒ **逐位不变**
    #     （由 `_r30_regress.sh` 第 20 次把关）。⚠ 打开后**只打印不改数**。
    ap.add_argument('--diag-terms', action='store_true',
                    help='逐胞直测速度律三项量级（默认关；只读记账，不改数值）')
    # ★★★★★ R238（`§135.6` / 条件③主线）：**逐变体 `ed` 分布**。
    #   动机：`§142.1` 已定量确认**界面能项不是杠杆**（F1 0.31% / F2 2–9%，
    #   且 F2 只占 8.7% 面积）⇒ 变体选择由 `ed` 决定 ⇒
    #   **自协调若有，只能走 `ed` 经共享应力场** ⇒ 必须直接量它。
    #   口径：每个变体在"winner 是它"的胞上的 `ed` 中位/均值/分位 + 体积，
    #         以及跨变体的**极差/标准差**（越大 ⇒ 被弹性项区别对待越强）。
    #   ⚠ 默认关、纯只读 ⇒ 归档逐位不变（回归把关）。
    ap.add_argument('--diag-edv', action='store_true',
                    help='逐变体 ed 分布（默认关；只读记账，不改数值）')
    # ★★★★★ R477（2026-10-01）：**准静态钟（路线 1B）**。
    #   物理依据与语义见主循环前的长注释。**默认关** ⇒ 归档路径逐位不变。
    ap.add_argument('--qs-clock', type=int, default=0, choices=(0, 1),
                    help='准静态钟（1B）：阶段内钉住 T、伪时间弛豫到收敛再降 T。'
                         '默认 0 = 旧的"CFL 步长当物理时间"路径（逐位不变）。'
                         '只在 --nuc-law athermal 下有效。')
    ap.add_argument('--qs-dT', type=float, default=0.0,
                    help='温度档步长 ΔT（K）。0（默认）⇒ 用 1/α_KM ⇒ 每档恰好放 1 根核'
                         '（= C-2 的 T_k 序列）。取更粗的值会让一档放多根核'
                         '（= 把 burst 强度当**建模选择**，必须显式记账）。')
    ap.add_argument('--qs-tol', type=float, default=2e-3,
                    help='收敛判据：**窗口内相对体积变化** Σ|ΔV|/V < qs_tol ⇒ 本档弛豫到底。'
                         '（不用 dG_max —— 实测它被最尖的那个胞主导、永不衰减，见主循环注释）')
    ap.add_argument('--qs-win', type=int, default=20,
                    help='收敛判据的滑动窗口步数（对单胞抖动去敏）')
    ap.add_argument('--qs-max-relax', type=int, default=400,
                    help='每个温度档的最大弛豫步数（安全上限）')
    # ★ R498：**纯溶解档早退**（任务(5) 的用时优化；默认 0 = 关）。
    #   依据 `_r497` 实测：早期档里场**只在溶解**（初始板条 400 步溶掉 97.3%），
    #   而纯溶解**没有不动点** ⇒ 收敛判据永远不满足 ⇒ 每档都撞 `--qs-max-relax`
    #   ⇒ 白烧 20×400 步。本开关让"连续 N 步 V 都在减少"的档提前降 T。
    #   ⚠ 这是**数值优化**，必须用对照实验确认末态在容差内一致。
    ap.add_argument('--qs-shrink-cap', type=int, default=0,
                    help='若本档 V 连续 N 步单调减少（纯溶解）则提前降 T；'
                         '0（默认）= 关，即完全按收敛/上限走')
    ap.add_argument('--plate-L', type=float, default=2400.0)
    ap.add_argument('--plate-W', type=float, default=640.0)
    ap.add_argument('--plate-T', type=float, default=250.0)
    ap.add_argument('--gap-nm', type=float, default=0.0)
    ap.add_argument('--grow-stack', action='store_true',
                    help='★ G-1 方案 B：t=0 只播第 1 片，此后每 --nuc-every 步'
                         '在当前块外侧播下一片（同变体、新场）⇒ 生长中堆叠成块')
    # ★★★ R28：**默认 0 = 形核交给引擎**（新默认）。
    #   要复现归档的**驱动层**行为，显式传 `--nuc-every 30`。
    #   **归档命令行全部显式传了 30**（见各臂 `meta.json` 的 `exp_args`）
    #   ⇒ 它们的行为**逐位不变**。
    ap.add_argument('--nuc-every', type=int, default=0)
    ap.add_argument('--nuc-gap-nm', type=float, default=0.0)
    # ★ Round 9：新核**咬进**已有块的深度（nm）。0 = 恰好相切（旧行为，
    #   实测会因阶梯错位留 1 胞 β 膜 ⇒ F3 覆盖率只有 0.62）。
    #   物理上"在界面上形核"就是共用一张界面 ⇒ 用一个正的重叠量。
    #   建议值 ≥ 1.5Δx（Δx=62.5 nm ⇒ 94 nm），保证中面离两侧零集都够远。
    ap.add_argument('--nuc-overlap-nm', type=float, default=0.0)
    # ⚠⚠ **R581-R17 撤回留痕**：我在这里加过 `--nuc-seed`（默认 11），
    #   理由是"`nuc_cfg` 的 seed 硬编码、CLI 没旋钮"（缺口 A22）。
    #   **实测证明那是错的**：`nuc_cfg(...)` 的调用里**本来就有 `seed=a.eng_seed`**
    #   ⇒ 旋钮是 **`--eng-seed`**（见 `ap.add_argument('--eng-seed'...)`）。
    #   加第二个开关会造成**两个旋钮控同一个量** ⇒ 已**撤回**，不留。见 P28。
    # ★ Round 10：把会被"咬"掉的厚度预先补上（见 `_seed_next` 的记账）。
    #   只在 `--nuc-overlap-nm > 0` 时有意义。
    ap.add_argument('--nuc-compensate', action='store_true')
    # ★★★ R12：`--arm eng` —— 引擎侧自发形核
    ap.add_argument('--eng-cadence', type=int, default=30,
                    help='引擎形核的**节奏**（步）；0 = 每步都问一次引擎')
    ap.add_argument('--eng-r-nm', type=float, default=320.0)
    ap.add_argument('--eng-t-nm', type=float, default=250.0)
    # ★★★ R28：**形核通道选择**。
    #   `auto`（默认）：`--grow-stack` 且 `--nuc-every <= 0` ⇒ **引擎**；
    #                     给了 `--nuc-every > 0` ⇒ **驱动层**。
    #   ⇒ **所有归档命令行都带 `--nuc-every 30` ⇒ 逐位不变**；
    #     而「只给 `--grow-stack`」这一新写法自动拿到**已验的引擎路径**。
    ap.add_argument('--nuc-mode', default='auto',
                    choices=['auto', 'driver', 'engine'])
    ap.add_argument('--eng-seed', type=int, default=11)
    # ★ R22：关掉"有事件就强制 reinit"（**R23 起改为引擎自动**：attach 下默认关）。
    ap.add_argument('--eng-no-force-reinit', action='store_true',
                    help='（R22 遗留，已由引擎自动决定取代；保留以免旧命令行失效）')
    # ★ R23：末片减薄（对齐驱动层 `_seed_next` 的 `T+o/2`）。默认 0 = 不减薄。
    ap.add_argument('--eng-t-last-reduce-nm', type=float, default=0.0)
    ap.add_argument('--eng-force-reinit', action='store_true',
                    help='强制打开事件后 reinit（用于复现 eng5..eng10）')
    # ★ R18：逐对 F3 面积记录间隔（步）。0 = 不记（默认，与改动前逐位相同）。
    ap.add_argument('--pair-every', type=int, default=0)
    # ★★★ R12：**核的形状**。默认 0 ⇒ 圆盘（= 引擎原行为）。
    #   实测（`--arm eng`，R=320、200 步）圆盘给出的第一次接触面只有 0.39 µm²，
    #   而驱动层的长条板条给 1.5174 µm² ⇒ 终态 F3 面积差 **7 倍**。
    #   传 `--eng-elong 3.75` 即恢复 `L/W = 2400/640` 的长条（沿 `a` 轴）。
    ap.add_argument('--eng-elong', type=float, default=0.0,
                    help='0 = 圆盘（引擎原行为）；>1 = 长条核（沿用 a 轴）')
    # ★★★ R29：**F1/F2 的标量面能**（原先硬编码 0.15）。加这个开关的理由：
    #   闭环要求把 `γ_α′β` 从 [占位] 0.15 换成文献值（Murzinova 2017 给
    #   0.201–0.337 @975 °C、0.298–0.429 @600 °C）⇒ 必须能**单变量**地扫它。
    #   默认 0.15 ⇒ **全部归档读数逐位不变**。
    ap.add_argument('--gamma0', type=float, default=0.15,
                    help='F1/F2 标量面能 [J/m²]；F3 仍走 Read–Shockley γ_RS(θ)')
    # ★★★ R29：**物理板条厚**（与"播种厚"区分开）。
    #   为什么必须分开记：`--plate-T` / `--eng-t-nm` 是引擎**播种**用的厚度，
    #   而共享界面会把每片**咬掉** o/2（两侧被咬的片吃 o）⇒ 播种厚必须比
    #   **物理板条厚**大，否则末态厚度系统性地偏薄。
    #   实测代价（`dry_cl1`，未补偿，t_seed = 510 nm、o = 125 nm）：
    #     场 1（被咬两次）剔孤儿厚度 **391.8 nm**，比 510 薄 **23%** ⇒ 掉出 V-8b 窗口。
    #   ⇒ `--plate-t-physical` 记的是**物理靶值**，判据（V-8b / A-8）必须用它。
    #   默认 0 ⇒ 等于 `--plate-T`（归档行为不变）。
    ap.add_argument('--plate-t-physical', type=float, default=0.0,
                    help='0 = 等于 --plate-T；否则记进 meta 供判据用（播种厚≠物理厚）')
    # ★★★ R29（2026-10-01）：**形核律**。用户要求"用形核率之类的方式让模型合理运转"。
    #   `cadence`（默认）：`--eng-cadence` 规定的节奏 ⇒ **与全部归档读数逐位相同**。
    #   `athermal`：由 `windowB_closure` 的 C-2/C-3 闭式驱动 ——
    #       ① 钟：`T(t) = M_s − q·t`（`windowB_km.linear_cool`），
    #          驱动力 `df(T) = drive_of_T(T; T0, DS)`（引擎的 `set_T`，T6 已接线）；
    #       ② 板条数：`n(T) = α_KM·(M_s − T)`（C-2，位置饱和律；`A_0 ≡ A_f` 由
    #          引擎几何本身给出）⇒ **`n` 从"规定的 6"变成导出量**；
    #          第 k 根在 `T_k = M_s − k/α_KM` 出现；
    #       ③ 步长：`dt = cfl·dx/(MOB·ΔG_v(T))` ⇒ 随降温自动变小；
    #       ④ 停止：`n` 达到 `floor(α_KM·(M_s − T_end))` 或步数用尽。
    #   ⚠ 记账：`q` 由 C-3 的**有序性上界** `q ≤ MOB·ΔG_crit/(α_KM·L_lath)` 乘安全系数定，
    #     不是自由参数；`--cool-rate` 给了就显式检查它是否越界。
    ap.add_argument('--nuc-law', default='cadence',
                    choices=['cadence', 'athermal'])
    ap.add_argument('--alpha-km', type=float, default=ALPHA_KM_REF,
                    help='athermal 位置饱和律的系数 [1/K]（唯一待标定常数）')
    ap.add_argument('--cool-rate', type=float, default=0.0,
                    help='athermal 钟的冷速 [K/s]；0 = 由 C-3 的有序性上界自动定')
    ap.add_argument('--cool-ratio', type=float, default=0.8,
                    help='athermal 钟：有序比目标（Δt_grow/Δt_nuc），<1 才有安全余量')
    ap.add_argument('--T-start', type=float, default=0.0, help='0 = 用 M_s')
    ap.add_argument('--T-end', type=float, default=298.0)
    # ★★★ R29：`--closed` —— **一条命令**拿到闭环配置（见 `_apply_closed`）。
    ap.add_argument('--closed', action='store_true',
                    help='由 windowB_closure.recommend() 推出并套用全部闭环参数')
    ap.add_argument('--closed-force', action='store_true',
                    help='允许闭式**覆盖**你显式传的冲突参数（默认硬失败）')
    # `--closed` 的两个**文献输入**（其余都由闭式导出）
    ap.add_argument('--closed-t-nm', type=float, default=None,
                    help='物理板条厚 [nm]；None = windowB_closure.T_LATH_MAIN_NM'
                         '（Shuai 2026 的 510）')
    ap.add_argument('--closed-aspect', type=float, default=None,
                    help='长:厚；None = windowB_closure.ASPECT_LT_WANG（9:1，Wang 2026）')
    # ★★ Round 10 实测更正：`--nuc-compensate` 用**名义** `o` 补，而**补过头了**。
    #   证据（同配置三点）：
    #     `gs4`（不补）   厚度 238/238/239/230/254/250（均值 241.5，−3.4%）Vt 2.1062
    #     `gs5`（补 o）   厚度 261/289/303/285/314/282（均值 289，**+15.6%**）Vt 2.6897
    #   原因：实际重叠**小于**名义 `o` —— `edge` 是**格心**投影，本来就落在真实
    #   α′ 边界**内侧**最多约 `0.5·max|n_i|·Δx ≈ 40 nm`；`_bk_pair.py` 实测的
    #   投影间隙只有 −2…−69 nm（均值 ≈ −28 nm），远小于 62.5。
    #   ⇒ 加这个系数：`T_j = T + frac·o`。`frac=1.0` ⇒ **与 `gs5` 逐位相同**。
    ap.add_argument('--nuc-compensate-frac', type=float, default=1.0)
    ap.add_argument('--norm-smooth', type=int, default=0)
    ap.add_argument('--beta-h', type=float, default=3.5)
    ap.add_argument('--beta-w', type=float, default=2.3)
    ap.add_argument('--facet-lam', type=float, default=0.0)
    ap.add_argument('--facet-eps', type=float, default=0.05)
    ap.add_argument('--adv', default='proj2')
    ap.add_argument('--reinit-band', type=float, default=6.0)
    # ★★★ R56：**速度扩展带宽**（胞）。默认 20 = T 系列（各向同性）验证过的值。
    #   P1-31 的定位实验用它扫 `v_a/v_w`（解析 9.90 vs 引擎 1.24）。
    ap.add_argument('--band-cells', type=int, default=20,
                    help='速度扩展带宽（胞）；20 = 已验证值，改动只用于定位实验')
    # ★★★★★ R61（P1-31 的实现）：**Wulff 凸化速度律（刻面机制）**。
    #   数学见 `R30_AUDIT_LEDGER.md` §46：把进入平流的法向速度从 `v(n)` 换成
    #   其**凸包络** `v**(n)` ⇒ `v**` 在缺失取向上是平的 ⇒ **平面刻面**。
    #   ⚠ E-1（§45）已证"光让 `v` 非凸没用"（三种平流格式都只给 1.6–2.0，
    #     而凸化预言 9.9）⇒ **必须显式凸化**。
    #   ⚠ 默认 **关**（`mob_wulff=False`、`mob_dip=0`）⇒ 归档路径逐位不变。
    ap.add_argument('--mob-wulff', action='store_true',
                    help='启用 Wulff 凸化速度律（刻面机制）；默认关')
    ap.add_argument('--mob-dip', type=float, default=0.0,
                    help='惯习面内 45° 方向的迁移率凹陷强度 c（exp(−c·sin²2θ)）；'
                         '0 = 不凹陷。3D 实测：c=4 时 h(a)/h(w)=9.73')
    # ★★★★★ R64（§52）：**椭圆面内极曲线**。
    #   把面内角函数从 `exp(−β_w sin²θ)` 换成椭圆径向函数 `g(θ)`：
    #   极集**本身凸** ⇒ 凸化是恒等变换 ⇒ `h(a)/h(w)` **恰等于 `--mob-ratio`**
    #   （实测 ratio=9 给 **8.93**），而 `h(n*)` 与现形式相同（**0.999×**）
    #   ⇒ **既拿到 9:1 的面内各向异性，又不动厚度钉扎**（§51 的两难消失）。
    #   ⚠ 默认 `exp2` = 现行为 ⇒ **归档路径逐位不变**。
    ap.add_argument('--mob-iform', choices=['exp2', 'ellipse'], default='exp2',
                    help='面内迁移率角函数形式；exp2 = 现行为（默认）')
    ap.add_argument('--mob-ratio', type=float, default=9.0,
                    help='椭圆面内极曲线的长短轴比（= 目标长径比）；默认 9')
    # ★★★★★ R64（§53）：**弹性驱动缩放**。`1.0` = 全量（默认，逐位不变）；
    #   `0` = 关掉弹性驱动 ⇒ 用于判定"限速环节是不是弹性驱动"。
    ap.add_argument('--el-scale', type=float, default=1.0,
                    help='弹性驱动 ed 的缩放因子；1.0 = 全量（默认），0 = 关掉')
    # ★★★★★ R69：**周期性面片投影**（保面机制，`BLOCK_SELFAC.md §8 C`）。
    #   每 N 步把每个变体场投影回"体的 min/max 盒（外扩 0.5Δx）+ 体积标定"。
    #   算子已过正对照：解析长方体上幂等（`s=1.000`、体积 0.0%）；
    #   真实圆化快照上 `f_flat` 0.005 → 0.155（解析值 0.172）。
    #   ⚠ 默认 0 = 关 ⇒ **归档路径逐位不变**。
    ap.add_argument('--facet-proj', type=int, default=0,
                    help='每多少步做一次面片投影；0 = 关（默认）')
    # ★★★★★ 2026-10-01（`R30_AUDIT_LEDGER.md` **§186**）：**投影的"排除掩码"开关**。
    #   `0`（**新默认**）= 不构造 `excl` ⇒ 同变体相邻两场的盒子**贴合**（实测缝宽 −0.32 胞）；
    #   `1` = 旧行为（R73）：把"与同变体另一个场相邻"的胞排除出取跨度的点云
    #         ⇒ 盒子单侧内缩 ⇒ **每对同变体板条之间张开 1.88 胞（≈118 nm）的缝**
    #         ⇒ `φ_0` 在缝里仍为负 ⇒ `region = 0` ⇒ **β 膜**：
    #            `t=0` 时 β 膜 **1451 胞（11.58% 已转变体积）**、**F3 面数 1169 → 0**、
    #            **块数 6 → 12**（三个独立量具 `_r410`/`_r411`/`_r412`，均先过正对照）。
    #   ⚠ 只影响**显式**传了 `--facet-proj > 0` 的臂；`--facet-proj 0` 下
    #     `facet_project()` 一次都不被调用 ⇒ 回归（`_r30_regress.sh` 不带该开关）**逐位不变**。
    #   ⚠ 保留 `1` 只为**逐位复现**归档中显式传过 `--facet-proj > 0` 的臂。
    ap.add_argument('--facet-excl', type=int, default=0, choices=(0, 1),
                    help='面片投影是否用"同变体邻域"排除掩码：0=否（默认，§186 修）；'
                         '1=旧的 R73 行为（会张开 β 膜，仅用于复现归档）')
    # ★★★★★ R131（**用户裁定 C**）：`§93/§102` 的选支受控对照。
    #   `none`（默认）= `NPF = argmin_normal(C,ε)`（弹性能极小法向）⇒ **逐位不变**；
    #   `invariant`  = 对**判据说该换**的变体（实测 `{1,3,8}`）把 `n*` 与 `a` 对调
    #                  （判据 `rB`，自带正对照；受影响集合**算出来**，不写死）。
    ap.add_argument('--rank1-swap', choices=['none', 'invariant'], default='none',
                    help='rank-1 选支规则：none=弹性能极小（默认，归档路径）；'
                         'invariant=按不变平面判据对调 n*/a（用户裁定 C 的对照臂）')
    # ★★★★ R164（`§122`）：**F2（异变体）面能的配对依赖** —— 补上"生长通道没有自协调机制"。
    #   `0.0`（默认）⇒ F2 的 `gtab` 项保持 NaN ⇒ 引擎走原标量路径 ⇒ **逐位不变**。
    ap.add_argument('--f2-pair-gamma', type=float, default=0.0,
                    help='F2 面能的配对依赖强度 λ∈[0,1]：'
                         'γ_F2(v,w)=γ₀[(1−λ)+λ·min(1,‖Δε‖/Δε_ref)]；0=关（默认，逐位不变）')
    ap.add_argument('--reinit-dt', type=float, default=6.0e-7,
                    help='重初始化间隔（秒）。**默认 6e-7 是生产值**；'
                         '诊断时给大值（如 1e-4）≈ 关掉 reinit')
    ap.add_argument('--nthreads', type=int, default=4)
    ap.add_argument('--gamma-film', type=float, default=0.6)
    ap.add_argument('--out', default='_exp/_bk_block')
    ap.add_argument('--tag', default='')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    # ★★★★★ 2026-10-04（**新增：`--snap-every 0` 的清晰报错**）
    #   实测（`_r528` 的 T1–T8 第一版）：传 `--snap-every 0` 会在**跑到一半**时
    #     死在 `_bk_exp.py` 的 `_snap_now = (it % a.snap_every == 0)`（**除零**），
    #     报 `ZeroDivisionError: integer modulo by zero` ——
    #     **报错信息完全不提是哪个参数**，且**已经白跑了一段**。
    #   ⚠ 注意 `--pair-every 0` 与 `--norm-smooth 0` 是**合法**的（各自的代码判了 0），
    #     只有 `--snap-every` 直接拿去取模 ⇒ **同一个 0 在不同参数上含义不同**，
    #     这正是最容易踩的那种坑。
    #   ⇒ 在**解析后立刻**拦住，并说清楚"0 不是关闭快照的意思"。
    if int(getattr(a, 'snap_every', 1) or 0) <= 0:
        raise SystemExit(
            '❌ **`--snap-every %d` 非法**（必须 ≥ 1）\n'
            '   它会被直接拿去取模（`it %% a.snap_every`）⇒ 传 0 会在跑到一半时\n'
            '   抛 `ZeroDivisionError`（**报错不说是哪个参数**，且已白跑一段）。\n'
            '   ⚠ `--pair-every 0` / `--norm-smooth 0` 是**合法**的（代码判了 0）——\n'
            '     同一个 0 在不同参数上含义不同，别类推。\n'
            '   想要"不打快照"就**不要传**这个参数，或传一个大到超过 `--steps` 的值。'
            % int(getattr(a, 'snap_every', 0) or 0))
    _apply_closed(a, ap)
    _warn_archived_path(a)
    return run(a)


# ---------------------------------------------------------------------------
# ★★★ R29：`--closed` —— 让**闭环配置**变成"一条命令"
# ---------------------------------------------------------------------------
# 用户 R29 的要求是「让**默认路径**用闭环参数跑通」。闭环配置由 12 个参数组成
# （Δx/L/W/T/播种厚/物理厚/r_nuc/o/elong/β_h/laths/nuc_law），全部来自
# `windowB_closure.recommend()` 的闭式。手打这 12 个不但易错，而且**看不出哪个是推出来的**
# ⇒ 提供一个开关，它调用闭式并把结果**套用**上去。
#
# 口径（本仓库的硬规矩：不许静默改用户显式传的东西）：
#   * 用户**没传**（等于 argparse 默认值）⇒ 直接套用推导值；
#   * 用户**传了**且与推导值一致 ⇒ 套用（无冲突）；
#   * 用户**传了**且与推导值冲突 ⇒ **硬失败**，除非同时给 `--closed-force`。
def _apply_closed(a, ap):
    if not getattr(a, 'closed', False):
        return
    t_phys = (float(a.closed_t_nm) if a.closed_t_nm
              else float(CL.T_LATH_MAIN_NM))
    aspect = (float(a.closed_aspect) if a.closed_aspect
              else float(CL.ASPECT_LT_WANG))
    rec = CL.recommend(N=a.N, t_lath_nm=t_phys, aspect=aspect,
                       alpha_KM=a.alpha_km, T_f=a.T_end)
    if not rec.get('ok'):
        raise SystemExit('✗ --closed：windowB_closure.recommend() 未通过（%s）'
                         % rec.get('blocked', '?'))
    t_seed = t_phys + rec['overlap_nm']
    targets = dict(
        dx_nm=rec['dx_nm'],
        plate_L=rec['L_lath'] * 1e9,
        plate_W=rec['W_lath'] * 1e9,
        plate_T=t_seed,
        plate_t_physical=t_phys,
        eng_r_nm=rec['r_nuc_nm'],
        eng_t_nm=t_seed,
        eng_elong=rec['elong'],
        nuc_overlap_nm=rec['overlap_nm'],
        eng_t_last_reduce_nm=0.5 * rec['overlap_nm'],
        beta_h=rec['beta_h_use'],
        laths=','.join(['1'] * rec['n_lath']),
        nuc_law='athermal',
        grow_stack=True,
        nuc_every=0,
        steps=rec['steps'],
    )
    conflicts, applied = [], []
    for k, v in targets.items():
        cur = getattr(a, k, None)
        dflt = ap.get_default(k)
        if isinstance(v, float) and isinstance(cur, float):
            same = abs(cur - v) <= 1e-9 * max(1.0, abs(v))
        else:
            same = (cur == v)
        if same:
            applied.append((k, v, '推导值'))
        elif cur == dflt:
            applied.append((k, v, '套用（你未指定）'))
            setattr(a, k, v)
        else:
            conflicts.append((k, cur, v))
    # ⚠ `P()` 定义在 `run()` 里 ⇒ 本函数在它之前跑，这里只能用 `print`
    #   （本函数在 `run()` 打标题**之前**执行）。
    print('=' * 104)
    print('★★★ `--closed`：由 `windowB_closure.recommend()` **推出**的闭环配置')
    print('    n = floor(α_KM·(M_s−T_end)) = **%d**；q=%.4e K/s；steps=%d；'
          'T_start=T_1=%.2f K' % (rec['n_lath'], rec['q'], rec['steps'],
                                  rec['T_start']))
    print('    t_phys=%.0f nm（Shuai）⇒ 播种厚 %.0f = t_phys + 咬入 %.0f；末片再减 %.0f'
          % (t_phys, t_seed, rec['overlap_nm'], 0.5 * rec['overlap_nm']))
    for k, v, why in applied:
        print('    %-22s = %-16s %s'
              % (k, ('%.4g' % v) if isinstance(v, float) else v, why))
    print('=' * 104)
    if conflicts:
        for k, cur, v in conflicts:
            print('   ✗ 冲突：`%s` 你传了 %s，而闭式给 %s' % (k, cur, v))
        if not getattr(a, 'closed_force', False):
            raise SystemExit('✗ `--closed` 与你显式传的参数冲突 ⇒ 拒绝运行。'
                             '要去掉那些参数，或加 `--closed-force` 让闭式覆盖它们。')
        print('   ⚠ `--closed-force` 已给 ⇒ **闭式覆盖你显式传的值**（上面逐条列出）')
        for k, cur, v in conflicts:
            setattr(a, k, v)
    if abs(a.steps - rec['steps']) > 0:
        print('   ⚠ `--steps` = %d ≠ 闭式的 %d ⇒ **C-3 的有序性判据要按实际步数重算**'
              % (a.steps, rec['steps']))
    # ★ 机器可读的一行：`_bk_closedcheck.py` 用它核"一条命令 == 长命令行"。
    #   为什么不从上面那张人读的表里正则抽：那张表是给人看的，格式会变
    #   （本仓库已多次栽在"从格式不稳定的文本里抠数"上）。
    print('CLOSED_ARGS ' + json.dumps(
        dict({k: getattr(a, k) for k in targets},
             **{'N': a.N, 'alpha_km': a.alpha_km,
                'cool_ratio': a.cool_ratio, 'T_end': a.T_end,
                'gamma0': a.gamma0}),
        ensure_ascii=False, sort_keys=True))
    # γ_F1 是**借来的文献值**，不是闭式能推的 ⇒ 这里只提醒，不擅自改。
    if abs(a.gamma0 - CL.GAMMA_F1_MAIN) > 1e-9:
        print('   ⚠ `--gamma0` = %.3f，而闭环主情景是 **%.2f**'
              '（Murzinova 2017 的 975 °C 带 %s 内取整值）'
              % (a.gamma0, CL.GAMMA_F1_MAIN, CL.GAMMA_F1_BAND))
        print('     ⇒ 复现闭环主配置请显式加 `--gamma0 %.2f`（本条**不自动改**：'
              '它是文献选择，不是推导量）' % CL.GAMMA_F1_MAIN)
    a.nuc_law = 'athermal'


def _warn_archived_path(a):
    """★★★ R29（用户要求）：**"你正在跑没有速率律的归档路径"这条提示**。

    背景：`--nuc-law` 默认是 `cadence` —— **形核节奏由 `--eng-cadence` 规定**
    （「每 N 步插一根」），它是**纯人为节拍**，与温度、驱动力、材料无关。
    而 `BLOCK_RESULT.md §3.1` 那条"最简命令"里**没有** `--nuc-law` ⇒
    照着敲的人会拿到这个模型，却**看不出来它没有速率律**。

    ⚠ **为什么不是"改默认"**（用户问过）：
      `--nuc-law` 只管**一条规则**；闭环配置是**12 个参数**
      （`Δx`/板条尺寸/`γ0`/`β_h`/播种厚/`α_KM`/`T_end`/`laths`/`steps`…）。
      只改默认 ⇒ 得到「闭环的形核律 + 归档的几何与能量」这种**从未验证过的第三种配置**。
      实测估算：归档几何（`L=2400 nm`）+ athermal 律，`q≈4.6e6 K/s`、200 步只降到 ~725 K
      ⇒ `n(T)=1.6` ⇒ **跑完 200 步只有 1 根板条**，看起来像坏了。
      ⇒ 所以**不改默认，只加提示**（零破坏）。

    触发口径（**两边都要测**：该响的时候响、不该响的时候不响）：
      * 用户**显式**传了 `--nuc-law` 或 `--closed` ⇒ **不提示**（他知道自己在做什么）；
      * 否则且**确实会走形核**（`--grow-stack` / `--arm eng` / `--nuc-every > 0`）
        ⇒ **提示**；
      * 预摆算例（不生长、不形核）⇒ 不提示（那条路径没有这个问题）。
    """
    argv = sys.argv[1:]
    explicit = any(x == '--nuc-law' or x.startswith('--nuc-law=') for x in argv)
    explicit = explicit or any(x == '--closed' or x.startswith('--closed=')
                               for x in argv)
    explicit = explicit or getattr(a, 'closed', False)
    if explicit:
        return
    if not (bool(getattr(a, 'grow_stack', False)) or a.arm == 'eng'
            or int(getattr(a, 'nuc_every', 0)) > 0):
        return
    print('=' * 104)
    print('⚠⚠ **你正在跑归档路径：模型里没有形核速率律。**')
    print('   当前 `--nuc-law` = `cadence`（默认）⇒ 形核节奏由 `--eng-cadence %d` '
          '**人为规定**（"每 %d 步插一根"），' % (a.eng_cadence, a.eng_cadence))
    print('   它与温度、驱动力、材料无关。**这条路径的结论必须写成'
          '"在给定的形核节奏下"。**')
    print('   ★ 要用**物理闭环**模型（板条数 `n = floor(α_KM(M_s−T_end))`、'
          '逐根温度 `T_k = M_s − k/α_KM`）请加：')
    print('       --closed --gamma0 0.25 --steps 2853')
    print('     （见 `BLOCK_PARAM_CLOSURE.md`；"一条命令"与长命令行等价已由 '
          '`_bk_closedcheck.py` 核过：20 项 0 不一致）')
    print('   若你**有意**走归档路径，请显式写 `--nuc-law cadence` 以消除本提示。')
    print('=' * 104)


if __name__ == '__main__':
    raise SystemExit(main())
