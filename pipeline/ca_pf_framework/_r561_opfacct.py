#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r561_opfacct.py --- **算子级时间记账**（不是 cProfile 采样，是显式包裹计时）。

## 为什么不用 cProfile 就下结论
`_r559` 用 cProfile 得到 `einsum 15.2% / eps0_fields 13.5% / ...`，但：
  * cProfile 对 **C 层调用**归因到被调函数，对 **Python 层的 numpy 表达式**
    归因到调用者 ⇒ `advance()` 自身的表达式开销全被"藏"在 `advance` 的 tottime 里；
  * 它**看不到** `elastic_driving` 里两段 `for_each` 的**真实归属**；
  * 它**不告诉你**"这一步到底花在哪一段物理流程上"。

本量具换一种口径：**在关键函数外挂计时器**，把每一步切成互不重叠的几大块：
    region / argmin2 / elastic(=elastic_driving 全链) / geom(梯度+曲率) /
    advect(界面推进) / finish(reinit+stefan)
并逐项给出 **绝对秒数**（不是百分比——百分比会掩盖总时间的变化）。

## 判据（先写死，必须能失败）
* **P0 正对照**：`pf.phi.dtype` 必须是 `float64`（`elastic_soft=True` 生产路径）
  ⇒ 若还是 `bool`，说明量具**从没跑过 advance**（`N16` 的错，已犯过一次）。
* **P1 覆盖性**：记账的各大块之和必须 ≤ `advance()` 总墙钟，且**覆盖率 ≥ 85%**
  （余下是未摊到子块的散开销）。若 < 85% ⇒ 说明有大块没被记账 ⇒ **不许下结论**。
* **P2 记账器自证**：把 `_minmod` 换成"每次多烧 T_burn 秒"的版本，
  记账必须**看得见**这笔人工开销（差值 ≥ 0.8×预期）⇒ 证明计时器真的挂在热路径上。
* **P3 调用计数**：`eps0_fields`（慢路）调用次数必须 > 0（生产 `soft=True` 走它）；
  `eps0_fields_idx` 必须 == 0。与 `_r559` 一致才算复现。
"""
import cProfile
import io
import os
import pstats
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
import windowB_pf3d as P3                                      # noqa: E402
import windowB_par as PAR                                      # noqa: E402
from T16_verify_rve import C, EPS0                             # noqa: E402

N = int(os.environ.get('R561_N', '64'))
NV = int(os.environ.get('R561_NV', '24'))
DX_UM = float(os.environ.get('R561_DX', '0.0625'))
STEPS = int(os.environ.get('R561_STEPS', '8'))
WORKERS = int(os.environ.get('R561_WORKERS', '4'))

# ============================================================ 记账器
T = {}
_INSTALLED = False


class Timer(object):
    """零分配计时累加器。`with Timer('tag'):` 累加 `tag` 的墙钟。"""

    __slots__ = ('tag', 't0')

    def __init__(self, tag):
        self.tag = tag

    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *a):
        T[self.tag] = T.get(self.tag, 0.0) + (time.perf_counter() - self.t0)
        return False


CNT = {}


def _cnt(tag):
    CNT[tag] = CNT.get(tag, 0) + 1


def _wrap(cls, name, tag=None, count=True):
    """把 `cls.name` 包一层计时（不改行为）。

    ⚠⚠ **本轮踩到的自杀式 bug（`§R561`）**：本函数**内部已经** `setattr(cls,name,_f)`，
       却又 `return orig`。调用处写成 `cls.name = _wrap(...)` ⇒ **把刚装好的包装又
       覆盖回原函数**，包装**静默失效**（不报错、表里就是 0 次）。
       症状极像"引擎没走那条路"，实际是量具自己把自己拆了。
       ⇒ 现在返回值改成包装后的 `_f`，调用处**怎么写都不会拆掉它**（幂等）。
       正对照留在 `_r563_wrapdiag.py`。"""
    tag = tag or ('%s.%s' % (cls.__name__, name))
    orig = getattr(cls, name)

    def _f(*a, **kw):
        if count:
            _cnt(tag)
        with Timer(tag):
            return orig(*a, **kw)
    _f.__name__ = name
    _f.__orig = orig
    setattr(cls, name, _f)
    return _f


def _wrap_mod(mod, name, tag):
    orig = getattr(mod, name)

    def _f(*a, **kw):
        _cnt(tag)
        with Timer(tag):
            return orig(*a, **kw)
    _f.__name__ = name
    _f.__orig = orig
    setattr(mod, name, _f)
    return _f


def install():
    # ★★★ R576：**幂等守卫**。`install()` 被调两次会把同一个函数包两层
    #   ⇒ 时间表翻倍、计数表翻倍（"看起来像引擎多跑了一遍"）。这是本仓库
    #   `_r561` v1 那类"量具自己把自己拆了"的同族错误，直接硬拦。
    global _INSTALLED
    if _INSTALLED:
        raise RuntimeError('_r561_opfacct.install() 已调用过 —— 二次包装会双计')
    _INSTALLED = True
    # ★★ R576：`_fft` / `_ifft` 的包装**撤掉** —— 计时点已经**移进生产代码**
    #   （`windowB_pf3d._fft/_ifft` 里的 `acct.mark('el.fft_fwd'/'el.fft_inv')`）。
    #   两处都留 ⇒ 同一个 tag 被外层包装与内层标记**各记一次**，表会**静默翻倍**。
    #   保留内层（它同时盖住 `_rfft/_irfft`，而 `_rfft` 是包装不到的 —— 见 R561 遗留项）。
    P3.PF3D.eps0_fields = _wrap(P3.PF3D, 'eps0_fields', 'el.eps0_fields')
    P3.PF3D.eps0_fields_idx = _wrap(P3.PF3D, 'eps0_fields_idx', 'el.eps0_fields_idx')
    P3.PF3D.sigma_tensor = _wrap(P3.PF3D, 'sigma_tensor', 'el.sigma_tensor')
    W.LevelSetMulti.region = _wrap(W.LevelSetMulti, 'region', 'region')
    # ★ `elastic_driving_pair` **调用** `elastic_driving` ⇒ 若共用一个 tag 会**重复计数**
    #   （`_r561` v1 的 `elastic` = 1.316 s/步 就是两份之和）。这里分开。
    W.LevelSetMulti.elastic_driving = _wrap(W.LevelSetMulti, 'elastic_driving',
                                            'elastic.core')
    W.LevelSetMulti.elastic_driving_pair = _wrap(W.LevelSetMulti,
                                                 'elastic_driving_pair', 'elastic.pair')
    W.LevelSetMulti._finish_advance = _wrap(W.LevelSetMulti, '_finish_advance',
                                            'finish')
    W.LevelSetMulti.reinitialize = _wrap(W.LevelSetMulti, 'reinitialize', 'finish.reinit')
    W.LevelSetMulti._stefan = _wrap(W.LevelSetMulti, '_stefan', 'finish.stefan')
    # ★ `ParCtx.for_each(items, tag=…)` 的 tag 是**它自己**的统计用名
    #   （`ed.soft_phi` / `ed.einsum` / `advance.k_loop` / …）⇒ 这里按它分流计时，
    #   才能把"弹性里那两段 for_each"与"几何/推进那两段"分开。
    _fe_orig = PAR.ParCtx.for_each

    def _fe(self, items, tag=None):
        k = 'fe.%s' % (tag or '?')
        _cnt(k)
        with Timer(k):
            return _fe_orig(self, items, tag=tag)
    _fe.__name__ = 'for_each'
    PAR.ParCtx.for_each = _fe
    PAR.ParCtx.argmin2 = _wrap(PAR.ParCtx, 'argmin2', 'argmin2')
    PAR.ParCtx.argmin = _wrap(PAR.ParCtx, 'argmin', 'par.argmin')
    PAR.ParCtx.gradient = _wrap(PAR.ParCtx, 'gradient', 'par.gradient')
    PAR.ParCtx.upwind_flux_vec = _wrap(PAR.ParCtx, 'upwind_flux_vec',
                                       'par.upwind_flux_vec')
    PAR.ParCtx.upwind_grad2 = _wrap(PAR.ParCtx, 'upwind_grad2', 'par.upwind_grad2')
    _wrap_mod(W, 'upwind_flux_vec', 'op.upwind_flux_vec')
    _wrap_mod(W, '_minmod', 'op._minmod')
    _wrap_mod(W, '_bbox_pad', 'op._bbox_pad')
    _wrap_mod(W, 'sussman_reinit', 'op.sussman_reinit')


def build():
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(NV)]
    # ★ R572：把算子开关也做成环境变量，好让**同一把量具**量"改之前/改之后"的剖面。
    _kw = {}
    if os.environ.get('R561_FFT'):
        _kw['fft_mode'] = os.environ['R561_FFT']
    if os.environ.get('R561_EPS0'):
        _kw['eps0_mode'] = os.environ['R561_EPS0']
    if os.environ.get('R561_EDPAIR'):
        _kw['ed_pair_mode'] = os.environ['R561_EDPAIR']
    if os.environ.get('R561_KLOOP'):
        _kw['k_loop_mode'] = os.environ['R561_KLOOP']
    if os.environ.get('R561_ACT'):
        _kw['act_mode'] = os.environ['R561_ACT']
    if os.environ.get('R561_ARG2'):
        _kw['argmin2_mode'] = os.environ['R561_ARG2']
    # ★ R581：`--pf-phi`（`materialized` / `onfly`）与 `--grad-mode`。
    #   为什么必须补：生产用 `onfly` ⇒ `fe.ed.soft_phi` + `el.e0.einsum` 会被
    #   `el.e0.stream` 取代 ⇒ **构成完全不同**。不补这一项，记账表会指向错靶子。
    if os.environ.get('R561_PFPHI'):
        _kw['pf_phi_mode'] = os.environ['R561_PFPHI']
    if os.environ.get('R561_GRAD'):
        _kw['grad_mode'] = os.environ['R561_GRAD']
    # ★ R581-L2：ε⁰ 流式装配的首轴分块。
    if os.environ.get('R581_EPS0TILE'):
        _kw['eps0_tile'] = int(os.environ['R581_EPS0TILE'])
    # ★ R581-L5：复用 region() 的 winner（省一次 argmin/步）。
    if os.environ.get('R581_ARGREUSE'):
        _kw['argmin_reuse'] = bool(int(os.environ['R581_ARGREUSE']))
    # ★ R581-L6：`upwind_flux_vec` 的融合 C 核。
    if os.environ.get('R581_UFVC'):
        _kw['ufv_c'] = bool(int(os.environ['R581_UFVC']))
    # ★ R581-L4：`_bbox_pad` 的实现档。
    if os.environ.get('R581_BBOXMODE'):
        _kw['bbox_mode'] = os.environ['R581_BBOXMODE']
    g = W.LevelSetMulti(N, N * DX_UM, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] + [3.0e8] * NV, workers=WORKERS,
                        reinit_every=20, reinit_dt=1e-4, reinit_band_cells=6.0,
                        phi_prec='f64', **_kw)
    g.init_parent()
    rng = np.random.default_rng(7)
    nrm = np.array([0.0, 0.0, 1.0])
    Lc = N * DX_UM
    nseed = max(3, NV // 8)
    for k in range(1, nseed + 1):
        g.seed_plate(k, rng.random(3) * (Lc * 0.6) + Lc * 0.2, nrm, 120e-9, 300e-9)
    return g


def clean(s_per, nstep):
    t0 = time.perf_counter()
    for _ in range(nstep):
        s_per.advance(dt=1e-8)
    return time.perf_counter() - t0


def main():
    L = []
    A = L.append
    A('=' * 100)
    A('R561 — 算子级时间记账  (N=%d nv=%d dx=%.4f um workers=%d steps=%d)'
      % (N, NV, DX_UM, WORKERS, STEPS))
    A('=' * 100)
    g = build()

    # ---- P0 正对照：必须先跑过 advance，否则看到的是"幽灵状态"（N16）----
    A('')
    A('  预热前 pf.phi.dtype = %s（soft 前）' % g.pf.phi.dtype)
    g.advance(dt=1e-8)
    A('  预热后 pf.phi.dtype = %s   ← **P0 正对照**' % g.pf.phi.dtype)
    p0 = (g.pf.phi.dtype == np.float64)
    A('  P0（必须是 float64，float64 = 生产 soft 路径）: %s'
      % ('✅ PASS' if p0 else '❌ FAIL ⇒ 量具没跑过 advance'))

    # ---- 干净总时间（无记账器）----
    ts = []
    for _ in range(STEPS):
        t0 = time.perf_counter()
        g.advance(dt=1e-8)
        ts.append(time.perf_counter() - t0)
    s_clean = float(np.median(ts))
    A('')
    A('  干净单步 = **%.4f s**（中位数 / %d 步）  min=%.4f max=%.4f'
      % (s_clean, STEPS, min(ts), max(ts)))

    # ---- 记账跑 ----
    for k in list(T):
        del T[k]
    for k in list(CNT):
        del CNT[k]
    install()
    # ---- P0b 记账器自检：包装必须真的挂上（`_r561` v1 就是在这里静默失效的）----
    _s0 = CNT.get('region', 0)
    _ = g.region()
    _sent = CNT.get('region', 0) - _s0
    _t0s = T.get('region', 0.0)
    A('')
    A('  P0b 记账器自检：直接调一次 g.region() ⇒ 计数 +%d、计时 +%.4f s  ⇒ %s'
      % (_sent, T.get('region', 0.0) - _t0s,
         '✅ PASS（包装真的挂上了）' if _sent == 1 else
         '❌ FAIL ⇒ 包装被调用处覆盖回原函数（setattr 了又 return orig），表不可信'))
    for _k in list(T):
        del T[_k]
    for _k in list(CNT):
        del CNT[_k]
    t0 = time.perf_counter()
    for _ in range(STEPS):
        g.advance(dt=1e-8)
    s_acct = time.perf_counter() - t0
    A('  记账跑单步 = %.4f s（含计时器开销 %.1f%%）'
      % (s_acct / STEPS, 100 * (s_acct / STEPS / s_clean - 1)))

    # ---- 分组（**互不重叠**口径）----
    #   嵌套关系：elastic.pair ⊃ elastic.core ⊃ {el.sigma_tensor ⊃ eps0_fields, fft} ∪ fe.ed.*
    #            finish ⊃ {finish.reinit, finish.stefan}
    #   平级：region / argmin2 / fe.<geom> / fe.advance.k_loop
    reg = T.get('region', 0.0)
    am2 = T.get('argmin2', 0.0)
    elp = T.get('elastic.pair', 0.0)
    elc = T.get('elastic.core', 0.0)
    fin = T.get('finish', 0.0)
    fe_all = {k: v for k, v in T.items() if k.startswith('fe.')}
    fe_in_el = sum(v for k, v in fe_all.items()
                   if k in ('fe.ed.soft_phi', 'fe.ed.einsum'))
    fe_out = sum(v for k, v in fe_all.items() if k not in
                 ('fe.ed.soft_phi', 'fe.ed.einsum'))

    A('')
    A('  ── 互斥顶层块（秒 / 每步；外层含内层，故不重复相加）──')
    rows = [('region()             区域场 argmin ×3', reg),
            ('argmin2()            winner+runnerup', am2),
            ('elastic_driving_pair() 【含下面全部】', elp),
            ('  └ elastic_driving()  （= pair 的实现）', elc),
            ('  └   fe.ed.soft_phi   nv 次整场 tanh', fe_all.get('fe.ed.soft_phi', 0.0)),
            ('  └   fe.ed.einsum     nv 次整场 einsum', fe_all.get('fe.ed.einsum', 0.0)),
            ('  └   el.sigma_tensor', T.get('el.sigma_tensor', 0.0)),
            ('  └     el.eps0_fields（慢路）', T.get('el.eps0_fields', 0.0)),
            ('  └     el.fft_fwd(c2c)', T.get('el.fft_fwd', 0.0)),
            ('  └     el.fft_inv(c2c)', T.get('el.fft_inv', 0.0)),
            ('finish()             reinit+stefan', fin),
            ('  └ finish.reinit', T.get('finish.reinit', 0.0)),
            ('  └ finish.stefan', T.get('finish.stefan', 0.0)),
            ('for_each（**弹性之外**的那几段）', fe_out),
            ('  └ par.gradient', T.get('par.gradient', 0.0)),
            ('  └ par.upwind_flux_vec（4 线程并发之和）', T.get('par.upwind_flux_vec', 0.0)),
            ('  └ op.upwind_flux_vec（模块级）', T.get('op.upwind_flux_vec', 0.0)),
            ('  └ op._minmod', T.get('op._minmod', 0.0)),
            ('  └ op._bbox_pad', T.get('op._bbox_pad', 0.0)),
            ('  └ op.sussman_reinit', T.get('op.sussman_reinit', 0.0))]
    for name, v in rows:
        A('    %-40s %8.4f s   %6.1f%%' % (name, v / STEPS, 100 * v / s_acct))
    A('    %-40s %8.4f s   %6.1f%%' % ('  [明细] 弹性里的 fe.ed.* 合计',
                                      fe_in_el / STEPS, 100 * fe_in_el / s_acct))

    # 覆盖性：互斥的几块相加
    cover = (reg + am2 + elp + fin + fe_out)
    A('')
    A('  P1 覆盖性：(region + argmin2 + elastic.pair + finish + 弹性外的 for_each)')
    A('     = %.4f s = **%.1f%%** 的墙钟  ⇒ %s'
      % (cover / STEPS, 100 * cover / s_acct,
         '✅ PASS(≥85%%)' if cover / s_acct >= 0.85 else
         '⚠ <85%%：还有大块没记账，**不许据此下结论**'))

    A('')
    A('  ── 调用次数（每步）──')
    for k in sorted(CNT):
        A('    %-34s %8.2f /步' % (k, CNT[k] / float(STEPS)))

    slow = CNT.get('el.eps0_fields', 0)
    fast = CNT.get('el.eps0_fields_idx', 0)
    A('')
    A('  P3 复现 `_r559`：慢路 eps0_fields=%d 次 / 快路 eps0_fields_idx=%d 次  ⇒ %s'
      % (slow, fast,
         '✅ 与 _r559 一致（生产走慢路）' if (slow > 0 and fast == 0)
         else '⚠ 与 _r559 **不一致**，需查明'))

    # ---- P2 记账器自证：人为加一笔已知开销，必须看得见 ----
    A('')
    T_BURN = 2.0e-3
    _mo = W._minmod

    def _burn(a, b):
        t = time.perf_counter()
        while time.perf_counter() - t < T_BURN:
            pass
        return _mo(a, b)
    _patched = []
    for _m in (W, PAR):
        if '_minmod' in getattr(_m, '__dict__', {}):
            _m.__dict__['_minmod'] = _burn
            _patched.append(_m.__name__)
    A('     （已替换 `_minmod` 的模块：%s）' % ','.join(_patched))
    for k in list(T):
        del T[k]
    for k in list(CNT):
        del CNT[k]
    n_mm0 = CNT.get('op._minmod', 0)
    t0 = time.perf_counter()
    g.advance(dt=1e-8)
    s_burn = time.perf_counter() - t0
    got = T.get('op._minmod', 0.0)
    n_mm = CNT.get('op._minmod', 0)
    exp = n_mm * T_BURN
    A('  P2 记账器自证：给 `_minmod` 每次加 %.1f ms；本步调用 %d 次'
      % (T_BURN * 1e3, n_mm))
    A('     预期人工开销 ≥ %.3f s；记账器看到 `op._minmod` = %.3f s  ⇒ %s'
      % (exp, got,
         '✅ PASS（计时器确实挂在热路径上）' if (n_mm > 0 and got >= 0.8 * exp)
         else '❌ FAIL ⇒ 记账器没挂在热路径上，上面的表**不可信**'))
    W._minmod = _mo
    for _m in (W, PAR):
        if '_minmod' in getattr(_m, '__dict__', {}):
            _m.__dict__['_minmod'] = _mo

    A('')
    A('  P0=%s  P1=%.1f%%  P2=%s  P3=%s'
      % ('PASS' if p0 else 'FAIL', 100 * cover / s_acct,
         'PASS' if (n_mm > 0 and got >= 0.8 * exp) else 'FAIL',
         'PASS' if (slow > 0 and fast == 0) else 'CHECK'))

    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r561_acct.log'), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
