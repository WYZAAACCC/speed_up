# R578 —— 算子优化第三轮：goal §(3) 落地 + 分配器的**长跑 RSS 轨迹**（结案）

> 本轮目标：① 完成 goal §(3) 的三个"逐位不变"的小项；② 把 R577 §2.5 要求的三条证据补齐
> （长跑 RSS 轨迹、真实路径、显式档位）。
> 只写**实测**；推理标【推理】。

---

## §0 结论摘要

| # | 结论 | 证据 |
|---|---|---|
| **A** | `k_loop_mode='act'`（推进循环只遍历活跃场）**逐位相同**、**1.064×** | `_r578_kloop.py` / `_r578_kloop_ab.sh` / `_r578_smoke.sh` |
| **B** | `act_mode='bincount'`（活跃集用线性计数替代三次排序）**同一个升序集合**、微基准 **6.12×** | `_r578_opt3.py` |
| **C** | `argmin2_mode='copyto'`（runner-up 用 `np.copyto(where=)`）**逐位相同**、微基准 **1.265×** | `_r578_opt3.py` |
| **D** | ★★★ 分配器结案：**mmap/trim 阈值在 N=96/200 步上只把峰值 RSS 降 8%**（1227→1128 MB），而**墙钟贵 1.64–1.78×**；`series.csv` **逐位一致** | `_r578_rsstrace.sh` |

---

## §1 goal §(3)① 与 ③：先量后改（`_r578_opt3.py`）

| 候选 | 旧 | 新 | 逐位 | 微基准（交错配对中位） |
|---|---|---|---|---|
| ① `argmin2` runner-up 扫描 | `l[mj]=j` / `best[mj]=pj[mj]`（布尔花式索引，每次走 `np.nonzero`） | `np.copyto(l, j, where=mj)` / `np.copyto(best, pj, where=mj)` | **max\|Δk\|=0, max\|Δl\|=0** ✅ | **1.265×** [1.132, 1.444] |
| ③ 活跃集 `act` | `unique(concat(unique(karr), unique(larr)))`（**三次 O(N³ log N) 排序**） | `flatnonzero(bincount(karr)+bincount(larr))`（**线性**） | **同一个升序集合**（`array_equal`） ✅ | **6.12×** [5.44, 7.14] |

**负对照**：`argmin2` 扰动一个胞的 winner ⇒ `max|Δ| = 5`（量具有分辨力）。
⚠ 这条负对照**我写错了两次**，都留档（`AGENTS.md` 教训 15「被比较的量本身是否随扰动变化？」）：
* v1 `F2[0,0,0,0] -= 0.5` —— 把场 0 变小 ⇒ 场 0 **仍然是** argmin ⇒ `k` 不变 ⇒ 假 FAIL；
* v2 `F2[0,0,0,0] += 10` —— 但那个胞的 argmin **本来就不是场 0**（随机数据，1/9 概率）⇒ 也不变；
* v3（正确）：**先找一胞、确认它当前的 winner 就是场 0**，再抬高场 0。

---

## §2 goal §(3) 的新项：`k_loop_mode='act'`

### §2.1 等价性（可证，不是近似）

`_step_k(k)` 的第一件事是

```python
vnk = coef * (np.where(karr == k, 1.0, 0.0) - np.where(larr == k, 1.0, 0.0))
if not np.any(vnk != 0): return
```

`k ∉ act = unique(karr) ∪ unique(larr)` ⇒ `karr == k` 与 `larr == k` **逐位全 False**
⇒ 括号恒 `0.0` ⇒ `vnk = coef * 0.0 ≡ ±0.0`（`coef` 实测无 inf/NaN ⇒ 不会出现 `0*inf=NaN`）
⇒ `np.any(vnk != 0)` 为 False ⇒ **必定 return，不写任何场**。

⇒ 把 k 限定在 `act` 上，**跳过的是"什么也不做"的调用**。

### §2.2 逐位判据（`_r578_kloop.py`，N=48/nv=8，两种构型各 5 步）

| 构型 | V1 逐位（5 步内 max\|Δφ\|） | V2 活跃集 | V3 负对照 |
|---|---|---|---|
| F1-only（3 个种子） | **0.000e+00** ✅ | nact=4（0 < 4 < nreg=9）✅ | **8.330e-08** ✅ |
| F1+F3（+3 个同变体种子） | **0.000e+00** ✅ | nact=7 ✅ | **1.324e-07** ✅ |

**V3 负对照的做法**（v1 写错、已改）：v1 去劫持 `np.unique` 让它少返回一个 k ——
那会**同时**改掉 `advance()` 里所有其它 `np.unique` 调用（诊断块、`_bbox_pad`…）
⇒ 差异出现了，但**不是"少遍历一个活跃场"造成的**（`AGENTS.md` 教训 21「隔离实验必须只差一个因素」）。
现改为**只包 `ParCtx.for_each` 的 `advance.k_loop` 这一路**，且**只在 `act` 臂上丢最后一个元素** ——
`act` 的每个元素**按定义**都是活跃场 ⇒ 丢掉的**一定**是活跃场。

### §2.3 墙钟与计数回归（`_r578_kloop_ab.sh`，N=64/nv=24/4 线程，交错 3 轮）

| 轮 | FULL `range(nreg)` | ACT `unique(karr∪larr)` | 配对提速 |
|---|---|---|---|
| 1 | 0.4293 | 0.4025 | 1.067× |
| 2 | 0.4149 | 0.4048 | 1.025× |
| 3 | 0.4380 | 0.4116 | 1.064× |

**中位 1.064×**（区间 1.025–1.067）。

**计数回归（硬证据）**：`adv.step.vnk` **25.00 → 4.00 次/步**（nreg=25、活跃场=4）；
`adv.step.advphi` 两臂都 **4.00/步**（活跃场没变）✅。

### §2.4 真实路径冒烟（`_r578_smoke.sh`，`_bk_exp.py` 30 步）

| 判据 | 结果 |
|---|---|
| S-1 两臂 exit 0 / Traceback = 0 | ✅ |
| S-2 `act` 臂 banner **列出** `k_loop=act` | ✅ |
| S-3 两臂 `series.csv` **共有列 96 个逐位一致**（max 相对差 **0.000e+00**） | ✅ |
| 物理判决与归档 `_w2_r569_off.log` 一致（`nslab_n 1→2 / nf3_col 0→1 / F3 面积 1.5347`） | ✅ 逐字相同 |

---

## §3 分配器结案：长跑 RSS 轨迹（`_r578_rsstrace.sh`）

**这是 R577 §2.5 第①条要求的证据**，也是"**峰值降 10% ≠ 长跑不涨**"这句话的检验。

工作负载与 `_r30_regress.sh` **完全同一条命令行**（N=96、200 步、2 线程），每 5 s 采一次
`/proc/<pid>/status` 的 `VmRSS`。

| 臂 | 采样点 | RSS 首 | RSS 末 | **RSS 峰** | 后半段斜率 | 墙钟（采样数代理） |
|---|---|---|---|---|---|---|
| **PLAIN**（不设 MALLOC_*） | 91 | 3 MB | **1185 MB** | **1227 MB** | 仍在爬 | 91 点 |
| **TUNED**（三个变量全开） | 125 | 2 MB | 475 MB | **1128 MB** | 剧烈振荡 | 125 点 |

**读法（结论与当年的假设相反）**：
1. **峰值**只差 **8%**（1227 → 1128 MB）。而**决定会不会撞 swap 的就是峰值**
   ⇒ mmap/trim 阈值在**这个规模上买不到内存安全**。
2. **末态**差很多（1185 → 475 MB）—— 但 `_bk_exp.py` **跑完就退出**，
   "进程末尾释放了多少"对单次跑没有意义。
3. TUNED 的轨迹**剧烈振荡**（320/468/502/984/473/572/932/923/650/932/529/616/517/1058/1118）
   —— 那是 mmap/munmap 的锯齿；PLAIN 是**平滑单调**的。
4. **墙钟**：`_r577` 已实测引擎单步 **1.78×**、真实路径 **1.64×**；
   本次采样点数 125 vs 91（同 5 s 间隔）⇒ TUNED 多跑了 **37%** 的时间 ✅ 一致。
5. **`series.csv` 96 列逐位一致**（`0.000e+00`）⇒ 分配器**不参与数值**。

⇒ **结论**：`MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536` 这条
"为控内存加的"设置，在**当前规模（N≤96）**上是**纯亏**：慢 1.6–1.8×，峰值只省 8%。
`MALLOC_ARENA_MAX=2` 单独用则**又快又省**（0.93× 墙钟、−48 MB 峰值）。

### §3.1 ⚠ 仍然不改任何脚本（按 goal 纪律）

goal 成功判据②要求"每一项改动都有新开关、默认关"。分配器这条**不是代码改动而是部署改动**，
且**N=160/nv≈359 的规模还没测**（临时量更大、TLB 压力不同）。
⇒ 本轮只**登记**，不动那 124 个脚本。下一步：**N=160 复测**（见 §5）。

---

## §4 本轮新增的三个开关（全部默认关 = 归档旧路）

| 开关 | 取值 | 位置 | 自述 |
|---|---|---|---|
| `--k-loop` | `full`(默认) / `act` | `_bk_exp.py` → `LevelSetMulti(k_loop_mode=)` | banner `k_loop=act` |
| `--act-mode` | `unique`(默认) / `bincount` | 同上 `act_mode=` | banner `act=bincount` |
| `--argmin2-mode` | `legacy`(默认) / `copyto` | 同上 `argmin2_mode=` | banner `argmin2=copyto` |

三者都在 `LevelSetMulti.__init__` 里**硬校验**（非法值直接 `ValueError`，`_r578_check.sh` C2 已验）。

---

## §5 复现

```bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
PY=/root/miniconda3/envs/ml/bin/python

bash _r578_check.sh        # C1 语法 / C2 非法值硬失败 / C3 argmin2 逐位 + 负对照 / C4 act 同集合
$PY  _r578_kloop.py        # k_loop 逐位判据（两构型）+ 负对照
$PY  _r578_opt3.py         # §(3)①/③ 微基准 + 逐位判据
bash _r578_kloop_ab.sh     # k_loop 交错配对墙钟 + 计数回归
bash _r578_r3_ab.sh        # §(3) 逐项 + 合并（**轮换顺序**）
bash _r578_smoke.sh        # 真实路径冒烟（含 96 列逐位）
bash _r578_rsstrace.sh     # 分配器长跑 RSS 轨迹（~18 min）
```

---

## §6 遗留

1. **分配器**：N=160 复测（本轮未做）+ `WB_ALLOC` 显式档位。
2. **goal §(5) C5 内存墙**：`_r579_mem160.py` 已写好（N=160 直接实测 `a`/`c` + 逐项构成 + 重算 nv 需求），本轮**未跑**。
3. goal §(3)② （`region()` 与 `argmin2` 重复 argmin 的复用）未做。
4. goal §(4) `pf.phi` 不物化、§(6) `par.gradient` 边界公式、§(7) 两个单变量实验、§(9) GPU 处置 —— 均未做。
