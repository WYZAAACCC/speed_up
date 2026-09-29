# R30-AUDIT-S5 —— **落盘够不够「事后用新量具重算所有结论」？**

> 只读审计 + 一条补做的端到端验证。**本审计没有改动任何已有文件、没有改动引擎、
> 没有起仿真**。新增文件只有 `_r30_snapinv.py` / `_r30_dumpscan.py` / `_r30_show.py` /
> `_r30_findf3.py` / `_r30_remeasure.py` / `_r30_p0.py` / `_r30_cost.py` /
> `_r30_phiinv.py` / `_r30_posfloor.py` / `_r30_phibin.py` / `_r30_dumpcost.py` /
> `_r30_seedinv.py` / `_r30_ls.sh`（全部只读工具）。
>
> 审计人：子代理（R30-S5）｜2026-09-30 05:4x–06:0x CST
> 状态标记：【实测】= 本次跑出来的数；【推理】= 由实测推出；【未核实】= 没查。

---

## §0 一句话结论

**「重算 `series.csv` 里绝大多数列」是够的（实测 16 个量在 9 个快照步上相对差 ≤1.6e-6）；
但「重算所有结论」不够** —— 缺 **`phi`（亚胞界面几何）**、**`psi` 全字段（仅 `auto` 臂，
且归档里 0 个快照有它）**、以及 **`P0` 基准（⇒ `Δpos` 无法独立复算）**。
其中 `phi` 这一条正是 `BLOCK_DERIVATION.md:1116` 标为**必做**的 I-6：
**代码里开关已实现（`--phi-every`）但归档默认没开** ——
102 个带快照的算例里 **只有 16 个存了 `phi`，且全部是 N≤64 冒烟 / t=0 预摆**。
（逐对界面表 `f3_pairs` 反而**不是**缺口：它只吃标签，可 100% 离线重算，实测见 §3。）

---

## §1 落盘物清点（5 个代表算例）

复现命令（只读）：

```bash
bash /mnt/f/speed_up/pipeline/ca_pf_framework/_r30_ls.sh
```

| 算例 | N | Δx | 步数 | `series.csv` | `snap_*.npz` | 快照步 | 每快照大小 | 目录大小 |
|---|---|---|---|---|---|---|---|---|
| `_exp/_bk_closed/dry_cl1b` | 96 | 125 nm | 2853 | 30 行 × 30 列 (12.5 kB) | **4** | 0/1000/2000/2853 | **3.3–11.2 kB** | 5.9 MB |
| `_exp/_bk_eng/eng_eng12` | 96 | 62.5 nm | 200 | 21 行 × 29 列 (8.5 kB) | **5** | 每 50 步 | **3.3–4.2 kB** | 6.0 MB |
| `_exp/_bk_time/dry_nc3` | **32** | — | 60 | 3 行 × 31 列 (1.3 kB) | **2** | 0/60 | 2.1–2.2 kB | 256 kB |
| `_exp/e7_selfac`（R1 系列） | — | — | 175+ | 38 行 × **76** 列 (21.6 kB) | **7** | 每 25 步 | 9.0–12.2 kB | 212 kB |
| `_exp/_bk_block/dry_p3` | **192** | 62.5 nm | 200 | 21 行 | **5** | 每 50 步 | **10.9–12.2 kB** | 158 MB（含 164.7 MB 的 `seeds.npz`） |

【实测】`seeds.npz`（t=0 全量态）在 **66 个算例里个个都有**，key 恒为
`phi[ nv,N,N,N]:float32 + region[N,N,N]:int8 + n_hab/w_ax/a_ax + vmap_keys/vmap_vals + N/L/arm/laths`
（`_r30_seedinv.py`）。**这是唯一一处真正存了 `phi` 的地方**，且只有 t=0。

【实测】`_exp/` 总计 **2.5 GB (2527 MB)**，其中 `_bk_block` 一个目录 **2.03 GB (80%)**
—— 那 2 GB 几乎全是 `*/seeds.npz` 里的 t=0 `phi`（每个 N=192/7 场 **164.7 MB**）。
算例数 `series.csv` × **104**、`snap_*.npz` × **517**、`seeds.npz` × **66**。

### 产物 → 内容 → 采样率 → 够不够离线重算

| 产物 | 内容 | 采样率 | 够不够离线重算 |
|---|---|---|---|
| `series.csv` | 24–76 列量具读数（每 10 步一行） | **每 10 步** | 是**读数**不是**状态**。能重算结论里"引用读数"的部分；**不能**换口径重测原始量 |
| `snap_*.npz`（`_bk_exp` 系） | `region:int8` + `N/L/n_hab/w_ax/a_ax/arm/vmap_keys/vmap_vals` | **每 50–1000 步** | **能**重算 `nslab_n/nf3_col/nf3/f3_area/f3_area_stair/f3_pos_m/f3_pos_dx/f3_std_m/vols/ths/n_lath/w_lath/a_lath/nreg_used/Vt`（§3 实测）；**不能**重算任何需要 `phi` 的量 |
| `snap_*.npz`（`_r1_exp` 系） | `region:int8 + step + t + nhist(8×8 int32)` | 每 20–25 步 | 同上；多一个 `t`（`_bk_exp` 系**没有 `t`**）和法向直方图 |
| `snap_*.npz`（`_bk_smoke_f3`） | `phi + region + nv + plate + gamma + gap_nm` | 每 40 步 | **唯一存了 `phi` 的快照族**，但只有 **N=64 冒烟** |
| `seeds.npz` | **`phi`(全量) + `region` + 轴元数据** | **只有 t=0** | t=0 的亚胞几何完整；**中间态没有** |
| `meta.json` | 引擎/板条层/量具 sha256 + 全参数 + 臂定义 + θ/γ_RS 表 | 一次 | 好（能复现**配置**，不能复现**状态**） |
| `nuc_dbg.json` | 形核事件诊断计数 | 一次 | 好 |
| `closure.json` | 闭环推荐配置 | 一次 | 好 |
| `run.log` / `log.txt` / `pervar.csv` | 文本日志（R1 系才有） | 每步 | 中 |

---

## §2 快照内容审计（实际打开）

复现命令：

```bash
wsl.exe -e bash -lc 'cd /mnt/f/speed_up/pipeline/ca_pf_framework && \
  /root/miniconda3/envs/ml/bin/python -u _r30_snapinv.py _exp/_bk_eng/eng_eng12'
/root/miniconda3/envs/ml/bin/python -u _r30_dumpscan.py     # 全 _exp/ 普查
```

### 2.1 全库普查【实测，102 个算例 / 517 个快照】

`_r30_dumpscan.py` 的全局 key 计数（**出现过的 key → 有多少个「算例内 key 集合」带它**
—— `_r30_dumpscan.py` 按 `(算例, key 集合)` 去重计数，所以这些数**不是快照文件数**；
快照文件总数是 **517**）：

```
region 103 | step 103 | L 66 | N 66 | a_ax 66 | n_hab 66 | w_ax 66 | arm 57
vmap_keys 57 | vmap_vals 57 | t 37 | phi 16 | gamma 9 | gap_nm 9 | nv 9
plate 9 | norm_smooth 6 | nhist 5
```

**`phi` 只出现在 16 个算例里，全部是 `_bk_block/*`（单快照 t=0 或 N=192 预摆）与
`_bk_f3smoke/*`（N=64 冒烟）**。生产闭环族（`_bk_closed/*`、`_bk_eng/*`、`_bk_gs/*`、
`_bk_time/*`、`_bk_colchk/*`、`_bk_ctrl/*`、R1 的 `lath192_*/mid192_*/e7_*`）
**一个都没存 `phi`**（逐算例清单见 `_r30_dumpscan.py` 输出的
`cases_with_phi_in_snap`）。

### 2.2 逐个 key 核实（`eng_eng12` 5 个快照 key 完全一致）

| 问 | 答（n=5，`_exp/_bk_eng/eng_eng12`） | 证据 |
|---|---|---|
| `region`？ | ✅ `int8`, shape **(96,96,96)**, 裸 884 736 B，磁盘 3.3–4.2 kB（压缩比 **210–271×**） | `_r30_snapinv.py` |
| `region` 是 int8 吗？ | ✅ 是（103 个算例 key 集合里全部是 int8，无一例外） | `_r30_dumpscan.py` |
| `phi`？ | ❌ **不存** | 同上 |
| `psi`？ | ❌ **不存**（全库 517 个快照里 `psi` 出现 **0** 次）；且 `psi_mean` 列在本算例 **30/30 行 = nan**（ψ 只在 `arm=auto` 存在） | `_r30_dumpscan.py`、`_r30_csvrows.py` |
| `nhist`？ | ❌ **不存**（`nhist` 只在 R1 系 5 个算例里） | 同上 |
| `step`？ | ✅ `int64` 标量，`values: 0/50/100/150/200` | `_r30_snapinv.py` |
| `t`？ | ❌ **不存**（`_bk_exp.py:743-746` 的字典里没有 `t`；只有 `_r1_exp.py:819` 有） | `_bk_exp.py:743` |
| `meta`？ | ⚠ 部分：有 `N/L/n_hab/w_ax/a_ax/arm/vmap_keys/vmap_vals`；**没有 `t`、没有 `dx`、没有 `dt`、没有 `nv`**（`dx` 要从 `L/region.shape[0]` 反算）。`_bk_smoke_f3` 存的是 `nv` 而**不存 `vmap`** ⇒ 变体归属丢失 | `_bk_exp.py:743`、`_bk_smoke_f3.py:225` |

### 2.3 快照是稀疏还是全量？

**稀疏**，而且两级稀疏：

1. **时间稀疏**：`snap_every` 默认 100（`_bk_exp.py:882`），闭环驱动硬编码 **1000**
   （`_bk_closed.py:147`：`'--snap-every', '1000'`）。`dry_cl1b` 跑 **2853 步只有 4 个快照**；
   R1 系是每 20–25 步（`e7_selfac` 7 个 / 175 步）。
2. **内容稀疏**：`region` 本身是**完全量化**的（它由 `np.argmin(phi,axis=0)` 得到，
   `windowB_surface.py:1221-1227`），所以 `region` 快照压缩比高达 **200–650×**。
   `phi` 则相反 —— 它是**连续 SDF**（见 §2.4），压缩不动：N=96/7 场 **21.4 MB**、
   N=192/7 场 **164.7 MB**。

### 2.4 ★ 关键分裂：`region` 只给离散标签，界面**位置**的亚胞信息在 `phi` 里

**`phi` 是连续的有符号距离场，不是二值场**【实测，`_r30_phibin.py`】：

```
_exp/_bk_block/dry_t1/snap_00030.npz
   phi: shape=(7,96,96,96) dtype=float32  唯一值个数=2 471 880
   |phi| 落在 (1e-6, 0.999) 的占比 = 0.869923  ⇒ **连续 SDF**（含亚胞信息）
```

⇒ **`region` 的离散标签丢掉的是亚胞界面位置**：`region` 只告诉你"这个胞属于场 k"，
不告诉你 `φ_i(x) = φ_j(x)` 的零点落在胞内的哪一处。
（`region == argmax(phi)` 的占比实测 **0.000000** —— 因为 `region` 的权威定义是
**`argmin`**，见 `windowB_surface.py:1226`。这条本身也是个记账点：名字叫 "region"
但语义是 "argmin 场"，不是 "最大相场"。）

### 2.5 「哪些量算不出来、为什么」

| 量 | 只在 `region` 里够不够 | 为什么 |
|---|---|---|
| `nslab`（柱里板条数）、`nf3col`、`runs` | ✅ 够 | 纯标签拓扑（`_bk_measure.py:356-386`） |
| 逐场 `L/W/T/V`、`n_lath/w_lath/a_lath` | ✅ 够 | 标签掩膜的线性跨度 / 体素数（`_bk_measure.py:368-379`） |
| F3 面积（无偏 + 阶梯） | ✅ 够 | `_area_from_faces` 只吃标签相邻面（`_bk_measure.py:112-127, 388-407`） |
| `f3_pos_m` / 汇总 `Δpos` | ✅ **实测够**（见 §3；§2.6 量出与 `φ=0` 口径差 0.0002–0.031 Δx） | 但它是**特定的 `region` 口径**（`_bk_measure.py:408-415`：F3 胞的 `n*·x` **角点坐标均值**），**不是** `φ=0` 口径。本报告实测两者对"全场平均位置"一致；**不保证**对"单张界面的亚胞位置/粗糙度"也一致 |
| `Δpos` 的**基准 `P0`** | ❌ **不够** | `P0` 在**中间步**（`eng12` = step 30、`cl1b` = step 400）被定下（`_bk_exp.py:626-628`），**那个步没有快照** ⇒ 从快照只能反算 `f3_pos_m`，**不能**独立复算 `f3_pos_dx`【实测，§3.2】 |
| 界面**剖面 φ(ξ)**、法向、**曲率 κ** | ❌ **不够** | 需要 `phi` 的梯度/Hessian；`region` 只是它的 argmin。P-1b 判据要"F3 上实测 κ 分布"（`BLOCK_DERIVATION.md:993`） |
| 逐对界面表（`f3_pairs` / `f3_pairs_pos`） | ⚠ 逐对**面积**可从 `region` 重算；逐对**位置**也可（`_pairpos_str` 的算法只吃标签）。但 `_bk_smoke_f3` 族**丢 `vmap`** ⇒ 变体归属没了 | `_bk_exp.py:643-688` |
| `psi_mean`、薄膜宽度/覆盖 | ❌ **不够（全库 0 个快照有 `psi`）** | `_bk_exp.py:719-722` 直接读 `g.psi`，**从不落盘**；列名在 `_bk_exp.py:74` |
| `ncomp_*` / `ncompbig_*` / `box_touch` | ✅ 够 | 纯 `region` + `scipy.ndimage.label`（`_bk_measure.py:54-109`） |
| `nhist`（界面法向直方图） | ❌ 只在 R1 系 5 个算例有 | `_r1_exp.py:795-817` |
| `E_el`（弹性能） | ❌ **全库无** | `BLOCK_SELFAC.md:370` 已登记"⛔ 无落盘" |

### 2.6 ★★ 量化「`region` 口径 vs `phi` 口径」的实际差

复现命令：

```bash
/root/miniconda3/envs/ml/bin/python -u _r30_posfloor.py \
    _exp/_bk_f3smoke/main _exp/_bk_f3smoke/ns0 _exp/_bk_block/dry_t1
```

【实测】同时有 `region` 与 `phi` 的 13 个快照上，两种口径的界面位置差（单位 Δx）：

```
   |Δ|=0.7970 Δx   _bk_f3smoke/main/snap_00120.npz      ← 异常（见下）
   |Δ|=0.0315 Δx   _bk_block/dry_t1/snap_00030.npz
   |Δ|=0.0283 Δx   _bk_f3smoke/main/snap_00080.npz
   |Δ|=0.0166 Δx   _bk_f3smoke/ns0/snap_00060.npz
   |Δ|=0.0119 Δx   _bk_f3smoke/ns0/snap_00100.npz
   |Δ|=0.0105 Δx   _bk_f3smoke/main/snap_00040.npz
   |Δ|=0.0029 Δx   _bk_f3smoke/ns0/snap_00120.npz
   |Δ|=0.0000 Δx   _bk_f3smoke/ns0/snap_00000.npz
   n=10  中位 0.0112 Δx  max 0.7970 Δx
```

⇒ **对"全场平均位置"这类汇总量，`region` 口径的经验量化误差 ≈ 0.01–0.03 Δx**
（远小于 V-3g 门槛 **0.12 Δx**），因为界面胞有上千个、逐胞的 ±Δx/2 量化误差取平均后互相抵消
【推理】。唯一 0.797 Δx 的离群点是 `f3smoke/main` 的 step 120 —— 那里界面变薄，
`φ` 梯度口径本身退化成 NaN/多界面混杂（`ns0` 的 step 200/300/400 直接返回 NaN），
**是 φ 口径坏了、不是 region 口径坏了**。

---

## §3 ★★★ 端到端重测对照（最重要的一条）

### 3.1 怎么做的

挑了 **两个已经跑完、且快照步与 CSV 步对齐**的算例：

* `_exp/_bk_eng/eng_eng12`（N=96，`snap_every=50`、`every=10`、`pair_every=10`
  ⇒ 快照步 **0/50/100/150/200 都在 CSV 里**）
* `_exp/_bk_closed/dry_cl1b`（N=96，快照步 **0/1000/2000/2853**，CSV 每 100 步一行）

**只吃落盘快照**，用 `_bk_measure.measure_state` 重算，口径与 `_bk_exp.py:690-726`
逐行对齐（`_r30_remeasure.py` 的 docstring 列了每一条对应关系）。

```bash
/root/miniconda3/envs/ml/bin/python -u _r30_remeasure.py _exp/_bk_eng/eng_eng12
/root/miniconda3/envs/ml/bin/python -u _r30_remeasure.py _exp/_bk_closed/dry_cl1b
```

### 3.2 ⚠ 第一版有一个**必须记账的坑：`P0` 对不上**

第一版直接用"快照里第一个有限 `f3_pos_n`"当 `P0`（照抄 `_bk_exp.py:626-628` 的语义），
结果 `f3_pos_dx` 差 **1.4e-3（`eng12`）/ 1.31（`cl1b`！）**。

**真因【实测】**：`P0` 是在**运行中的第 30（`eng12`）/ 第 400（`cl1b`）步**
第一次出现 F3 时被钉下的，**那一步没有快照**。
把 CSV 逐行反解 `P0 = pm − f3_pos_dx·dx`（`_r30_p0.py`）得到：

```
_exp/_bk_eng/eng_eng12   （19 行反解出的 P0 逐位相同）
    step f3_pos_m(CSV)          f3_pos_dx(CSV)         P0 = pm - d·dx
      30 -2.24124689364e-06     0                      -2.24124689364e-06   ← P0 定在这里
     200 -2.65634765487e-06     -6.64161217961         -2.24124689364e-06
_exp/_bk_closed/dry_cl1b
     400 -4.44007366806e-06     0                      -4.44007366806e-06   ← P0 定在这里
```

⇒ **这不是"口径不同"，是"数据不够"**：`f3_pos_dx` 的原点落在两次快照之间。
（`f3_pos_m` 本身**可以**逐位重算，见下。）

### 3.3 结果：修正 `P0` 后**全部对到 CSV 的 6 位有效数字**

`eng_eng12`（5 个步 × 25 个量，`--p0 -2.24124689364e-06`）：

| step | `nslab_n` | `nf3_col` | `nf3(f3_faces)` | `f3_area_m2` | `f3_area_stair` | `f3_pos_m` | `f3_std_m` | `f3_pos_dx` |
|---|---|---|---|---|---|---|---|---|
| 0 | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | nan | nan | — |
| 50 | 2 / 2 | 1 / 1 | 990 / 990 | 1.550321444e-12 / 同 | 同 | **0.000e+00** | **0.000e+00** | **8.81e-09** |
| 100 | 4 / 4 | 3 / 3 | 1982 / 1982 | 4.636138478e-12 / 同 | 同 | **0.000e+00** | **0.000e+00** | **1.25e-11** |
| 150 | 6 / 6 | 5 / 5 | 3278 / 3278 | 7.687070021e-12 / 同 | 同 | **0.000e+00** | **0.000e+00** | **5.39e-12** |
| 200 | 6 / 6 | 5 / 5 | 3279 / 3279 | 7.699348554e-12 / 同 | 同 | **0.000e+00** | **0.000e+00** | **5.44e-12** |

（格式：CSV / 离线重算；`0.000e+00` = 相对差 0）

`dry_cl1b`（`--p0 -4.44007366806e-06`）：

| step | `nslab_n` | `nf3_col` | `f3_area_m2` | `f3_std_m` | `f3_pos_dx` |
|---|---|---|---|---|---|
| 1000 | 3 / 3 | 2 / 2 | 1.037181082e-11 / 同 | **0.000e+00** | **1.62e-11** |
| 2000 | 5 / 5 | 4 / 4 | 6.082315511e-12 / 同 | **0.000e+00** | **2.13e-11** |
| 2853 | 6 / 6 | 5 / 5 | 1.035687226e-11 / 同 | **0.000e+00** | **8.09e-12** |

**全量相对差的最大值（两个算例合并）**：

```
=== 相对差最大的 10 条（eng_eng12）===
   th_1(nm)   step=0    rel=1.5830e-06      ← 全部 ≤1.6e-6
   th_6(nm)   step=200  rel=1.5745e-06
   vol_1      step=100  rel=1.5502e-06
   ...
=== 相对差最大的 6 条（dry_cl1b）===
   vol_1  step=0     rel=7.4592e-07
   ...
```

### 3.4 差异的归因【实测 + 推理】

| 差异 | 量级 | 归因 |
|---|---|---|
| `vol_k` / `th_k` / `n_lath/w_lath/a_lath` | **rel ≤ 1.6e-6** | **纯粹是 CSV 的 `%.6g` 截断**（6 位有效数字 ⇒ 理论舍入上限 5e-7，实测 1.6e-6 是同一量级）【推理 + 实测一致】 |
| `f3_area_m2` / `f3_area_stair` / `nf3` / `f3_pos_m` / `f3_std_m` | **rel = 0.000e+00**（逐位相同） | 这些列 `_bk_exp.py` 不做 `%.6g`，写的是 `repr` 全精度 |
| `f3_pos_dx` | 修正 `P0` 后 5e-12 ~ 2e-11 | 同上；**未修正 `P0` 时 1.4e-3 ~ 1.31** |
| 第一版把 `n_lath/w_lath/a_lath` 差出 1e9 | — | **本审计自己的单位错**（那三列是**米**，不是 nm；`ths` 列才是 nm）。见 `_bk_exp.py:702`（`*1e9`）vs `_bk_exp.py:714-716`（无 `*1e9`）。已修 |

⇒ **结论：`region` 落盘足以在离线侧逐位复现 CSV 的全部几何量具读数；
对不上的只有两处，一处是我们自己的单位错，一处是真·数据缺口（`P0`）。**
**没有发现"量具口径不同导致对不上"的情况。**

---

## §4 缺口清单

### 4.1 ★ I-6 到底实现了没有？—— **部分实现：开关在，生产没开**

`BLOCK_DERIVATION.md:1116`：

```
| I-6 | 全量状态落盘（`region` 图 + 带内稀疏 φ）到 F 盘 | **必做**（用户明确要求） |
```

**file:line 证据链**：

| 项 | 位置 | 事实 |
|---|---|---|
| 开关存在 | `_bk_exp.py:883-884` | `ap.add_argument('--phi-every', type=int, default=0, help='存 phi 的间隔；0 = 与 snap-every 相同（region 每次都存）')` |
| 落盘实现 | `_bk_exp.py:734-749` | `if a.phi_every > 0 and (it % a.phi_every == 0 or it == a.steps): d['phi'] = g.phi.astype(np.float32)` → `np.savez_compressed(..., **d)` |
| **`region` 无条件存** | `_bk_exp.py:743` | `d = dict(region=reg, step=it, n_hab=…, w_ax=…, a_ax=…, N=…, L=…, arm=…, vmap_keys=…, vmap_vals=…)` |
| 默认 0 | `_bk_exp.py:883` | ⇒ **默认不存 phi** |
| 闭环驱动连 `--phi-every` 都不传 | `_bk_closed.py:146-147` | `'--steps', str(steps), '--every', str(a.every), '--snap-every', '1000'` —— **只有这三项**；`--phi-every` 缺省 ⇒ 0 |
| 实测后果 | `eng_eng12/meta.json:78` | `"phi_every": 0` |
| 「必做」被判为未做 | `BLOCK_SELFAC.md:386-391` | J-8 行 + **「⚠ J-8 是用户明确要求、而当前没有做到的… `dry_cl1b` 的 `snap_*.npz` 只含 `region`（int8）+ 轴元数据（实测，`_r30_peeksnap.py`），不含 `phi` ⇒ 界面位置、`f3_pos`、亚胞厚度、`ψ` 都无法离线重算 ⇒ "量具有 bug 也能事后重测"这条要求目前不成立（必须重跑才能重测）。**」 |
| **另有反向说法（★需裁定）** | `BLOCK_STATUS.md:322-330` | 「★★ "量具可事后重测"已**实测验证**… `python3 _bk_measure.py --npz _exp/_bk_block/wet_p2/snap_00000.npz` → … **与运行中同一状态的在线读数逐位一致**」 |

**本审计的裁定**【实测】：两句**都对，但说的是不同的量**。
`BLOCK_STATUS.md` 的验证用的是 `wet_p2`——**它是 `phi_every>0` 的那 16 个算例之一**
（`_bk_block` 族），所以"逐位一致"成立；但它**不是生产闭环族的代表**。
生产族（`_bk_closed` / `_bk_eng` / R1 的 `l192/m192/e7`）实测 **`phi` 一个都没存**。
⇒ **I-6 应判「部分实现」：代码路径可用、归档默认未开、`_bk_closed.py` 未接。**

另外，I-6 原文里的「**带内稀疏** φ」也**没有实现**：`_bk_exp.py:748` 存的是
`g.phi`（**整场 nv×N³**），不是带内稀疏。这一点在磁盘/时间上是**唯一真正的成本项**
（见 §5）。

### 4.2 「若现在把量具改对，想重算结论，会缺哪些数据」

| # | 缺什么 | 影响哪些结论（file:line 证据） | 补上它的代价【实测】 |
|---|---|---|---|
| **G-1** | **`phi`（亚胞 SDF）在 102 个带快照的算例里只有 16 个存了**（且全是 N≤64 冒烟 / t=0 预摆） | ① **界面剖面 / 法向 / κ 分布** ⇒ P-1b「由 F3 上实测 κ 预测全程位移」（`BLOCK_DERIVATION.md:993`）；② 「亚胞厚度」（`BLOCK_SELFAC.md:390`）；③ 任何"越过标签台阶"的判据 | **磁盘**：N=192/7 场 **+164.7 MB/快照**，N=96/7 场 **+21.4 MB/快照**。<br>**耗时**：N=192 **+10.48 s/次**、N=96 **+1.35 s/次**（本机 `/mnt/f`，`_r30_dumpcost.py`）。<br>**内存**：`g.phi` 本来就常驻（198 MB @192），`astype(float32)` 会**多一份 198 MB 瞬时**。<br>**占算例总时**：`dry_p3` 200 步 ≈ 11880 s ⇒ 5 次快照 +52 s = **+0.44%**（可忽略） |
| **G-2** | **`psi`（面带）从未落盘** | `psi_mean` 列（`_bk_exp.py:74` 定义、`_bk_exp.py:719-722` 求值）；D-1「干/湿低角晶界」判决（`BLOCK_DERIVATION.md:1127`）、`auto` 臂退湿判据 A-3。**实测**：全 `_exp/` **104 个 CSV 里只有 `_bk_ctrl/auto_ctrl` 一个算例的 `psi_mean` 是有限值**（12/13 行，0.98→0.09）；主生产臂 `dry_cl1b` **30/30 行全是 `nan`**（`g.psi is None`，ψ 只在 `arm=auto` 时由 `_bk_exp.py:282-286` 的 `g.film` 建出来 ⇒ 只有 `auto` 臂付这份钱） | 同 G-1 的量级：**若只对 `auto` 臂存 ψ**，一算例只多一个 `N³` float32 场（N=192 ⇒ +28.3 MB/快照）。<br>★ 注意：**`auto` 臂的结论现在只能重跑** —— `auto_ctrl` 是唯一的 `auto` 算例，而它的 ψ 时间序列（0.98→0.09 退湿）**只在 CSV 里，没有原始场** |
| **G-3** | **`P0`（Δpos 基准）没落盘** | `f3_pos_dx` **无法从快照独立复算**（§3.2 实测：`cl1b` 差 **1.31**、`eng12` 差 1.4e-3）。影响 **V-3g**（`BLOCK_STATUS.md:303`，门槛 **0.12 Δx**）与 **V-6**。⚠ `f3_pairs_pos` **不受影响**（`_bk_exp.py:686` 报的是绝对位置，不减 `P0`） | **≈0**：`P0` 是个**标量**。直接写进 `meta.json` / 快照即可（或在 `series.csv` 增设一个 `f3_pos_p0_m` 列） |
| **G-4** | **快照的时间分辨率**（`snap_every=50/100/1000` vs CSV 的 `every=10`） | 任何"逐点差分"的判据（V-3g 的 `max|ΔΔpos|`）：CSV 是 10 步分辨率，快照只有 50–1000 步 ⇒ **离线重算的时间分辨率低 5–100 倍** | 纯磁盘：把 `snap_every` 降到 10 ⇒ 快照数 ×5。region-only 时 **×10 也只有 0.06 MB/算例**（基本免费）；**但若要带 `phi` 就 ×10**（N=192 一算例 825 MB→4 GB） |
| **G-5** | **`nhist`（界面法向直方图）只在 5 个 R1 算例** | A-1「`M̄` 在各方向的有效值」（`_r1_exp.py:797-817`）；B-18 的"为何只劣化 w–n* 一对" | **512 B/快照**（8×8 int32），代价≈0。但它**需要 `phi`**（要算梯度） |
| **G-6** | **`vmap` 在 `_bk_smoke_f3` 族快照里丢失**（`_bk_smoke_f3.py:225` 只存 `nv`，不存 `vmap_keys`/`vmap_vals`） | 该族的 F3 面**无法离线独立复算**：`vmap` 决定"哪些场对算 F3"。<br>**实测** `_bk_measure.py --npz _exp/_bk_f3smoke/main/snap_00000.npz` 走 `_bk_measure.py:673-675` 的 fallback（全部场同一变体）⇒ `f3_faces=600 f3_area=1.4167909e-12 nslab_n=2 nf3_col=1`；**与 CSV step 0 逐位相同**（`nf3=590` 是**另一口径**：那是运行中的 `_bk_smoke_f3.py` 自己数的，不是 `f3_faces`）⇒ **数值对上了，但这不是独立验证** —— 因为"vmap 恰好全同"与"vmap 其实不全同、而 fallback 猜错了"**在落盘里无法区分**【实测 + 推理】 | **几十字节**（`vmap_keys`/`vmap_vals`）。`_bk_exp.py:745-746` 已经存了，`_bk_smoke_f3.py` 没存 |
| **G-7** | **`t` 在 `_bk_exp` 系快照里没有** | 用快照做"时间 vs 量"的图 / 速率回归（R14「长窗平均」、R20「全样本线性回归」）要回到 CSV | **8 B**。`_r1_exp.py:819` 已经存了，`_bk_exp.py:743` 没存 |
| **G-8** | **`E_el` / `r_obs` / `f_i` 从未落盘** | J-2/J-3（`BLOCK_SELFAC.md:380-381`）：「块表量具」「`E_el` 时间序列」 | 设计未定；`E_el` 单次在 N=192 上是**几十秒量级**【未核实】 |

### 4.3 「带内稀疏 φ」值不值得做？—— 建议**不做，直接全量存**

【实测】`phi` 的**真实**压缩比只有 **1.2×**（N=96/7 场：裸 24.8 MB → 落盘 21.4 MB），
因为它是连续 SDF，`savez_compressed` 的 DEFLATE 拿它没办法：

```
N=96  nv=7  | region-only  0.00 MB 0.01 s | region+phi 21.44 MB 1.35 s
N=192 nv=7  | region-only  0.01 MB 0.03 s | region+phi 164.73 MB 10.48 s
N=64  nv=3  | region-only  0.00 MB 0.00 s | region+phi  2.77 MB 0.20 s
```

⇒ 「带内稀疏」的收益来自**只存界面附近的胞**。本项目实测
`|φ_K| ≤ 1.5Δx` 的带内胞占比在 N=192 上只有 **0.023%**（`R1_PROBLEM_LEDGER.md:45`）
⇒ 稀疏存能把 164.7 MB 降到 **≈40 kB**。
**但**：稀疏化会让快照**不再自描述**（需要额外索引表），而且 §5 的估算显示
全量存 N=192 生产盒一算例只有 **0.83 GB** —— **在 612 GB 空闲面前不值得引入稀疏格式的复杂度**。
（若真要省，第一刀应该砍 `snap_every`，不是砍带。）

---

## §5 磁盘与水印

### 5.1 现状【实测】

```
du -sh /mnt/f/speed_up/pipeline/ca_pf_framework/_exp      →  2.5G
du -sm _exp/*  (top)  _bk_block 2030 · _bk_eng 113 · _bk_f3smoke 88
                      _bk_ctrl 88 · _bk_closed 70 · _bk_gs 68 · _bk_time 25
df -h /mnt/f   →  Filesystem F:\  1.9T  1.3T  612G  68%  /mnt/f
df -B1 /mnt/f  →  2000363188224  1344242139136  656121049088  (612 GiB 空闲)
```

* `_exp/` = **2.5 GB** —— 只占 F 盘已用空间的 **0.19%**。
* **单个算例**：
  * region-only（现状）≈ **6 MB**（`cl1b` 5.9 MB / `eng12` 6.0 MB），其中
    **`seeds.npz` 占 6.0 MB / 164.7 MB（t=0 的 φ）**，`snap_*.npz` 只占 3–12 kB。
  * **`_bk_block` 族的 2 GB 全在 `seeds.npz` 的 t=0 φ 上**（N=192/7 场 164.7 MB × 12 个算例）。

### 5.2 估算：`N=192`、几千步

单位成本【实测，`_r30_dumpcost.py`】：

| 项 | N=192 nv=7 | N=96 nv=7 |
|---|---|---|
| 单个 `region`-only 快照 | **10.9–12.2 kB** | 3.3–11.2 kB |
| 单个 `region`+`phi` 快照 | **164.7 MB** | 21.4 MB |
| 单次写盘耗时 | **10.48 s** | 1.35 s |
| `seeds.npz`（t=0 φ） | **164.7 MB** | 21.4 MB |

**场景 A —— `BLOCK_DERIVATION.md:1100` 定下的阶段 3 配置（N=192、Δx=62.5 nm、200 步）**：

| 采样率 | 快照数 | region-only | **+φ** |
|---|---|---|---|
| `snap_every=50`（现 `dry_p3`/`eng12`） | 5 | 60 kB | **0.82 GB / 算例** |
| `snap_every=10`（与 CSV 同分辨率） | 21 | 250 kB | **3.46 GB / 算例** |

**场景 B —— N=96 闭环族（`cl1b` 口径：2853 步）**：

| 采样率 | 快照数 | region-only | **+φ** |
|---|---|---|---|
| `snap_every=1000`（现 `_bk_closed.py:147`） | 4 | 45 kB | **64 MB / 算例** |
| `snap_every=50`（`eng12` 口径） | 58 | 0.6 MB | **1.24 GB / 算例** |
| `snap_every=10`（与 CSV 同分辨率） | 286 | 3.2 MB | **6.1 GB / 算例** |

**若真跑"几千步的 N=192"**（用户假设的最坏情形）【推理，按 N=192 + `snap_every=50` 外推】：

```
3000 步 / 50 = 61 个快照
   region-only :  61 × 11 kB      ≈     0.7 MB   + seeds 165 MB  ≈  0.17 GB
   + phi       :  61 × 164.7 MB   ≈    10.0 GB   + seeds 165 MB  ≈ 10.2 GB / 算例
```

⇒ **结论**：
1. **现状（region-only）的磁盘占用可以忽略**（每算例 6–170 MB）。
2. **开 `phi` 全量后**，单算例在 N=192 上 **0.82 GB（200 步）/ 10.2 GB（3000 步）**。
   F 盘 **612 GB** 空闲 ⇒ 200 步的算例可存 **~700 个**，3000 步的可存 **~60 个**。
3. **真正的门槛不是磁盘，是时间**：N=192 每个快照 **+10.5 s**。若把 `snap_every`
   降到 10（与 CSV 同分辨率），**每个算例光落盘就 +220 s（200 步）/ +3.3 h（3000 步）**。
   ⇒ **建议：`phi` 只在"判决步"存**（例如 `--phi-every` = `snap_every`，
   即每个 region 快照配一个 φ），并把 `snap_every` 保持在 50 而不是降到 10。
4. **`seeds.npz` 已经在存 t=0 的 164.7 MB φ** ⇒ 开 φ 落盘**不引入新的量级**，
   只是把"只存 t=0"变成"每个快照都存"。

---

## §6 未核实 / 需要裁定

1. **【未核实】** 本报告没有核 `_r1_exp.py` 那条快照路径在**实际归档**里的
   `nhist` 内容是否可用（只核了 key 存在与 shape 8×8 int32）。
2. **【未核实】** N=192、3000 步的**单步耗时**是从 `dry_p3` 的 59 s/步（N=192/62.5 nm）
   与 `T_RESULTS_T1_T5.md:2636` 的 14.7 s/步（N=192/50 nm**两种不同盒子**）推的，
   没有单独测。§5.2 的耗时估算**不依赖**它（只依赖每次快照的 10.48 s 实测值）。
3. **【需裁定】** `BLOCK_STATUS.md:322-330` 的「"量具可事后重测"已实测验证」
   与 `BLOCK_SELFAC.md:388-391` 的「目前不成立」**互相矛盾**。
   本审计的裁定是**两者都对、说的是不同算例**（前者用 `wet_p2`，是带 φ 的 16 个之一），
   但**文档层面必须改成按算例族限定**，否则下一轮会再踩一次。
4. **【推理，未实测】** §2.6 的「region 口径量化误差 ≈0.01–0.03 Δx」是在
   **N=64 冒烟 + N=96 预摆**上量的（13 个快照）。N=192 生产盒、
   长轨迹（界面显著粗糙、多个 F3 面同时在）上**可能更大**，没有数据。

---

## §7 复现命令汇总

```bash
# 环境（全部在 WSL 里）
cd /mnt/f/speed_up/pipeline/ca_pf_framework
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python

bash _r30_ls.sh                                   # §1 落盘物清点
$PY -u _r30_dumpscan.py                           # §2.1 全库 key 普查（→ /tmp/r30_dumpscan.json）
$PY -u _r30_show.py                               # §2.2 代表算例细节
$PY -u _r30_snapinv.py _exp/_bk_eng/eng_eng12     # §2.2 逐个 key/shape/dtype
$PY -u _r30_phibin.py _exp/_bk_block/dry_t1       # §2.4 phi 是连续 SDF 还是二值
$PY -u _r30_posfloor.py _exp/_bk_f3smoke/main \
       _exp/_bk_f3smoke/ns0 _exp/_bk_block/dry_t1  # §2.6 region 口径 vs phi 口径
$PY -u _r30_p0.py _exp/_bk_eng/eng_eng12          # §3.2 反解 P0
$PY -u _r30_remeasure.py _exp/_bk_eng/eng_eng12 --p0 -2.24124689364e-06     # §3.3
$PY -u _r30_remeasure.py _exp/_bk_closed/dry_cl1b --p0 -4.44007366806e-06   # §3.3
$PY -u _r30_dumpcost.py                           # §4.3 / §5.2 落盘代价
$PY -u _r30_seedinv.py                            # §1 seeds.npz 清了什么
$PY -u _r30_psicol.py                             # §4.2 G-2 哪些算例的 ψ 是活的
$PY -u _r30_csvrows.py _exp/_bk_closed/dry_cl1b/series.csv \
       step,psi_mean,cfl_used,nf3,f3_pos_dx        # 逐行列核对（本次改掉一个列错位）
du -sh _exp; df -h /mnt/f                         # §5.1
```

---

## §8 三条最硬的证据

1. **`eng_eng12` 的 16 个几何量在 5 个快照步上与 CSV 逐位/1.6e-6 内一致**
   （`nslab_n`、`nf3_col`、`nf3`、`f3_area_m2`、`f3_area_stair`、`f3_pos_m`、`f3_std_m`
   相对差 **0.000e+00**；`vol_k`/`th_k` ≤ **1.6e-6** = CSV 的 `%.6g` 地板）。
   **修正 `P0` 后 `f3_pos_dx` 也从 1.31 的假差掉到 5e-12。**
2. **`phi` 是连续 SDF（`dry_t1` 单快照 190 万–247 万个唯一值，`|φ|∈(1e-6,0.999)` 占 87%），
   而 102 个带快照的生产算例里只有 16 个存了 `phi`**（全库 517 个快照），
   且那 16 个全在 `_bk_block`（t=0 预摆、单快照）/ `_bk_f3smoke`（N=64 冒烟）。
   `_bk_exp.py:883` 的默认是 `0`，`_bk_closed.py:147` 连参数都不传。
   ⇒ **`BLOCK_DERIVATION.md:1116` 的 I-6 判「部分实现」**。
3. **落盘代价实测：N=192/7 场 `region`+`phi` = 164.7 MB + 10.48 s/次**；
   N=192、200 步、`snap_every=50` ⇒ **0.82 GB/算例**，只占算例总机时 **+0.44%**。
   F 盘空闲 **612 GB** ⇒ 磁盘不是瓶颈。
