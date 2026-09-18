# 代理工作笔记（agent-notes）

> **这是什么**：本项目在 Claude Code 里长期积累的**持久记忆**，2026-09-19 原样导出。
> 交接给其它代理（Codex 等）时，这些文件就是「上一个代理脑子里装着的东西」。
>
> **快照日期**：2026-09-19。此后如有更新，需人工同步——这里的文件是**某一时刻的副本**，
> 不是活的记忆库。

---

## 怎么用

1. **先读 `MEMORY.md`**（本目录下）——那是索引，一行一条，带「钩子」。
2. 接到具体任务时，**先读对应主题的那一条**。这些笔记的价值在于它们记录了
   **为什么**某个做法是对的/错的，而代码和报告里通常只写「是什么」。
3. **权威性顺序**：`pipeline/` 下的正式文档 > 本目录的笔记 > 无。
   笔记可能滞后（它们写于当时），**引用前先与代码核对**——这也是本项目的一贯要求。

---

## 文件格式

每个文件是一段独立的事实，带 Claude Code 的 frontmatter：

```markdown
---
name: <kebab-case 短名>
description: <一行摘要，用于判断相关性>
metadata:
  node_type: memory
  type: user | feedback | project | reference
  originSessionId: <会话 ID>
  modified: <时间戳>
---

<正文>
```

- `type: project` —— 正在做的事、目标、约束（**多数是这个**）
- `type: reference` —— 外部资源指针、API 事实
- `type: feedback` —— 用户给过的指导（含「为什么」）
- `type: user` —— 用户是谁、偏好

正文里的 `[[another-note]]` 是**指向另一条笔记的链接**，对应本目录下的
`another-note.md`。链接不存在的说明「这条还没写」。

---

## 索引（17 条）

> 与 `MEMORY.md` 同源，此处列出方便直接浏览。

### 课题与目标

| 文件 | 内容 |
|---|---|
| `grain-solute-acceleration-project.md` | 研究方向、MOOSE 实测结论（拓扑事件不破坏守恒、AMR 才破坏）、文献核查结果 |
| `gb-solute-goal.md` | 晶界溶质的目标：核心立足点是复现**可观测的积分量**（`Γ_GB`、`s·δ·D_GB`）而非 1 nm 剖面 |
| `physics-gaps-for-reviewers.md` | 论文级的物理缺口清单（7 条，写论文前必须逐条解决） |
| `lpbf-roadmap.md` | 四份规划文档的分工；含已验证事实、架构、形核 API、性能结论 |
| `neural-operator-pipeline-state.md` | pipeline 管线状态、守恒已达机器精度、27–35% 方差未解释 |

### 决策与评审

| 文件 | 内容 |
|---|---|
| `expert-review-2026-09-18.md` | 项目定位降级为「可验证数值框架 + 加速预研」；三处纠正；Gate 0–3 执行结构 |
| `solver-choice-mumps-vs-asm.md` | 非 AD + MUMPS 二次收敛到 4e-10，**推翻**「非 AD 有 7e-7 残差地板」的旧归因 |
| `ad-version-performance-blocker.md` | AD 版雅可比精确但牛顿**线性爬行**；含两个「先测量救了」的教训 |

### 已完成的修复

| 文件 | 内容 |
|---|---|
| `landau-melting-fix.md` | **④ 熔化开关的 Landau 修复**：温度从四次项移到二次项，自由能有界、`η ≤ 1` 可证 |
| `gate0-frozen-reproducibility.md` | Gate 0 冻结可重复性；生产数据曾用**占位溶质参数**；含「不限作用域的 kill -9 会杀掉自己的长跑」 |

### 排查历史（最有价值的一类）

| 文件 | 内容 |
|---|---|
| `d-version-stall-debug.md` | D 版不收敛排查：已排除 5 个假设、发现 `align4` 的 0/0 bug |
| **`d-version-kernel-bug.md`** | **D 版不收敛的真根因**——手写核漏了 `TimeDerivative`、`v` 含自己、没设 `variable_L` ⇒ **解的根本不是同一个方程** |

### 环境与 API

| 文件 | 内容 |
|---|---|
| **`moose-api-gotchas.md`** | **MOOSE 输入文件的 19 个坑**（全是实测踩出来的）——接手前必读 |
| `wsl-moose-environment-setup.md` | WSL + MOOSE 运行环境布局与六个坑的解法 |
| `artifact-publishing-unavailable.md` | 本机 Artifact 工具不可用，改用本地 HTML |
| `overnight-2026-09-18-plan.md` | 某次夜间工作的状态快照（**已过期，仅作历史**） |

---

## 交接时还需要人工做的两件事

这两件**不在本目录里**，但缺了交接不完整：

### 1. 全局偏好

`C:\Users\mycomputer\.codex\AGENTS.md` 与 `C:\Users\mycomputer\.claude\CLAUDE.md`
内容相同（中文回答、Python、最小改动、先读项目结构……）。
**Codex 侧已经有了，不用重做**，但换机器时要记得带。

### 2. 项目信任与网络

`~/.codex/config.toml` 里有 `[projects.'...']` 信任列表，**`f:\speed_up` 不在里面**。
另外该配置里 **`web_search = "disabled"`** —— 而本项目有大量文献检索工作，
需要时得显式开启。
