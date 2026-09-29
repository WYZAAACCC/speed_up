# R30 审计 S1 —— `windowB_surface.py::LevelSetMulti.advance()` 的多核并行审计

> 审计对象：`pipeline/ca_pf_framework/windowB_surface.py::LevelSetMulti.advance()`
> （行 2810–3440）及其调用链 `elastic_driving` / `elastic_driving_pair` /
> `curvature_of` / `_advance_perfield` / `reinitialize` / `nucleate`
> 审计类型：**只读**（未修改任何已有文件；新增脚本 8 个，见 §10）
> 审计日期：2026-09-30　机器：WSL / 20 逻辑核 / 23 GB
> 全部命令均在 WSL `ml` 环境跑；**本审计自身最多用 4 线程**

---

## §0 结论速览（先看这 8 条）

| # | 结论 | 判据强度 |
|---|---|---|
| **C1** | **并行确实生效、也确实"逐位相同"**：`workers=1/2/4` 的 `phi`（与开 ψ 时的 `phi`+`psi`）**逐位相同**（max\|Δ\| = 0.000e+00），且并行路径**确实被走到**（8 个 tag 的 `nth_max` ≥2） | 【实测】`_r30_identity.py`：8 项判据 + 2 项对照全 PASS（含 1 ULP / dt·(1+1e-12) 分辨力对照） |
| **C2** | **加速比只有 ×1.9–2.3 @4 线程**（N=96 / 12 活跃场 / 5.66–6.27 s·步⁻¹ 单线程）。有效并行度 CPU/wall = **2.72–2.74**（两次独立测量几乎完全一致） | 【实测】`_r30_speedup.py` ×2 次 |
| **C3** | 上限由**两件事**共同锁死：① **串行残差 1.22 s/步（单线程步时的 18.6%）**，到 w=4 时它占该步的 **38–49%**；② 并行段自身反推只到 **×2.5–3.6**（DRAM 天花板：本机 triad 实测 **×1.99** @4 线程） | 【实测】+【推理】 |
| **C4** | ⚠ **`ParCtx.upwind_flux_vec` 的 slab 并行在生产路径上是"死代码"** —— `advance` 里它唯一的调用点（`:3426`）位于 `_step_k` 内，而 `_step_k` 跑在 `par.for_each` 的 worker 里 ⇒ 死锁守卫（`windowB_par.py:124-127`）**强制 `_segments()` 返回 1** ⇒ 每次都走单线程回退。**实测 12/12 次调用 `nth=1`** | 【实测】`_r30_pathprobe.py` |
| **C5** | 同一守卫使 `_geom_k` 里的 `par.gradient` **12/12 次被强制串行**（实测 `gradient` 59 次调用中 12 次 `depth1/nth1`），另 47 次 `depth0/nth4` 真并行 | 【实测】同上 |
| **C6** | `ParCtx` 提供但**从未被 `windowB_surface.py` 调用**的算子：`einsum_ii`、`norm_last`、`where`、`sussman_reinit`（方法版）、`set_threads`、`report`。其中前三者正对着 `advance` 里 ~0.34 s/步（5.2%）的串行逐胞块 | 【实测】全仓 grep + `_r30_pathprobe.py` |
| **C7** | **`--nthreads` 确实生效**（构造时进 `ParCtx`，实测 `--nthreads 2 ⇒ g.par.n=2`）。`_bk_exp.py` 默认 **4**、`_bk_closed.py` 默认 **2**、正在跑的生产任务用的是 **2**。但旧探针 `_probe_workers.py` 改的是 `g.workers`/`g.pf.workers` ⇒ **对 `advance` 无效**，它的"advance 恒为单线程"结论是 **R1 之前的**、且**量错了旋钮** | 【实测】`_r30_wire.py` |
| **C8** | 一次 `reinitialize(force=True)`（N=96、21 配对、`reinit_iters=100`）= **413.5 s @w1 / 323.5 s @w4（只 ×1.28）**。它是 `advance` 收尾段的**量级跳变源**，不是每步成本 | 【实测】`_r30_reinit.py` |

**一句话**：并行层写得**对**（逐位相同，8 项判据 + 2 项对照全过），但**没吃满**：
`advance` 里真正被并行覆盖的是 **81.4% 的步时**，而并行段自己撞 DRAM/分配天花板只到 **×2.5–3.6**；
剩下 **18.6%（w=1）/ 38–49%（w=4）是串行**，且**最贵的一处（`upwind_flux_vec` 的 slab 实现）
在生产里一次都没被用上**。

---

## §1 审计范围（读了什么、跑了什么）

### 1.1 读过的文件与行数

| 文件 | 读了哪些 | 行数 |
|---|---|---|
| `windowB_par.py` | **全文** | 416 |
| `windowB_surface.py` | `advance` 2810–3440（**全文逐行**）、`_finish_advance` 3442–3478、`_advance_perfield` 3480–3542、`reinitialize` 3661–3870、`__init__` 852–1046、`region` 1221–1227、`nucleate` 定位 1438–1942、`curvature_of` 2437–2462、`sussman_reinit`/`_sussman_core` 187–290、`upwind_flux_vec` 371–418、`_minmod` 42–44、`elastic_driving` 2627–2721、`elastic_driving_pair` 2759–2801 | ≈1600 |
| `windowB_pf3d.py` | `eps0_fields`/`eps0_fields_idx`/`_epsh`/`sigma_tensor` 225–285 | 60 |
| `windowB_lath.py` | `LathTable.__init__`/`facet_gamma_sub` 定位 | grep |
| `windowB_film.py` | 函数签名（`psi_step_local` 无 `par` 参数） | grep |
| `_bk_exp.py` | 32–49、140–320、495–534、535–615、878–1006 | ≈300 |
| `_bk_closed.py` | 60–99、138–167 | 70 |
| `_prof_step.py` / `_probe_workers.py` / `_prof_show.py` | 全文 | 190 |
| `_bk_par_identity.py` | 全文 | 133 |
| `T16_verify_rve.py` | 25–64 | 40 |

### 1.2 跑的脚本与实验（全部新增，未改动任何已有文件）

| 脚本 | 作用 | 关键输出 |
|---|---|---|
| `_r30_prof_line.py` | `sys.settrace` **逐行**计时（`windowB_surface/par/lath/film`），N=96 / 11 板条 / workers=1 | `_r30_prof_line_N96_w1.log` + `.json` |
| `_r30_table.py` | 把逐行数据聚成**算子表** | §3 的 A/B/C/D/E 表 |
| `_r30_speedup.py` | workers=1/2/4 的 `advance` wall/CPU + `par.report()` 自证 | `_r30_speedup_N96.log`（第 1 次）、`_r30_speedup_N96_rerun.log`（第 2 次） |
| `_r30_microbench.py` | 21 个算子的独立标度 + triad 带宽天花板 | `_r30_microbench_N96.log` |
| `_r30_identity.py` | 端到端逐位判据 + 正/负对照（8 项判据 + 2 项对照） | `_r30_identity_N64.log`、`_r30_identity_N64_film.log` |
| `_r30_pathprobe.py` | 给每个 ParCtx 算子装计数器，量**真实分段数** | `_r30_pathprobe.log` |
| `_r30_wire.py` | `--nthreads` 接线核查 + 旧探针负对照 | `_r30_wire.log` |
| `_r30_reinit.py` | 单次 `reinitialize(force=True)` 代价 | `_r30_reinit_N96.log` |

### 1.3 机器负载记账（**测量有效性**）

* 全程有一个**别人的生产长跑**在跑：`_bk_exp.py --tag cln11 --nthreads 2`（2 线程、~830 MB），**未动它**。
* 期间**另一个代理**也在本仓库跑作业（`_r30_selfac_struct.py`、`_r30_ctl_column.py`、`_r30_psi.py`，
  各 ~90–100% CPU）。测速期间 `uptime` 实测 load average = **4.83–5.83**。
* ⇒ **本报告的所有 wall 时间都是"机器上有 3–6 个别人的线程"条件下测的**，
  因而**加速比是下界**（并行段撞 DRAM 天花板，别人占带宽只会让它更低）。
* 本审计自身**最多 4 线程**；`workers>4` 的点**未测**（见 §4.3）。

---

## §2 并行层清单（问题 1）

### 2.1 `ParCtx` 提供了什么（`windowB_par.py`，全文 416 行）

| 算子 | 定义处 | 语义 | 是否被 `windowB_surface.py` 调用 |
|---|---|---|---|
| `edges_of(n,nth)` | `:54` | 均分段边界 | 内部用 |
| `ParCtx(nthreads, min_rows=2)` | `:66` | 上下文 | `:915 self.par = ParCtx(workers)` |
| `pool`（property） | `:91-98` | `ThreadPoolExecutor(max_workers=n)` | 内部 |
| `set_threads(n)` | `:100-107` | 运行期改线程数 | ✗ **从未调用** |
| `close()` | `:109-112` | 关池 | ✗ |
| `report()` | `:135-139` | 返回 `(总wall, 逐算子表)` | ✗（只有诊断脚本在用） |
| `map0(fn,n0,…)` | `:151-166` | 通用切片拼接 | 内部（`argmin`/`gradient`/`upwind_*`/`where`/`einsum_ii`/`norm_last` 都走它） |
| `map0_two(fn,n0)` | `:168-181` | 双返回值切片 | 内部（`argmin2`） |
| `for_each(items,tag)` | `:183-199` | 按**对象**并行（不是按空间） | ✅ `:2687, :2716, :3010, :3438` |
| `argmin2(fields)` | `:209-226` | winner/runner-up | ✅ `:2899` |
| `argmin(fields)` | `:228-231` | 区域指派 | ✅ 经 `region()` `:1226` |
| `upwind_flux_vec` | `:233-255` | 矢量迎风对流（周期 halo=2） | ✅ `:3426`（**但见 C4**） |
| `gradient` | `:257-281` | `np.gradient`（盒边界截断 halo） | ✅ `:2975, :3036, :3158, :3200, :3201, :3395, :3430` |
| `upwind_grad2` | `:283-301` | 二阶 ENO 迎风 \|∇φ\|（周期 halo=2） | ✅ 经模块级 `sussman_reinit(par=…)` `:208` → `_sussman_core:278` |
| `upwind_grad` | `:303-316` | 一阶版 | 仅在 `reinit_grad='upwind'` 时；默认 `'upwind2'` ⇒ **实测 0 次调用** |
| `sussman_reinit(…)`（方法版） | `:318-332` | 委托给 `windowB_surface.sussman_reinit` | ✗ **从未调用** |
| `einsum_ii(a,b)` | `:334-338` | `np.einsum('...i,...i->...')` 并行版 | ✗ **从未调用** |
| `norm_last(a)` | `:340-343` | `np.linalg.norm(a,axis=-1)` 并行版 | ✗ **从未调用** |
| `where(cond,x,y)` | `:345-348` | `np.where` 并行版 | ✗ **从未调用** |
| `_segments` / `_wrapped` / `_call_guarded` | `:121-127 / :141-148 / :201-206` | 私有：分段数 + 重入守卫 | 内部 |

> **"提供了但没被调用"清单（6 个）**：`einsum_ii`、`norm_last`、`where`、方法版 `sussman_reinit`、
> `set_threads`、`report`。
> 前三个正好对着 `advance` 里**实测 0.34 s/步（占单线程步时 5.2%）的串行逐胞块**（见 §6）。

### 2.2 `advance()` 及其子函数**实际**调用了什么

`advance` 直接调用的并行入口（file:line 全部为 `windowB_surface.py`）：

| 调用点 | 算子 | 并行维度 | 实测是否真并行 |
|---|---|---|---|
| `:2899` | `par.argmin2` | 空间切片 | ✅ `nth=4`（depth 0） |
| `:2919–2947` | **无**（`lath.gtab` gather + `np.where`） | — | ✗ 串行（0.010 s/步，便宜） |
| `:3010` | `par.for_each(_geom_k)` | **12 个场** | ✅ `nth_max=4` |
| `:2687`/`:2716`（在 `elastic_driving` 内） | `par.for_each`（`ed.soft_phi` / `ed.einsum`） | **11 个变体场** | ✅ `nth_max=4` |
| `:3017`→`:2759` | `elastic_driving_pair`（内部 `:2714 sigma_tensor`） | **串行** | ✗ 见 §3.2 |
| `:3036, :3158, :3200, :3201, :3395` | `par.gradient` | 空间切片 | ✅ `nth=4`（depth 0） |
| `:3338–3380` | `distance_transform_edt` ×2 | — | ✗ 串行（scipy C，单线程） |
| `:3391–3397` | `np.where`/`np.einsum` 内联 | — | ✗ 串行 |
| `:3426` | `par.upwind_flux_vec` | 空间切片 | ❌ **恒 `nth=1`（depth 1，被守卫强制串行）** |
| `:3438` | `par.for_each(_step_k)` | **12 个场** | ✅ `nth_max=4` |
| `:3440` → `_finish_advance:3448` | `region()` → `par.argmin` | 空间切片 | ✅ `nth=4` |
| `:3440` → `_finish_advance:3464`/`:3474` | `reinitialize()` → `sussman_reinit(par=…)` → `upwind_grad2` | 空间切片 | ✅ `nth_max=4`（触发时才跑） |

**`nucleate()`（`:1438–1942`，505 行）：`self.par` 出现 0 次 ⇒ 完全串行。**
（`advance` 之外；生产由 `_bk_exp.py:593-602` 的 athermal 循环驱动，**只在形核事件时**
才真正执行 `g.nucleate`，那时它还会额外调一次 `g.elastic_driving()` —— 稀疏事件。）

**`_advance_perfield()`（`:3480–3542`）：`self.par` 出现 0 次 ⇒ 完全串行。**
（生产不走这条：`_bk_exp.py:465-467` 的 kwargs 里没有 `per_field`，默认 `False`。）

**`reinitialize()`（`:3661–3870`）：只有 Sussman 热核走并行。**
`:3812 np.argsort(self.phi, axis=0)`（造 `(nreg,N³)` int64 = N=96 时 **85 MB**）、
`:3824/:3826/:3827 np.where` 回写、`:3873 _band_bonds`（6 次 `np.roll`）**全是串行**。
（`:3812` 是**懒构造**：所有配对都被 `reinit_skip_tol` 跳过时不付这笔钱 —— 这个优化是对的。）

### 2.3 ⚠ C4/C5 的**直接实测证据**（不靠读代码）

`_r30_pathprobe.py` 给每个算子装了计数器，跑**一步真实 `advance` + 一次 `reinitialize(force=True)`**
（N=48 / 11 场 / workers=4）：

```
算子                 调用次数  调用时深度分布        分段数分布（nth=1 ⇒ 单线程回退）
  argmin2                 1   {'depth0': 1}          {'nth4': 1}
  argmin                  9   {'depth0': 9}          {'nth4': 9}
  gradient               59   {'depth0': 47, 'depth1': 12} {'nth1': 12, 'nth4': 47}
  upwind_flux_vec        12   {'depth1': 12}         {'nth1': 12}
  upwind_grad2          840   {'depth0': 840}        {'nth4': 840}
  upwind_grad             0   {}                     {}
```

* **`upwind_flux_vec`：12 次调用全部 `depth1` ⇒ 全部 `nth=1` ⇒ 单线程回退。**
  `ParCtx.upwind_flux_vec`（`:233-255`）的 slab 实现（含 `% n0` 周期 halo 那套）
  在 `advance` 里**一次都没被执行**。代码注释里"实测加速比 ×2.43 @20 线程
  （`_w2_r1par_N192.log`，算子级）"（`windowB_surface.py:3408`）说的是**算子空跑**，
  **不是**它在 `advance` 里的实际贡献。
* **`_geom_k` 里的 12 次 `par.gradient` 全部被强制串行**（`depth1 ⇒ nth1`）。
  死锁守卫在 `windowB_par.py:124-127`：
  ```python
  def _segments(self, n0):
      if self.n <= 1 or self._depth() > 0:
          return 1
  ```
  这是一个**正确的**防死锁设计（固定大小池不能嵌套），代价是**两级并行只能开一级**。
  ⇒ 净效果不是 bug，但**必须记账**：`advance` 的并行度 = 12 个场 / 4 线程，
  而不是 12×空间切片。

---

## §3 算子级耗时表（问题 2）

### 3.1 装置

* N=96、Δx=125 nm、L=12 µm（与**正在跑的生产任务** `_bk_exp --N 96 --dx-nm 125` 同分辨率）；
* `LathTable` 11 根同变体板条（`omegas=default_omega(11, 5.0)`、`gamma0=0.25`），
  与 `_bk_closed --tag cln11` 的 `--laths 1×11` 同形；**12 个区域全部活跃**；
* `advance(dt, aniso=0.4, npref=…, band_cells=20, mob_beta=3.5, mob_beta_w=2.3,
  adv_grad='proj2', norm_smooth=0, facet_lam=0.0, facet_eps=0.05)`
  —— 与 `_bk_exp.py:465-467` **逐字相同**（`mob_beta` 生产取 6.62，本装置取默认 3.5，
  它只改速度大小、不改算子清单）；
* `elastic_soft=True`（`windowB_surface.py:1042` 的**默认**，Round 139 用户批准）；
* `workers=1`、`reinit` 未触发（`reinit_dt=1e-4` ≫ 3 步）；
* 单步 wall = **6.568 s**（无跟踪）/ **6.498 s**（带跟踪）⇒ **跟踪开销未检出**
  （比值 ×0.99，落在批间噪声内；全程只有 3424 个 call 事件），
  所以下面的逐行数字可以直接读。

### 3.2 A 表：`advance()` 顶层算子表（单线程，含子帧）

由 `advance` 帧内**逐行 incl** 按行号区间求和（各区间之和 = 6.4883 s，**基线 6.568 s 的 98.8%**；
未归入区间的 `advance` 行合计仅 0.0035 s）。

| # | 算子 | file:line（调用点） | 走并行？ | 实测 s/步 | 占步时 |
|---|---|---|---|---|---|
| ① | `region()` 区域指派 | `:2863` → `:1226` `par.argmin` | ✅ 空间切片 | 0.0327 | 0.5% |
| ② | winner/runner-up `par.argmin2` | `:2899` | ✅ 空间切片 | 0.1098 | 1.7% |
| ③ | F3 面能表 `_gc_full`（lath gather） | `:2919–2947` | ✗ | 0.0101 | 0.2% |
| ④ | `per_field` 分支 | `:2948–2961` | —（生产不走） | 0.0000 | 0.0% |
| ⑤ | 小分配 / `np.unique` 活跃场清单 | `:2962–2966` | ✗ | 0.0436 | 0.7% |
| ⑥ | **按场几何 `_geom_k`** | `:2968–3011`，`for_each`@`:3010` | ✅ **按场（12）** | **2.0341** | **31.0%** |
| ⑦ | **弹性驱动 `elastic_driving_pair`** | `:3017` → `:2759` | ⚠ **部分**（见 B 表） | **0.8873** | **13.5%** |
| ⑧ | 界面法向 `ndir_` / 参考取向 `nd_ref` | `:3021–3091` | ✗（`gradient` 除外） | 0.1761 | 2.7% |
| ⑨ | 曲率 `kap_cell` + 镜像 SDF 检查 | `:3092–3220` | ✗（`gradient` 除外） | 0.2013 | 3.1% |
| ⑩ | 驱动力 `dG_cell` / `v_cell` | `:3221–3241` | ✗ | 0.0255 | 0.4% |
| ⑪ | M(n) 迁移率各向异性 | `:3242–3293` | ✗ | 0.1440 | 2.2% |
| ⑫ | 配对规范形 `sigma·v_cell` | `:3294–3317` | ✗ | 0.0074 | 0.1% |
| ⑬ | **速度延拓（EDT）** | `:3318–3380` | ✗（scipy EDT 单线程） | 0.1992 | 3.0% |
| ⑭ | 投影 `V = v·n`（proj2） | `:3381–3399` | ✗ | 0.0524 | 0.8% |
| ⑮ | **逐场平流 `_step_k`** | `:3419–3438`，`for_each`@`:3438` | ✅ **按场（12）** | **2.5318** | **38.5%** |
| ⑯ | `_finish_advance`（region+reinit+Stefan） | `:3440` → `:3442` | 部分 | 0.0329 | 0.5% |
| | **合计** | | | **6.4883** | 100% |

### 3.3 B 表：子帧拆分（已含在 A 表内，此处拆开）

| 子帧 | file:line | 走并行？ | incl s/步 | excl s/步 | hits |
|---|---|---|---|---|---|
| `par.for_each`（合计 4 处） | `windowB_par.py:183` | ✅ | 4.8681 | 0.0012 | 104 |
| ├ `advance.k_loop`（`_step_k`） | `:3438` | ✅ 按场 | 2.5301 | 0.1574 | 108 |
| │ └ `par.upwind_flux_vec` | `windowB_par.py:233` | ❌ **回退** | 2.3727 | 0.0043 | 72 |
| │ 　 └ `upwind_flux_vec`（模块级） | `:371` | — | 2.3684 | 1.3984 | 432 |
| │ 　 　 └ **`_minmod`** | `:42-44` | — | **0.9700** | 0.9700 | 72 |
| ├ `advance.geom_k`（`_geom_k`） | `:3010` | ✅ 按场 | 2.0196 | 0.1153 | 252 |
| │ ├ `_stiff_of` | `:2555` | — | 0.7038 | 0.6274 | 126 |
| │ ├ `facet_nref` | `:2464` | — | 0.4309 | 0.4309 | 135 |
| │ ├ `curvature_of` | `:2437` | — | 0.4565 | 0.4565 | 234 |
| │ ├ `par.gradient`（**被守卫强制串行**） | `:2975` | ❌ `nth=1` | 0.1992 | — | 12 |
| │ ├ `_bbox_pad` | `:131` | — | 0.0837 | 0.0835 | 120 |
| │ └ `herring_stiffness` | `:320` | — | 0.0765 | 0.0765 | 33 |
| ├ `ed.soft_phi`（λ@`:2689`） | `:2687` | ✅ 按场 | 0.1432 | 0.1432 | 11 |
| └ `ed.einsum`（λ@`:2718`） | `:2716` | ✅ 按场 | 0.1339 | 0.1339 | 22 |
| `elastic_driving_pair` | `:2759` | ⚠ | 0.8652 | 0.0180 | 7 |
| └ `elastic_driving` | `:2627` | ⚠ | 0.8472 | 0.5030 | 70 |
| 　 └ **`sigma_tensor(None)`（串行！）** | `:2714` | ✗ | **0.5027** | 0.5027 | 1 |
| `windowB_par.gradient`（全部 17 次） | `:257` | 5 并行 +12 串行 | 0.3183 | 0.3182 | 68 |
| `region()`（3 次调用合计） | `:1221` | ✅ | 0.1072 | 0.0029 | 9 |
| `par.argmin` | `windowB_par.py:228` | ✅ | 0.1043 | 0.0001 | 9 |

### 3.4 C 表：`_geom_k` 内部（每步 12 次调用，合计 **2.0196 s**）

| 行 | 内容 | incl s/步（12 次） | 占比 |
|---|---|---|---|
| `:2981` | `_stiff_of`（γ(n)/Herring/面片身份） | 0.7082 | 35.1% |
| `:2979` | `facet_nref`（(k,l) → 参考取向） | 0.4352 | 21.5% |
| `:2977` | `curvature_of`（3×`np.roll` 对角项） | 0.4237 | 21.0% |
| `:2975` | `par.gradient`（**串行**，子盒） | 0.1992 | 9.9% |
| `:2976` | `np.sqrt(Σg²)` | 0.1222 | 6.0% |
| `:2972` | `_bbox_pad` | 0.0850 | 4.2% |
| 其它 | mask/写回 | 0.0461 | 2.3% |

### 3.5 E 表：`upwind_flux_vec`（模块级）内部（每步 12 次调用，合计 **2.3684 s**）

| 行 | 内容 | incl s/步 | 备注 |
|---|---|---|---|
| `:413` | `dm += 0.5*_minmod(dm-dmm, dp-dm)` | 0.7271 | 内含 1 次 `_minmod` |
| `:414` | `dp -= 0.5*_minmod(dpp-dp, dp-dm)` | 0.7666 | 内含 1 次 `_minmod` |
| `:416` | `acc += np.where(Va>0, Va*dm, Va*dp)` | 0.3288 | |
| `:408` | `dm = (φ − roll(φ))/dx` | 0.2042 | |
| `:409` | `dp = (roll(φ) − φ)/dx` | 0.1460 | |
| `:411/:412` | `dmm`/`dpp`（各一次 roll） | 0.1689 | |
| `:406` | `np.any(Va)` | 0.0252 | |
| **`_minmod` 合计（72 次）** | | **0.9700** | **占整个 `advance` 的 14.8%** |

### 3.6 与"生产真实步时"对齐（**独立证据**，不是本装置的）

正在跑的生产任务日志 `_w2_bk_cln11.log`（N=96、Δx=125 nm、`--nthreads 2`）实测：

| 步区间 | 活跃场数 | 实测 s/步 |
|---|---|---|
| 100–300 | 1 | 2.03–2.12 |
| 400–700 | 2 | 2.47–2.56 |
| 800–1100 | 3 | 2.71–3.79 |
| 1200–1600 | 4 | 2.80–2.93 |
| 1700–2100 | 5 | 2.52–3.45（含一次 reinit 尖峰） |

即 **≈ 2.0 s 底 + 0.35 s/活跃场**。本装置的 12 个全活跃场 ⇒ 折算 **≈ 6.2 s/步**，
与我在 **workers=1** 下实测的 5.66–6.27 s/步**吻合**。
⇒ 本报告的装置**代表生产的上界工况**（生产此刻是 5 个场）。

---

## §4 加速比曲线（问题 3）

### 4.1 实测（N=96，12 活跃场，每档 3 步，含预热）

**第 1 次**（`_r30_speedup_N96.log`，05:50–05:52）：

| workers | wall s/步 | CPU s/步 | 加速比 | CPU/wall |
|---|---|---|---|---|
| 1 | 6.271 | 6.318 | ×1.00 | **1.01** |
| 2 | 4.141 | 7.084 | **×1.51** | **1.71** |
| 4 | 3.251 | 8.829 | **×1.93** | **2.72** |

**第 2 次**（`_r30_speedup_N96_rerun.log`，06:03–06:04，同时记录了 load）：

| workers | wall s/步 | CPU s/步 | 加速比 | CPU/wall |
|---|---|---|---|---|
| 1 | 5.661 | 5.712 | ×1.00 | **1.01** |
| 2 | 3.556 | 6.022 | **×1.59** | **1.69** |
| 4 | 2.474 | 6.771 | **×2.29** | **2.74** |

* wall 有 ±10–15% 的批间散布（机器上有别人的 3–6 个线程）；
  **CPU/wall 两次几乎逐位一致（2.72 vs 2.74）** ⇒ "有效并行度 ≈ 2.7 线程"是稳的。
* 每档都**打印了生效值自证**：`g.par.n=1/2/4` 与 `g.pf.workers=1/2/4`。

### 4.2 偏离线性的原因（**分解，不是猜测**）

**(a) 串行段 —— 最大的一块。**
用 §3 的单线程预算（那次 `advance` = 6.568 s/步）：并行覆盖不到的 =
`advance` 内联 0.686 + `sigma_tensor` 0.503 + `_finish_advance` 0.033 = **1.22 s ⇒ f = 18.6%**。
这部分是**串行**的，在 w=4 时 wall 基本不变：
从 §4.1 的实测反推 w=4 步时里的非并行残差 = `w4_step − 并行tag累计`：

| | w=4 步时 | 并行 tag 累计/步 | **串行残差** | 占比 |
|---|---|---|---|---|
| 第 1 次 | 3.251 | 1.911 | **1.340** | 41% |
| 第 2 次 | 2.474 | 1.479 | **0.995** | 40% |

⇒ f = 0.995/5.661 ~ 1.340/6.271 = **17.6%–21.4%**，与上面按算子表的 18.6% **一致**（两个独立路径）。
**Amdahl 预测**：`S(4) = 1/(f + (1−f)/4)` = **2.32–2.56**；实测 **1.93–2.29**。
`S(∞) = 1/f` = **4.6–5.7** ⇒ 就算核无限多，本装置也快不到 6 倍。

**(b) 并行段自己也没吃满。**
反解并行段自身的效率 `S_p = (1−f)/(1/S − f)`：
第 2 次 `f=0.216, S=2.29 ⇒ S_p = 3.55`；第 1 次 `f=0.186, S=1.93 ⇒ S_p = 2.45`。
即 **4 线程下并行段只跑到 ×2.45–3.55**（理论 ×4）。
（另一条等价算法：把 w=1 与 w=4 的并行 tag 相除——`k_loop 2.532→0.749`、
`geom_k 2.034→0.551`、`ed.* 0.277→0.098`、`argmin* 0.145→0.081`——
得 4.99 s → 1.48 s = ×3.4；扣掉两次测量 w=1 基线的 5% 差后落在 ×2.5–3.4 区间。）

**(c) 硬天花板 = DRAM 带宽。**
本机 N=96 实测 triad（读2写1，21 MB 数组）：**w=1 20.0 GB/s → w=4 39.9 GB/s = ×1.99**。
（与 `windowB_par.py:15-17` 引用的 N=192 数据"11.08 → 23.05 GB/s = ×2.08"同一结论。）
逐算子单线程实测与 4 线程标度：

| 算子 | w1 (s) | w2 | w4 | ×@4 | 性质 |
|---|---|---|---|---|---|
| `triad`（带宽标尺） | 0.0032 | 0.0023 | 0.0016 | **×1.99** | 纯流式 |
| `par.argmin`（12 场） | 0.0332 | 0.0176 | 0.0140 | **×2.37** | 延迟受限 |
| `par.argmin2`（12 场） | 0.0598 | 0.0394 | 0.0340 | ×1.76 | 延迟受限 |
| `par.norm_last` | 0.0199 | 0.0166 | 0.0118 | ×1.69 | 混合 |
| `par.upwind_grad2` | 0.2434 | 0.2317 | 0.1506 | ×1.62 | 分配受限 |
| `par.upwind_flux_vec(o2)` | 0.1803 | 0.1681 | 0.1289 | ×1.40 | 分配/带宽 |
| `par.einsum_ii` | 0.0048 | 0.0049 | 0.0041 | ×1.16 | 太小（池开销占优） |
| `par.where` | 0.0073 | 0.0083 | 0.0075 | ×0.99 | 太小 |
| `par.gradient` | 0.0144 | 0.0205 | 0.0210 | **×0.69（变慢）** | 太小 + 带宽 |

> ⚠ **与仓库现有声称的差异（必须记账）**：`windowB_par.py:17-19` 写
> "`np.where` ×4.6、`norm` ×5.3、`argmin` ×4.1、`winner/runner-up` ×6.8"，
> 那是 `_r1_par.py` 在 **N=192（54 MB/数组）** 上量的；我在这里用 **N=96（7 MB/数组）**
> 量到的是 ×0.99 / ×1.69 / ×2.37 / ×1.76。
> 两者不矛盾但**不可混用**：段越小，线程池提交/拼接与缓冲分配开销占比越大。
> **生产就是 N=96**，所以本审计的数是生产口径。
> 更关键的是：**算子空跑的加速比 ≠ 它在 `advance` 里的实际贡献** ——
> `upwind_flux_vec` 空跑 ×1.40–2.43，在 `advance` 里**一次都没并行**（C4）。

**(d) GIL —— 不是主因。**
正/负对照（`_r1_par.py` P-1，抄录）：`time.sleep` 真并行 ✓、纯 Python 循环完全平坦 ✗。
本审计的线程标度里没有一个算子出现"完全平坦"，说明 numpy 逐元素核确实释放 GIL。
⇒ 偏离线性来自 **(a) 串行段 + (b) 带宽/分配**，**不是 GIL**。

### 4.3 ⛔ **未测 >4 线程（明确声明）**

环境纪律规定"任何 CPU 密集测试最多用 4 个线程，不要占用超过 4 个核"，
本机还有别人的生产长跑（2 线程）。⇒ **workers = 8 / 16 / 20 未测**。
【推理，非实测】按 triad 在 w=4 已到 39.9 GB/s（×1.99，接近饱和）推断：
继续加线程对**带宽受限段**没有收益，只有 `argmin2` 这类延迟受限算子还能涨；
整体大概在 **×2.3–2.6 @8 线程** 附近封顶。
**这个数没有测，不要在别处引用为实测。**

---

## §5 正确性（问题 4）

### 5.1 (a) `windowB_par._selftest` —— 照跑并报告

`_r30_identity.py` 的 [A] 段，`_selftest(N=64, nthreads=4)`：**15/15 全部逐位相同**
（`_r30_identity_N64.log:6-21`）。逐项：`upwind_flux_vec o1/o2`、`np.gradient[0]/[2]`、
`argmin2.karr/larr`、`np.argmin(region)`、`einsum_ii`、`norm_last`、`where`、
`upwind_grad`、`upwind_grad2`、`sussman_reinit iters=5/20/band=None`
—— 每一项 `最大差 0.000e+00`。
⇒ `windowB_par.py:407-408` 的声称**成立**。

> 附一条文档不一致（不影响结论）：`windowB_surface.py:911` 写"10/10 PASS"，
> 实际自检有 **15** 项；`_bk_par_identity.py:10` 写 15/15 是对的。

### 5.2 (b) 我自己的独立正/负对照（端到端）

`_r30_identity.py`，N=64 / 11 板条 / 3 步 / `reinit_dt=1e-7`（**reinit 每 2 步触发一次**，
把 Sussman 热核也覆盖进去）：

| 判据 | 结果 | 数字 |
|---|---|---|
| **[B-0]** 覆盖自证：workers=1 时并行算子不启用 | PASS | tags=0 |
| **[B] workers=1 vs 2：`phi` 逐位相同** | **PASS** | max\|Δφ\| = **0.000e+00** |
| **[B] workers=1 vs 4：`phi` 逐位相同** | **PASS** | max\|Δφ\| = **0.000e+00** |
| **[B] 开 ψ 通道后 `psi` 也逐位相同**（`_r30_identity_N64_film.log`） | **PASS** | max\|Δψ\| = **0.000e+00** |
| **[B-1]** 覆盖自证：workers=4 时确有算子真分段 | PASS | 8 个 tag `nth_max`=4（`advance.geom_k`/`advance.k_loop`/`argmin`/`argmin2`/`ed.einsum`/`ed.soft_phi`/`gradient`/`upwind_grad2`） |
| **[C] 正对照**：只改分段粒度 `g.par.min_rows` = 1 / 3（**不改任何数值**） | PASS | max\|Δφ\| = 0.000e+00 |
| **[D] 负对照**：`dt ← dt·(1+1e-12)` ⇒ **必须不同** | PASS（确实不同） | max\|Δφ\| = **2.92e-07** |
| **[E] 比较器分辨率**：把 1 个元素改 1 ULP ⇒ 必须判"不同" | PASS | — |

**检验有分辨力的论证（这是本审计最看重的部分）**：
* [D] 证明"逐位相同"这个判据**不是恒真的**——换一个相对 1e-12 的 dt，`phi` 就分叉到 2.9e-7；
* [E] 证明比较器能看见 **1 ULP**；
* [C] 证明"相同"**不是**因为两条路都没跑：`min_rows` 从 2 改到 1/3 会**改变分段数与每段行数**
  （`nth_max` 仍为 4，但段长不同）⇒ 走的确实是不同的 slab 分解，结果仍逐位相同。
* [B-1] 证明"相同"**不是平凡相同**：8 个 tag 的分段数真的 >1，即并行分支确实被执行。
* 另外：**[C] 的两次运行 + [B] 的 workers=4 运行 = 3 次独立的 4 线程执行**，
  全部与 workers=1 的参考逐位相同 ⇒ 没有观察到**时变竞态**。

### 5.3 **未覆盖**的面（如实登记）

| 未覆盖 | 原因 |
|---|---|
| `per_field=True`（`_advance_perfield`） | 生产不走（`_bk_exp.py:465-467` 不传）；且该函数**完全没接并行** |
| `pair_kernel=True` | 实验性，默认 False |
| `aniso_elastic=True` | 生产不用 |
| `norm_smooth>0` | 生产用 0 |
| `adv_grad='central'/'upwind'` | 生产用 `proj2`；这两条分支里 `par.gradient`（`:3430`）同样是 `depth1` 串行 |
| `workers ∈ {8,…,20}` | 资源限制（§4.3） |
| `reinitialize` 的多线程**数值**逐位性（在 N=96 全尺寸） | 只在 N=64 覆盖了（[B] 段里 reinit 每 2 步触发） |

### 5.4 一条容易被误读的**陈旧结论**（顺手清掉）

`_w2_r1par_N192.log` 的 **P-4 总判定是 `✗ 有差异（分解不安全）`**
（`upwind_flux_vec order=2` slab 与全域差 1.4e8）。
那是**旧探针自己 halo 取法的 bug**（当时代码用 `np.take` 没环绕），
已在 `windowB_par.py:247-255` 用 `np.arange(lo-halo, hi+halo) % n0` 修掉，
并由 `_selftest`（15/15）+ 本审计的 [B] 段（端到端）双重证实。
⇒ **今天读那个日志会得出反向结论**，建议在日志旁加一行"已被 R1 修复"。

---

## §6 生产驱动实际用了几个线程（问题 5）

### 6.1 默认值与实际值

| 位置 | 值 | 证据 |
|---|---|---|
| `_bk_exp.py` `--nthreads` 默认 | **4** | `_bk_exp.py:1005  ap.add_argument('--nthreads', type=int, default=4)` |
| `_bk_closed.py` `--nthreads` 默认（"推荐"） | **2** | `_bk_closed.py:73  ap.add_argument('--nthreads', type=int, default=2)` |
| `_bk_closed.py` 转发给 `_bk_exp.py` | 是 | `_bk_closed.py:149  '--norm-smooth', '0', '--nthreads', str(a.nthreads)` |
| **正在跑的生产任务实际值** | **2** | `ps` 实测：`_bk_exp.py … --nthreads 2 --tag cln11`（PID 4460，已跑 1h46m） |
| 落到引擎哪里 | `ParCtx(workers)` + `PF3D(workers=…)` | `windowB_surface.py:915`、`:1046` |

### 6.2 **参数真的生效了吗？**（本仓库最忌讳的那类问题）

`_r30_wire.py` 复刻 `_bk_exp.py:266-272` 的**逐字**构造调用：

```
--nthreads 1 ⇒  g.par.n=1  g.nthreads=1  g.pf.workers=1     PASS
--nthreads 2 ⇒  g.par.n=2  g.nthreads=2  g.pf.workers=2     PASS
--nthreads 4 ⇒  g.par.n=4  g.nthreads=4  g.pf.workers=4     PASS
```

静态消费者清单（`windowB_surface.py` 里 `workers` 的全部去处，W-3 段打印）：
`:915 self.par = ParCtx(workers)`、`:916 self.nthreads = int(workers or 1)`、
`:1046 PF3D(..., workers=workers, ...)`。**没有第三条路，也没有任何地方事后覆盖它。**
（`:457 self.workers = workers` 属于 `LevelSetSurface`，是**另一个类**。）
⇒ **结论：`--nthreads` 确实生效。本维度未发现"传了没生效"的缺陷。**

### 6.3 但有一个**已经失效的探针**在误导人（必须记账）

`_probe_workers.py`（mtime **2026-09-29 00:53**）在构造之后写：

```python
g.pf.workers = Wk          # :90
g.workers    = Wk          # :91
```

`windowB_par.py` 的 mtime 是 **2026-09-29 01:57** —— 即该探针**早于** R1 并行层 1 小时。
`_r30_wire.py` 的 [W-2] **负对照**实测：构造 `workers=1` 之后再改
`g.workers=4` / `g.pf.workers=4`，**`g.par.n` 仍然是 1**（`g.pf.workers` 只影响 FFT）。
⇒ `_w2_workers.log` 里那句"`advance` 的 CPU/wall 恒在 1.03–1.15 ⇒ **基本单线程**"
**在它测量的那个引擎版本上是对的**，但**今天不成立**：
本审计实测 CPU/wall = **2.72–2.74 @4 线程**。
⇒ 谁再引用那条结论都会得出错误判断。**正确改法是 `g.par.set_threads(n)`（实测生效）。**

### 6.4 一个零风险的收益点

`_bk_closed.py` 默认 `--nthreads 2`，而本审计实测 **2→4 线程 = 3.556→2.474 s/步 ≈ −30%**。
这是**唯一一个"改一个默认值就拿到"的加速**。代价：多占 2 个核（本机共享资源，需用户点头）。

---

## §7 可操作建议（问题 6）

> 排序口径 = **预计收益 ÷ 改动风险**。所有收益都用实测单线程数折算，
> 并同时给出"相对 w=1 步时"和"相对 w=4 步时（2.474 s）"两个口径。

### 🥇 建议 1：把 `pf.sigma_tensor` 的**逐胞装配**接进并行（`elastic_driving`）

* **调用点**：`windowB_surface.py:2714 sig = self.pf.sigma_tensor(None)`
  ← `elastic_driving_pair:2786` ← `advance:3017`；
  实现：`windowB_pf3d.py:235-240 eps0_fields()`（**6×nv = 66 次整场乘加，串行**）
  与 `:281-284 np.einsum('kpq,qk->pk', Lam, Eh)`（串行）。
* **实测**：`sigma_tensor` 单行 **0.5027 s/步**，**完全串行**；
  在 w=4 的 2.474 s 步时里占 **20.3%**（这一块是 w=4 下**最大的单点串行**）。
* **收益上限**：按 `p ∈ {0..5}` 切 6 段并行（≥4 段即吃满 4 线程），
  保守用并行段实测效率 ×2.9 ⇒ **0.503 → 0.17 s，省 0.33 s/步**：
  **−5.8%（相对 w=1）/ −13%（相对 w=4）**。
* **依据 / 为什么逐位相同**：`eps0_fields()` 里每个胞的求和是
  `Σ_v e0v[v,p]·phi[v]`（**在 v 上**），沿 `p` 切片不改变任何胞的求和次序与结合次序；
  `e[3:] *= 2.0` 与之后的 `Lam` einsum 按 `k`（6）切也同理。
  ⇒ 可用现成的 `ParCtx.map0(fn, 6)`，**不需要新算子**。
* **风险**：**低**（切片不变、需用 §5.2 的 uint8 逐位比较器验收）。
  ⚠ 注意 `sigma_tensor` 内部已有 `sfft.fftn(workers=self.workers)`，改它的时候
  别把 FFT 的 `workers` 弄丢。

### 🥈 建议 2：**瘦身 `_minmod`（减少 N³ 临时量）** —— 收益最大的一条，但不是"并行化"

* **调用点**：`windowB_surface.py:42-44`，被 `:413` / `:414` 调用；
  **实测 72 次/步、0.9700 s/步 = 单线程步时的 14.8%**。
* **为什么贵（实测标定，不是猜）**：
  `_minmod` 一行 `0.5*(np.sign(a)+np.sign(b))*np.minimum(np.abs(a),np.abs(b))`
  会产生 **7 个 N³ 临时量**；单次实测 **0.0134 s**（微基准），
  换算 DRAM 流量 ≈ 7×2×7.08 MB = **99 MB/次 ⇒ 7.4 GB/s**（低于同机 triad 20 GB/s，
  说明它同时被"多趟 + 分配"拖累）。72 次 × 99 MB = **7.1 GB/步**。
* **收益上限**：改成"预分配 scratch + `out=` 原地链"（读 a、读 b、写 out 共 3 趟 ≈ 21 MB/次）
  ⇒ 单次 ~0.003 s，**0.97 → ~0.25 s，省 0.7 s/步**
  = **−12%（相对 w=1）/ −28%（相对 w=4）**。
  【估算，非实测】依据是流量账 + `np.add(3N³)` 实测 0.0053 s（63.7 MB ⇒ 12 GB/s）。
* **风险**：**低但有一个坑**。`minmod` 在 `a=0 或 b=0` 时当前实现给 **−0.0**，
  而 `np.where` 版会给 **+0.0**；`np.array_equal` 认为它们相等，
  **但本仓库的逐位比较器（uint8 视图）会判 FAIL**。⇒ 要么保留符号表达式，
  要么同步修改判据并**显式记账**（`AGENTS §3.22`：判据要写清楚"什么量在物理上应该相同"）。
* 顺带：`upwind_grad2`（`:47-72`，reinit 的热核，实测 0.2175 s/次 × 2100 次/次 reinit）
  是同一类写法，**同一条瘦身规律**适用。

### 🥉 建议 3：把 `advance` 内联的逐胞块接到**已经写好却没人调用**的 `ParCtx.where/einsum_ii/norm_last`

* **调用点与实测**（全部串行，合计 **≈0.34 s/步 = 5.2%**）：

  | 行 | 内容 | 实测 s/步 | 对应的现成算子 |
  |---|---|---|---|
  | `:3271` | `w_of = np.where(...)` | 0.0683 | `where` |
  | `:3080` | `nd_ref = np.where(...)` | 0.0314 | `where` |
  | `:3064` | `np.linalg.norm(ndir_, axis=-1)` | 0.0287 | `norm_last` |
  | `:3079/:3083` | `np.where` ×2 | 0.0444 | `where` |
  | `:3272/:3273` | `w_of` 相关 | 0.0325 | `where`/`einsum_ii` |
  | `:3084/:3263` | `np.einsum('...i,...i->...')` | 0.0212 | `einsum_ii` |
  | `:3081/:3281/:3373` 等 | 余下 `np.where` | ≈0.10 | `where` |

* **收益上限**：按这些算子在 N=96 实测的 ×1.2–2.4（§4.2 表）⇒ **省 0.15–0.20 s/步**
  = **−2.7~−3.5%（相对 w=1）/ −6~8%（相对 w=4）**。
* **依据**：三个算子的**逐位相同性已由 `_selftest` 15/15 判过**，且**零新代码**。
* **风险**：**低**。唯一要注意的是 `np.where(cond[...,None], x, y)` 这类**带广播的掩模**
  不在 `ParCtx.where` 的语义里（它只在 `axis=0` 切三个同形操作数）
  ⇒ `:3074-3083` 那几处广播写法**不能直接替换**，要显式改写成同形再切。

### ❌ 明确**不推荐**的两条（免得别人走弯路）

* **EDT 速度延拓块**（`:3344/:3346`，0.155 s/步 = 2.4%）：`distance_transform_edt`
  是**全局最近点变换**，沿 axis=0 切片会让段内的点从**错误的段**取最近界面胞
  ⇒ **不逐位相同**（这正是 `_band_bbox` 在 reinit 上被实测否决的同一类陷阱，
  见 `windowB_surface.py:3757-3766`）。要么不并行，要么换算法，收益 0.15 s 不值得冒险。
* **`_geom_k` 的负载均衡微调**：实测 `advance.geom_k` 从 2.034 → 0.551 s = **×3.69**
  （4 线程效率 **92%**），已经没有多少空间。

### 📌 附带：`reinitialize` 的并行很差，但它是**尖峰**不是**底噪**

* 实测（N=96 / 21 配对 / `reinit_iters=100`，`_r30_reinit_N96.log`）：
  **w=1 413.5 s → w=4 323.5 s，只 ×1.28**。
  分解：`upwind_grad2` 被调用 **2100 次**，单次 0.197 s（w=1）/ 0.150 s（w=4）
  ⇒ reinit 的耗时 **≈100% 是 `upwind_grad2`**，而它自己的并行上限只有 ×1.6。
* 生产 `--reinit-dt 1e-4` + `dt≈1.7e-7 s` ⇒ 约每 **600–1900 步**触发一次；
  `_w2_bk_cln11.log` 里 step 800→900 的 100 步均值从 2.71 跳到 3.79 s/步，
  与该处一次 reinit 的量级吻合。
* ⇒ **想再压这个尖峰，只能压 `upwind_grad2`（=建议 2 的同一类瘦身）或降低 `reinit_iters`**。
  后者**不建议动**：仓库记账（`windowB_surface.py:873-876`，依据 `_tune_reinit.py`）说
  `iters=30` 时零等值面停在 0.025 µm、`iters≥100` 才落到解析值 0.012 µm；
  降到 20 会省 5 倍机时但**零等值面会偏 0.013 µm ≈ 0.1 dx**（**我没有复测这一点**，
  只是引用仓库记账）。

---

## §8 我没能确定 / 没测的事（明确列出）

1. **workers>4 的加速比**：未测（资源纪律 + 别人在跑生产）。§4.3 的 ×2.3–2.6 是【推理】。
2. **`_minmod` 瘦身后的实际收益**：0.7 s/步是【估算】，只做了流量账与单算子实测标定，
   **没有真的改写并测**（本审计是只读的，不改代码）。
3. **§5.2 的逐位判据只在 N=64 上做过**；N=96 上我只做了**性能**实验，**没做** workers=1 vs 4 的
   逐位对比（一次 N=96 双跑 ≈ 4 分钟；如需要可补：`_r30_identity.py 96 3 0`，
   注意它的板条尺寸是**小尺寸冒烟配置**（3/8/20 Δx），不是生产尺寸）。
4. **`nucleate()` 的耗时占比**：本审计未单独测（它不在 `advance` 内，
   且生产 `--nuc-every 0` + athermal 下是稀疏事件）。**未核实**。
5. **`-0.0` 与 `+0.0` 是否在本仓库的物理口径上等价**：`_minmod` 建议 2 里提到这个坑，
   我**没有**去查下游有没有对 `minmod` 结果做符号敏感的操作。**未核实**。
6. **`_probe_workers.py` 是否需要修**：它现在会给出误导结论。
   我**没有改它**（只读审计），但 §6.3 已给出证据与正确改法。
7. **>4 线程时 `scipy.fft` 的 `workers` 与 `ParCtx` 线程数争抢**：两者共用同一台机器的核，
   本审计没有做"两者都调大"的对照。

---

## §9 复现命令（全部在 WSL，模板与用户给定一致）

```bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python

# §2.3 并行路径真实命中（不靠读代码）
$PY -u _r30_pathprobe.py 48 4                      # → _r30_pathprobe.log

# §3 逐行/逐算子耗时（N=96 / 11 板条 / 单线程；约 2 分钟）
$PY -u _r30_prof_line.py 96 1 2                    # → _r30_prof_line_N96_w1.{log,json}
$PY -u _r30_table.py _r30_prof_line_N96_w1.json    # → 算子表

# §4 加速比（两次独立测量；每次约 2 分钟）
$PY -u _r30_speedup.py 96 3 1,2,4                  # → _r30_speedup_N96.log
$PY -u _r30_microbench.py 96 3 1,2,4               # → _r30_microbench_N96.log

# §5 正确性（约 1 分钟；第三参数 1 = 开 ψ 通道）
$PY -u _r30_identity.py 64 3 0                     # → _r30_identity_N64.log
$PY -u _r30_identity.py 64 3 1                     # → _r30_identity_N64_film.log
$PY -u windowB_par.py 64 4                         # 仓库自带算子级自检

# §6 接线核查（秒级）
$PY -u _r30_wire.py                                # → _r30_wire.log

# §7 附带：单次 reinitialize 代价（约 12 分钟，21 配对 × iters=100 × w1/w4）
$PY -u _r30_reinit.py 96 1,4                       # → _r30_reinit_N96.log
```

---

## §10 本审计新增的文件（**未修改任何已有文件**）

| 文件 | 说明 |
|---|---|
| `_r30_prof_line.py` | 逐行计时器（`sys.settrace`，只跟 `windowB_*.py`） |
| `_r30_table.py` | 逐行 → 算子表聚合 |
| `_r30_speedup.py` | workers 标度 + `par.report()` 自证 |
| `_r30_microbench.py` | 21 个算子标度 + triad 带宽天花板 |
| `_r30_identity.py` | 端到端逐位判据 + 正/负对照 |
| `_r30_pathprobe.py` | ParCtx 算子分段数探针 |
| `_r30_wire.py` | `--nthreads` 接线核查 + 旧探针负对照 |
| `_r30_reinit.py` | 单次 `reinitialize` 代价 |
| `_r30_prof_line_N96_w1.{log,json}`、`_r30_speedup_N96{,_rerun}.log`、`_r30_speedup_N96.json`、`_r30_microbench_N96.log`、`_r30_identity_N64{,_film}.log`、`_r30_pathprobe.log`、`_r30_wire.log`、`_r30_reinit_N96.log` | 原始产物（报告里每个数字都指向其中之一） |

> ⚠ 同目录下还有**另一个代理**的 `_r30_*.py` / `_r30_*.log`（如 `_r30_gk.py`、`_r30_psi.py`、
> `_r30_selfac_struct.py`、`_r30_identity.log`）。它们**不是**本审计的产物，本审计未读取、未修改。
> 工作区是共享的 ⇒ 请用下面的指纹确认你读到的是不是本报告依据的那一份。

### §10.1 证据指纹（SHA256，2026-09-30 06:2x 冻结）

```
36b3ec7acd60644b1e90db1c82ccbed6a31eee4593cf2b10869604cfd2b38361  _r30_prof_line.py
cca51d0e7b3022d731587c04c72576fa8d94f2994d79f51a95bc60dcee06f5cb  _r30_table.py
e7a59822240b8e82ed6dae6a6ba56973876dd12ccad3a62d5c127adead801bb4  _r30_speedup.py
fbd74364c338c3fb893c356e02e9c027938854d8d44dde3b2dbbd765f3d9720b  _r30_microbench.py
03b7d1061aff102888877d6325bfd244a790f3837800040a775874bebc3b4a4f  _r30_identity.py
eba2dfbb77b821c40232634f0aa7665d80266f7fa048af1ef1ea7bdd189ce16a  _r30_pathprobe.py
2259cc6cc82837548bc51d52c3d088ebaa8cb5f65671b0019e4da66605ae9f05  _r30_wire.py
3a516f83e10389dd852cabcb18d163a36fc95d8378ff770af7c48db1b96a8f17  _r30_reinit.py
b7931de7ff7e1fc9ce2ecb8e0fa3733969099ac7fe48976cc309a37126118a37  _r30_prof_line_N96_w1.log
5678ef5784dafb07585fded638401957a0e79a18a3b56238fc127b63da552a66  _r30_prof_line_N96_w1.json
d4058ad2fd21d4b2d9e362c84992a08c4b31eaaddbfe41a04716ddf987f6fcb5  _r30_speedup_N96.log
0fd8766c62ec265f5f639116e667ae380e2597a59459a3096d41ac24ea469133  _r30_speedup_N96_rerun.log
e96bcbf749419e1f022547df2a14694637372b2fdeaef18408b754ebfd5f2328  _r30_speedup_N96.json
55a68868ae369b78918cd77337d0e83f17f0b6c2a8001f7b45427160af7cae61  _r30_microbench_N96.log
c936902b6e9986e467d2b11bf09418248e3d8710d79dfbeb530725b39f431d93  _r30_identity_N64.log
49034fc159aea5d54c7d95ca0436f8727dfe7c1140c0120e05350bc931899800  _r30_identity_N64_film.log
bd85c8145761b2128a0c5a70cf0c0d97a409ba26585d52b88e4885936a10218c  _r30_pathprobe.log
c855fec4aef1792bd9669f11642c103d2ba69310cfaec37bfd54f09c8872823f  _r30_wire.log
e301b50ac5c8b2f6fd6581d2bd8dc3dd1bdd0249062a138293253f353c86d0cf  _r30_reinit_N96.log
```

验证：`sha256sum -c <(上面这段)`（或逐行比对）。
❌ 若 `_r30_*.log` 的哈希对不上 ⇒ 有人重跑过，**报告里的数字仍以本表对应的那一版为准**。
