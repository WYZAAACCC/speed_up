---
name: omega0-segregation-calibration
description: 晶界偏析参数 Ω₀ 的理论依据、量纲坑、标定值（当前值大了 100 倍），以及 Γ 的量纲错误
metadata: 
  node_type: memory
  type: project
  originSessionId: b6decc92-d1df-4297-b052-ad15b31c0547
  modified: 2026-09-19T12:06:58.752Z
---

**`Ω₀`（生产/1D 研究里的晶界偏析项系数）有理论公式，且当前值大了约 100 倍。**

## 理论公式（Cahn 1962）

Cahn 把晶界当成带相互作用势 `E(x)` 的板 ⇒ 我们的 `f_seg = (Ω₀/w_GB)(c−c₀)h_gb`
就是 `c·E`。映射：

```
Ω₀ = w_GB · ΔG_seg / v_m       ⇔   s = exp(−ΔG_seg/RT)
物理更透明的等价写法：f_seg = (ΔG_seg/v_m)(c − c₀)h_gb    ← 自带温度依赖
```

## ⚠ 两个必须先纠正的坑

1. **`c` 是摩尔分数 ⇒ `Γ = ∫(c−c_far)dx` 的单位是【米】**，
   必须乘摩尔密度 `ρ_mol ≈ 1.01×10⁵ mol/m³` 才是物理的 Gibbs 过剩（**差 10⁵ 倍**）。
2. **不能用「守恒量做差」的后处理读 Γ**：`gamma_gb = c_total − c_edge×L`
   是两个 2.7e-7 量级的数相减，**噪声地板 ~1e-6 相对量级**，
   会把真值读成差 169 倍的假数。**改用 `c_max − c_min` 直接读剖面**。

## 标定值

`|Ω₀| = (3/4)·f_cc·Γ_target/ρ_mol`。对上 Tan 2016 的 V 锚点（2.2~5.3 at·nm⁻²）
⇒ **`Ω₀ ≈ −5×10⁻¹¹`**（**当前 `−4.6×10⁻⁹` 大 60~150 倍**）。
实验确认：`Ω₀=−5e-11` 给 `Γ ≈ 2.5 at·nm⁻²`，正落锚点内。

## ⚠ 但 `Ω₀` 不是主要矛盾

分配项 `A_part·c²·Ση²` 在固固晶界上**凭空造出** 222 at·nm⁻² 的过剩
（`Ση²` 在晶界处是 0.5 不是 1 ⇒ 晶界被当成另一种相）。
**必须同时把分配项改成 `h_solid`**，基座才会精确归零。
⇒ **Phase 3 的两个增量都还没进生产**（生产 `f_loc` 仍是 `A_part·c²·Ση²`）。

## 无法同时对上 s 与 Γ

模型 `s = 1.44`（真实 3~10，偏小）而 `Γ = 290 at·nm⁻²`（真实 2.2~5.3，偏大约 100 倍）。
反向偏、根因同为「真实晶界 ~1 nm vs 模型 400 nm~4 µm」。
**按本课题立足点标定 Γ，代价是局域剖面不再有物理意义 —— 论文必须明写。**

**Why**：这决定 Phase 3 能否合入生产；不先改对会让后面所有「修好了」的结论不可信。

**How to apply**：合入顺序 = ① 改 `Ω₀` ② 分配项换 `h_solid` ③ 加偏析项 ④ 加温度依赖。
生成器 `pipeline/validated/make_phase3_prod.py`（三处必须一起改，含 `M` 的分母 `f_cc`）。

详见 `pipeline/GB_SEGREGATION_LITERATURE.md` §0.3。
相关：[[gate0-frozen-reproducibility]]、[[physics-gaps-for-reviewers]]
