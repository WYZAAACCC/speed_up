# R623 —— burst / 块的形成 / 顺序形核 的代码专项检查与修复方案

日期：2026-10-05（第 11 轮）
检查对象：`_bk_exp.py`、`windowB_surface.py`、`_bk_measure.py`
方法：**读全代码协议**（每处都读整段 + 调用方 + 前置条件）；每条缺口标「代码行 + 判据 + 影响」。
⚠ 本文件**包含一条对我此前说法的更正**（见 §2.1）。

---

## 0. 三条物理的正确图景（先立标准，再对代码）

### 0.1 ★ 参考文献（用户指定，**修复时以此为准**）

| # | 出处 | 本地全文 | 用途 |
|---|---|---|---|
| **R-A** | **R. Shi, Y. Wang**, "Variant selection during α precipitation in Ti–6Al–4V under the influence of local stress – A simulation study", *Acta Materialia* **61**(16) (2013) 6553–6568，**DOI `10.1016/j.actamat.2013.06.042`**（PII `S1359645413004820`；关键词含 `Correlated nucleation`） | `F:\参考论文\马氏体仿真\Variant selection during α precipitation in Ti–6Al–4V under the influence of local stress – A simulation study.pdf`（33 页）+ `_litidx/lit_txt/Variant_selection_during_precipitation_…A_simulation_study.txt` | **本专项的主依据**：burst 后由应力选变体、edge-to-edge 顺序形核、`E_int` 判据、自协调三变体簇 |
| **R-B** | "Effect of autocatalysis on variant selection of α precipitates during phase transformation in Ti-6Al-4V alloy", *Computational Materials Science*（2016），PII `S0927025616303597`，DOI `10.1016/j.commatsci.2016.06.028`【DOI 待 Crossref 复核】 | 未取到（`F:\参考论文\马氏体仿真` 内**暂无**此篇） | **自催化的定量率律** —— 正是本项目缺的那一条 |

⚠ **记账（硬步骤 B）**：R-B 的 DOI 是我由 PII 推出的，**未复核**；R-A 的卷/期/页由 Infona 的期刊卷期索引（`Volume 61, Number 16, 2013`）与 Mendeley 记录交叉确认，**DOI 已确认**。
⚠ **跨机制警告照旧适用**：R-A 是**扩散型 α 析出**（`t=1073 K`、parabolic 增厚、Al/V 配分、ledge 长大）⇒ 其 **`λ₂/λ₁=10`、`Lφ=6.0e-8 J/m³/s` 不可搬**；可搬的只有**晶体学、应变、界面能、簇结构、"变体由应力场选"这个机制**。
⚠ 修复时若需要"自催化率律"的定量形式，**优先找 R-B**（本库里没有就去取），而不是用 `p_auto` 那个已被撤回的自设值（`windowB_closure.py:762-763` 记「本项目自设；原引 Bhadeshia (5.24) 已撤」）。

### 0.2 三条物理的标准

| 阶段 | 物理 | 出处 |
|---|---|---|
| **① burst** | 过冷度一大，转变量按 **KM 分数律** `f = 1 − exp[−α_KM(M_s − T)]` 爆发（首档即 ~63%）；核事件出现在 `T_k = M_s − k/α_KM`，**与步数无关** | Koistinen–Marburger 1959；Ti-64 用 KM 律见 Nitzler 2021 eq.(5) |
| **② 块（同取向）** | **同一变体 + 互相接触**的板条连成一块（块 = 一摞平行板条）。能贴脸叠的物理原因是每个变体有**不变线**（沿它挪位长度不变） | **R-A**；`lat_*` 系列（Morito 2003：block 内同变体） |
| **②′ 块（不同取向的抵消）** | **不同变体凑成组、整体形状变化互相抵消** ⇒ 能量低 ⇒ 高频出现。最好的是 **V1+V4+V6**（`60°/[11̄20]α`），次之 **V1+V9+V11**（`63.26°/[10̄553]α`） | **R-A** §4（转述 Wang et al.）+ 该文自己的相场复现 |
| **③ 顺序形核** | **在已有板条的界面上**继续形核，一代接一代（`edge-to-edge`），块往外长。位置与变体由**已有板条应力场里的弹性相互作用能 `E_int`** 决定（`E_int<0` 促进、`>0` 抑制，最负处在板条边缘，且**远超**化学驱动力） | **R-A** `:645-679`、`:941-962` |
| **③′ 自催化** | R-A 结论(6)：观察到的是 **"coherency stress-induced correlated nucleation（即 autocatalytic effect）"**，**而非**经典 SN（后者源于二次/初生 α 间较低的晶界能） | **R-A** 结论 (6)（末页）；定量率律见 **R-B** |

---

## 1. 缺口 1：burst 的算式被"块数 `B`"污染，且与顺序形核次序互扰

**代码**（`_bk_exp.py`）
```
:2640-2644   _N_end = floor(α·(M_s − T_end))                 # = 23（一个块的板条数）
             _f_km  = 1 − exp(−α·(M_s − T_now))              # KM 分数律（物理）
             _n_blk = int(round(_N_end * _f_km))             # 本档的 n
:2648        _tgt   = min(_Bt * _n_blk, nv)                  # ★ 把块数 B 乘了进去
:2675        _rej_cap = 8 if _burst_on else 1e9
:2693-2696   _tgt_try / _do_try = (_tgt > _tgt_try)          # 同一档只补投一次
:2700        while _do_try and n_ath_tgt < _tgt and n_ath_tgt < nv and _rej < _rej_cap:
:2745-2751    _Bpar2 ⇒ _fresh_now = (n_fresh_ok < _Bt)        # 前 B 个成功事件各建新块
```

**问题**
1. **`_tgt = B × (_N_end·f_KM)`**：`_N_end` 是**一个块**的板条数（C-2 只对"堆叠型块"成立），乘 `B` 得全盒目标。**在 natural 模式下 `B` 不存在**，这个乘积失去意义。
2. **burst 的形状被"先建块"打乱**：burst 首档想投 `round(23×0.632) ≈ 15` 根，而 `_Bpar` 让**前 9 个成功事件全去开新块**，第 10 根才 `stack`。
   **实测证据**（`t10B9` 日志）：`累计 fresh=9 stack=32` ⇒ `fresh` **全落在一开头**。这不是数值冲突，是**语义被打乱**：`R29` 要的"首档爆发"变成了"首档先摊 9 个块"。
3. `R30_AUDIT_LEDGER §189.3` 描述的是同一硬币的另一面（`K=n` 时前 22 根全挤进 1 号块）⇒ **两条规则各偏一头**。

**修复方案**
```
manual  （归档逐位不变）： _tgt = min(_Bt · _n_blk, nv)
natural （新）          ： _tgt = min(round(_N_end · _f_km), nv)    # 用总量，不乘 B
                         顺序形核不用计数器；位置与变体由 argmax(驱动力) 决定
```
⚠ **待定项（不猜）**：`_f_km = 1 − exp(−αΔT)`（KM 分数律）与 `alpha_km_n_lath = floor(αΔT)`（C-2 线性式）是**同一物理量的两种形式**。natural 的档目标用哪个，需先把 `R29` 引入分数律的推导读实后再定。

---

## 2. 缺口 2：异变体的"贴面/界面形核"通道被两个守卫关死

**代码**（`windowB_surface.py`）

| 通道 | 守卫 | 行号 |
|---|---|---|
| `attach` | `if not bool(np.isin(_okr, (0, k)).all()): _dbg['cov'] += 1; continue` —— 注释明写「允许落在**母相(0)**或**源板条 k** 上…**绝不能落在别的场上**」 | `:2612-2615` |
| `stack` | `if not bool((reg[cover] == 0).all()): _dbg['cov'] += 1; continue` —— **必须全落在母相** | `:2675-2677` |

**问题**：用户指定那篇的核心机制是 **V4/V6 在 V1 的宽面上形核**（**异变体、贴着已有板条**）。而这两个守卫把"落在别的变体上"**直接判为失败**（计入 `cov`）。
⇒ **文献里的第 2 波、第 3 波在当前引擎里就发生不了**；只能"同变体接同变体"。
⇒ 实证：`t10B9` 分诊 `cov=319` 是被这个守卫拒掉的计数。

**修复方案**：把守卫从「只许落在母相或源板条」放宽为「**允许落在已有板条的界面上**」，并按文献的物理加一条判据 —— **只有当核与已有微结构的弹性相互作用能为负（`E_int < 0`）时才允许**，即由 `E_int + ΔG_chem` 决定，而不是几何白名单。
⚠ 必须**新开关 + 默认关**，否则归档路径改变。

### 2.1 ★ 对我此前说法的更正（硬步骤 B：说明我从哪一层读到的）

我此前说「`fresh` 的变体是手写标签决定的」—— **不准确，更正**：
* `_Bpar` 分支（`_bk_exp.py:2746`，t10B9 走的就是这条）**不传 `var_rule`** ⇒ 引擎用默认 `'ed'`；
* `windowB_surface.py:2104 _ks = [int(np.argmax(drv)) + 1]`，`:1583` 注释：「`fresh`（独立）：变体取该点 **`argmax_k ed[k]`**（弹性能变化最小，Du 2017 的规则）」。
⇒ **变体选择这一步是物理的**（在全部可用场号上取 `argmax` 驱动力，等价于在可用的 12 个变体里挑）。
**但仍然有问题**（这才是真缺口）：`argmax` 只能返回 `vmap` 里**已分配的场号** ⇒ **变体分布被 `--laths` 的配额限制**：若 `argmax` 偏斜到某个变体，它只有 22 个槽位，**用光后那个变体再也选不到**（这正是 `R606 §0` 担心的"配额墙"）。而实测 `t10B9` 停机时 `empty=387` ⇒ **空位还在，只是不属于被选中的那些变体**。

---

## 3. 缺口 3：同一根新核的"取向"与"长轴"取自不同来源 ⇒ 同变体内部不自洽

**代码**（`windowB_surface.py`）

| 量 | 取自 | 行号 |
|---|---|---|
| 新核法向 `nrm` | **源板条 `k` 自己的 `npref`** ⇒ 与源变体一致 ✅ | `:2470`（stack/attach）、`:2136` |
| 新核变体身份（`eps0`） | `nfsv` 找同变体的空闲场 ⇒ 也一致 ✅ | `:2621/:2692` |
| 新核**长轴** | `_along_of(k_new)`，而该函数**默认恒返回全局 `c['along']`** ❌ | `:1956-1963`、`:2620/:2692` |

**问题**：`along_per_variant=False`（**默认**）⇒ 长轴**永远是全局那一个**。在"所有板条同一取向"的归档配置下**恰好无害**，但**在 natural（变体真正分化）下就会错**：变体 2 的板条会用变体 1 的长轴。
⇒ 同一个坑还有第 4 处（见下）。

**修复方案**：natural 下强制 `along_per_variant=True`（按 `k_new` 自己的变体取长轴），并加断言：`along · nrm ≈ 0`（长轴必须落在惯习面内），否则报错。

---

## 4. 缺口 4：驱动层播种仍用**单一取向轴**，且"逐变体修正"只在未启用的分支里

**代码**（`_bk_exp.py`）
```
:962-968   n_hab = NPF[laths[0]]；w_ax、a_ax 也都从 laths[0] 取   ← 只取一次
:1632      c = c0 + ((edge − cproj) + side·(Tj/2 − o)) · n_hab     ← 所有片沿同一 n_hab 堆
:1634-35   g.seed_plate(j, c, n_hab, …, along=a_ax)               ← 同一 n_hab、同一 a_ax
:1297-1319 _variant_axes(v) 做对了（逐变体取轴，含 rank1_swap），但只在
:1321      if a.multi_block: 分支里被调用；生产 multi_block=False ⇒ 从不生效
```
**问题**：几何上 220 片**同一个取向**（与 §2.1 的"变体身份"形成两处不一致）；且沿 `n_hab`（= 长度轴）堆叠 ⇒ 总厚 `220×510 nm = 112 µm > 盒子 10 µm`。
**修复方案**：把 `_variant_axes` 从 `multi_block` 分支解放出来，让 `_seed_next` 用**该场自己的** `(n_hab, a_ax, w_ax)`。

---

## 5. 缺口 5：顺序形核缺少"钝化"机制；解卡路径被 `n_fresh > 0` 挡在门外

**代码**
```
windowB_surface.py:2011   if sites_refill and n_fresh > 0 and ('sites' in c):     # 补位点
windowB_surface.py:2260   if (not _any_ok) and sites_refill and sites:            # 重抽整张位点表（唯一解卡）
```
**问题**
1. **`fresh` 用尽后 `n_fresh` 恒 0 ⇒ 解卡路径永不执行** ⇒ `stack/attach` 反复重试同一批放不下的位点 ⇒ **步进永不推进**。
   **实测（`t10B9`）**：`fresh_cand=9`、`empty=387`、`sites_refilled=7` 而 **`sites_resampled` 字段不存在**（`R617`）。
2. **没有"钝化"**：物理上，一旦某个面的新片长满、应力被松弛，那个面**就不再促发形核**了。引擎里 `E_int` 的符号是算得出来的，但**没有任何地方用它来关闭已饱和的形核面** ⇒ 会一直"往同一个地方挤"。
   ⚠ **自催化的定量形式**：R-A 只给机制（"coherency stress-induced correlated nucleation"）与定性判据（`E_int` 符号），**没有率律**；本项目 `p_auto` 那个自设值已撤（`windowB_closure.py:762-763`）。
   ⇒ **要率律就去取 R-B**（`Effect of autocatalysis on variant selection …`，*Comput. Mater. Sci.* 2016），**不要自己编**。

**修复方案**
- **去门控**：解卡（位点重抽）不再依赖 `n_fresh > 0`；
- **加钝化**：形核位置的必要条件改为 `E_int + ΔG_chem > 阈值`，`E_int` 由已有场的应力场现算；已饱和面自然被排除（**这就是文献的机制，不是新律**）。

---

## 6. 缺口清单汇总（按优先级与依赖关系）

| # | 缺口 | 代码位置 | 影响 | 依赖 |
|---|---|---|---|---|
| **G1** | burst 的 `_tgt` 乘了块数 `B`；顺序形核次序被 `_Bpar` 打乱 | `_bk_exp.py:2648`、`:2745-2751` | 目标量在 natural 下无意义；爆发形状失真 | 无 |
| **G2** | 异变体贴面/界面形核被 `cov` 守卫关死 | `windowB_surface.py:2612-2615`、`:2675-2677` | 文献的第 2/3 波**发生不了** | **R-A** §3.3 / 结论(5)(6) |
| **G3** | 新核长轴取全局 `along`（非逐变体） | `windowB_surface.py:1956-1963` | natural 下用错长轴 | 需先做 G4 |
| **G4** | 驱动层播种用单一 `n_hab/a_ax`；`_variant_axes` 只在 `multi_block` 分支 | `_bk_exp.py:962-968`、`:1632-35`、`:1297-1319` | 220 片几何同一取向；堆叠方向 112 µm 装不下 | 无 |
| **G5a** | 解卡路径被 `n_fresh > 0` 门控 | `windowB_surface.py:2260` | `fresh` 用尽即死锁（`t10B9` 实测） | **必须最先做** |
| **G5b** | 无"钝化"（`E_int` 未用于关闭饱和形核面） | 引擎全局缺失 | 会一直往同一处挤 | 依赖 G5a；率律取 **R-B** |
| **G6** | 变体分布仍被 `--laths` 配额限制（`argmax` 只能选已分配的场号） | `_bk_exp.py:2746` + `windowB_surface.py:2104` | 配额墙：偏斜变体用光 22 槽位后选不到 | 与 G1 同一处改 |

**修复次序（依赖决定）**：`G5a`（解卡）→ `G4`（逐变体轴）→ `G3`（逐变体长轴）→ `G1/G6`（`--nuc-mode natural`：去配额 + 去 B + 驱动力决定次序）→ `G2`（放开界面形核 + `E_int` 判据）→ `G5b`（钝化）。
**每步都**：新开关、默认关、门控可复现、归档逐位不变、写死可 FAIL 的预登记判据。

---

## 7. 预登记判据（可 FAIL，逐条对应缺口）

| 判据 | 对应 | 反例（FAIL 长什么样） |
|---|---|---|
| 换一组 `manual` 配额，`natural` 的结果**必须不变** | G1/G6 | 变了 ⇒ 还在看配额表 |
| `natural` 下**不出现**"重复被拒后卡死" | G5a | 日志再现 `本步第 8/8 次被拒` |
| **异变体贴面形核发生**（出现"新场变体 ≠ 源场变体"且二者接触的 `attach` 事件） | G2 | `attach` 全是同变体 |
| 同一根新核的 `along · nrm ≈ 0` 且 `along` 随变体变化 | G3 | `along` 恒为常数 |
| 220 片**不再共用同一个 `n_hab`**（`_seed_next` 用逐场轴） | G4 | `meta.json`/banner 只有一个 `n_hab` |
| 板条总数自然落在**「两百多」且 ≤ `nv`** | G1/G6 | 停在 73 根、或超 `nv` |
| `natural` 与 `manual` 在**同总根数**下成块结构**必须不同** | G1 | 逐位相同 ⇒ natural 没生效 |
| 形核**钝化**：某形核面饱和后不再出现该处的新事件 | G5b | 同一位置反复出新事件 |
