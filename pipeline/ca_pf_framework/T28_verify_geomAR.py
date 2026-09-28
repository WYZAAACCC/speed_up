#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T28_verify_geomAR.py --- `geom_ar()` 的**真对照**（取代 `_chk_geomAR.py`）

为什么要重写（`WINDOWB_AUDIT_REGISTER.md` / 量具审计 **M2 + A1**）
----------------------------------------------------------------
旧 `_chk_geomAR.py` **不是 `geom_ar()` 的对照**：
  ① 它**手抄**了"只取最大分量"的内部逻辑、**从不调用真函数**；
  ② **全脚本没有 `sys.exit` / 返回码**（实跑恒 0）；
  ③ 种子用 `seed_plate(..., nrm=NPF[K])` ⇒ **轴严格沿参考方向（θ≡0）**
     ⇒ 对量具的**主导误差项零分辨力**。

主导误差项（审计**实测**）：半径 R、厚 t、轴与 `n*` 成 θ 的圆柱，沿 `n*` 的展宽是
      **`t·cosθ + 2R·sinθ`**
⇒ θ=2° 就 +29%、θ=5° +38%（R=600/t=200）。而本项目自己实测长大中 `M6p` 退化到
**1.1–3.5°** ⇒ **该偏差正好落在实际工况里**。旧对照对这件事完全无分辨力。

判据（每条都给期望值与来源）
--------------------------
  G-1 **θ≡0 正对照**：`t_` 复现已知 t（±6%），`L_/t_` 复现 `2R/t`（±8%）
      —— 这一条旧脚本也覆盖，保留以证明"我没把好的一起改坏"
  G-2 ★ **θ=5° 必须出现预测的偏差**（`t·cos5° + 2R·sin5°`，±20%）
      —— 这是**反向对照**：若量具在这里"照样准"，说明我的误差模型错了、或量具有别的机制
  G-3 **受控合并**：同变体两片沿 `n*` 错开 ⇒ 逐分量口径必须报 **≥2 个分量**，
      且**各自**的 `t_` ≈ t（±10%）⇒ 证明"逐分量"确实把合并拆开了
  G-4 **退出码**：任一判据不过 ⇒ 非零退出（旧脚本恒 0，是它失效的直接原因之一）

用法：python3 T28_verify_geomAR.py
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402
from T24_verify_grouping import geom_ar                          # noqa: E402

L, DX = 3.2e-6, 50e-9
N = int(round(L / DX))
K = 1
R_NM, T_NM = 600.0, 200.0
R, T = R_NM * 1e-9, T_NM * 1e-9
fails = []


def build(tilt_deg=0.0, second_offset_nm=0.0):
    """造一片（或两片）已知几何的板条。`tilt_deg`：轴相对 `NPF[K]` 的倾斜。"""
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                        df=[0.0] + [3.5e8] * NV, workers=1, reinit_every=0)
    n_ref = np.asarray(NPF[K], float)
    n_ref = n_ref / np.linalg.norm(n_ref)
    if tilt_deg == 0.0:
        n_use = n_ref
    else:
        # 在 `n_ref` 的正交补里取一个方向，把法向转 `tilt_deg`
        v = np.array([1.0, 0.0, 0.0])
        v = v - (v @ n_ref) * n_ref
        v = v / np.linalg.norm(v)
        a = np.radians(tilt_deg)
        n_use = np.cos(a) * n_ref + np.sin(a) * v
        n_use = n_use / np.linalg.norm(n_use)
    c0 = np.array([L / 2] * 3)
    g.seed_plate(K, c0, n_use, R, T)
    if second_offset_nm > 0:
        g.seed_plate(K, c0 + n_use * (second_offset_nm * 1e-9), n_use, R, T)
    g.init_parent()
    # `geom_ar` 用 `atab[k]` 当长轴、`NPF[k]` 当厚度轴 ⇒ 这里照真接口调用
    # ⚠⚠ Round 139：`geom_ar` 的返回元组**已扩为 7 元**
    #    旧 (k, L_, t_, L_/t_, cells)            =>  t_ 在 v[2]
    #    新 (k, L_, W_, t_, L_/t_, L_/W_, cells)  =>  t_ 在 **v[3]**、W_ 在 v[2]
    #   ⇒ 本文件所有取厚度的 `v[2]` 必须改成 `v[3]`；不改会**静默**拿"宽"当"厚"比。
    #   本文件是 `geom_ar` 的正对照 ⇒ 索引必须与实现同步（AGENTS §3.24「改一半」）。
    return g, geom_ar(g.region(), g, NPF)


# ★ 统一取槽位的小工具（以后再改元组长度时只改这里，避免又散落 v[2]/v[3]）
def T_of(rec):
    """沿 `npref` 的厚度（新元组 v[3]）。"""
    return rec[3]


def W_of(rec):
    """沿 `npref × a` 的宽度（新元组 v[2]）。"""
    return rec[2]


def LW_of(rec):
    """几何长:宽（新元组 v[5]）—— **靶② 只认这个**。"""
    return rec[5]


print('=' * 100)
print('T28 —— `geom_ar()` 的真对照（调用**真函数** + θ 斜置 + 受控合并 + 退出码）')
print('几何：R=%.0f nm  t=%.0f nm  ⇒ `2R/t` = %.2f' % (R_NM, T_NM, 2 * R_NM / T_NM))
print('=' * 100)

# ---------------- G-1 θ≡0
g1, a1 = build(0.0)
t1 = [T_of(v) for v in a1]
ok1 = bool(t1) and all(abs(x / T - 1.0) <= 0.06 for x in t1)
print('\n【G-1】θ≡0：分量数 %d，`t_`=%s nm（真值 %.0f，判据 ±6%%）⇒ %s'
      % (len(a1), ['%.1f' % (x * 1e9) for x in t1], T_NM, 'PASS' if ok1 else 'FAIL'))
if not ok1:
    fails.append('G-1')

# ---------------- G-2 θ=5° 必须出现预测偏差
DEG = 5.0
pred = T * np.cos(np.radians(DEG)) + 2 * R * np.sin(np.radians(DEG))
g2, a2 = build(DEG)
t2 = [T_of(v) for v in a2]
ok2 = bool(t2) and abs(np.mean(t2) / pred - 1.0) <= 0.20
print('【G-2】θ=%.0f°：`t_`=%.1f nm vs 预测 `t·cosθ+2R·sinθ`=%.1f nm（比 %.3f，判据 ±20%%）⇒ %s'
      % (DEG, np.mean(t2) * 1e9, pred * 1e9, np.mean(t2) / pred, 'PASS' if ok2 else 'FAIL'))
print('      ★ 这是**反向对照**：量具在斜置下必须"偏"，否则说明误差模型错或另有机制。')
print('      相对 θ≡0 的偏差 = %+.1f%%（审计预测 ≈ +38%%）'
      % ((np.mean(t2) / np.mean(t1) - 1) * 100))
if not ok2:
    fails.append('G-2')

# ---------------- G-3 受控合并：两片沿 n* 错开
g3, a3 = build(0.0, second_offset_nm=800.0)
ok3 = (len(a3) >= 2) and all(abs(T_of(v) / T - 1.0) <= 0.10 for v in a3)
print('【G-3】受控合并（同变体两片沿 `n*` 错开 800 nm）：分量数 **%d**（判据 ≥2）；'
      '各自 `t_`=%s nm（判据 ±10%%）⇒ %s'
      % (len(a3), ['%.1f' % (T_of(v) * 1e9) for v in a3], 'PASS' if ok3 else 'FAIL'))
print('      ★ 若只报 1 个分量且 `t_`≈1000 nm，就复现了审计说的"合并把厚度抬高"。')
if not ok3:
    fails.append('G-3')

# ---------------- G-4 ★★★ 非紧凑形状：`max−min` 必须"爆表"（**缺的就是这条反向对照**）
#   动机（`WINDOWB_ROADMAP_TO_CORRECT.md`，Round 128 实测）：
#     `_probe_LT` 的三把尺子在 step 25→50 给出 **`max−min` ×2.49 / `L_vol` ×1.18 / `L_gyr` ×1.52**，
#     而**胞数只涨 +23%** ⇒ `max−min` 的"翻 2.5 倍"**没有体积支撑**。
#     病根：`max−min` 由**极值胞**主导，形状一旦不紧凑（细丝/突起）跨度就爆表
#     （`T` 在长大中**下降** 801.3→785.3 是同一个病根）。
#   ⚠ `T28` 原有的 G-1/G-2/G-3 **全部是紧凑凸体** ⇒ **从没测过非紧凑形状** ⇒ 验收不完备。
#   本判据：合成一个**单一连通分量**（板条 + 一条同变体细丝），
#   则 `max−min` **必须显著大于**体积等效长度 `L_vol = V/(W·T)`。
#   ⇒ 这条是"**量具必须偏**"的反向对照：**若不偏，说明我上一轮的诊断错了**。
# ★★ G-4 第一版**失败，但失败的是测试本身**（与 D-4/E-4 同族）：
#   ① 从已种板条"取中位胞往外接细丝"⇒ **细丝没接上主体**（连通分量数 = 2）；
#   ② `L_vol` 的分母用了 `a4[0][2]*(2R)` —— **把 `max−min` 的厚度又乘回去** ⇒ 循环论证；
#   ③ 阈值 1.5 是拍的。
#   ⇒ 改为**在网格上按已知几何直接合成**：一个 **T 形件**（主体 + 细臂，**臂从主体边缘起** ⇒ 单连通），
#     尺寸**全部已知** ⇒ `L_vol` 可用解析值，判据也可解析地推出来。
n_ax = np.asarray(NPF[K], float)
n_ax = n_ax / np.linalg.norm(n_ax)
a_ax = np.asarray(g1.atab[K], float)
a_ax = a_ax - (a_ax @ n_ax) * n_ax
a_ax = a_ax / np.linalg.norm(a_ax)
w_ax = np.cross(n_ax, a_ax)
_ax = (np.arange(N) + 0.5) * DX
_X, _Y, _Z = np.meshgrid(_ax - L / 2, _ax - L / 2, _ax - L / 2, indexing='ij')
_pa = _X * a_ax[0] + _Y * a_ax[1] + _Z * a_ax[2]
_pw = _X * w_ax[0] + _Y * w_ax[1] + _Z * w_ax[2]
_pn = _X * n_ax[0] + _Y * n_ax[1] + _Z * n_ax[2]
# ★★ 第三版修正：**形状超出了盒子**。盒 `L=3.2 µm`，而沿对角方向 `_pa` 的上限约
#   `1.6·(|a_x|+|a_y|+|a_z|) ≈ 2.4 µm`，而上一版细臂要伸到 `3.6 µm` ⇒ **被盒截断**，
#   实测跨度 2993 nm = 2.4−(−0.6) µm ✓ **与截断后的几何完全吻合**（`geom_ar` 没错）。
#   ⇒ 按**盒内可容纳**的尺寸重设，并让细臂宽 `≥ 3Δx = 150 nm`（`R13`）。
L0, W0, T0 = 600e-9, 1200e-9, 200e-9         # 主体（12×24×4 胞）
L1, w1 = 1200e-9, 150e-9                     # 细臂：宽 = 主体的 1/8，且 = 3Δx
main = (np.abs(_pa) <= L0 / 2) & (np.abs(_pw) <= W0 / 2) & (np.abs(_pn) <= T0 / 2)
arm = (_pa > L0 / 2) & (_pa <= L0 / 2 + L1) & (np.abs(_pw) <= w1 / 2) & (np.abs(_pn) <= T0 / 2)
regS = np.zeros((N, N, N), dtype=np.int8)
regS[main | arm] = K
import scipy.ndimage as _nd                                                   # noqa: E402
_lab2, _n2 = _nd.label(regS > 0)
a4 = geom_ar(regS, g1, NPF)
print('      `geom_ar` 返回 **%d** 条记录（本件应只有 1 个连通分量）：' % len(a4))
for _r in a4:
    # ⚠ Round 139：元组已扩为 7 元 ⇒ 这里的槽位必须同步。
    #   旧写法 `_r[2]`=t_、`_r[3]`=L/t、`_r[4]`=cells 在新元组里分别变成
    #   **宽**、**L/t**、**L/W** ⇒ 会打出 "t_=宽 / L/t=0.00 / 胞数=错"。
    print('        k=%d  L_=%.1f nm  W_=%.1f nm  t_=%.1f nm  L/t=%.2f  L/W=%.2f  胞数=%d'
          % (_r[0], _r[1] * 1e9, W_of(_r) * 1e9, T_of(_r) * 1e9, _r[4], LW_of(_r), _r[6]))
L_mm = max((_r[1] for _r in a4), default=float('nan'))
# ★ 自证：**我自己**在同一个胞集上量一遍跨度（与 `geom_ar` 用同一 `a_ax` 与同一取整口径）
_ix = np.argwhere(regS > 0).astype(float)
_pj = _ix @ a_ax
_span_mine = float(_pj.max() - _pj.min()) * DX
print('      [自证] 我自己在**同一胞集**上量的 `(i,j,k)·a_ax` 跨度 = **%.1f nm**（%d 胞）'
      % (_span_mine * 1e9, int(round(_span_mine / DX))))
print('      ⇒ 若它与 `geom_ar` 的 L_ 不同 ⇒ **`geom_ar` 内部有额外处理**；若相同 ⇒ 是我的构造问题。')
# 解析真值：`max−min` 跨度 ≈ L0+L1 ；体积等效长度 = V/(W0·T0) = L0 + L1·(w1/W0)
L_true = L0 + L1
L_vol_true = L0 + L1 * (w1 / W0)
_ratio = L_mm / max(L_vol_true, 1e-30)
ok4 = (_n2 == 1) and (_ratio > 2.0)
print('【G-4】非紧凑形状（**合成 T 形件**：主体 %.0f×%.0f×%.0f nm + 细臂 %.0f×%.0f nm，连通分量数 **%d**）'
      % (L0 * 1e9, W0 * 1e9, T0 * 1e9, L1 * 1e9, w1 * 1e9, _n2))
print('      `geom_ar` 的 `max−min` L = **%.1f nm**（解析跨度 ≈ %.1f nm）'
      % (L_mm * 1e9, L_true * 1e9))
print('      体积等效长度 `L_vol = V/(W0·T0)` = **%.1f nm**（解析 %.1f nm）'
      % (L_vol_true * 1e9, L_vol_true * 1e9))
print('      ⇒ 比值 **%.2f**（判据 >2.0）⇒ %s'
      % (_ratio, 'PASS（**量具在非紧凑形状上爆表** ⇒ Round 128 的诊断成立）' if ok4
         else 'FAIL（没有爆表 ⇒ 上一轮的诊断需要推翻）'))
if not ok4:
    fails.append('G-4')

# ---------------- G-5 ★★ Round 139 新增：**新字段 `W_` 与 `L_/W_` 的正对照** ------------
#   为什么必须加（`AGENTS.md §3.19`）：本轮给 `geom_ar()` **加了 `W_` 与 `L_/W_` 两个新输出**
#   （靶② 的正确轴是**长:宽 ≈ 9:1**，见 `WINDOWB_ROADMAP_TO_CORRECT.md §9.17b`）。
#   **新字段从未与已知答案比过** ⇒ 不验证就不该被引用。
#   本件（G-1 的构型）是 `seed_plate(K, c0, n_use, R, T)` = **半径 R 的圆盘** ⇒
#   面内两个方向都应是 **2R**，且 **`L_/W_ ≈ 1.00**；厚度应是 `T`（G-1 已验）。
_R = R_NM * 1e-9
_L1 = a1[0][1]
_W1 = W_of(a1[0])
_LW1 = LW_of(a1[0])
ok5 = (abs(_L1 / (2 * _R) - 1.0) <= 0.08 and abs(_W1 / (2 * _R) - 1.0) <= 0.08
       and abs(_LW1 - 1.0) <= 0.12)
print('【G-5】★ 新字段正对照（圆盘种子 R=%.0f nm ⇒ 面内两向都应为 2R=%.0f nm、`L/W`≈1.00）：'
      % (R_NM, 2 * R_NM))
print('      `L_`=%.1f nm（偏差 %+.1f%%）  `W_`=%.1f nm（偏差 %+.1f%%）  **`L_/W_`=%.2f**'
      '（判据：两向 ±8%%、比值 ±0.12）⇒ %s'
      % (_L1 * 1e9, (_L1 / (2 * _R) - 1) * 100, _W1 * 1e9, (_W1 / (2 * _R) - 1) * 100,
         _LW1, 'PASS' if ok5 else 'FAIL'))
if not ok5:
    fails.append('G-5')

print('\n' + '=' * 100)
print('【汇总】%s' % ('全部 PASS' if not fails else 'FAIL：%s' % fails))
print('★ 结论口径：`geom_ar()` 是 `max−min` 型量具 ⇒ **只在紧凑凸体上可信**；')
print('  非紧凑形状（细丝/突起）下它会**系统性高估**长度 ⇒ 靶② 的几何长:厚读数必须配')
print('  **与极值无关的尺子**（`L_vol` / `L_gyr`）一起报。')
sys.exit(0 if not fails else 1)
