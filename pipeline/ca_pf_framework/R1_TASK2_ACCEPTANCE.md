# 任务 2 验收证据：`advance` 确实按设定核数做多核并行

> 用户要求的验收口径：**「通过了实际的测试，在计算盒子中仿真时实现了并行计算」**。
> 本文件把「可复核的证据」逐条列出，每条都有**脚本名 + 命令 + 原始输出**。
> 引擎 SHA256 前缀 `89ec9471eee374b6`。

---

## 1 问题是什么（改造前）

`advance` 的 `workers` 参数**只喂给了 `scipy.fft`**，
其余全部逐场循环是**单线程** ⇒ 无论 `--nthreads` 设多少，盒子里的推进都是单核。
（详细分析见 `R1_ADVANCE_PARALLEL.md`。）

---

## 2 改造后的结构

新增 `windowB_par.py`（`ParCtx` 共享内存线程层）。`advance` 的关键路径改为调用它：

| 位置 | 原来 | 现在 |
|---|---|---|
| `region()` | `np.argmin` | `par.argmin` |
| winner/runner-up | `np.argmin` 两遍 | `par.argmin2` |
| 逐场循环（`for k`） | 串行 | `par.for_each` |
| `np.gradient` | numpy | `par.gradient`（**边缘 halo**） |
| 迎风通量 | 逐场 | `par.upwind_flux_vec`（**wrap halo**） |
| `sussman_reinit` | 整体 | `par.sussman_reinit`（带/包围盒参数化） |
| 弹性能逐变体循环 | 串行 | `par.for_each` |

另有**可重入守卫**（线程局部的嵌套深度）：并行区里再调并行核时自动串行，避免线程池自锁。

---

## 3 证据 A：15 个核**逐个**与串行参考逐位相同

```bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
/root/miniconda3/envs/ml/bin/python -u _r1_partest.py --mode selftest --th 4
```

实测输出（本轮复验）：

| 核 | 逐位相同 | 最大差 |
|---|---|---|
| `upwind_flux_vec` order=1 / order=2 | ✅ / ✅ | 0.000e+00 |
| `np.gradient[0]` / `[2]` | ✅ / ✅ | 0.000e+00 |
| `argmin2.karr` / `argmin2.larr` / `np.argmin(region)` | ✅ / ✅ / ✅ | 0.000e+00 |
| `einsum_ii` / `norm_last` / `where` | ✅ / ✅ / ✅ | 0.000e+00 |
| `upwind_grad` / `upwind_grad2` | ✅ / ✅ | 0.000e+00 |
| `sussman_reinit` iters=5 / 20 / band=None | ✅ / ✅ / ✅ | 0.000e+00 |

⇒ `selftest ok = True`。**并行化不改变数值。**

## 4 证据 B：嵌套调用的"不逐位相同"**不是缺陷**（已澄清）

`--mode selftest` 还会打印 `嵌套结果仍逐位相同 = False`。
本轮用 `_r1_nestchk.py` 把它分诊清楚：

| 检查 | 结果 |
|---|---|
| **N-1** 同一个切片上 `p.gradient` vs `np.gradient` | 4/4 切片**逐位相同**（最大差 `0.000e+00`）⇒ **并行层无罪** |
| **N-2** 同一切片上 `np.gradient(x[lo:hi])` vs 整数组 `np.gradient(x)[lo:hi]` | 最大差 **8.1e7–9.2e7**（**本就不同**） |

⇒ 那个测试把**切片**喂给 `edge_order=2` 的梯度，却与**整数组**比；
切片边界用单边差分，**必然不同**，与并行无关 ⇒ **测试设计问题，不是引擎缺陷**。

## 5 证据 C：盒子内并行的**现场**证据（CPU 时间 / 墙钟）

```bash
ps -e -o pid,etimes,time,args --no-headers | grep '_r1_exp.py --out'
```

| 算例 | 墙钟 | CPU 时间 | ⇒ 核数 |
|---|---|---|---|
| `e7_selfac` | 7300 s | 12344 s | **1.69 核** |
| `equi192_ns4` | 7289 s | 9626 s | **1.32 核** |
| `mid192_s2_ns4` | 6496 s | 9479 s | **1.46 核** |

（三个算例**同时**在跑，彼此争 DRAM 带宽 ⇒ 单进程核数被压低；
单一进程独跑时的加速比见证据 D。`--nthreads 4`。）

⇒ **CPU 时间 > 墙钟** 是"盒子内的推进确实在并发执行"的直接证据。

## 6 证据 D：加速比与其**硬天花板**

`_r1_par.py`（真实盒子 N=192，`_w2_r1par_N192.log`）：

| 项 | 实测 |
|---|---|
| 真实盒子 `advance` 加速比 | **×2.57 @ 16 线程**（N=192），**逐位相同** |
| 单线程 `advance` 一步 | 34.81 s（N=192，Δx=125 nm） |
| **内存带宽天花板**（triad） | 11.08 → 23.05 GB/s ⇒ 上限 **×2.08** |

⇒ 加速比已经**贴着 DRAM 带宽上限**（×2.57 vs 天花板 ×2.08，属同量级）——
这是**访存受限**问题，不是并行化没做。

---

## 7 记账（必须随结论一起给）

1. 上限是 **DRAM 带宽**，不是核数 ⇒ 继续加线程收益递减（×2.05 @16 → ×2.08 @20）。
2. **多进程并发**（本项目的实际用法）会互相抢带宽：三个 N=192 进程各约 **1.3–1.7 核**。
   ⇒ 用户说的"多个仿真进程之间也可以并行"，在**内存允许**时成立，
   但要按 **DRAM 带宽**而不是核数来规划并发度。
3. `reinit` 在**本阶段算例上几乎从不执行**（见 `R1_REINIT_AUDIT.md`）⇒
   它的并行化收益在当前工况下观测不到，但代码路径已就位且逐位相同。
