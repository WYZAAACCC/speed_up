# R617 —— t10B9 停机根因：fresh 通道用尽后位点表死锁（已定性）

日期：2026-10-05（第 11 轮）
纪律：每条结论标注**证据层级**（生效值 / 代码 / 运行期独有串）。

---

## 0. 结论（先给判据，再给证据）

**②-6「`_Bpar` 门 + F1 死锁」判为【真问题】，但形态与我此前的叙述不同。**

| 项 | 结论 |
|---|---|
| 是不是真问题 | **是**（有运行期独有串 + 代码逐行） |
| 表现 | **不是**"块数永远=1"（旧注释 `:2794` 的说法）；实际是 **B=9 块全部建齐后，卡在"往块里补板条"上，步进永不推进** |
| 根因 | `n_fresh` 恒 0 时，引擎的**位点表重抽（唯一解卡机制）不运行**，过期的、"放不下"的位点永久堵在队首 |
| 触发条件 | `nuc_block_parallel=1` 且 `fresh` 事件数达到 `nuc_block_target` |

---

## 1. 生效值（**硬步骤 A**：来自算例自己的 `meta.json` / `exp_args`，不是 `.sh`、不是 argparse 默认）

`dry_t10B9/meta.json → exp_args`（118 键）：

| 参数 | **生效值** | 此前我以为 | 备注 |
|---|---|---|---|
| `nuc_init` | **6** | 0 | `_t5_short.py:99` 在未传 `--no-nucleation` 时**硬编码** `['--grow-stack','--nuc-init','6']` |
| `nuc_block_parallel` | **1** | 「从未生效」 | `:145` 透传 |
| `nuc_block_target` | **9** | 9 ✓ | `:100 --nuc-block-target a.B` |
| `nuc_sites_refill` | **1** | 1 ✓ | `:101` 硬编码 |
| `nuc_supercrit` | **1** | 1 ✓ | `:101` 硬编码 |
| `nuc_max_per_step` | 1 | — | |
| `nuc_law` | `athermal` | — | |
| `nuc_shape` | `ellipsoid` | — | |
| **`qs_clock`** | **1** | 曾按默认 0 推 | `:102` 硬编码 `--qs-clock 1` ⇒ **准静态钟是开着的** |
| **`burst_km`** | **1** | — | ⇒ 下面 `_rej_cap = 8` |
| `therm_hist` | `linear` | — | KM.linear_cool 占位 |
| `cool_rate` | 2 352 400 K/s | — | = 用户给的 `q` |
| `T_end` / `alpha_km` | 298.0 / 0.041739 | — | `n(T_end)=23` |

⚠ **两个"块数"是不同的量，此前被我混为一谈（已撤）**：
- `vmap` = **手写的 10 组 × 22 场**（变体分组），来自 `--laths`；
- banner 的 **`B=9`** = `nuc_block_target`。
两者数值不同、语义不同，不可互推。

---

## 2. 代码路径（`_bk_exp.py`）

```
:2625  _Bt = nuc_block_target                      # = 9
:2646  _n_blk = floor(alpha_km_n_lath(Tnow, α))    # 每块根数，本档 = 23
:2648  _tgt = min(_Bt * _n_blk, nv)                # = min(207, 220) -> 逐档增长
:2675  _rej_cap = 8 if burst_km else 1e9           # burst_km=1 ⇒ 8
:2693  _tgt_try = g._burst_tgt_try                 # 本档是否已补投过
:2694  _do_try = (_tgt > _tgt_try) if burst      else True
:2700  while _do_try and n_ath_tgt < _tgt and n_ath_tgt < nv and _rej < _rej_cap:
:2745      _Bpar2 = nuc_block_parallel             # = 1
:2746      if _Bpar2 and _Bt > 0 and nuc_init > 0: # 三个条件全真 ⇒ 进入
:2747          _fresh_now = (n_fresh_ok < int(_Bt))
:2802      if _nf > 0 and str(_ev[0][1]) == 'fresh':
:2803          n_fresh_ok += 1                    # 只认真 fresh 事件（s294 已修）
```

**`_fresh_now` 在 `n_fresh_ok` 达到 9 后永久为假** ⇒ `n_fresh` 恒 0。

## 3. 引擎侧（`windowB_surface.py`）—— 解卡机制被 `n_fresh > 0` 门控

```
:1916  def nucleate(self, ed, R_nuc=None, t_nuc=None, n_fresh=0, n_stack=0,
                     f_now=0.0, drive_min=None, df=0.0)
:2011  if sites_refill and n_fresh > 0 and ('sites' in c):     # ← 补位点（append）
:2260  if (not _any_ok) and sites_refill and sites:            # ← 重抽整张位点表（解卡）
```

`:2245-2249` 自己写下了这条卡死的**精确形态**（原文）：

> 事件数 = `[1, 0, 0, 0, 0, 0, 0, 0]`，**池子剩下 1 个一直不动**
> ⇒ **池子根本没被用尽**，而是**被一个"放不下"的位点卡死**：
> 那个位点在几何上永远不合格（落在已转变区里），
> 而 `sites.pop(i)` 只在**成功**时执行（`if _any_ok`）
> ⇒ 它**永远留在队里、每次都被重试、每次都失败**。

（同一现象另见 `R481_NUC_SITES.md`。）

---

## 4. 运行期独有串（**硬步骤 D**：这是"真的发生了"的证据）

`_w2_t5_short_t10B9.log` 末行（`◆ s295 形核分诊（引擎 dbg）`）：

```
att=184  attach_ok=31  c_shift_max_dx=27.48  cov=319  edge_gap_min_dx=0.0
empty=387  end_pref=60  exc=0  forced_reinit=0
fresh_cand=9  n_events=72  nfsv_ok=71  nocand=0  ok=63  oob=0
sc_last_df=1.2273e+08  sc_last_ed=-2.107e+08  sc_last_fcrit=1.6e+06
sc_pass=9  sc_try=9  sites_refilled=7  t_last_used=2.8125e-07
```

逐项读法：

| 量 | 值 | 含义（判据） |
|---|---|---|
| `sc_try` / `sc_pass` | 9 / 9 | 超临界探针**全部通过** ⇒ **不是探针挡的** |
| **`fresh_cand`** | **9** | 引擎**总共只被要求过 9 次 fresh** ⇒ 与 `_Bt=9` 精确吻合 ⇒ **门控确实生效** |
| `n_events` / `ok` | 72 / 63 | 真的成了 72 个事件（与形核行「累计 fresh=9 stack=32」+ attach 相符） |
| `empty` | **387** | 盒子里**还有 387 个空格** ⇒ **不是盒满** |
| `cov` | 319 | 被覆盖/重叠挡掉的候选 |
| **`sites_refilled`** | **7** | **:2011 那条路跑过 7 次**（当时 `n_fresh>0`） |
| **`sites_resampled`** | **字段不存在** | **:2260 那条解卡路一次都没跑** ⇒ 正是 `n_fresh` 恒 0 所致 |

日志尾部另证（逐行）：
- `块内第 9 根 / 共 9 块`（第 9 块的最后一根）；
- `累计 fresh=9 stack=32` ⇒ **B=9 建齐**；
- `本步第 8/8 次被拒`（`_rej` 撞 `_rej_cap=8`）；
- 停机时 `目标 135 根、实有 73 根`（该档 `_tgt = 9×15 = 135`）。

---

## 5. 与"旧注释说法"的差异（**必须撤的旧叙述**）

`:2794` 的旧注释写：*「⇒ **再也不请求 fresh** ⇒ 块数永远 = 1」*。
**实测不是这样**：`fresh=9` 真的建起了 9 个块，`vmap` 也有 9 组（+ 第 10 组）。
⇒ 「块数永远=1」是 s293 当时的症状描述，**不能当作当前代码的后果**。

**当前代码的真正后果**是：
> `fresh` 通道用尽后，系统退化为纯 `stack`/`attach`；一旦位点表里卡住一个
> 几何上放不下的位点，`stack`/`attach` 每次全败，而**唯一的解卡机制被
> `n_fresh > 0` 挡在门外** ⇒ 每个时间步重复同一批失败 ⇒ `n_ath_tgt` 不变
> ⇒ 步进永不推进（准静态钟也永远不收敛）。

---

## 6. 待办（②-6 的收尾）

1. 写**定点复现**：同参数、小步数，读 `dbg` 的 `sites_resampled` 字段是否出现，
   并**故意把 `n_fresh=0`** 调一次 `nucleate()` 做**正对照**（判据：`sites_resampled` 应出现；
   若仍不出现 ⇒ 说明还有第二个门）。
2. 判定修法方向（**不预先钉死**）：
   - (a) 把 `:2260` 的 `n_fresh > 0` 门去掉（解卡机制对 `stack`/`attach` 也生效）；
   - (b) 在 `:2245` 那条"放不下"的位点上做**逐位点淘汰**（成功才 pop 的语义改成
     "连续 K 次失败即淘汰并重抽"）；
   - (c) 把 `fresh` 预算与"块内板条预算"解耦（`_Bt` 只限建块数，不冻结 fresh 通道）。
   三条都要先在 ② 里定性，再决定做不做。

---

## 7. 顺带记下（同一次读取中得到，供其他条目用）

- **`gamma_RS` 表：`n=24090` 项，但只有 `2310` 项非 NaN、其余 21780 项是 `NaN`**
  ⇒ 与 banner 的 `F2(γ 退回标量)` 行数**精确一致**。
  ⇒ ②-2 的「表空」是**真的**，且**不是"没建表"**，而是**"建了表但只填了 F3 那 2310 对"**。
  ⇒ 修法应是**填表**（用 `ncmp[k,l]` 法向算 `γ₂(n)`），不是"接通道"。**（判定待写）**
- `theta_deg`：`n=24090`，**全部非 NaN**，`max=5.0` ⇒ 与 `--omega-max-deg 5.0` 一致。
- `qs_clock=1`、`qs_tol=2e-3`、`qs_win=20`、`qs_max_relax=100` ⇒ 停机时是**准静态弛豫不收敛**，
  不是"时间积分推不动"。这两者的修法完全不同。
