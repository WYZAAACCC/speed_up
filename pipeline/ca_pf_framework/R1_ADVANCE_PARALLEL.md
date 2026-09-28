# R1 任务②：`advance` 为什么只能单核，以及改造结果

> 日期 **2026-09-29** ｜ 引擎 `windowB_surface.py` + 新增 `windowB_par.py`
> 全部数字都有对应的日志文件；**推理与实测分开标注**。

---

## §0 一句话结论

`advance` **不是"不能并行"，而是"并行度从来没接进去"**。
接进去之后实测 **×2.57 @16 线程（N=192，真实计算盒）**，
**逐步逐位相同**；而**上限不是核数，是本机 DRAM 带宽（triad ×2.08）**。

---

## §1 诊断：为什么表现为单核

### 1.1 事实（`grep` 可核）

`workers` 这个参数在改造前**只有一个消费者**：

```
windowB_pf3d.py:191   self.workers = workers
windowB_pf3d.py:262   return sfft.fftn(x,  axes=self.axs, workers=self.workers)
windowB_pf3d.py:265   return sfft.ifftn(x, axes=self.axs, workers=self.workers)
```

即**只有谱法弹性的 FFT** 用到了它。而 `advance` 里的**全部**逐胞算子 ——
迎风通量 `upwind_flux_vec`、`_minmod`、`argmin`（winner/runner-up、`region()`）、
`np.gradient`、`np.einsum`、`np.where`、`np.linalg.norm` —— 都是**直接调用 numpy**，
numpy 的逐元素循环**默认单线程**。

⇒ 一次 `advance` 就是**几千个串行的全场 pass**，自然只跑在一个核上。

### 1.2 反推 pass 数

实测单线程 triad（读2写1）带宽 **11.08 GB/s** ⇒ 在 N=192（N³=7.08e6，一个数组 54 MB）
上一个"读2写1"pass ≈ **14.3 ms**。`advance` 实测 34.8 s/步（`_w2_cost_N192.log`）
⇒ **≈ 2400 个 DRAM 级 pass/步**。

其中 `upwind_flux_vec(order=2)` 单次调用实测 **0.854 s ≈ 60 pass**，
而它被**每个活跃场各调用一次**（最多 13 次）≈ **11 s** ⇒ **单步最大的一块**。

---

## §2 能不能并行：实测（不是推理）

### 2.1 numpy 的逐元素算子**确实释放 GIL**

判据是**双对照**（`_r1_par.py`，`_w2_r1par_N192.log`）：

| 对照 | th=1 | th=2 | th=4 | th=8 | th=16 | th=20 |
|---|---|---|---|---|---|---|
| **正**：`time.sleep`，20 个任务 × 0.05 s | 0.0502 | 0.0511 | 0.0513 | 0.0526 | 0.0550 | **0.0542** |
| **负**：纯 Python 循环（400k 次） | 0.0130 | 0.0112 | 0.0122 | 0.0137 | 0.0115 | **0.0131** |

正对照 = 20 个任务**并行**完成（串行要 1.0 s）⇒ **量具能分辨真并行**；
负对照 = 完全平坦（GIL 串行）⇒ **量具能分辨假并行**。
两个对照都通过 ⇒ 下面的标度是真的。

### 2.2 逐算子线程标度（加速比 t(1)/t(nth)）

| 算子 | t(1) s | th=2 | th=4 | th=8 | th=16 | th=20 |
|---|---|---|---|---|---|---|
| `np.exp` | 0.025 | 1.47 | 3.24 | 3.19 | 2.46 | 2.74 |
| `np.where` | 0.047 | 2.17 | 3.95 | **4.58** | 4.52 | 4.50 |
| `np.linalg.norm(axis=-1)` | 0.110 | 1.65 | 2.68 | 4.05 | **5.26** | 5.26 |
| `argmin(13 场)` | 0.216 | 1.64 | 2.55 | 3.28 | **4.13** | 4.05 |
| **winner+runner-up(13 场)** | 1.486 | 1.74 | 2.98 | 4.77 | **6.79** | 6.01 |
| `upwind_flux_vec o2` | 0.854 | 1.73 | 2.21 | **2.71** | 2.53 | 2.43 |
| `np.gradient` | 0.060 | 1.37 | 2.27 | 2.33 | 1.72 | 1.32 |

### 2.3 **硬天花板 = DRAM 带宽**

| | 单线程 | 饱和（≥8 线程） | 比值 |
|---|---|---|---|
| triad（读2写1） | **11.08 GB/s** | **23.0 GB/s** | **×2.08** |

⇒ **纯流式算子最多 ×2.1**（`upwind_flux_vec` 实测 ×2.71 略高，因为它不是纯流式）；
**延迟受限**的算子（`where` / `argmin` / winner-runner-up / `norm`）能吃到 ×4–6.8。
⇒ **并行化的收益由"算子的性质"决定，不是"有多少核"。**

---

## §3 改造

新增 `windowB_par.py`：`ParCtx`（**共享内存多线程 + 空间切片**）。

接入点（`windowB_surface.py`）：

| 位置 | 改法 |
|---|---|
| `LevelSetMulti.__init__` | 新增 `self.par = ParCtx(workers)`（`workers` 语义扩展，见 §5）|
| `region()` | `ParCtx.argmin`（空间切片）|
| `advance`：winner/runner-up | `ParCtx.argmin2` |
| `advance`：几何循环 `for k in act` | `for_each`（按场并行，写入位置互不相交）|
| `advance`：推进循环 `for k in range(nreg)` | `for_each`（**天然无依赖**，不需要 halo）|
| `advance`/`elastic_driving`：`np.gradient` | `ParCtx.gradient` |
| `sussman_reinit` | 逐胞算子并行（迭代循环仍串行 —— 见下）|
| `elastic_driving` 的两处 `for v` | `for_each` |

### 3.1 正确性：H-1「逐位相同」是硬门槛

`ParCtx` 的所有核都在**空间**（axis 0）上切片，逐胞归约次序**不变**
（`argmin`/`einsum`/`norm` 的 axis 归约次序没动）。halo 必须**按 stencil 的周期性**分两类：

* **`np.roll` 系（周期 stencil）⇒ halo 必须环绕取**（`np.take(..., mode='wrap')`）。
  ⛔ 不环绕时最末一段的 `np.roll` 会拿**自己的开头**当邻居。
  **我的探针第一版就栽在这里**，判 P-4 FAIL（差 1.4e8）——那是**探针的 bug，不是算子的 bug**；
  修正后逐位相同。
* **`np.gradient` 系（盒边界用单边差分）⇒ halo 必须在盒边界截断**。
  用环绕 halo 会让边界胞从"单边"变成"中心" ⇒ 不同。

### 3.2 H-3：固定大小线程池**不能嵌套** ⇒ 必须有重入守卫

若 n 个任务各自再向同一个池提交子任务，池被占满 ⇒ 子任务永远排不上 ⇒ **死锁**。
`ParCtx` 用 thread-local 深度计数：**已在并行区内的线程，其嵌套调用一律串行**
（结果逐位相同，因为所有核都是"切片不变"的）。

### 3.3 一处**自我纠正**（记账）

我一度以为 `advance` 的推进循环里写了 `self.dG_max`（共享标量）⇒ 并行会竞态，
于是加了一行 `self.dG_max = max_k max|vnk|/M` 去"修"它。
**逐行核对后确认：那个循环体里根本没有 `dG_max` 赋值** —— 它只在循环**之前**定值
（`windowB_surface.py` 的 `max|dG_cell|` / `max|dG_cell·Mfac|`），**无竞态**。
我那一行是**凭想象加的行为改动**，会静默改掉 `dG_max` 的语义
（`suggest_dt` 与 `_t21b_1step.py` / `prod_boxB_mob.py` / `_chk_m6_route.py` 都在读它）
⇒ **已删除**。（与 `AGENTS §3.24`「改一半比不改更危险」同类。）

### 3.4 又一处自我纠正：并行 reinit **复制**了迭代循环

`ParCtx.sussman_reinit` 最初**复制**了一份 Sussman 迭代、且**只有并行路径**支持子盒
⇒ 那会让**线程数变成物理参数**（`nthreads=1` 与 `8` 走不同代码）。
现已改为**纯委托**：唯一实现是 `windowB_surface._sussman_core`，
"全域/子盒 × 单线程/多线程"**四条组合共用同一段代码**。

---

## §4 验证

| 判据 | 结果 |
|---|---|
| `windowB_par._selftest`（15 个核 vs 单线程，逐位） | **15/15 逐位相同** |
| `_r1_smoke.py` **端到端**（N=32，3 步 + 强制 reinit，1 vs 4 线程） | `phi` / `region` / `dG_max` / `elastic_driving` **全逐位相同** |
| E-3 **正对照**（dt 差 1e-7 相对 ⇒ 必须不同） | **不同** ✓（证明守卫有分辨力） |
| E-4 并行**真的被调用** | `advance.k_loop` / `geom_k` / `argmin2` / `gradient` … 均 ≥4 分段 |
| `_r1_reinit_bbox.py` B-4（reinit，1/2/4 线程） | **逐位相同** |

### ★ 用户要求的"真实计算盒里的并行加速"—— `_r1_partest.py --mode scale`

N=192、24 µm 盒、64 核 RVE、`adv_grad='proj2'`、每档 best-of-2：

| 线程 | `elastic_driving` s | **`advance` s** | 合计 s/步 | **加速比** | 与 th=1 逐位 |
|---|---|---|---|---|---|
| 1  | 6.04 | **48.73** | 54.77 | 1.00 | — |
| 2  | 5.57 | **37.22** | 42.79 | ×1.31 | **True** |
| 4  | 4.41 | **24.85** | 29.26 | ×1.96 | **True** |
| 8  | 4.16 | **22.51** | 26.67 | ×2.17 | **True** |
| 12 | 3.89 | **19.72** | 23.61 | ×2.47 | **True** |
| 16 | 3.64 | **18.97** | 22.61 | **×2.57** | **True** |

**正对照**：参考态与本步结果的最大变化 = **2.115e-07**（确认这一步**真的在演化**，
不是"两次都没动所以相同"）。
⚠ 记账：这组数是在**另外 3 个单线程作业同时运行**的情况下测的 ⇒ 绝对值偏高、
加速比可能偏低（保守）。

---

## §5 R8 记账

* **数值逐位不变** ⇒ **不触发 R8**，归档读数**不需要重跑**。
* ⚠ 但**运行时间会变**：全仓多处传 `workers=4`（原先只影响 FFT，现在也影响 level-set 核）
  ⇒ 那些脚本现在更快，**数不变**。
* ⚠ `nthreads <= 1` 时全部算子**逐位退回原实现**（不做任何拼接）。

---

## §6 还没做的（如实登记）

| # | 项 | 状态 |
|---|---|---|
| 1 | **减少 pass 数**（循环融合/原地运算） | 未做。**理论上限比并行更大** —— 当前 2400 pass/步，融合掉一半就是 ×2，且与并行叠加。 |
| 2 | `_finish_advance` 里 `np.argsort(13 场)` 的 (13,N³) int64 临时量 | 只在 `reinitialize()` 里（0.177 s @N=96，小） |
| 3 | `elastic_driving(soft=True)` 的 `eps0_fields` 72 次整场乘加 | 未优化（`soft=True` 是生产默认）|
| 4 | `extend='edt'` 的两次 `distance_transform_edt` | **scipy 单线程、不可并行**；未测占比 |
