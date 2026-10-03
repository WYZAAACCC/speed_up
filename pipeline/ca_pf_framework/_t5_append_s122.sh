#!/bin/bash
# _t5_append_s122.sh --- 第 122 轮：★★★ V2 臂成功启动（两臂并行）+ 两处事故已修
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
cat >> R581_T5_RESTART.md <<'EOF'

---

## §122 ★★★★★★★ 第 122 轮：**V2 臂成功启动**（两臂并行）+ 两处事故已修

### §122.1 ★ 结果
```
进程：pid=3121（长跑 t5H3，4:26:37）+ **pid=11386（t5V2，14:58）** ⇒ 两臂并行 ✓
V2 横幅：导出板条数 n = 23（nv=72）
        ★ N8 自动推导：--nuc-fresh-every 未传 ⇒ 自动取 **K = n(T_end) = 23**
          （⇒ 实际块数 ceil(B·n/K) = 3 ✓ **自洽**）
        **无"不自洽"报错** ✓
内存 **13642 MB 用 / 8754 MB 余** ✓（两臂合计 ~13.6 GB < 22 GB，P23 之内）
```

### §122.2 ★★★ 引擎自己抓到了我的配置错误（**这是本轮最有价值的一步**）
上一版我传了 `--nuc-fresh-every 5`，**引擎拒绝运行**并报：
```
❌ `--nuc-fresh-every 5` 与 `--nuc-block-target 3` 不自洽（N8）
   ⇒ 修法：去掉它（自动取 23），或显式传 23。
```
**N8 的条件**：`实际块数 = ceil(B·n/K)` **必须等于** `--nuc-block-target B`。
| 配置 | `ceil(B·n/K)` | 与 `B=3` 自洽？ |
|---|---|---|
| `K=5, B=3, n=23` | `ceil(69/5) = 14` | ❌ **不自洽** |
| **`K=23, B=3, n=23`** | `ceil(69/23) = 3` | ✅ **自洽** |

**⇒ ★★★★ 这条错误信息**闭合了整个逻辑环**：**
**`t5H3` 的调度**本来就是对的**（`B=3, K=23` ⇒ **目标就是 3 个块**），
问题**不在调度**，而在**那 2 个额外块的 `fresh` 事件全被拒**（单变体组没空位）。**
**⇒ 所以正确修法是：保留自洽的 `K=23`，只加 `--var-rule random` + `m=36`。**

### §122.3 ⚠ 两处事故（**都是我自己造成的，已修并验证**）
| # | 事故 | 根因 | 修法与验证 |
|---|---|---|---|
| **1** | **`--nuc-fresh-every` 重复定义** | **s112** 那次尝试的 argparse 行**先执行了才撞上语法错误** ⇒ **留在了文件里**；**s122** 的补丁**又加一遍**（它只查语法、不查"参数是否已存在"）⇒ `argparse.ArgumentError: conflicting option string` ⇒ **`_t5_short.py` 任何调用都失败 ⇒ 长跑的 `--resume` 入口被破坏** | `_t5_fixdup.py`（**自验证：先编译、通过才写盘**）⇒ **三条判据全过**（py_compile / 定义数=1 / 定义数=1）|
| **2** | **s112 的 `SyntaxError`** | 我在上下文枯竭时**向已有的 `list + list` 表达式里插 `] +`** | 已修；本轮改用**并入原 `+` 链 + 先编译后写盘** |

**★★ 教训（第 16 条，**比 s112 那条更具体**）**：
> **补丁脚本必须检查"目标是否已存在"** —— 我的 s122 补丁只查语法，**没查重复** ⇒
> **把一个"看起来成功"的补丁写进了文件**，直到**运行期**才由 argparse 报错。
> **⇒ 判据不能只有"语法通过"，还要有"语义唯一性"（如 `grep -c` 计数 = 1）。**
> ⚠ 讽刺的是：**我 s122 的复核里**确实有**两条 `grep -c` 计数判据，但它们数的是"出现次数 = 1"**，
> 而我**先入为主地以为只有一处** ⇒ **没有先去数"改之前有几处"**。
> **⇒ 正确的是：改动前先数基线，改动后数一次，比较"增量"是否等于预期。**

### §122.4 ★ V2 与 t5H3 的差异（**正是为解除两个障碍**）
| 项 | `t5H3` | **`t5V2`** |
|---|---|---|
| `nvar` × `m` | 3 × **24** | **2 × 36** |
| `nv` | 72 | **72**（内存不变）|
| 每组余量 | **24（用尽 ⇒ 封顶）** | **36（有余量）** |
| `--var-rule` | `ed`（永远 `argmax(drv)`）| **`random`（能选不同变体）** |
| `K` | 23（自洽）| **23（自洽）** |

**⇒ 两臂共用**同一物理基线**（abA）+ **同一 13 项算子** + `--grow-stack` + `--therm-hist linear` + 断点续跑；
差异**只在"场配平 + 变体选择"** ⇒ **判据（预先写死）**：
**`n_var_sig > 1`**（随机选变体生效）· **`nblk_sig ≥ 2`**（真的出现新块）· **`nf2 > 0`**（块相遇）。**

**⚠ 三项偏离记账（不变）**：① `--var-rule random` 是**显式物理选择**；② 本臂与 abA 的**变体选择规则不同** ⇒ 块数**不可与 abA 直接比**；③ **本臂不保证成功**。
EOF
echo "已追加，现在 $(wc -l < R581_T5_RESTART.md) 行"
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R581_T5_RESTART.md pipeline/ca_pf_framework/_t5_short.py \
        pipeline/ca_pf_framework/_t5_patch122.py pipeline/ca_pf_framework/_t5_fixdup.py \
        pipeline/ca_pf_framework/_t5_v2.sh pipeline/ca_pf_framework/_t5_v2b.sh \
        pipeline/ca_pf_framework/_t5_chkv2.sh pipeline/ca_pf_framework/_t5_retryv2.sh \
        pipeline/ca_pf_framework/_t5_run122.sh pipeline/ca_pf_framework/_t5_append_s122.sh
git commit -F - <<'MSGEOF'
R581-T5R-s122 ★★★ V2 臂成功启动(两臂并行) + 两处事故已修

结果: pid=3121(长跑 t5H3) + pid=11386(t5V2) 并行; 内存 13.6GB<22GB。
V2 横幅: n=23(nv=72), N8 自动推导 K=23 => 实际块数 ceil(B*n/K)=3 = --nuc-block-target 3 自洽, 无报错。

★ 引擎自己抓到我的配置错误: --nuc-fresh-every 5 与 --nuc-block-target 3 不自洽(N8)并拒绝运行。
N8 条件: 实际块数 = ceil(B*n/K) 必须等于 B。K=5 => 14 != 3 不自洽; K=23 => 3 = 3 自洽。
=> 闭合逻辑环: t5H3 的调度本来就对(目标就是 3 个块), 问题不在调度, 而在那 2 个额外块的
   fresh 事件全被拒(单变体组没空位) => 正确修法 = 保留 K=23, 只加 --var-rule random + m=36。

两处事故(都是我造成的, 已修并验证):
1. --nuc-fresh-every 重复定义: s112 那次 argparse 行先执行后才撞语法错误=>留在文件里;
   s122 补丁又加一遍(只查语法不查已存在) => argparse 冲突 => _t5_short.py 任何调用都失败
   => 长跑 --resume 入口被破坏。已用自验证补丁(先编译通过才写盘)修好, 三条判据全过。
2. s112 的 SyntaxError: 已修; 本轮改用"并入原 + 链 + 先编译后写盘"。

教训(第16条): 补丁脚本必须检查"目标是否已存在"; 判据不能只有"语法通过", 还要有语义唯一性;
且改动前应先数基线, 改动后数一次, 比较增量是否等于预期。

V2 vs t5H3 差异: nvar*m 2x36(m=36 有余量) vs 3x24(m=24 用尽); var-rule random vs ed; K 都 23。
两臂共用同一物理基线(abA)+同一13项算子+--grow-stack+--therm-hist linear+断点续跑。
判据预先写死: n_var_sig>1 / nblk_sig>=2 / nf2>0。
MSGEOF
git log --oneline -1
