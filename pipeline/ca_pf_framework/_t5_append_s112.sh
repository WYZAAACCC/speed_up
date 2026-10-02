#!/bin/bash
# _t5_append_s112.sh --- 第 112 轮：★ 事故记录（我在上下文枯竭时改坏了启动器，已修好）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
cat >> R581_T5_RESTART.md <<'EOF'

---

## §112 ★★★★★ 第 112 轮：**事故记录 —— 我在上下文枯竭时改坏了启动器（已修好）**

### §112.1 事故经过（**原样登记**）
**目标**：按 §111 的方案②，给 `_t5_short.py` 加 `--nuc-fresh-every` 透传，
起一个短诊断臂去取 `fresh_*` 归因计数。

**我做了什么**：在 `--phi-band-every` 之后插入
```python
] + (['--nuc-fresh-every', …] if … else []),
```
**结果**：
```
SyntaxError: closing parenthesis ']' does not match opening parenthesis '(' on line 43
（_t5_short.py:85  '--nuc-overlap-nm', …] +   ← 与我的 `] +` 冲突）
```
**⇒ `_t5_short.py` **一度不可用**。**
**⚠ 风险评估**：它**是长跑恢复的依赖**（`--resume` 的入口）⇒
**若在此时长跑被中断，我会无法用标准命令续跑**（虽可手写 `_bk_exp.py` 的完整参数，但那是绕路）。

### §112.2 修复（**已完成并验证**）
**修法**：删掉那个冲突的 `] + (…)` 片段（**并入原有的 `+` 链**的位置）。
**验证（四项全过）**：
```
① py_compile ⇒ ✅ SYNTAX_OK
② 错误片段残留 = False ✅（已清除）
   四段关键代码全在：--therm-hist / --nuc-periodic-seed / --resume / --laths
③ 模块可导入 ⇒ ✅
④ **长跑未受影响**（pid 3121 仍在跑）—— 它早已把旧代码载入内存
```
**⚠ 但 `--nuc-fresh-every` 透传**最终没有加上**** ⇒ **诊断臂暂时传不了它**（留给上下文充裕时再加）。

### §112.3 ★★ 教训（**这是本 goal 最该记住的一条**）
| 项 | 内容 |
|---|---|
| **错因** | **在上下文枯竭时改**多行结构化代码**（向一个已有的 `list + list` 表达式里插东西）** |
| **本可避免** | 若先**读完整那个表达式**（第 43–91 行）再动手，就会看到第 85 行已有 `] +` |
| **险在哪** | **改坏的是"恢复长跑的入口"** —— 而它保护的是一份已跑 700+ 步、还需 1–2 天的数据 |
| **纪律（新，第 15 条）** | **① 上下文枯竭时，只做**单点、可立即验证**的改动；<br>② 改**结构化表达式**前，必须**先读完整表达式**（不是它的一部分）；<br>③ 一批改动后**立刻 `py_compile`**（本次正是它当场抓住的）。** |

### §112.4 下一步（**不变**，但换路子）
**§111 的三个方案里，方案②暂时做不了（缺透传）** ⇒ 剩下：
* **方案①**：小臂跑**更多步**（如 800 步）⇒ **不需要新参数**，但小臂的 `K` 仍是 23 ⇒ 要跑到事件 24；
* **方案③**：**等长跑自己到事件 47/70**（~3 小时）—— **最忠实**。

**⇒ 建议：直接做方案③**（不需要改任何代码，且回答的是**最忠实**的那个问题）。
EOF
echo "已追加，现在 $(wc -l < R581_T5_RESTART.md) 行"
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_short.py pipeline/ca_pf_framework/R581_T5_RESTART.md \
        pipeline/ca_pf_framework/_t5_freshdiag.sh pipeline/ca_pf_framework/_t5_patch112.py \
        pipeline/ca_pf_framework/_t5_vfy112.sh pipeline/ca_pf_framework/_t5_append_s112.sh
git commit -F - <<'MSGEOF'
R581-T5R-s112 事故记录: 我在上下文枯竭时改坏了 _t5_short.py (已修好并验证)

经过: 为加 --nuc-fresh-every 透传, 我在 --phi-band-every 后插入 "] + (...)",
与已有的 "] +" 冲突 => SyntaxError, _t5_short.py 一度不可用。
风险: 它是长跑恢复(--resume)的入口, 保护着一份已跑 700+ 步、还需 1-2 天的数据。

修复并验证(四项全过): py_compile OK / 错误片段已清除 / 四段关键代码全在 / 模块可导入 / 长跑未受影响。
⚠ 但 --nuc-fresh-every 透传最终没加上 => 诊断臂暂时传不了它。

教训(第15条): (1)上下文枯竭时只做单点可立即验证的改动; (2)改结构化表达式前先读完整表达式;
(3)一批改动后立刻 py_compile(本次正是它当场抓住)。

下一步不变但换路子: 方案②暂不可做; 建议直接做方案③(等长跑自己到事件 47/70, 最忠实且不需改代码)。
MSGEOF
git log --oneline -1
