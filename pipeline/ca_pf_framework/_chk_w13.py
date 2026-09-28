#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_chk_w13.py —— `W1-3`（`C4`：种核后强制 reinit）的**验收判据**

背景：`seed_plate` 的 `phi[j] = max(phi[j], −sdf)` 在盘内**覆写** `φ_j`、盘外保留旧值
⇒ 盘边界出现 O(|旧 φ_j|) 的**跳变**；而 `region()` 靠 `argmin` 仍然正确 ⇒ **不报错**。
兜底是定时 reinit，但它可能因 `reinit_skip_tol` 被跳过。

判据
----
* **E-4 `force=True` 必须绕过跳过容差**（本项的**核心**判据）：
  把 `reinit_skip_tol` 设成 1.0（⇒ 任何场都会被跳过），
  `reinitialize()` 必须计入 `_reinit_skipped`，而 `reinitialize(force=True)` 必须计入 `_reinit_done`。
* **E-1 不形核 ⇒ 逐位不变**：`nuc_cfg` 已配置但每步 `nucleate(n_fresh=0, n_stack=0)`
  （⇒ 永不产生事件）时，`advance()` 的轨迹必须与"完全不调 `nucleate()`"的对照 **逐位相同**，
  且 `_forced_reinit` 计数为 **0**。
* **E-2 形核 ⇒ 强制 reinit 确实发生**：`n_fresh>0` 且位点可用时，`_forced_reinit` 必须 **>0**。
* **E-3 无害**：强制 reinit 不得改变 `region()` 的**逐胞**指派（翻转 = 0），
  界面键膨胀必须 ≤ 1.2×（`P0-3` 门槛）。

退出码：0 = 全 PASS。
"""
import os
import sys
import hashlib

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402

MOB, DF, N, L = 1e-9, 3.5e8, 48, 48 * 50e-9
R_NUC, T_NUC = 300e-9, 700e-9
fails = []


def build(n0=8):
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0, reinit_dt=None)
    rng = np.random.default_rng(7)
    ns, guard = 0, 0
    while ns < n0 and guard < 500:
        guard += 1
        c = rng.random(3) * (L - 2 * (300e-9 + 0.3e-6)) + (300e-9 + 0.3e-6)
        k = int(rng.integers(1, NV + 1))
        nv_ = np.asarray(NPF[k], float)
        try:
            g.seed_plate(k, c, nv_ / np.linalg.norm(nv_), 300e-9, 200e-9)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    return g


def sha(g):
    return hashlib.sha1(np.ascontiguousarray(g.phi).tobytes()).hexdigest()[:16]


DT = 0.15 * (L / N) / (MOB * DF)
print('=' * 100)
print('_chk_w13 —— W1-3（C4：种核后强制 reinit）验收')
print('=' * 100)

# ---------------------------------------------------------------- E-4 核心
g = build()
g.reinit_skip_tol = 1.0                      # 让"任何场都会被跳过"
g._reinit_skipped = 0
g._reinit_done = 0
g.reinitialize()
s1, d1 = getattr(g, '_reinit_skipped', 0), getattr(g, '_reinit_done', 0)
g.reinitialize(force=True)
s2, d2 = getattr(g, '_reinit_skipped', 0), getattr(g, '_reinit_done', 0)
ok4 = (s1 > 0) and (d1 == 0) and (d2 > d1) and (s2 == s1)
print('\n【E-4 `force=True` 必须绕过跳过容差】（`reinit_skip_tol=1.0` ⇒ 任何场都会被跳过）')
print('   `reinitialize()`            : 跳过 0 → %d，执行 0 → %d' % (s1, d1))
print('   `reinitialize(force=True)`  : 跳过 %d → %d，执行 %d → %d' % (s1, s2, d1, d2))
print('   ⇒ %s（要求：普通调用只跳过、执行数为 0；force 调用必须真的执行，且**不新增跳过**）'
      % ('PASS' if ok4 else 'FAIL'))
print('   ★ 记账（本判据第一版的错）：我最初写 `d2 == d1 + 1`，**假设只执行 1 个配对** ——')
print('     而 `reinitialize()` 是**逐配对**做的，实测这一构型有 **%d** 个配对 ⇒ 断言过窄。' % (d2 - d1))
print('     **实现是对的，是判据写错了**（与 `AGENTS.md` 教训 14 同族：先问判据能不能容纳真实现象）。')
if not ok4:
    fails.append('E-4')

# ---------------------------------------------------------------- E-1 不形核 ⇒ 逐位不变
def run(use_nucleate, steps=6):
    gg = build()
    gg.nuc_cfg(R_NUC, T_NUC, gamma=0.15, n_init=16, harden_f=1.0,
               sym_gap_cells=2, max_per_step=8, seed=11)
    for _ in range(steps):
        gg.advance(DT, aniso=0.4, npref=NPF, band_cells=20,
                   mob_beta=3.5, mob_beta_w=2.3)
        if use_nucleate:
            ed = gg.elastic_driving()
            gg.nucleate(ed, f_now=0.3, n_fresh=0, n_stack=0)   # 永不产生事件
    return gg


gA = run(False)
gB = run(True)
ok1 = (sha(gA) == sha(gB)) and getattr(gB, '_forced_reinit', 0) == 0
print('\n【E-1 不形核 ⇒ 必须逐位不变】（`n_fresh=0, n_stack=0` ⇒ 永不产生事件）')
print('   不调 `nucleate()` : phi=%s' % sha(gA))
print('   调但零事件        : phi=%s   `_forced_reinit`=%d'
      % (sha(gB), getattr(gB, '_forced_reinit', 0)))
print('   ⇒ %s' % ('PASS（零事件时不触发任何额外 reinit）' if ok1 else 'FAIL'))
if not ok1:
    fails.append('E-1')

# ---------------------------------------------------------------- E-2 形核 ⇒ 强制发生
gC = build()
gC.nuc_cfg(R_NUC, T_NUC, gamma=0.15, n_init=16, harden_f=1.0,
           sym_gap_cells=2, max_per_step=8, seed=11)
nev = 0
for _ in range(8):
    gC.advance(DT, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
    ed = gC.elastic_driving()
    nev += len(gC.nucleate(ed, f_now=0.3, n_fresh=2, n_stack=2))
nfr = getattr(gC, '_forced_reinit', 0)
ok2 = nev > 0 and nfr > 0
print('\n【E-2 真形核 ⇒ 强制 reinit 必须确实发生】')
print('   形核事件数 = %d ；`_forced_reinit` = **%d**' % (nev, nfr))
print('   ⇒ %s' % ('PASS' if ok2 else 'FAIL'))
if not ok2:
    fails.append('E-2')

# ---------------------------------------------------------------- E-3 无害
gD = build()
gD.nuc_cfg(R_NUC, T_NUC, gamma=0.15, n_init=16, harden_f=1.0,
           sym_gap_cells=2, max_per_step=8, seed=11)
gD.advance(DT, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
gD.nucleate(gD.elastic_driving(), f_now=0.3, n_fresh=2, n_stack=2)
reg_b = gD.region()
nb0 = int(sum((reg_b != np.roll(reg_b, -1, ax)).sum() for ax in range(3)))
gD.reinitialize(force=True)
reg_a = gD.region()
nb1 = int(sum((reg_a != np.roll(reg_a, -1, ax)).sum() for ax in range(3)))
flip = int((reg_a != reg_b).sum())
ok3 = (flip == 0) and (nb1 / max(nb0, 1) <= 1.2)
print('\n【E-3 强制 reinit 必须无害（`region()` 逐胞不变 + 界面键 ≤1.2×）】')
print('   `region()` 翻转 = **%d** ；界面键 %d → %d（**%.4f×**）'
      % (flip, nb0, nb1, nb1 / max(nb0, 1)))
print('   ⇒ %s' % ('PASS' if ok3 else 'FAIL'))
if not ok3:
    fails.append('E-3')

print('\n' + '=' * 100)
print('=== W1-3 验收 %s ===' % ('全部 PASS' if not fails else ('FAIL: ' + ','.join(fails))))
sys.exit(0 if not fails else 1)
