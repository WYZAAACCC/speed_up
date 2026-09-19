#!/usr/bin/env python3
"""
把**溶质液相扩散系数 `D_L` 改成子网格闭合**（缺口 #3 修复的第 3 条）。

## 为什么必须改（这是修复里唯一**偏离物理值**的一步，必须写清楚理由）

### 物理事实

生产工作点上溶质边界层是

    δ_c = D_L / V = 2.52e-9 / 0.6 = **4.2 nm**

而网格 `dx = 1 µm` ⇒ **`δ_c` 比一个网格还小 238 倍**。
连续性偏微分方程的离散解**不可能**表示一个比网格还薄的层 ——
数值上那层会被摊到 `~dx` 宽。

### 后果（实测，不是推断）

`validated/run_prod_1d.sh` 在**生产工作点**上实测：

| 量 | 值 |
|---|---|
| `∫(c−c0)dx` | `8.870e-11`（= 解析式 `2MAc0/V`，逐位相同） |
| `k_eff`（模型） | **0.999015** |
| `k_eff`（Aziz 物理值，`a0 = 0.3 nm`） | 0.6549 |
| **界面排出的溶质被低估** | **350×** |

⇒ 微偏析被低估 350 倍，而微偏析正是本课题要预测的量。

### 为什么放大 `D_L` **不改变答案**

模型里有一条**严格关系**（CH 方程积分一次得到，与 `κ_c`、与网格都无关）：

    ∫(c − c0)dz = 2·M·A·c0 / V
    ⇒ c_max − c0 = 2·M·A·c0 / (V · L_eff),   L_eff ≡ ∫(c−c0)dz / (c_max − c0)

抗截留项把 `L_eff` 从 `δ_c + 1.5·ξ` 拉回 `δ_c = M·k_c / V`。代进去：

    c_max − c0 = 2·M·A·c0 / (V · M·k_c/V) = **2·A·c0 / k_c**

**与 `D_L`、与网格都无关。** 所以放大 `D_L` 只是把"物理上本来就有、但网格看不见"
的那一层变成**可解析**的，不引入新的近似。

### 取值

要求 `δ_c ≥ 2·dx`（最慢的情形：最快的前沿速度、最粗的网格）：

    V_max = 0.6 m/s（生产扫描速度，来自 laser_T 里的 0.6*t）
    dx    = 1 µm（基础网格；AMR 在界面处细到 0.5 µm）
    ⇒ D_L ≥ 2 · 0.6 · 1e-6 = **1.2e-6 m²/s**

取 `1.2e-6` ⇒ `δ_c = 2 µm`、`ξ/δ_c = 1`。
而抗截留项的 1D 标定显示 **`ξ/δ_c = 1` 正是残差最小（−0.69%）的那一档** ✓
`V ∈ [0.3, 1.2] m/s` ⇒ `ξ/δ_c ∈ [0.5, 2]` ⇒ 残差 ∈ [+2.3%, −4.2%] ✓

### 副作用，逐条核算

| 关注点 | 核算 | 结论 |
|---|---|---|
| 熔池尺度是否被搅匀 | `D_L·t/L² = 1.2e-6 × 1.7e-4/1e-8 = 0.02` | **≪ 1，仍然不混合** ✓ |
| 固相/晶界扩散 | `D(η) = D_L + (D_S−D_L)h_s + (D_GB−D_S)h_gb`<br>`h_s=1` 处 `D = D_S`、`h_gb=1` 处 `D = D_GB`，**逐点精确、与 `D_L` 无关** | **不影响 `s·δ·D_GB` 这个可观测量** ✓ |
| 平衡分配（T4） | `V = 0`，与 `D` 无关 | **不受影响** ✓ |
| 矩阵条件数 | `M/dx²` 从 2.8e3 升到 1.3e6，更接近 `1/dt=5e5` | **反而改善** ✓ |
| 时间步上限 | `dx⁴/(16·M·κ_c)` 从 2.2e-3 降到 4.7e-6，仍 > 生产的 `dtmax=2e-6` | **无额外代价** ✓ |

### ⚠ 必须如实声明的偏离

`1.2e-6` **不是** Ti64 中 V 的液相扩散系数（那是 `2.52e-9`）。
它是**子网格闭合参数**：在 `dx = 1 µm` 上代表"把物理边界层放大到网格能看见"。
论文里必须写成 closure，不能写成材料常数。

用法
----
    python3 make_dl_prod.py --src stage1_meltpool_c.i --out x.i --dry-run
    python3 make_dl_prod.py --src stage1_meltpool_c.i --out stage1_meltpool_c.dlclosure.i
"""

import argparse
import difflib
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

D_L_PHYS = 2.52e-9
D_L_NEW = 1.2e-6
V_SCAN = 0.6
DX = 1.0e-6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dl", type=float, default=D_L_NEW)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = open(a.src, encoding="utf-8").read()

    # 定位 [solute_mobility] 的 constant_expressions = 'D_L D_S D_GB k_c A_part'
    # ⚠ 行首锚定 + re.M；块名在注释里也出现过（本仓库的坑）
    m = re.search(r"^[ \t]*\[solute_mobility\]\n(?:.*?\n)*?[ \t]*constant_expressions\s*=\s*'([^']*)'",
                  src, re.M)
    if not m:
        sys.exit("错误：找不到 [solute_mobility] 的 constant_expressions —— 源文件变过了？")
    vals = m.group(1).split()
    if len(vals) != 5:
        sys.exit(f"错误：constant_expressions 应有 5 个数，实际 {len(vals)}：{vals}")
    old_dl = float(vals[0])
    if abs(old_dl - D_L_PHYS) / D_L_PHYS > 0.01:
        sys.exit(f"错误：当前 D_L = {old_dl:g}，与预期的物理值 {D_L_PHYS:g} 不符 —— "
                 "源文件可能已经改过，先确认再动")

    vals[0] = f"{a.dl:.6g}"
    new_ce = " ".join(vals)

    out = src[:m.start(1)] + new_ce + src[m.end(1):]

    # 在被改的行上方补一条说明（只加一次）
    note = (
        f"    # 【缺口 #3 修复 (c)】D_L = {a.dl:g} m²/s —— **子网格闭合，不是材料常数**。\n"
        f"    #   物理值 D_L = {D_L_PHYS:g}（Ti 的液相扩散系数）⇒ δ_c = D_L/V = "
        f"{D_L_PHYS/V_SCAN*1e9:.1f} nm，\n"
        f"    #   比 dx = {DX*1e6:g} µm 小 {DX/(D_L_PHYS/V_SCAN):.0f} 倍 ⇒ **网格不可解析**，\n"
        f"    #   数值上那层被摊到 ~dx 宽 ⇒ 实测 k_eff = 0.999 vs 物理 0.655（微偏析低估 350×）。\n"
        f"    #   取 D_L ≥ 2·V_scan·dx = {2*V_SCAN*DX:.3g} 使 δ_c ≥ 2 个网格。\n"
        f"    #   **精确关系 c_max−c0 = 2A·c0/k_c 与 D_L 无关** ⇒ 放大不改变答案，\n"
        f"    #   只是把物理上本就有、但网格看不见的那层变成可解析的。\n"
        f"    #   副作用核算（熔池混合 0.02、D_S/D_GB 逐点不变）见 make_dl_prod.py 的文件头。\n"
    )
    line_start = out.rfind("\n", 0, m.start()) + 1
    out = out[:line_start] + note + out[line_start:]

    print("将做以下改动：")
    print(f"  1. [solute_mobility] 的 D_L：{old_dl:g} → **{a.dl:g}** m²/s"
          f"（×{a.dl/old_dl:.0f}）")
    print(f"  2. 上方补一段说明（它是闭合参数，不是材料常数）")
    print(f"  3. D_S / D_GB / k_c / A_part **不动**：{new_ce}")
    print()

    diff = list(difflib.unified_diff(
        src.splitlines(keepends=True), out.splitlines(keepends=True),
        fromfile=a.src, tofile=a.out))
    nchg = len([d for d in diff if d.startswith(("+", "-"))]) - 2
    print(f"diff：{nchg} 行变化")
    if a.dry_run:
        sys.stdout.writelines(diff[:40])
        print("\n(--dry-run：没有写文件)")
        return

    open(a.out, "w", encoding="utf-8", newline="").write(out)
    open(a.out + ".diff", "w", encoding="utf-8", newline="").write("".join(diff))
    print(f"\n写出 {a.out}    diff 存到 {a.out}.diff")

    # 自检
    m2 = re.search(r"^[ \t]*\[solute_mobility\]\n(?:.*?\n)*?[ \t]*constant_expressions\s*=\s*'([^']*)'",
                   out, re.M)
    v2 = m2.group(1).split()
    print("\n自检：")
    print(f"  D_L = {float(v2[0]):g}（应为 {a.dl:g}）")
    print(f"  D_S = {float(v2[1]):g}（应为 4e-13）")
    print(f"  D_GB = {float(v2[2]):g}（应为 4e-10）")
    print(f"  k_c = {float(v2[3]):g} / A_part = {float(v2[4]):g}（应为 0.9 / 0.264）")
    assert abs(float(v2[0]) - a.dl) / a.dl < 1e-9
    assert abs(float(v2[1]) - 4e-13) / 4e-13 < 1e-9
    assert abs(float(v2[2]) - 4e-10) / 4e-10 < 1e-9
    assert abs(float(v2[3]) - 0.9) < 1e-12 and abs(float(v2[4]) - 0.264) < 1e-12
    print("  ✅ 只有 D_L 变了")


if __name__ == "__main__":
    main()
