# R629 —— ★★ 实验隔离纪律（**用户 2026-10-06 指示，硬约束**）

> **用户原话**：
> 「注意，实验千万**不能修改原始的仿真代码**，必须与主代码**隔离开**，
>  防止因为做实验影响了主仿真」
> 「写进去，**实验尽量不改主代码**」
>
> **性质**：**硬纪律**。违反它 = 主仿真的可复现性被实验污染。
> **摘要已写入 `AGENTS.md §7.6`**（一行 + 指针），本文是完整正文。

---

## §1 三条硬规则

### **E1（最强，默认必须遵守）：实验**不得修改**任何主代码文件**

下列文件是**主仿真**的一部分 ⇒ **实验一律不得就地改**：

```
_bk_exp.py            # 引擎驱动
windowB_surface.py    # 水平集 / Gibbs 面引擎
windowB_pf3d.py       # 弹性求解
windowB_km.py         # KM 律 / 热历史
windowB_lath.py       # LathTable / F3 面能
windowB_closure.py    # 闭环判据
windowB_aniso_elastic.py
windowB_ti64_variants.py
_bk_measure.py        # 量具
windowB_drag.py / windowB_wulff.py / T16_verify_rve.py …
```
（判据：**`git status --porcelain -- <这些文件>` 必须为空**。）

### **E2：实验的正道 = "只加新文件 + 只传参数 + 落独立目录"**

| 手段 | 做法 |
|---|---|
| **新脚本** | 实验编排一律**新文件**（如 `_t11_cube_growth.py`），只做：构造命令行 → `subprocess` 起引擎 → **只读**产物 |
| **参数覆盖** | 靠 **CLI 参数**改变实验条件（`--N` / `--plate-*` / `--beta-h` / `--grow-stack` …） |
| **独立目录** | 每个臂用**独立 `--tag`** ⇒ 落 `_exp/_bk_t5/dry_<tag>/`，**绝不覆盖归档** |
| **只读分析** | 量形状/读 `series.csv`/读 `npz` 的工具**不得 import 或改**主模块 |

### **E3：若实验**必须**动主代码 ⇒ 走"新开关 + 默认关 + 回归"流程，且**先报用户**

1. **先停下来告诉用户**（不得自行就地改）；
2. 改动形式**只能是**：**新增 `add_argument`（默认 = 归档旧行为）**；
3. **必须**跑 `bash _r30_regress.sh` ⇒ 判据 **共有列差异 = 0**；
4. **留档**：改了什么 / 依据 / 可 FAIL 判据 / 回归结果。

---

## §2 为什么这条纪律是硬的（后果，不是教条）

| 若违反 | 后果 |
|---|---|
| 实验里就地改引擎 | **正在跑的主仿真**中途改变行为 ⇒ 其 `series.csv` **前后段不同源**，整条轨迹作废 |
| 改了但没记 | 下次跑的人**无法复现**归档读数（本仓库已因此类问题付出过代价：`kappa_c` 只改一半 ⇒ 四个实验白做） |
| 实验产物写进归档目录 | **污染对照基线** ⇒ 之后的"逐位回归"全部失去意义 |
| 改量具去"迁就"实验 | 主仿真的**判据**被悄悄放宽 ⇒ 结论不可信 |

---

## §3 本条纪律的**首次应用**（`R628` 的立方核实验）

**实际做法（可作范例）**：

| 项 | 内容 |
|---|---|
| 新增文件 | `_t11_cube_growth.py`（编排）、`_t11_lath_shape_when.py`（只读量形状）、`_t11_check_flags.py`（校验选项名） |
| 主代码改动 | **零** —— `git status --porcelain` 对 7 个主模块**全空** |
| 实验条件靠什么变 | **纯 CLI**：`--N 64`、`--plate-L/W/T 500`（立方核）、`--grow-stack`（只播 1 片）、`--beta-h 0/6.477/15` |
| 落盘 | `_exp/_bk_t5/dry_cubeEq0` / `dry_cubeB647` / `dry_cubeB15`（**独立 tag**） |
| 主代码最后提交 | `eb8f45f4`（**10-06 01:02**）⇒ 早于实验 **约 21 小时** ⇒ 实验期间**逐字未动** |

**⇒ 结论**：这个实验**完全满足 E1/E2**，无需走 E3。

---

## §4 自检命令（每次实验前后各跑一次）

```bash
cd /mnt/f/speed_up
# ① 主代码是否被实验改动（必须为空）
git status --porcelain -- \
  pipeline/ca_pf_framework/_bk_exp.py \
  pipeline/ca_pf_framework/windowB_surface.py \
  pipeline/ca_pf_framework/windowB_pf3d.py \
  pipeline/ca_pf_framework/windowB_km.py \
  pipeline/ca_pf_framework/windowB_lath.py \
  pipeline/ca_pf_framework/windowB_closure.py \
  pipeline/ca_pf_framework/_bk_measure.py
# ② 主代码最后提交时刻（应早于实验开始）
git log -1 --format='%h %ad %s' --date=format:'%m-%d %H:%M' -- pipeline/ca_pf_framework/_bk_exp.py
# ③ 未提交改动总览（实验新增文件应**只有**新脚本/文档）
git status --porcelain | head -20
```

⚠ **本会话早期的一处历史改动**（**不是**实验，且已合规）：
`windowB_surface.py` / `_bk_exp.py` 曾在 **`eb8f45f4`（10-06 01:02）** 被改，
内容是 **`_oobcap()` 纯记录 + 5 个默认关的新开关 + C-5 判据 + 绕盒列**，
并已由 `_r30_regress.sh` 回归证明 **共有列逐位一致（差异 0）**（`R625 §4.7`）
⇒ **符合 E3 的流程**（新开关、默认关、回归通过），且**远早于**本轮实验。
