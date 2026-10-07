# BASELINE.md —— 原始代码保险基线（R581）

> **为什么要这份文件**：goal 成功判据 ② 要求「**基线快照 + SHA256SUMS + BASELINE.md**」。
> 前两样在 R580/R581 期间已建，**这份 MD 之前缺**（R581 第 9 轮用 `_r581_inv.sh` 查出）。
>
> **为什么不能用 git**：实测 `HEAD = fe550c27 R48`，而工作区已在 R579
> ⇒ **领先约 500 轮**；`git checkout` 会**抹掉几百轮工作**
> ⇒ **git 不是可用的回滚点**；也**不新建 git 提交**以免扰动仓库历史。
> ⇒ 一律用**文件级快照 + SHA256**。

---

## §1 基线是什么

| 项 | 值 |
|---|---|
| **tag** | `baseline_R579` |
| **目录** | `pipeline/ca_pf_framework/_r580_backup/baseline_R579_20261002_062805/` |
| **时间** | 2026-10-02 06:28:13 +0800 |
| **含义** | **R580 验证前的当前代码**（含 `pf_phi onfly` / `grad_mode` 等 7 个开关） |
| **文件数** | 7 个 `.py` + `SHA256SUMS` + `MANIFEST.txt` |
| **宿主指纹** | `py_ops_per_s=43963579.3  axpy_GB_per_s=32.73  matmul_GFLOP_per_s=229.6` |

### ⚠ 基线 ≠ "关掉全部开关"
**全部 R581 开关的默认值就是归档旧路**（`--eps0-mode loop`、`--ed-pair full`、
`--extend-mode legacy`、`--eps0-tile 0`、`--argmin2-reuse 0`、`--ufv-c 0`、`--bbox-mode legacy` …）
⇒ **"不传任何开关" == 归档路径 == 这份基线**。
R581 的**每一个**新开关都被四道门判过**逐位相同**（见 `R581_OPOPT_L1L2.md`）
⇒ **开与不开给出同一个解**，只是快慢不同。

---

## §2 七个文件的 SHA256（**完整值**，取自快照自带的 `SHA256SUMS`）

```
79922f88991a8bfb82185970def498b3010c6bfae520639d1c0e19d83a37419a  ./_bk_exp.py
d81c2a54bf5d8d4bf71063179889f4eced9ed8b829dc45868be69129a8256055  ./windowB_acct.py
5f7228decde7aaa6a4119bc9674d5775b6df853e42d3b2121d3b08278f154eea  ./windowB_lath.py
aa58d94341d3a48a5eaed1164a392292f529afdb24467f9b0f134c00912e2825  ./windowB_par.py
3bafad94da554d70667c3777007e61f5527ba46ceee4cfb7463d0d1c089de923  ./windowB_pf.py
2d945c30233dcad6b0cf3eebf27241d6b3f4a6fd342ffec1457a369a028cf74c  ./windowB_pf3d.py
d1bf1d24a8f5457f4faab5fb94e67f8164be7c2a8e32cf56a466363cedaea288  ./windowB_surface.py
```

**对照：R581 结束时（`afterDecisions_20261002_105936`）**

| 文件 | 基线 sha256 前 16 位 | R581 末 sha256 前 16 位 | 变了吗 |
|---|---|---|---|
| `windowB_surface.py` | `d1bf1d24a8f5457f` | `2e60e7aa13294686` | ✅ 改了（L1/L4/L5/L6 的开关） |
| `windowB_pf3d.py` | `2d945c30233dcad6` | `7ce0ddf1d89ab1c0` | ✅ 改了（L2 分块） |
| `windowB_par.py` | `aa58d94341d3a48a` | `78eed934a8b9bac9` | ✅ 改了（L5 的 `argmin2` 口） |
| `_bk_exp.py` | `79922f88991a8bfb` | `2ca202dde39f6e74` | ✅ 改了（新 CLI 开关） |
| `windowB_lath.py` | `5f7228decde7aaa6` | `5f7228decde7aaa6` | ⬜ **没改** |
| `windowB_acct.py` | `d81c2a54bf5d8d4b` | `d81c2a54bf5d8d4b` | ⬜ **没改** |
| `windowB_pf.py` | `3bafad94da554d70` | `3bafad94da554d70` | ⬜ **没改** |

---

## §3 怎么用

### 3.1 打新快照（**任何编辑之前必须先做**）
```bash
cd pipeline/ca_pf_framework
bash _r580_snapshot.sh <tag> "<一句话备注>"
# ⇒ _r580_backup/<tag>_<时间戳>/  + SHA256SUMS + MANIFEST.txt
```

### 3.2 回滚
```bash
bash _r580_rollback.sh <tag>            # 只看，不动（默认 dry-run）
bash _r580_rollback.sh <tag> --apply    # 真恢复
```
**安全性质（`_r580_rollback.sh` 的实现）**：
1. **唯一匹配**快照 —— 多个匹配就**报错退出**（不猜）；
2. **先校验 `SHA256SUMS`** —— 不符就**拒绝恢复**；
3. `--apply` 前**自动给当前工作区再打一份** `rollback_from_<tag>` 快照；
4. 恢复后**逐文件复验 sha256**；
5. 再跑一次 `_r576_regress.sh` 确认能跑。

### 3.3 ★ 回滚的**实测**验证（成功判据②要求"实测回滚一次"）
`bash _r580_rollback_test.sh` ⇒ **T1–T6 全过** ✅

| 判据 | 内容 | 结果 |
|---|---|---|
| **T1** | 故意破坏一个文件 ⇒ hash 必须变 | `aa58d943…` → `52c93a42…` ✅ |
| **T3** | 回滚后 hash 必须回到原值 | 回 `aa58d943…` ✅ |
| **T4** | 回滚前必须自动留档 | 生成 `rollback_from_afterP1_20261002_074659` ✅ |
| **T5** | 恢复后回归必须能跑 | 通过 ✅ |
| **T6** | **坏快照必须被拒绝**（负对照） | `exit=4`，且**未覆盖**当前文件 ✅ |

---

## §4 全部快照（15 个，截至 R581 第 9 轮）

```
baseline_R579_20261002_062805        ← ★ 基线（本文档的主角）
afterP1_20261002_065520
rollback_from_afterP1_20261002_074659  ← 回滚实测的留档
L1_before_20261002_080733
afterL1L2_20261002_092350
afterL5L6_20261002_100944
afterL4_20261002_102425
afterFinalAB_20261002_103255
afterAudit_20261002_103912
afterAudit2_20261002_104052
afterC6judge_20261002_104612
afterC3mis_20261002_105204
afterFrag_20261002_105409
afterC5budget_20261002_105618
afterDecisions_20261002_105936         ← 最新
```
**每个都是 9 个文件**（7 个 `.py` + `SHA256SUMS` + `MANIFEST.txt`）。
**❌ 一个都没删过**（goal 硬要求）。

---

## §5 硬纪律（R581 期间遵守情况自查）

| 纪律 | 执行情况 |
|---|---|
| 任何编辑之前先 snapshot | ✅ 本会话共 15 份快照 |
| 未过门 ⇒ 立刻回滚 + 失败留档 | ✅ 未出现"半成品留在主副本"（L1 第一版打错靶子那次**没改主副本**，只写了候选微基准） |
| 绝不删除旧文件/旧日志/旧备份 | ✅ `_r580_backup/` 15 个快照一个没少 |
| **禁止 `rm -rf` 打在运行目录上** | ✅ **全程未用 `rm -rf`**；重跑一律 `_r581_archive_arm.sh`（**`mv` 改名**，实测归档过 `p2_b5ps_superseded_killed_early_20261002_105000`） |
| 每道车道在独立工作副本 | ✅ 车道都只写各自的候选脚本 + `_w2_*.log`；主副本只在四道门全过后才改 |

---

## §6 复现命令（基线路径）

```bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
PY=/root/miniconda3/envs/ml/bin/python

# ① 回国基线的**数值**（不传任何开关 == 归档路）
taskset -c 8-15 $PY _bk_exp.py --N 64 --dx-nm 62.5 --steps 12 --every 1 \
    --snap-every 99999 --pair-every 0 --norm-smooth 0 --nthreads 4 \
    --out _exp/_bk_base --tag base_check

# ② 逐位回归（基线 vs 当前）
bash _r576_regress.sh

# ③ 宿主指纹（**任何性能比较之前先打**）
$PY _r576_hostfp.py
```
