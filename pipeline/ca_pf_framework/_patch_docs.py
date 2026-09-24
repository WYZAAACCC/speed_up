# -*- coding: utf-8 -*-
"""_patch_docs.py --- 文档更正：MATH_FRAMEWORK 4.4 的 (a/2)；CA3D_REPORT 指向审计报告"""
import io, sys

# 1) MATH_FRAMEWORK §4.4 的三档判据：胞心约定（无 1/2）
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/MATH_FRAMEWORK.md"
s = io.open(P, encoding="utf-8").read()
old = "按邻居类型展开即得常用的三档判据（@@a@@ 为胞边长）："
new = ("按邻居类型展开即得常用的三档判据（@@a@@ 为胞边长；【2026-09-23 更正】这里用的是\n"
       "**胞心到胞心**的偏移 @@d_{ij}@@：面邻 @@|d|=a@@、棱邻 @@a\\sqrt2@@、角邻 @@a\\sqrt3@@，"
       "故下面三式**没有 1/2**；代码 `_thr_tables` 的 `thr=dx*Σ` 正是这个约定，与 ExaCA 一致）：")
if old not in s:
    print("!! MF 锚点未找到"); sys.exit(1)
s = s.replace(old, new, 1)
old2 = r"""\text{面邻：}\ell\ge \frac{a}{2}\sum_a|\mathbf p_a\!\cdot\!\hat{\mathbf n}|,\quad
\text{棱邻：}\ell\ge \frac{a\sqrt2}{2}(\dots),\quad
\text{角邻：}\ell\ge \frac{a\sqrt3}{2}(\dots)"""
new2 = r"""\text{面邻：}\ell\ge a\sum_a|\mathbf p_a\!\cdot\!\hat{\mathbf n}|,\quad
\text{棱邻：}\ell\ge a\sqrt2\,(\dots),\quad
\text{角邻：}\ell\ge a\sqrt3\,(\dots)"""
if old2 not in s:
    print("!! MF 公式未找到（可能已被改过），跳过")
else:
    s = s.replace(old2, new2, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("MATH_FRAMEWORK §4.4 已更正（去掉 1/2，明确胞心约定）")

# 2) MATH_FRAMEWORK 里加一条 2026-09-23 修复说明
old3 = "### 4.4 取向与捕获判据（decentered octahedron）"
new3 = ("""### 4.4 取向与捕获判据（decentered octahedron）

> ⚠ **2026-09-23 修复（见 `CA3D_AUDIT_2026-09-23.md` / `CA3D_FIX_PLAN_2026-09-23.md`）**
> 代码默认捕获已从 `decentered`（逐胞 L 预算 + 格点路径代价）换成 **`envelope`**
> （逐晶粒连续包络 ℓ_g + 外延邻接 + 逐胞 argmax(ℓ_g/sup_g)），原因：
> ① `decentered` 的格点路径代价使**径向可达距离短 25~40%**（实测 r(<100>)/ℓ=0.60~0.76，
>    正确 1.00），KD 各向异性 1.73 被压到 1.05~1.12，晶粒体积 −25%，且**不随 dx 收敛**；
> ② 旧 `thermal_capture` 的 26 邻域洪泛**依赖扫描顺序**（30% 的初始胞换主）且残留冷液相会
>    **每胞一颗**自形核（41³ 盒造 68578 个假晶粒）。
> 新实现实测：体积误差 ∝ dx（0.003%/0.07%/0.98%/2.2% @ dx=0.5/1/2/3 µm）、顺序无关、
> 无假晶粒、熔池界面单连通无孤岛且随 dt 收敛。`decentered` / `analytic` 保留可选。""")
if old3 not in s:
    print("!! MF 4.4 标题未找到")
else:
    s = s.replace(old3, new3, 1)
    io.open(P, "w", encoding="utf-8").write(s)
    print("MATH_FRAMEWORK 已加修复说明")