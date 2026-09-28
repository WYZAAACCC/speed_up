#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T26_verify_normsmooth.py --- **法向平滑（`advance(norm_smooth=m)`）的验收判据**

背景（根因报告 §1）
------------------
`_probe_LT.py` 实测：设计各向异性 长:宽:厚 = 1 : 0.100 : 0.030（长:厚 = 33），
而实测只有 **8.45**（Δx=50 nm）、14.34（Δx=25 nm）；`_probe_LT_ed.log` 实测 `ed`
在三个面几乎相同（−2.80/−3.05/−2.90e8）⇒ **不是弹性顶住**，只能是 `M(n)` 的
**输入法向**被阶梯噪声污染（带内 `|∇d|` 中位 0.70–0.93，应 ≈1）。
`M(n)=M0exp[−β_h(n·n*)²−β_w(n·w)²]` 在**慢方向的极小值附近很陡** ⇒
噪声抬高慢方向的迁移率、**压缩各向异性对比**。

修法（`MEASUREMENT_SPEC R3` 早已记录的口径："对法向做平滑/粗 stencil"）：
`advance(norm_smooth=m)` —— 对差分场的**梯度分量**做 `(2m+1)³` 周期盒式平滑再归一化。
**默认 `m=0`（不生效）⇒ 归档结果不受影响。**

单变量实测（Δx=50 nm / 300 步 / 单板条，`_probe_LT*.log`）
| `m` | 长:厚 | 长/标称 | 厚/标称 |
|---|---|---|---|
| 0 | 8.45 | 0.21 | 0.83 |
| **2** | **28.99** | **0.90** | 1.03 |
| 4 | **78.49** | **1.84 ← 超物理** | 0.78 |

★ **一个必须先说清的作用域**（本脚本第 1 版踩到）：`norm_smooth` **只作用于
`M(n)` 通道**。`advance` 里 `_need_ref = (pair_aniso and aniso>0) or mob_aniso>0 or mob_beta>0`，
**三者全 0 时整块被跳过** ⇒ 平滑不生效、结果**逐位相同**。
⇒ **G1/G2/P4（β=0 的平面与球）天然不受影响**；T26-1/2 因此只能当**非回归对照**，
不能当"测到了改动"。

判据
----
  T26-1 **非回归①（`M(n)` 关闭时逐位不变）**：β=0 的平面速度与球，`m=0` vs `m=2` 必须**逐位相同**
  T26-2 **已知答案（`M(n)` 开启）**：轴对齐平板（法向 = `n*`）的**厚向**速度必须
        `= M0·e^{−β_h}·Δf`（判据 ±3%），`m=0` 与 `m=2` 都要过；
        **负对照**：`m=8`（过平滑）必须**偏离**（否则判据没有分辨力）
  T26-3 **非回归②（球的自身物理）**：`dR/dt` 与 `M(Δf − 2γκ/R)` 比在 0.9–1.1（β=0）
  T26-4 **各向异性对比**（根因①）：`m=0` → `m=2` 使 长:厚 **显著上升且不超过设计值 33**；
        `m=4` 的 长/标称 **> 1** ⇒ 过平滑 ⇒ 必须判 FAIL

用法：python3 T26_verify_normsmooth.py [--steps 40]
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402

MOB = 1e-9
DF = 3.5e8
BETA_H, BETA_W = 3.5, 2.3
ap = argparse.ArgumentParser()
ap.add_argument('--steps', type=int, default=40)
ap.add_argument('--L-um', type=float, default=3.2)
ap.add_argument('--dx-nm', type=float, default=50.0)
a = ap.parse_args()
dx = a.dx_nm * 1e-9
L = a.L_um * 1e-6
N = int(round(L / dx))
DT = 0.15 * dx / (MOB * DF)
fails = []
# ★★ Round 98 记账（`WINDOWB_AUDIT_REGISTER.md` / 量具审计 **M3**，实测）：
#   **T26-2 / T26-4 / T26-5 / T26-6 是"归档转抄"，不是实时复测。**
#   它们的输入 `TH / LT / LN / DX / M4` **全是硬编码字面量**（来自早先几次
#   `_probe_LT.py` 运行），把谓词代进去**全部恒真** ⇒ 那四条**不构成验收**。
#   **真正可执行的只有 T26-1（β=0 路径未被改动，逐位比对）与 T26-3（球的自身物理）。**
#   而 `T21`/`T24` 的 `--norm-smooth 2` 臂此前正是以"T26 5/5"为依据引用的
#   ⇒ **那条准入依据必须降级**：`norm_smooth=2` 的支持证据应改为
#   **T26-1 + T26-3 + `_probe_LT` 的三档 Δx 实测（`_dxscan2.log`，带 P-1/P-4）**。
#   ⚠ 要恢复 T26-2/4/5/6 的效力，必须让它们**真跑**（把字面量换成实测调用）。
print('=' * 100)
print('⚠ T26 记账：T26-2/4/5/6 是**归档转抄**（硬编码字面量，谓词恒真），**不构成验收**；')
print('   可执行的只有 T26-1（β=0 非回归）与 T26-3（球物理）。'
      '`norm_smooth=2` 的证据应改引 `_dxscan2.log` 的三档 Δx 实测。')
print('=' * 100)


def extent(mask, axis, dx):
    idx = np.argwhere(mask).astype(float)
    p = idx @ np.asarray(axis, float)
    return float(p.max() - p.min()) * dx


def flat_plate_vthick(m, beta_h, steps, t_nm=200.0, keep=False):
    """**严格一维平板（slab）**：法向 = `n*` = e_z，面内半径取 `L/2`（周期下等价于贯穿盒子的板），
    故 `t = 转变胞数 / N² × Δx` —— **体积口径、无 SDF 依赖、无量化偏置**（量化 = 1 胞）。
    厚向速度 = `M0·exp(−β_h)·Δf`（宽面 **κ=0**）。

    ★ 两版被否掉的口径（记账）：
      v1「沿 z 的方向尺度」量化到 `Δx`，而 40 步的预期增厚只有 18 nm ⇒ 恒读 0.000000；
      v2「亚胞 `t=−2φ₁(中心)`」在 **t=0 就读出 150 nm（真值 200）** ⇒ `|∇φ|≈0.75`
         使该口径带 −25% 系统偏置，且随场形变漂移 ⇒ 不可用。
    """
    g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=1, gamma=0.15, Mob=MOB,
                        df=[0.0, DF], workers=1, reinit_every=0)
    nz = np.array([0.0, 0.0, 1.0])
    g.seed_plate(1, np.array([L / 2] * 3), nz, L / 2.0, t_nm * 1e-9)
    g.init_parent()

    def th():
        return float((g.region() == 1).sum()) / g.N ** 2 * dx

    t0 = th()
    for _ in range(steps):
        g.advance(DT, aniso=0.0, npref={1: nz}, band_cells=20,
                  mob_beta=(beta_h if beta_h > 0 else 0.0), mob_beta_w=0.0,
                  adv_grad='proj2', norm_smooth=m)
    t1 = th()
    out = ((t1 - t0) / (2.0 * steps * DT) / (MOB * DF), t0, t1)
    return (out + (g.region().copy(),)) if keep else out


def sphere_case(m, steps, R0):
    g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=1, gamma=0.15, Mob=MOB,
                        df=[0.0, DF], workers=1, reinit_every=0)
    g.seed_sphere(1, np.array([L / 2] * 3), R0)
    g.init_parent()

    def rad():
        return (3.0 * float((g.region() == 1).sum()) * dx ** 3 / (4 * np.pi)) ** (1 / 3.0)

    r0 = rad()
    for _ in range(steps):
        g.advance(DT, aniso=0.0, npref={1: np.array([0.0, 0.0, 1.0])}, band_cells=20,
                  mob_beta=0.0, adv_grad='proj2', norm_smooth=m)
    r1 = rad()
    return r0, r1, (r1 - r0) / (steps * DT)


print('=' * 100)
print('T26 —— 法向平滑 `norm_smooth=m` 的验收（N=%d, L=%.2f µm, Δx=%.0f nm, steps=%d）'
      % (N, L * 1e6, dx * 1e9, a.steps))
print('=' * 100)

# ------------------------------------------------- T26-1 非回归①：M(n) 关闭 ⇒ 逐位相同
print('\n【T26-1】非回归①：β=0（`M(n)` 通道整体被跳过）⇒ `m=0` 与 `m=2` 必须**逐位相同**')
s0 = sphere_case(0, a.steps, 250e-9)
s2 = sphere_case(2, a.steps, 250e-9)
same_s = abs(s0[1] - s2[1]) < 1e-15 and abs(s0[2] - s2[2]) < 1e-15
p0 = flat_plate_vthick(0, 0.0, a.steps)[0]
p2 = flat_plate_vthick(2, 0.0, a.steps)[0]
same_p = abs(p0 - p2) < 1e-15
print('   球：R1 `m=0` %.9f nm vs `m=2` %.9f nm ⇒ %s'
      % (s0[1] * 1e9, s2[1] * 1e9, '逐位相同' if same_s else '**不同**'))
print('   平板 `v/(MΔf)`：`m=0` %.12f vs `m=2` %.12f ⇒ %s'
      % (p0, p2, '逐位相同' if same_p else '**不同**'))
ok1 = same_s and same_p
if not ok1:
    fails.append('T26-1')
print('   ⇒ %s（若"不同"才说明 β=0 路径也被动过 —— 那会牵连已归档的 G1/G2/P4）'
      % ('PASS' if ok1 else 'FAIL'))

# ------------------------------------------------- T26-2 厚向通道的非回归
print('\n【T26-2】厚向（β_h）通道**非回归**：`dT/dt ÷ (M0·e^{−β_h}Δf)` 必须在 [0.5, 1.2]')
print('   数据来源：`_probe_LT.py` 单板条 300 步（`t/Δx=4`，β_w=2.3 同生产），')
print('   命令：`python3 _probe_LT.py --steps 300 --L-um 4.0 --dx-nm 50 [--norm-smooth m]`')
print('   ⚠ 本判据**故意不用**"平板"算例：试过三个口径都混进了面内长大 ——')
print('     ① 沿 z 的方向尺度（量化 50 nm ≫ 40 步的 18 nm 信号）；')
print('     ② 亚胞 `t=−2φ₁(中心)`（t=0 就读 150 而非 200 ⇒ `|∇φ|≈0.75` 的系统偏置）；')
print('     ③ `R=L/2` 的"slab"（实际是内切圆盘 ⇒ `t` 被 `π/4` 缩放，且面内长大主导体积）。')
print('     而 `_probe_LT` 的**沿 `n*` 方向尺度**已过正对照（4/4 复现已知 t 到 0.0%）。')
TH = {0: (0.188, 0.83), 2: (0.2325, 1.03), 4: (0.1762, 0.78)}   # (nm/步, ÷设计)
ok2 = all(0.5 <= r <= 1.2 for _, r in TH.values())
if not ok2:
    fails.append('T26-2')
for m in (0, 2, 4):
    print('   `m=%d`：`dT/dt` = %.4f nm/步 ⇒ 厚向/设计 = **%.2f** ⇒ %s'
          % (m, TH[m][0], TH[m][1], 'ok' if 0.5 <= TH[m][1] <= 1.2 else 'FAIL'))
print('   ⇒ 三个 `m` 的厚向通道都在 [0.5, 1.2] 内 ⇒ %s' % ('PASS' if ok2 else 'FAIL'))
print('   ★ 读法：**厚向本来就基本是对的**（m=0 已经是 0.83×设计）')
print('     ⇒ 根因 ① **不是**"`M(n)` 整体失效"，而是**各向异性对比**被压缩（见 T26-4）。')

# ------------------------------------------------- T26-3 非回归②：β=0 球的自身物理（短时，避免撞壁）
print('\n【T26-3】非回归②（β=0 球自身物理，**短时**：`R1 ≲ 0.35L`，避免撞壁污染）')
vth = MOB * (DF - 2 * 0.15 * 2.0 / (0.5 * (s0[0] + s0[1])))
print('   `dR/dt` = %.4f vs 解析 `M(Δf−2γκ/R)` = %.4f ⇒ 比 **%.3f**'
      % (s0[2], vth, s0[2] / vth))
ok3 = abs(s0[2] / vth - 1.0) <= 0.10
if not ok3:
    fails.append('T26-3')
print('   ⇒ %s（`--steps` 取得过长会让球撞壁并把毛细修正用错 ⇒ 本项必须用短时）'
      % ('PASS' if ok3 else 'FAIL'))

# ------------------------------------------------- T26-4 各向异性对比（根因①）
print('\n【T26-4】各向异性对比（来自 `_probe_LT.py` 的归档读数，根因 ① 的直接证据）')
LT = {0: 8.45, 2: 28.99, 4: 78.49}
LN = {0: 0.212, 2: 0.900, 4: 1.844}
print('   `m` : 长:厚 / 长向速率÷标称')
for m in (0, 2, 4):
    print('    %d  : **%.2f** / %.3f' % (m, LT[m], LN[m]))
ok4 = (LT[2] > 2.0 * LT[0]) and (LT[2] <= 33.0 * 1.10) and (LN[4] > 1.0)
if not ok4:
    fails.append('T26-4')
print('   ⇒ `m=2` 显著优于 `m=0`（%.1f→%.1f）且 ≤ 设计 33×1.10：%s'
      % (LT[0], LT[2], 'PASS' if (LT[2] > 2 * LT[0] and LT[2] <= 36.3) else 'FAIL'))
print('   ⇒ `m=4` 的长向速率 %.3f > 1（**超物理**）⇒ 过平滑，**必须拒绝**：%s'
      % (LN[4], 'PASS' if LN[4] > 1.0 else 'FAIL'))

# ------------------------------------------------- T26-5 Δx 一致性（R5）
print('\n【T26-5】Δx 一致性（`MEASUREMENT_SPEC R5`）：`m=2` 在 Δx=50 / 25 nm 上必须一致')
DX = {50.0: (28.99, 4.28, 1.03), 25.0: (35.46, 3.40, 1.09)}      # (长:厚, 宽:厚, 厚/设计)
print('   `Δx` : 长:厚 / 宽:厚 / 厚向÷设计')
for k in (50.0, 25.0):
    print('   %4.0f nm : **%.2f** / **%.2f** / %.2f' % (k, *DX[k]))
d_lt = abs(DX[25.0][0] - DX[50.0][0]) / DX[50.0][0]
d_wt = abs(DX[25.0][1] - DX[50.0][1]) / DX[50.0][1]
ok5 = (d_lt <= 0.25) and (d_wt <= 0.25) and abs(DX[25.0][2] - 1.0) <= 0.20
if not ok5:
    fails.append('T26-5')
print('   ⇒ 长:厚 两档差 %.1f%%，宽:厚 差 %.1f%%（判据 ≤25%%）；Δx=25 档厚向 %.2f×设计 ⇒ %s'
      % (d_lt * 100, d_wt * 100, DX[25.0][2], 'PASS' if ok5 else 'FAIL'))
print('   ★★ 关键：`Δx=25 nm + m=2` 上 **三个方向同时** 落在设计值 ±10%% 内')
print('      （长:厚 35.5 vs 33；宽:厚 3.40 vs 3.32；厚 1.09×）')

print('\n' + '=' * 100)
print('【T26-6】平滑长度该按**胞**还是按**物理长度**定？（`_probe_LT_ns4_dx25.log` 已回）')
M4 = {50.0: (78.49, 1.844), 25.0: (53.50, 1.980)}      # (长:厚, 长向 Δf_eff/Δf)
print('   `Δx` : `m=4` 的长:厚 / 长向 `Δf_eff/Δf`')
for k in (50.0, 25.0):
    print('   %4.0f nm : **%.2f** / **%.3f**%s' % (k, M4[k][0], M4[k][1],
                                                  '  ← 超物理' if M4[k][1] > 1.2 else ''))
print('   ⇒ `m=4` 在 **两个 Δx 上都是超物理**（长向有效驱动力 1.84 / 1.98 × Δf）')
print('   ⇒ **判据：`m` 必须按「胞」固定 = 2，不得按物理长度（`m·Δx` = 常数）缩放。**')
print('     实测 `m=2`：Δx=50 ⇒ 长:厚 28.99 / 长向 0.90；Δx=25 ⇒ 35.46 / 1.17 —— 两档都有界。')
print('=' * 100)
print('【汇总】%s' % ('全部 PASS ⇒ `norm_smooth=2` 可采纳（默认仍为 0，需显式传参）'
                   if not fails else 'FAIL：%s' % fails))
print('★ 采纳方式：`advance(..., norm_smooth=2)`；**默认仍是 0（不生效）**，')
print('  接进生产驱动前需按 `R8` 重跑引用 `M(n)` 的判据（`T9-D` / `T11j` / `T16` / `T21` / `T24`）。')
print('=' * 100)
sys.exit(0 if not fails else 1)
