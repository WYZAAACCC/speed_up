#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_chk_w14.py —— `W1-4`（形核判据 `f_nuc^ch > 4γ/d` 接线）的**验收判据**

背景：`WINDOWB_AUDIT_REGISTER.md` D1/A1 —— 该判据此前是"**算了却从不比较**"，
`gamma`/`drive_min` 是死参数，而 docstring 却声称按它筛选形核点 ⇒ **未实现的声称**。
本轮的接线方式：`nuc_cfg(use_fcrit=False)` 默认 **不比较** ⇒ **逐位向后兼容**。

判据（每条都带"已知答案"或反向对照，`MEASUREMENT_SPEC R0`）
------------------------------------------------------------
* **D-1 向后兼容（逐位硬判据）**：`use_fcrit=False` 时，`df` 必须**完全没有效果** ——
  取 `df=0` 与 `df=1e30` 两次，`out` 长度与 `phi` 的 SHA **必须相同**。
* **D-2 开关有效**：`use_fcrit=True` + 极大 `gamma` ⇒ **拒绝数 > 0**且结果与关闭时不同。
* **D-3 单调性**：拒绝数必须随 `gamma` **单调不减**（因为 `fcrit = 4γ/t`）。
* **D-4 `df` 真的有作用**：固定阈值下，`df` 从 0 增到 `1e30` ⇒ 拒绝数**必须降到 0**。
* **D-5 退化极限（强对照）**：`drive_min = −1e30`（判据恒真）⇒ 拒绝数 0，
  **且 `phi` 的 SHA 与"开关关闭"完全相同** ⇒ 证明整条判定式在恒真时是**恒等**的。
* **D-6 范围缺口的**实测确认**：`n_fresh=0, n_stack=2`（纯 stack）时，
  切换 `use_fcrit` **不得**改变输出 ⇒ **实证**"该判据只覆盖 `fresh` 通道"这一声明，
  而不是把它当成假设写进文档。

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


def build(n0=8, seed=7):
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0, reinit_dt=None)
    rng = np.random.default_rng(seed)
    ns = 0
    guard = 0
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


def trial(gamma=0.15, use_fcrit=False, drive_min=None, df=0.0,
          n_fresh=2, n_stack=2, n0=8):
    g = build(n0)
    g.nuc_cfg(R_NUC, T_NUC, gamma=gamma, n_init=16, harden_f=1.0,
              sym_gap_cells=2, max_per_step=8, seed=11, use_fcrit=use_fcrit)
    # ★ 必须先跑一步 `advance(npref=...)`：`_npref_of` 的 **A12 硬失败守卫**要求
    #   `npref_tab` 已在 `advance()` 入口缓存好（否则抛 RuntimeError 而不是静默用 z 轴）。
    #   这不是缺陷，是上一轮加的守卫在正常工作 —— 本行是**配合守卫**，不是绕过它。
    dt = 0.15 * g.dx / (MOB * DF)
    g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
    ed = g.elastic_driving()
    kw = {} if drive_min is None else dict(drive_min=drive_min)
    out = g.nucleate(ed, f_now=0.3, n_fresh=n_fresh, n_stack=n_stack, df=df, **kw)
    rej = int(g._nuc.get('dbg', {}).get('fcrit', 0))
    sha = hashlib.sha1(np.ascontiguousarray(g.phi).tobytes()).hexdigest()[:16]
    return dict(n=len(out), rej=rej, sha=sha)


print('=' * 100)
print('_chk_w14 —— W1-4（形核判据 4γ/d 接线）验收')
print('=' * 100)

# ---------------------------------------------------------------- D-1 向后兼容（逐位）
a1 = trial(df=0.0)
a2 = trial(df=1e30)
ok1 = (a1['n'] == a2['n']) and (a1['sha'] == a2['sha']) and a1['rej'] == 0 and a2['rej'] == 0
print('\n【D-1 向后兼容：`use_fcrit=False` 时 `df` 必须毫无效果】')
print('   df=0    : n_nuc=%d  拒绝=%d  phi=%s' % (a1['n'], a1['rej'], a1['sha']))
print('   df=1e30 : n_nuc=%d  拒绝=%d  phi=%s' % (a2['n'], a2['rej'], a2['sha']))
print('   ⇒ %s' % ('PASS（逐位相同）' if ok1 else 'FAIL'))
if not ok1:
    fails.append('D-1')

# ---------------------------------------------------------------- D-5 退化极限（强对照）
d5 = trial(use_fcrit=True, drive_min=-1e30)
ok5 = (d5['rej'] == 0) and (d5['sha'] == a1['sha'])
print('\n【D-5 退化极限：`drive_min=-1e30` ⇒ 判据恒真 ⇒ 必须与"关闭"完全一致】')
print('   use_fcrit=True + drive_min=-1e30 : n_nuc=%d 拒绝=%d phi=%s'
      % (d5['n'], d5['rej'], d5['sha']))
print('   对照：use_fcrit=False             : n_nuc=%d 拒绝=%d phi=%s'
      % (a1['n'], a1['rej'], a1['sha']))
print('   ⇒ %s' % ('PASS（恒真时是恒等变换）' if ok5 else 'FAIL'))
if not ok5:
    fails.append('D-5')

# ---------------------------------------------------------------- D-2 开关有效
d2 = trial(gamma=1e7, use_fcrit=True)
ok2 = (d2['rej'] > 0) and (d2['sha'] != a1['sha'])
print('\n【D-2 开关有效：`gamma=1e7` ⇒ `fcrit=4γ/t` 极大 ⇒ 必须拒掉位点】')
print('   n_nuc=%d  拒绝=**%d**  phi=%s（对照关闭时 n_nuc=%d）'
      % (d2['n'], d2['rej'], d2['sha'], a1['n']))
print('   ⇒ %s' % ('PASS' if ok2 else 'FAIL'))
if not ok2:
    fails.append('D-2')

# ---------------------------------------------------------------- 标定：阈值落在哪一档？
# ★ 第一版 D-4 直接取 `drive_min=0`，结果**两臂都拒绝 0 次** ⇒ FAIL。
#   原因**不是实现错，是测试设计错**：实测在 16 个位点上 `max_k ed_k` 恒为正
#   （`drive_min=0` 远低于驱动力 ⇒ 判据恒真 ⇒ 看不到任何现象）。
#   这与 `AGENTS.md` 教训 14「**设计验证算例前，先问这个测试能不能看到目标现象**」同族
#   （也与平衡态看不到边界层那条同类）。
#   ⇒ 改为**自标定**：先扫 `drive_min` 几个十进档，找到**部分拒绝**的那一档，再在那里测 `df`。
print('\n【标定】`drive_min` 十进扫描（找"部分拒绝"的那一档；n_sites=16）')
scan = {}
for thr in (1e4, 1e6, 1e8, 1e10, 1e12, 1e14):
    r = trial(use_fcrit=True, drive_min=thr)
    scan[thr] = r['rej']
    print('   drive_min=%-8.0e ⇒ 拒绝 %2d 次，n_nuc=%d' % (thr, r['rej'], r['n']))
partial = [t for t in scan if 0 < scan[t] < 16]
print('   ⇒ 部分拒绝的档：%s' % (['%.0e' % t for t in partial] if partial
                               else '（无 —— 判定被"全拒/全过"两端夹住）'))

# ---------------------------------------------------------------- D-3 单调性（在可见区间上）
gams = [1e2, 1e3, 1e4, 1e5]
rejs = [trial(gamma=x, use_fcrit=True)['rej'] for x in gams]
ok3 = all(rejs[i] <= rejs[i + 1] for i in range(len(rejs) - 1)) and rejs[-1] > 0
print('\n【D-3 单调性：拒绝数必须随 `gamma` 单调不减】')
print('   gamma = %s' % '  '.join('%.0e' % x for x in gams))
print('   拒绝数 = %s' % '  '.join('%d' % x for x in rejs))
print('   ⇒ %s（注意：高档会饱和到 16 = 全部位点，饱和段本身不提供分辨力）'
      % ('PASS' if ok3 else 'FAIL'))
if not ok3:
    fails.append('D-3')

# ---------------------------------------------------------------- D-4 df 真的有作用（自标定）
THR = partial[0] if partial else 1e12
r_small = trial(use_fcrit=True, drive_min=THR, df=0.0)
r_mid = trial(use_fcrit=True, drive_min=THR, df=THR)
r_big = trial(use_fcrit=True, drive_min=THR, df=1e30)
ok4 = (r_small['rej'] > 0) and (r_big['rej'] == 0) and (r_mid['rej'] <= r_small['rej'])
print('\n【D-4 `df` 真的有作用（在标定档 `drive_min=%.0e` 上）】' % THR)
print('   df=0     : 拒绝=**%d**  n_nuc=%d' % (r_small['rej'], r_small['n']))
print('   df=THR   : 拒绝=**%d**  n_nuc=%d' % (r_mid['rej'], r_mid['n']))
print('   df=1e30  : 拒绝=**%d**  n_nuc=%d' % (r_big['rej'], r_big['n']))
print('   ⇒ %s（要求：df=0 有拒绝、df=1e30 拒绝归零、中间档不增）'
      % ('PASS（`df` 确实以 **+** 号进入判定式，与 `argmax_k ed` 的选法自洽）' if ok4 else 'FAIL'))
if not ok4:
    fails.append('D-4')

# ---------------------------------------------------------------- D-6 stack 未覆盖
s_off = trial(use_fcrit=False, n_fresh=0, n_stack=2, gamma=1e7)
s_on = trial(use_fcrit=True, n_fresh=0, n_stack=2, gamma=1e7)
ok6 = (s_off['sha'] == s_on['sha'])
print('\n【D-6 范围缺口实测：纯 `stack` 调用必须**不受** `use_fcrit` 影响】')
print('   纯 stack，关闭: n_nuc=%d 拒绝=%d phi=%s' % (s_off['n'], s_off['rej'], s_off['sha']))
print('   纯 stack，开启: n_nuc=%d 拒绝=%d phi=%s' % (s_on['n'], s_on['rej'], s_on['sha']))
print('   ⇒ %s' % ('PASS（确认：判据**只覆盖 fresh**，与文档声明一致；这是已知缺口，不是 bug 掩盖）'
                  if ok6 else 'FAIL（说明 stack 也被改了 ⇒ 文档里的"只覆盖 fresh"要改）'))
if not ok6:
    fails.append('D-6')

print('\n' + '=' * 100)
print('=== W1-4 验收 %s ===' % ('全部 PASS' if not fails else ('FAIL: ' + ','.join(fails))))
print('★ 措辞红线：本实现是"登记表 §9 所载判定式"的接线；`d` 取核厚 `t`，')
print('  其定义**未从 Du 2017 原文核实** ⇒ 不得写成"实现了 Du 2017 的形核判据"。')
sys.exit(0 if not fails else 1)
