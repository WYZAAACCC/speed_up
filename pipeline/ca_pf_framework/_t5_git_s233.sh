#!/bin/bash
# _t5_git_s233.sh --- ★★★★★★ 决定性结论：ellipse 公式修好后仍**不起作用**（空开关）
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_amwait.sh pipeline/ca_pf_framework/_t5_amnow.sh 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s233 ★★★★★★ 决定性结论: ellipse 公式修好后**仍不起作用**（空开关）

## 用户目标
"验证一下当前的物理公式是否真正起作用，如果起作用，就将其和已经证明有效的 --eng-elong 叠加"

## 结果（**step 40，同一末步，格式 = 长宽比 / 长厚比**）
```
臂          配置                          step40 长宽比        长厚比
t5AM_ell    ellipse, eng-elong=0           **1.88** [1.88,2.03]  **3.44**
t5AB_A      exp2(默认), eng-elong=0        **1.88**              **3.27**
   => 1.88 vs 1.88 => --mob-iform ellipse **毫无效果**

t5AM_combo  ellipse + eng-elong=7          **6.67** [2.04,6.68]  **12.14**
t5AD_700    exp2    + eng-elong=7          **6.66**              **12.15**
   => 6.67 vs 6.66 => ellipse **一点贡献都没有**
```

## 三条结论
1. 【判据1】公式**未真正起作用**: 修好 BUG 后它能跑(无 traceback、形核正常),
   但长宽比与对照**逐数相同**(1.88 vs 1.88) => 效果 ≈ 0(比仓库自己记的"引擎实际 1.24"还低);
2. 【判据2】叠加**无效**: ellipse+eng-elong7 给 6.67, 单用 eng-elong7 给 6.66
   => 差 0.01 = 噪声 => 两机制没有叠加(因为 ellipse 本身没作用);
3. => --eng-elong 仍是唯一**有效**的手段; --mob-iform ellipse 目前是一个**空开关**。

## 按预登记判据
判据 1「ellipse 应显著 > 1.85」**不成立** => 记账, 且**不进入叠加**(叠加本已无效)。

## 因果链（完整记账）
* 阶段一: 开 ellipse => **两臂 step 0 崩**(sorted 对三维数组) => 找到并修好框架 BUG;
* 阶段二: 修好后重启 => 两臂**静默死亡** => 查出是**我的重启脚本缺 setsid/wait**(SIGHUP),
  **不是修复的错** => 加 setsid 后存活;
* 阶段三: 修好 BUG **且**存活后 => **公式仍无效果**(本轮) => **结论: 空开关。**

## 下一步(记账, 待用户定)
要让它真起作用，需要查出 `_mfac_dt` 为何 ≈ 1（`mob_iform='ellipse'` 分支里
`_g = B/sqrt(B²cos²θ + sin²θ)`、`_B = 1/mob_ratio`），可能原因:
 (a) `mob_beta` 与 `_s2` 的组合让指数项主导、面内项被淹没;
 (b) `ndir_` 的形状/归一化让 `_ca`、`_sw` 退化;
 (c) 该分支可能**没有真正接到 `v_cell` 的最终乘子**上（被后续 `v_cell = ...` 覆盖）。
=> 三条都可离线查代码/print 诊断，**不需要长跑**。
MSGEOF
git log --oneline -1
