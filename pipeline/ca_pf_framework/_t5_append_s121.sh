#!/bin/bash
# _t5_append_s121.sh --- 第 121 轮：decide = 另起一臂；先钉死**精确实施方案**
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
cat >> R581_T5_RESTART.md <<'EOF'

---

## §121 ★★★★ 第 121 轮：**决策 = 另起一臂**（自主规则）；先钉死**精确实施方案**

### §121.1 决策（按用户立的自主规则：不停等裁决，取"最保守 + 可回退 + 显式记账"）
| 判据 | 本配置（`t5H3`）| **另起一臂** |
|---|---|---|
| 是否损坏已有数据 | — | **不会**（纯新增）|
| 是否可回退 | — | **可**（随时 kill，数据保留）|
| 内存 | ~6 GB | +12 GB ⇒ **合计 18 GB < 22 GB** ✓ |
| 对判据 ③(多块)/④/⑥ | **不可能** | **唯一有路** |

**⇒ 采用"另起一臂"。⚠ 三项偏离必须记账**（`--var-rule` 是显式物理选择；`--nuc-fresh-every` 与 abA 的 `K=23` 不同 ⇒ 块数不可直接比；本方案不保证成功）。**

### §121.2 ⚠ 但**实施方式**必须先钉死（s112 事故的教训）
**已查明**：`--var-rule` 与 `--nuc-fresh-every` **都不在启动器的透传里** ⇒ **必须加**。
**而 s112 我在上下文枯竭时改这个文件 ⇒ `SyntaxError`（一度影响长跑恢复）。**
**⇒ 所以本轮**先写清"精确到行"的实施方案**，**下一轮（或上下文充裕时）一次性执行并立即验证。**

### §121.3 ★ 精确实施方案（**三处改动，逐字**）
**文件**：`_t5_short.py`
**① argparse 两行**（放在已有的 `--therm-hist` 定义之后 —— 那是我 s69 加过的、位置已知）：
```python
    ap.add_argument('--var-rule', default='ed', choices=('ed', 'random', 'doublet'),
                    help='变体选择（只对 fresh 通道生效）：ed=归档默认 | random=随机 | doublet=一对')
    ap.add_argument('--nuc-fresh-every', type=int, default=0,
                    help='fresh 通道周期（0=引擎自动取 K=n(T_end)；>0=显式，诊断/配平用）')
```
**② `build()` 里并入**已有的 `+` 链**（**不是**新开 `] +`** —— s112 就是错在这里）：
在 `             (['--nuc-periodic-seed', '1'] if int(a.periodic_seed) == 1 else []) +` **这一行之前**插入：
```python
             (['--var-rule', str(getattr(a, 'var_rule', 'ed'))]
              if str(getattr(a, 'var_rule', 'ed')) != 'ed' else []) +
             (['--nuc-fresh-every', str(a.nuc_fresh_every)]
              if int(getattr(a, 'nuc_fresh_every', 0) or 0) > 0 else []) +
```
**⇒ 两处都用 `getattr(..., 默认)` + "默认档不传"的守卫 ⇒ 归档路径**逐字不变**。**

**③ 做完立刻验证（**四条**）**：
```
python -m py_compile _t5_short.py                     # 必须过
grep -c "nuc-fresh-every', str(a.nuc_fresh_every)"    # 应 = 1
grep -c "var-rule', str(getattr(a, 'var_rule'"        # 应 = 1
python _t5_short.py --tag X --N 96 ... --help 或干跑  # 模块可导入
```

### §121.4 起的臂（**参数定死**）
```
--tag t5V2 --N 160 --nvar 2 --m 36 --B 3 --var-rule random --nuc-fresh-every 5
--cores 8-15（⚠ 长跑用 0-7）  --mem-limit-gb 12
其余与 t5H3 逐字相同（abA 物理基线 / 13 项算子 / --grow-stack / --therm-hist linear / 断点续跑）
```
**判据（预先写死）**：
| 观察 | 结论 |
|---|---|
| `n_var_sig > 1` | "随机选变体"生效 ✓ |
| `nblk_sig ≥ 2` | **真的出现新块** ✓ ⇒ 判据③(多块)/④ 有路 |
| `nf2 > 0` | 块相遇 ✓ ⇒ 判据④ |
| 若三者仍不变 | ⇒ **`fresh` 被拒另有原因** ⇒ 回到 `nuc_dbg.json` 归因 |

### §121.5 ⚠ 本轮**不做**改动（**自我约束**）
**我这一轮的上下文已接近上限** ⇒ 按 s112 立的第 15 条纪律，**不做多行结构化改动**。
**⇒ 本轮只把方案钉死；**执行放到下一轮**（届时先读完整表达式、再改、再立刻 `py_compile`）。**
EOF
echo "已追加，现在 $(wc -l < R581_T5_RESTART.md) 行"
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R581_T5_RESTART.md pipeline/ca_pf_framework/_t5_append_s121.sh
git commit -F - <<'MSGEOF'
R581-T5R-s121 决策=另起一臂(自主规则); 先钉死精确实施方案 (s112 事故的教训)

决策依据: 另起一臂不损坏已有数据/可回退/内存合计 18GB<22GB/且是判据③(多块)④⑥ 的唯一有路。
三项偏离记账: var-rule 是显式物理选择; nuc-fresh-every 与 abA 的 K=23 不同=>块数不可直接比; 不保证成功。

⚠ 实施方式先钉死: var-rule 与 nuc-fresh-every 都不在启动器透传里 => 必须加;
而 s112 我在上下文枯竭时改这文件 => SyntaxError 一度影响长跑恢复。
所以本轮只写清"精确到行"的方案(三处改动逐字 + 四条验证), 执行放下一轮。

本轮不做改动(自我约束): 上下文接近上限 => 按第15条纪律不做多行结构化改动。
MSGEOF
git log --oneline -1
