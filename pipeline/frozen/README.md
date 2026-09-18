# frozen/ —— 冻结的生成器

> 建立：2026-09-18（Gate 0 步骤 1）
> 目的：**消除"同名不同内容"的生成器漂移**

---

## 一、为什么要有这个目录

仓库里有两个功能相同、文件名相同、**内容不同**的生成器，产出物**都叫
`stage1_meltpool_d.i`**。在本次固化之前，**没有任何哈希能区分产物是哪个版本生成的**。

这不是假想的风险——本项目已经因为"选错生成器"误诊过一次（C1 验证第一版把 AD 版的
收敛问题错误归因到 `k = 0.63`）。

|candidate|位置|性质|
|---|---|---|
| **非 AD 版** | `/root/work/bak/gen_aniso.py`（生产用，WSL，**无版本管理**） | 生产 |
| AD 版 | `pipeline/gen_aniso.py` | 实验/对照 |

⇒ 生产版本只存在于 WSL 的一个 `bak/` 目录里，**随时可能因误删/误改而永久丢失**。
本目录把生产版复制进仓库，两版并存。

---

## 二、冻结清单与 SHA256

| 文件 | SHA256 | 行数 | 来源 |
|---|---|---|---|
| `gen_aniso_nonad.py` | `07629ed6272b39ede93edfa47cdf4acd47adf157636b8c51b86757d9f725f875` | 556 | `cp -p /root/work/bak/gen_aniso.py` |
| `splice_aniso_nonad.py` | `1009d666f6e9101d7ad78692cb9bba642237c6d78f60469a837c117f177e14b7` | 236 | `cp -p /root/work/bak/splice_aniso.py` |

**对照（未改动，仅登记）**：

| 文件 | SHA256 | 行数 |
|---|---|---|
| `../gen_aniso.py`（AD） | `78c7705b5b31a2ada5b8dea2025f97c227c4b8472a407d56d0a042c807b3043f` | 608 |
| `../splice_aniso.py`（AD） | `9d1167aa2208bfdc80bafb323a77600dc9c2622033c80057547d915a06cc8311` | 252 |

四个哈希**两两不同**——确认确实是四份不同的文件。

**复制保真性已验证**：`cmp` 逐位比对通过，复制后 SHA256 与源完全一致。
`/root/work/bak/` 原件与 `pipeline/` 下的 AD 版**均未移动、未修改**。

---

## 三、两版差异（实测 `diff`，不是凭印象）

### 3.1 `gen_aniso` 的差异（250 行）

**(a) 取向集的默认值不同 —— 这是最危险的差异**

| 版本 | 默认取向分布 |
|---|---|
| 非 AD | 固定确定性铺开，`[0,90)` 内等间距 + 抖动 |
| AD | `--texture fiber`（默认！），`<100>` 纤维织构，`hwhm=20°` |

实测（`op_num = 8`）：

```
非 AD                : [0.0, 14.85, 29.7, 34.65, 49.5, 64.35, 69.3, 84.15]
AD --texture random  : [0.0, 14.85, 29.7, 34.65, 49.5, 64.35, 69.3, 84.15]   ← 逐位相同
AD --texture fiber   : [2.67, 8.30, 15.07, 26.06, 63.94, 74.93, 81.70, 87.33] ← 完全不同
```

> **⇒ 非 AD 版 ≡ AD 版加 `--texture random`，逐位相同。**
> 而 AD 版的**默认**是 fiber，与生产版**不是同一套物理**。
> 谁若直接用 `python3 gen_aniso.py`（不带参数）去复现生产结果，取向集就错了。

**(b) 实现机制不同（数学等价）**

| | 非 AD | AD |
|---|---|---|
| 材料类型 | `DerivativeParsedMaterial` | `ADDerivativeParsedMaterial` |
| `gdir` | 独立材料 `gdir_p`/`gdir_q`，经 `material_property_names` 分层 | 内联进 `align4` 表达式 |
| `L` | 三层 `L2a × L2b`，各自显式 `coupled_variables` | 单层内联 |
| kernel | `TimeDerivative` / `ACGrGrPoly` / `ACInterface` | `ADTimeDerivative` / `ADGrainGrowth` / `ADACInterface` |
| 辅助变量 | `MaterialRealAux` | `ADMaterialRealAux` |

已逐行核对：两版的 `align4` 与 `L` **数学表达式等价**（非 AD 的属性名
`gdir_p`/`gdir_q` 正是 AD 内联进去的那两个表达式，`GDIR_EPS=1e-30`、`DELTA=1e-3`
等常量也完全相同）。⇒ **差异只在机制与取向集，不在 L 的数学形式。**

**(c) AD 版多一个 `--texture` / `--hwhm` CLI 参数**（非 AD 版没有）。

### 3.2 `splice_aniso` 的差异（16 行）

AD 版多一段：把 `[Materials]/barrier_mu` 从 `DerivativeParsedMaterial` 强制换成
`ADDerivativeParsedMaterial`（附有"不是就 `sys.exit`"的守卫），以及上面表格里的
三个 kernel / aux 类型替换。

**原因**（AD 版自己的注释）：MOOSE 禁止同一属性既有 AD 又有非 AD 声明，
而 `ADGrainGrowth` 用 `getADMaterialProperty("mu")` 取 `mu`。

**⇒ `splice_aniso_nonad.py` 从不修改 `barrier_mu`**，这一点与非 AD 生产的
熔化开关语义一致，不要混用。

---

## 四、生产流程（照 `../run_nonad_prod.sh` 实录）

```
conda activate ml
python3 gen_aniso_nonad.py --op-num 8 --out aniso_block.i     # 不能传 --texture
python3 splice_aniso_nonad.py                                  # 产出 stage1_meltpool_d.i
# —— 然后是一段 Python 正则补丁，产出真正的运行文件 N.i ——
phase_field-opt -i N.i
```

### ⚠️ 真正被运行的是 `N.i`，不是 `stage1_meltpool_d.i`

`run_nonad_prod.sh:46-62` 的补丁 heredoc 会**无条件覆盖**以下 6 项：

| 项 | `stage1_meltpool_c.i` 里 | 补丁后 `N.i` |
|---|---|---|
| `l_max_its` | 30 | **300** |
| `l_tol` | 1e-6 | 1e-6（不变） |
| **`nl_abs_tol`** | 1e-7 | **1e-6** ← 见下 |
| `end_time` | 6.5e-4 | 6.5e-4（不变） |
| `file_base` | `stage1c` | `N` |
| `time_step_interval` | 1 | **5** |

该补丁还断言核是修好的那一版（`type = TimeDerivative` 恰好 8 个、
`variable_L = true` 存在、`type = ADGrainGrowth` 一个都没有）。

> **⇒ 只改 `stage1_meltpool_c.i` 的 `nl_abs_tol` 是无效的**——补丁第 56 行会把它
> 重新覆盖回 `1e-6`。Gate 0 步骤 2 必须同时处理这一行（详见 `../GATE0_PLAN.md` 步骤 2）。

### 该补丁里已过期的归因（**必须修正**）

`run_nonad_prod.sh` 文件头（第 12-16 行）与第 55-56 行仍写着：

> 非 AD 版唯一的缺陷是 `ACGrGrPoly` 丢 `dL/deta_j` → 雅可比误差 1.2e-3
> → 牛顿残差地板 **7.3e-07**（只比 `nl_abs_tol=1e-7` 高 7 倍）
> => 把 `nl_abs_tol` 放到 `1e-6` 即可推进。

**这个归因已被实测推翻**：残差地板来自 **ASM/ILU 预条件子**，不是 Jacobian 不完备——
非 AD + MUMPS 能二次收敛到 **4.01e-10**。若不改这条，将来一定会有人照着它把容差放宽。

---

## 五、复现基线

用本目录的两个文件、对当时（2026-09-18，未改前）的
`../stage1_meltpool_c.i` 跑完整流程，产物基线：

```
stage1_meltpool_d.i   sha256 = 6914a7cdbecd1dd38d5da4ed9507c710237ba6a53a62ae74b7b59b6f3455913d
                      28924 字节 / 24651 字符
```

`splice` 自报的分段：Functions 667 字符、AuxVariables 309、AuxKernels 1336、
替换 Materials 10127 字符。

`gen_aniso` 自检：`kappa_op = 1.799943021e-06` vs 基线 `1.8e-6`，相对偏差 `3.17e-05`。

> **注意**：Gate 0 步骤 2 会修改 `stage1_meltpool_c.i`，上述 `d.i` 哈希**届时必然改变**。
> 它是"改前基线"，用于证明冻结版可用；改后的新基线需重新登记。

---

## 六、使用约定

1. **生产只用本目录的两个文件**，不要再从 `/root/work/bak/` 取。
2. 本目录文件**不得修改**。需要改动时，另存新文件并在此登记新哈希与理由。
3. 每次生产运行的产物 `stage1_meltpool_d.i` / `N.i` 的 SHA256 应记入该次运行的
   `diagnostics.json`（Gate 0 步骤 3），使"哪次运行用了哪个生成器"可追溯。
4. `--texture` 只在 AD 版存在。若要复现生产取向集而必须用 AD 版，
   **必须显式传 `--texture random`**。
