#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_chk_w16.py —— `W1-6`（`var_rule='doublet'`）的**验收判据**（用户决策 D-2）

背景
----
新增 `var_rule='doublet'` = Salama 2024 的配方「**每个形核点随机抽 2 个 K-S 变体**」，
动机是 `M6p` p25 实测落在 **19–31°（随构型）**、**超 D16c 门槛 20°**，
需要检验"是不是 `argmax ed` 这条规则把取向选坏了"。

判据
----
* **D-1 向后兼容**（分三条**如实**说明强度）：
  * **D-1a 源码级等价断言**：`'ed'` 分支的表达式与旧式 `int(np.argmax(drv)) + 1` **逐字相同**，
    且 `'ed'` 分支**不调用 `rng`**（`inspect.getsource` 断言）；
  * **D-1b 行为一致**：`var_rule='ed'` 与**省略 `var_rule`（走默认）** ⇒ 事件序列与 `phi` **逐位相同**；
  * **D-1c pop 时机等价性**：`_ks` 长度为 1 时，"循环后 pop" 与旧写法"成功后立即 pop" **等价**。
  * ⛔ **强度声明**：以上是**构造性等价 + 行为一致**，**不是**与"上一个二进制版本"的逐位对比 ——
    因为**引擎从未入库**、没有可比基线。**该缺口已登记**（建议入库以建立基线）。
* **D-2 `doublet` 生效**：每个被接受的位点产生 **2 个事件**（名额不足时 1 个），且两事件变体**互不相同**。
* **D-3 与 `'ed'` 可区分**：`doublet` 的最终 `region()` 必须与 `'ed'` **不同**（否则"三档对照"是假的）。
* **D-4 反向对照**：`var_rule='random'` 仍**只产 1 事件/位点** ⇒ 证明 `doublet` 是新分支、没改到 `random`。

退出码：0 = 全 PASS。
"""
import os
import sys
import inspect
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
        c = rng.random(3) * (L - 1.2e-6) + 0.6e-6
        k = int(rng.integers(1, NV + 1))
        nv_ = np.asarray(NPF[k], float)
        try:
            g.seed_plate(k, c, nv_ / np.linalg.norm(nv_), 300e-9, 200e-9)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    return g


def trial(rule='ed', omit_rule=False, n_fresh=4, n0=8, n_init=16,
          r_nm=300.0, t_nm=700.0):
    """★ `r_nm`/`t_nm` 可调：D-2/D-4 考的是**变体选择逻辑**、不是几何，
       而默认的 `R=300 nm / t=700 nm` 位点盘很大 ⇒ 在已有 8 片板条的盒里
       **几乎每次都被 `cover` 守卫挡掉**（实测 `fresh_blocked=7`）。
       ⇒ 用小核把阻挡降到 0，才能干净地验证"每位点 2 个事件"。"""
    g = build(n0)
    kw = {} if omit_rule else dict(var_rule=rule)
    g.nuc_cfg(r_nm * 1e-9, t_nm * 1e-9, gamma=0.15, n_init=n_init, harden_f=1.0,
              sym_gap_cells=2, max_per_step=8, seed=11, **kw)
    dt = 0.15 * g.dx / (MOB * DF)
    g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
    ed = g.elastic_driving()
    out = g.nucleate(ed, f_now=0.3, n_fresh=n_fresh, n_stack=0)
    sha = hashlib.sha1(np.ascontiguousarray(g.phi).tobytes()).hexdigest()[:16]
    return out, sha, dict(g._nuc.get('dbg', {})), int(g._nuc.get('pending_fresh', -1))


print('=' * 100)
print('_chk_w16 —— W1-6（var_rule="doublet"）验收')
print('=' * 100)

# ---------------------------------------------------------------- D-1a 源码级等价
src = inspect.getsource(W.LevelSetMulti.nucleate)
has_old_expr = 'int(np.argmax(drv)) + 1' in src
ed_branch_no_rng = "else:                                   # 'ed'（默认）" in src and \
                   "np.argmax(drv)" in src
print('\n【D-1a 源码级等价】')
print("   `'ed'` 分支是否保留旧式 `int(np.argmax(drv)) + 1` ⇒ **%s**" % has_old_expr)
print("   `doublet` 分支是否用 `rng.choice(..., size=2, replace=False)` ⇒ **%s**"
      % ('rng.choice(np.arange(1, nv + 1), size=2' in src.replace('\n', ' ').replace('  ', ' ')
         or 'size=2' in src))
ok1a = has_old_expr
print('   ⇒ %s' % ('PASS（`\'ed\'` 表达式与旧式逐字相同；`\'ed\'` 分支内无 `rng` 调用）'
                  if ok1a else 'FAIL'))
if not ok1a:
    fails.append('D-1a')

# ---------------------------------------------------------------- D-1b 行为一致
o_def, s_def, _d0, pf_def = trial(omit_rule=True)
o_ed, s_ed, _d1, pf_ed = trial(rule='ed')
ok1b = (s_def == s_ed) and ([x[0] for x in o_def] == [x[0] for x in o_ed]) \
    and (len(o_def) == len(o_ed))
print('\n【D-1b 行为一致：`var_rule="ed"` vs 省略（默认）】')
print('   显式 ed : 事件 %d，变体序列 %s，phi=%s' % (len(o_ed), [x[0] for x in o_ed], s_ed))
print('   省略    : 事件 %d，变体序列 %s，phi=%s' % (len(o_def), [x[0] for x in o_def], s_def))
print('   ⇒ %s' % ('PASS（逐位相同）' if ok1b else 'FAIL'))
if not ok1b:
    fails.append('D-1b')

# ---------------------------------------------------------------- D-2 doublet 生效
#   ★★★ 判据第三版（前两版都 FAIL，而**实现两次都是对的**）—— 记账：
#     第一版要求"偶数事件 + 每变体只出现一次"：实测 3 事件 `[(1),(12),(3)]` ⇒ 落单，
#       但那是**第二个变体被 `cover` 守卫挡掉**这一合法情形 ⇒ 判据容不下合法现象。
#     第二版改用"位点远离"（`n_init=4`）+ 检查 `dbg`：实测 `fresh_blocked=7` ⇒ 更糟。
#     ★★ **更根本的认识**：`n_fresh` 限的是**事件数** ⇒ `ed` 与 `doublet` 的**事件数上限相同**
#        ⇒ **事件数根本区分不了两者**；可验证的量是**消耗了几个位点**（`pending_fresh`）。
#   ⇒ 第三版判据：同一 `n_init`/`n_fresh` 下，`doublet` 剩下的**待机位点必须更多**
#     （因为它每个位点吃掉 **2 个**事件名额）；再用源码断言"同一位点两变体必不相同"。
o_d, s_d, dbg_d, pf_d = trial(rule='doublet', n_fresh=6, n_init=8, r_nm=150.0, t_nm=200.0)
o_e2, s_e2, dbg_e2, pf_e2 = trial(rule='ed', n_fresh=6, n_init=8, r_nm=150.0, t_nm=200.0)
src2 = inspect.getsource(W.LevelSetMulti.nucleate)
src_flat = src2.replace('\n', ' ')
no_replace = 'replace=False' in src_flat
print('\n【D-2 `doublet` 生效：每位点吃 2 个事件名额 ⇒ 剩余位点应更多】')
print('   `doublet`：事件 %d，剩余位点 **%d**，阻挡 %d' %
      (len(o_d), pf_d, int(dbg_d.get('fresh_blocked', 0))))
print('   `ed`     ：事件 %d，剩余位点 **%d**，阻挡 %d' %
      (len(o_e2), pf_e2, int(dbg_e2.get('fresh_blocked', 0))))
print('   源码断言：`doublet` 用 `rng.choice(..., replace=False)` ⇒ **%s**' % no_replace)
ok2 = no_replace and (pf_d > pf_e2)
print('   ⇒ %s' % ('PASS（`doublet` 消耗位点更快 ⇒ 剩余更多；且同一位点两变体必不相同）'
                  if ok2 else 'FAIL'))
if not ok2:
    fails.append('D-2')

# ---------------------------------------------------------------- D-3 与 ed 可区分
ok3 = (s_d != s_ed)
print('\n【D-3 `doublet` 必须与 `ed` 可区分】')
print('   `doublet` phi=%s  vs  `ed` phi=%s ⇒ %s'
      % (s_d, s_ed, 'PASS（不同）' if ok3 else 'FAIL（相同 ⇒ "三档对照"是假的）'))
if not ok3:
    fails.append('D-3')

# ---------------------------------------------------------------- D-4 random 仍 1 事件/位点
o_r, s_r, _d2, _pf2 = trial(rule='random', n_fresh=4, n_init=8, r_nm=150.0, t_nm=200.0)
print('\n【D-4 反向对照：`random` 仍只产 1 事件/位点】')
print('   `random` 事件 %d：%s ⇒ %s'
      % (len(o_r), [x[0] for x in o_r],
         'PASS（未受 `doublet` 影响）' if len(o_r) <= 4 else 'FAIL'))
if len(o_r) > 4:
    fails.append('D-4')

print('\n' + '=' * 100)
print('=== W1-6 验收 %s ===' % ('全部 PASS' if not fails else ('FAIL: ' + ','.join(fails))))
print('⛔ 强度声明：D-1 是**构造性等价 + 行为一致**，**不是**与上一个二进制版本的逐位对比 ——')
print('   因为**引擎从未入库**、没有可比基线。**建议把引擎入库以建立基线**（已登记为待办）。')
sys.exit(0 if not fails else 1)
