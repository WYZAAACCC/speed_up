#!/usr/bin/env python3
"""
把 **AMR** 打进生产输入（用户 2026-09-19 决定「改用 AMR」）。

## 为什么是 max_h_level = 1

由 **Q10 的裁决**直接给出（见 `VALIDATION_STATUS.md` §2.2）：
判据是 `d/dx ≥ 4`，其中 `d = sqrt(2κ/μ0) = 2.00 µm` 是**平衡剖面的实际宽度**
（不是 `w = sqrt(κ/μ) = 1.41 µm` —— 那只是它的 1/√2）。

生产基础网格 `dx = 1 µm` ⇒ `d/dx = 2` ❌（T8b 实测 ε 偏 **+6.85%**）
**`max_h_level = 1` ⇒ 界面处 `dx = 0.5 µm` ⇒ `d/dx = 4` ✅**（T8b 实测 +1.61%）
⇒ **不需要 level 2。**

## 指示量：`S = Ση²`，**节点型**

| 候选 | 判定 |
|---|---|
| `liquid_flag` / `unique_grains` | ❌ **CONSTANT MONOMIAL** ⇒ 单元内梯度恒为 0 ⇒ `GradientJumpIndicator` 恒为 0，AMR 不触发 |
| `T` | ⚠ 节点型可用，但梯度最大处在**熔池内部**，不是界面 |
| **`S = Ση²`（新增）** | ✅ 同时捕捉**固固晶界**（1 → 0.5）与**固液界面**（1 → 0） |

## coarsen 必须小到不破坏守恒（⚠ 这一条是本轮实测改出来的）

原以为「`coarsen = 0` 会让单元数单调增长 ⇒ 生产必须粗化」，于是先设了 `coarsen = 0.1`。
**但实测发现粗化会破坏守恒判据（T2，1e-8）**：

| `coarsen` | 守恒漂移 | `n_elem` 末 | 判定 |
|---|---|---|---|
| 0.00 | **0.00e+00** | 1134 | ✅ |
| **0.02** | **0.00e+00** | 1134 | ✅ **生产用这个** |
| 0.05 | 1.01e-07 | 1128 | ❌ 超判据 |
| 0.10 | 2.05e-07 | 1125 | ❌ 超判据 |

（`validated/run_nucleation_check.sh` 的 54×19 算例，7 个输出步。）

**⇒ 阈值在 0.02 与 0.05 之间。** 而且那个短算例里单元数几乎没有差别（1134 vs 1125）——
说明**原来的 0.1 是拿守恒换了一个这里根本看不到的收益**。

⚠ **仍未验证**：长跑下 `coarsen = 0.02` 能不能把单元数压住
（短算例看不出，因为前沿还没扫过整个域）。这是**已知的未验证项**。

## 实测（`validated/run_prod_amr.sh`，54×19 缩小网格，`end_time=2e-6`）

| 档 | 墙钟 | `n_elem` | AMR | 守恒漂移 | vs uniform |
|---|---|---|---|---|---|
| `uniform` | 187 s | 1026→1026 | 未生效 | 0.00e+00 | — |
| **`amr1`（level=1）** | **177 s** | 1026→**1587** | **已生效** | **0.00e+00** | **0.453%** |
| `amr2`（level=2） | 198 s | 1026→2934 | 已生效 | 0.00e+00 | 0.661% |

⇒ **level=1 反而比 uniform 快**（单元多 55%，但自适应步长走的步数更少）。

## ⚠ 前提：后处理里不能有硬编码 `elementid`

AMR 段错误的**真正原因**是硬编码 `elementid` 的后处理（见 §1.6）——
AMR 后该 id 变成非活动父单元，其 DOF 不在解向量里 ⇒ `PetscVector::get` 越界。
**生产输入已核查：零 `elementid`** ✓ 本脚本会再断言一次。

用法
----
    python3 make_amr_prod.py --src stage1_meltpool_c.i --out x.i --dry-run
    python3 make_amr_prod.py --src stage1_meltpool_c.i --out stage1_meltpool_c.i
"""

import argparse
import difflib
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

N = 8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-h-level", type=int, default=1,
                    help="AMR 最大加密层数。1 = 1µm→0.5µm，正好满足 d/dx=4（默认）")
    ap.add_argument("--coarsen", type=float, default=0.02,
                    help="粗化比例。0 = 只加密（长期跑会让单元数单调增长）")
    ap.add_argument("--interval", type=int, default=2, help="每几个时间步自适应一次")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = open(a.src, encoding="utf-8").read()

    # ---- 前提断言：不能有 elementid ----
    if "elementid" in src:
        sys.exit("错误：源输入里有 `elementid` —— AMR 会段错误。先看 VALIDATION_STATUS.md §1.6")
    if "[Adaptivity]" in src:
        sys.exit("错误：源输入里已经有 [Adaptivity] —— 不要重复加")
    print("  前提：源输入零 `elementid` ✓，且无既有 [Adaptivity] ✓")

    out = src

    # ---- ① 节点型 AuxVariable ----
    m = re.search(r"^\[AuxVariables\]\n", out, re.M)
    if not m:
        sys.exit("错误：找不到 [AuxVariables]")
    out = out[:m.end()] + """  # 【AMR 指示量】固相指示 S = Ση² —— 晶粒内 1、固固晶界 0.5、液相 0。
  # ⚠ 必须**节点型**：单元常量没有单元内梯度，GradientJumpIndicator 会恒为 0。
  [S_eta2_aux]
    order = FIRST
    family = LAGRANGE
  []
""" + out[m.end():]

    # ---- ② 对应的 AuxKernel ----
    vars8 = " ".join(f"gr{i}" for i in range(N))
    expr = "+".join(f"gr{i}^2" for i in range(N))
    m = re.search(r"^\[AuxKernels\]\n", out, re.M)
    if not m:
        sys.exit("错误：找不到 [AuxKernels]")
    out = out[:m.end()] + f"""  [S_eta2_k]
    type = ParsedAux
    variable = S_eta2_aux
    coupled_variables = '{vars8}'
    expression = '{expr}'
  []
""" + out[m.end():]

    # ---- ③ [Adaptivity] ----
    adapt = ("[Adaptivity]\n"
             "  marker = marker\n"
             f"  interval = {a.interval}\n"
             f"  max_h_level = {a.max_h_level}\n"
             "  [Indicators]\n"
             "    [jump]\n"
             "      type = GradientJumpIndicator\n"
             "      variable = S_eta2_aux\n"
             "    []\n"
             "  []\n"
             "  [Markers]\n"
             "    [marker]\n"
             "      type = ErrorFractionMarker\n"
             "      indicator = jump\n"
             "      refine = 0.5\n"
             f"      coarsen = {a.coarsen}\n"
             "    []\n"
             "  []\n"
             "[]\n\n")
    i = out.index("[Outputs]")
    out = out[:i] + adapt + out[i:]

    print("将做以下改动：")
    print(f"  1. 新增节点型 AuxVariable `S_eta2_aux` = Ση²（AMR 指示量）")
    print(f"  2. 新增对应 AuxKernel")
    print(f"  3. 新增 [Adaptivity]：max_h_level={a.max_h_level}、"
          f"coarsen={a.coarsen}、interval={a.interval}")
    print()

    diff = list(difflib.unified_diff(
        src.splitlines(keepends=True), out.splitlines(keepends=True),
        fromfile=a.src, tofile=a.out))
    nchg = len([d for d in diff if d.startswith("+") or d.startswith("-")]) - 2
    print(f"diff：{nchg} 行新增")

    if a.dry_run:
        sys.stdout.writelines(diff)
        print("\n(--dry-run：没有写文件)")
        return

    open(a.out, "w", encoding="utf-8", newline="").write(out)
    open(a.out + ".diff", "w", encoding="utf-8", newline="").write("".join(diff))
    print(f"\n写出 {a.out}    diff 存到 {a.out}.diff")
    print("\n自检：")
    print("  [Adaptivity]      :", out.count("[Adaptivity]"), "（应为 1）")
    # ⚠ `[S_eta2_aux]` 只该出现 **1** 次（那是块头）；AuxKernel 用的是
    #   `variable = S_eta2_aux`，**不带方括号**。别把期望值写成 2。
    print("  S_eta2_aux 块头   :", out.count("[S_eta2_aux]"), "（应为 1）")
    print("  引用 S_eta2_aux   :", out.count("= S_eta2_aux"), "（应为 2 = 变量声明 + 核引用）")
    print("  max_h_level       :", a.max_h_level)
    print("  仍无 elementid    :", "elementid" not in out)


if __name__ == "__main__":
    main()
