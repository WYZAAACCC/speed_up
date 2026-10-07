#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r576_prof.py --- R576 的**全量分块记账**：把 `advance()` 函数体内部的表达式也切开。

## 为什么要有这一版

`_r561_opfacct.py` 只能包**函数**，包不到 `advance()` 函数体里的表达式。
实测（`_w2_r572_acct_AFTER_24x64_w4.log`）覆盖率只有 **77.1%**，剩下 **22.9%**
是**单一最大的未知块**。本轮把钩子写进了生产代码（`windowB_acct.py` + 各算子文件），
本量具负责把它们读出来并**按互斥顶层块**求和。

## 判据（先写死，必须能失败）

* **P0**  `pf.phi.dtype == float64`（生产 soft 路径真的跑过）
* **P0b** 外部包装自检：直接调一次 `g.region()` ⇒ 计数 +1
* **P1**  **互斥顶层块之和 / 墙钟 ≥ 95%**（本轮目标；未归属 ≤5%）
* **P2**  自证：给 `_minmod` 每次加 2 ms，`op._minmod` 必须看得见
* **P2b** ★R576 新增：`acct.corrupt()` 必须为空 —— 否则 `span_begin/span_end`
        配对坏了，**时间被记到别人的 tag 上**而表面完全正常
* **P2c** ★R576 新增：**新钩子必须真的活**：`adv.vel_law` == 1.00/步、
        `adv.extend` == 1.00/步、`adv.region0` == 1.00/步。
        （上一轮的教训：量具静默失效时读数"看起来像引擎没走那条路"。）
* **P3**  `eps0_fields`（慢路）> 0 且 `eps0_fields_idx` == 0（与 `_r559` 一致）
* **P5**  构造期记账表非空
"""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import windowB_acct as acct                                     # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_pf3d as P3                                       # noqa: E402
import windowB_par as PAR                                       # noqa: E402
import _r561_opfacct as AC                                      # noqa: E402

N = int(os.environ.get('R576_N', '64'))
NV = int(os.environ.get('R576_NV', '24'))
DX_UM = float(os.environ.get('R576_DX', '0.0625'))
STEPS = int(os.environ.get('R576_STEPS', '6'))
WORK = int(os.environ.get('R576_WORKERS', '4'))
TAG = os.environ.get('R576_TAG', 'base')
OUT = os.environ.get('R576_OUT', '_w2_r576_prof.log')

os.environ['R561_N'] = str(N)
os.environ['R561_NV'] = str(NV)
os.environ['R561_DX'] = str(DX_UM)
os.environ['R561_WORKERS'] = str(WORK)
AC.N, AC.NV, AC.DX_UM, AC.WORKERS = N, NV, DX_UM, WORK

# ★ R581-L1：把 `--extend-mode` 也做成环境变量（**同一把量具**量改前/改后）。
#   为什么用猴补丁而不是改 5 个调用点：本文件是**量具**，调用点散在 5 处；
#   猴补丁只加一层 `kw.setdefault`，每次 `advance` 一次，代价 ~1 µs/步（可忽略）。
#   ⚠ 它**不改任何数值**（只是把同一个档名传进去）；逐位判据由 `_r581_L1check.py` /
#     `_r581_L1ab.sh` 独立把关。
_EM = os.environ.get('R581_EXTEND')
if _EM:
    _adv0 = W.LevelSetMulti.advance

    def _adv(self, dt, **kw):
        kw.setdefault('extend_mode', _EM)
        return _adv0(self, dt, **kw)
    W.LevelSetMulti.advance = _adv

# ---- 互斥顶层块（**静态声明**；顺序 = advance() 里的执行顺序）----------------
#   ⚠ 并行段（`for_each`）无法用栈自动推断嵌套 ⇒ 必须**人工声明**。
TOP = [
    ('adv.region0',        '步首 region()（含一次性 banner）'),
    ('argmin2',            'winner / runner-up'),
    ('adv.cast_idx',       'karr/larr -> intp ×2'),
    ('adv.gc_full',        'F3 面能表（N³ gather + isfinite + where）'),
    ('adv.alloc',          'kap_w / stk_w / stl_w 分配'),
    ('adv.unique_act',     'np.unique(karr) + np.unique(larr)'),
    ('fe.advance.geom_k',  'for_each 几何（内含 adv.geom.*）'),
    ('elastic.pair',       '弹性全链（内含 el.* / fe.ed.*）'),
    ('adv.take_ph',        'take_along_axis 取 φ_k / φ_l'),
    ('adv.pair_aniso',     '配对各向异性分支（默认不进）'),
    ('adv.kap_diff',       '差分场曲率 kap_cell（pair_curvature=True，**默认进**）'),
    ('adv.mirror_check',   '镜像 SDF 前提**每步**直测（纯诊断，`or True` 恒真）'),
    ('adv.vel_law',        '速度律 dG_cell = Δdf + Δed − γκ'),
    ('adv.diag',           '诊断块（默认关）'),
    ('adv.dg_max',         'max|dG_cell|'),
    ('adv.ed_by_face',     '按面族统计 ed/dG（纯记账）'),
    ('adv.v_cell',         'v = M·dG'),
    ('adv.solve_v',        '拖曳隐式解（默认不进）'),
    ('adv.mfac',           'M(n) 各向异性（默认不进）'),
    ('adv.dg_max_mfac',    'Mfac 后重定 dG_max + 百分位（默认不进）'),
    ('adv.v_by_face',      '按面族速度统计（纯记账）'),
    ('adv.extend',         '速度延拓（EDT / 带宽掩模）'),
    ('adv.proj_geom',      '投影几何 ∇d/|∇d|'),
    ('adv.sigma_vcanon',   'sigma = sign(l−k) 与 vcanon = sigma·v'),
    ('fe.advance.k_loop',  'for_each 推进（内含 adv.step.* / par.upwind_flux_vec）'),
    ('finish',             '_finish_advance（含 region#2 / reinit / stefan）'),
]

# 不属于任何顶层块的 tag（应尽量少、尽量小）→ 直接在 GAP 表里按大小列出。
#   ★ 必须**静态声明**每个 GAP tag 的父块：并行段（`for_each`）无法用调用栈自动推断
#     （worker 线程的栈里没有主线程那个 `for_each` 帧）⇒ 不声明就只能靠猜。
NEST = {
    'argmin2.winner': 'argmin2',
    'argmin2.runnerup': 'argmin2',
    'adv.geom.mask_bbox': 'fe.advance.geom_k',
    'adv.geom.grad': 'fe.advance.geom_k',
    'adv.geom.curv': 'fe.advance.geom_k',
    'adv.geom.stiff': 'fe.advance.geom_k',
    'adv.geom.scatter': 'fe.advance.geom_k',
    'elastic.core': 'elastic.pair',
    'fe.ed.soft_phi': 'elastic.pair',
    'fe.ed.einsum': 'elastic.pair',
    'el.sigma_tensor': 'elastic.pair',
    'el.eps0_fields': 'el.sigma_tensor',
    'el.eps0_fields_idx': 'el.sigma_tensor',
    'el.epsh': 'el.sigma_tensor',
    'el.epsh_r': 'el.sigma_tensor',
    'el.e0.loop': 'el.epsh / el.epsh_r',
    'el.e0.einsum': 'el.epsh / el.epsh_r',
    'el.e0.gemm': 'el.epsh / el.epsh_r',
    'el.e0.stream': 'el.epsh（onfly 路）',
    'el.fft_fwd': 'el.epsh',
    'el.fft_inv': 'el.sigma_tensor',
    'el.rfft_fwd': 'el.epsh_r',
    'el.rfft_inv': 'el.sigma_tensor',
    'el.sig.contract': 'el.sigma_tensor',
    'el.sig.real': 'el.sigma_tensor',
    'adv.step.vnk': 'fe.advance.k_loop',
    'adv.step.advphi': 'fe.advance.k_loop',
    'par.upwind_flux_vec': 'adv.step.advphi',
    'op.upwind_flux_vec': 'par.upwind_flux_vec',
    'op.ufv.body': 'op.upwind_flux_vec',
    'op.ufv.diff': 'op.ufv.body',
    'op.ufv.minmod': 'op.ufv.body',
    'op.ufv.where': 'op.ufv.body',
    'op._minmod': 'op.ufv.minmod',
    'op._bbox_pad': 'adv.geom.mask_bbox',
    'op.sussman_reinit': 'finish.reinit',
    'par.gradient': 'adv.geom.grad 与 adv.step.* **两处都有**',
    'par.argmin': 'region',
    'par.upwind_grad2': 'adv.step.advphi（非 proj 路）',
    'region': 'adv.region0 与 finish **各一次**（与顶层有重叠）',
    'finish.reinit': 'finish',
    'finish.stefan': 'finish',
    'fe.advance.geom_k': '—（**本身就是顶层块**）',
    'fe.advance.k_loop': '—（**本身就是顶层块**）',
}


def main():
    L = []
    A = L.append
    A('=' * 104)
    A('R576 — 全量分块记账 (N=%d nv=%d dx=%.4f um workers=%d steps=%d tag=%s)'
      % (N, NV, DX_UM, WORK, STEPS, TAG))
    A('=' * 104)
    A('  宿主：python %s  numpy %s  scipy %s'
      % (sys.version.split()[0], np.__version__, __import__('scipy').__version__))

    # ---- 构造期记账（钩子已开，PF3D/LevelSetMulti 的建表都在里面）----
    acct.enable()
    acct.reset()
    g = AC.build()
    bld = dict(acct.B)

    A('')
    A('  预热前 pf.phi.dtype = %s' % g.pf.phi.dtype)
    g.advance(dt=1e-8)
    A('  预热后 pf.phi.dtype = %s   ← **P0 正对照**' % g.pf.phi.dtype)
    p0 = (g.pf.phi.dtype == np.float64)
    A('  P0（必须 float64 = 生产 soft 路径）: %s'
      % ('✅ PASS' if p0 else '❌ FAIL ⇒ 量具没跑过 advance'))

    # ---- 干净总时间（钩子**关**）----
    acct.disable()
    ts = []
    for _ in range(STEPS):
        t0 = time.perf_counter()
        g.advance(dt=1e-8)
        ts.append(time.perf_counter() - t0)
    s_clean = float(np.median(ts))
    A('')
    A('  干净单步（钩子关）= **%.4f s**  min=%.4f max=%.4f'
      % (s_clean, min(ts), max(ts)))

    # ---- 记账跑（钩子开 + 外部包装）----
    acct.enable()
    acct.reset()
    AC.install()
    if not getattr(AC, '_INSTALLED', False):
        A('  ⚠ 无法判定 install 状态')
    _s0 = AC.CNT.get('region', 0)
    _ = g.region()
    _sent = AC.CNT.get('region', 0) - _s0
    A('')
    A('  P0b 记账器自检：直接调一次 g.region() ⇒ 计数 +%d  ⇒ %s'
      % (_sent, '✅ PASS' if _sent == 1 else '❌ FAIL（包装被覆盖回原函数）'))
    acct.reset()
    AC.T.clear()
    AC.CNT.clear()
    t0 = time.perf_counter()
    for _ in range(STEPS):
        g.advance(dt=1e-8)
    s_acct = time.perf_counter() - t0
    A('  记账跑单步 = %.4f s（钩子+计时器开销 %.1f%%）'
      % (s_acct / STEPS, 100 * (s_acct / STEPS / s_clean - 1)))

    T, C = acct.totals()
    cor = acct.corrupt()
    # ★★★ R576 自查抓到的错（第 2 条量具错误）：**两套记账器必须合并读取**。
    #   ① `acct`（写进生产代码的钩子）：`adv.*` / `el.e0.*` / `op.ufv.*` / `argmin2.*`
    #   ② `_r561_opfacct`（monkey-patch 的函数边界）：`region` / `argmin2` /
    #      `elastic.pair` / `finish` / `fe.*` / `el.sigma_tensor` / `par.*` / `op.*`
    #   v1 只读了 ① ⇒ 所有函数边界 tag 全 0 ⇒ P1 覆盖率假报 **20.0%**，
    #   而真值在 90% 以上。**"覆盖率低"和"量具读错表"在这里长得一模一样。**
    #   ⇒ 合并读取；并**硬断言两套 tag 不相交**（相交 = 同一个量记两次 ⇒ 静默翻倍）。
    _inter = sorted((set(AC.T) | set(AC.CNT)) & (set(T) | set(C)))
    if _inter:
        A('')
        A('  ⚠⚠ P2d FAIL：两套记账器 tag **相交** %r ⇒ 会双计，表不可信' % _inter)
    _merged = dict(T)
    _merged.update(AC.T)
    T = _merged
    _mergedC = dict(C)
    _mergedC.update(AC.CNT)
    C = _mergedC

    # ---- 顶层互斥块 ----
    A('')
    A('  ── 互斥顶层块（秒/步，占比按**记账跑墙钟**）──')
    cover = 0.0
    for tag, desc in TOP:
        v = T.get(tag, 0.0)
        n = C.get(tag, 0)
        cover += v
        A('    %-22s %8.5f s  %6.2f%%  n=%5.2f/步  %s'
          % (tag, v / STEPS, 100 * v / s_acct, n / float(STEPS), desc))
    A('    %-22s %8.5f s  %6.2f%%'
      % ('—— 顶层合计', cover / STEPS, 100 * cover / s_acct))

    # ---- 关键子块（**嵌套**，不参与上面求和）----
    A('')
    A('  ── 关键子块（嵌套在上面某些块里，**不参与**覆盖率求和）──')
    SUB = [
        ('adv.geom.grad', '  └ geom: par.gradient'),
        ('adv.geom.curv', '  └ geom: curvature_of'),
        ('adv.geom.stiff', '  └ geom: _stiff_of'),
        ('adv.geom.mask_bbox', '  └ geom: 掩模 + _bbox_pad'),
        ('adv.geom.scatter', '  └ geom: 散点写回'),
        ('fe.ed.soft_phi', '  └ el: nv 次整场 tanh'),
        ('fe.ed.einsum', '  └ el: nv 次 einsum（gather 版）'),
        ('el.sigma_tensor', '  └ el: sigma_tensor（总）'),
        ('el.epsh', '  └   c2c: eps0_fields + ×2 + fftn'),
        ('el.epsh_r', '  └   rfft: eps0_fields + ×2 + rfftn'),
        ('el.e0.loop', '  └     eps0_fields loop'),
        ('el.e0.einsum', '  └     eps0_fields einsum'),
        ('el.e0.gemm', '  └     eps0_fields gemm'),
        # ★ R581：`--pf-phi onfly` 下 `eps0_fields` 走**流式**路（不物化 h）。
        #   ⚠ 这个钩子**生产代码里一直有**（`windowB_pf3d.py` 的 `acct.mark('el.e0.stream')`），
        #     但本量具的 SUB 表**没声明它** ⇒ 读数被采集了却**从不打印**
        #     ⇒ 第一版"生产口径靶子表"里 `el.epsh` 那 1.10 s 只能靠
        #     `el.epsh − el.fft_fwd` **反推**。**这是量具的缺口，不是引擎的**（AGENTS P6 同类）。
        ('el.e0.stream', '  └     eps0_fields stream（onfly，R581-L2 的靶子）'),
        ('el.fft_fwd', '  └     fftn(c2c)'),
        ('el.fft_inv', '  └     ifftn(c2c)'),
        ('el.rfft_fwd', '  └     rfftn'),
        ('el.rfft_inv', '  └     irfftn'),
        ('el.sig.contract', '  └   Lam 缩并 einsum'),
        ('el.sig.real', '  └   real(ifftn)'),
        ('adv.step.vnk', '  └ k_loop: vnk 掩模'),
        ('adv.step.advphi', '  └ k_loop: 推进本体'),
        ('par.upwind_flux_vec', '  └   par.upwind_flux_vec（线程并发之和）'),
        ('op.upwind_flux_vec', '  └     op.upwind_flux_vec（模块级）'),
        ('op.ufv.diff', '  └       D⁻/D⁺（4×roll）'),
        ('op.ufv.minmod', '  └       minmod ×2'),
        ('op.ufv.where', '  └       迎风选边'),
        ('op._minmod', '  └       _minmod（模块级）'),
        ('par.gradient', '  └ par.gradient'),
        ('region', '  └ region()（**含 finish 里那次**，与顶层有重叠）'),
        ('finish.reinit', '  └ finish: reinitialize'),
        ('finish.stefan', '  └ finish: _stefan'),
    ]
    for tag, desc in SUB:
        v = T.get(tag, 0.0)
        n = C.get(tag, 0)
        A('    %-22s %8.5f s  %6.2f%%  n=%5.2f/步  %s'
          % (tag, v / STEPS, 100 * v / s_acct, n / float(STEPS), desc))

    # ---- GAP：不在顶层块里的 tag ----
    topset = set(t for t, _ in TOP)
    A('')
    A('  ── GAP：**不属于任何顶层块**的 tag（未归属的逐项去向）──')
    gap = sorted(((k, v) for k, v in T.items() if k not in topset),
                 key=lambda kv: -kv[1])
    for k, v in gap:
        A('    %-30s %8.5f s  %6.2f%%  n=%5.2f/步   嵌套于: %s'
          % (k, v / STEPS, 100 * v / s_acct, C.get(k, 0) / float(STEPS),
             NEST.get(k, '—（**未声明父块**）')))
    A('')
    A('  **未归属 = 墙钟 − 顶层合计** = %.5f s = **%.2f%%**'
      % ((s_acct - cover) / STEPS, 100 * (s_acct - cover) / s_acct))
    A('  （GAP 表里的 tag **绝大多数嵌套在顶层块内部**，所以**不能**从"未归属"里再减一次；'
      '它们的作用是给出顶层块的内部构成。）')
    # ★ R576：**局部**口径的未归属（不依赖墙钟，免疫 run-to-run 抖动）。
    _tot = T.get('adv.total', 0.0)
    if _tot > 0:
        A('')
        A('  ── 局部口径（`adv.total` = 整个 advance 函数体，与墙钟无关）──')
        A('    adv.total                %8.5f s  n=%.2f/步' % (_tot / STEPS,
                                                              C.get('adv.total', 0) / float(STEPS)))
        A('    顶层合计                 %8.5f s' % (cover / STEPS))
        A('    **函数体内未归属**        %8.5f s = **%.2f%%**  ← 还要往下切的部分'
          % ((_tot - cover) / STEPS, 100 * (_tot - cover) / _tot))

    # ---- ★ R576：**区间轨迹** ⇒ 未归属部分的**逐项去向**（不靠猜）----
    A('')
    A('  ── 区间轨迹：`adv.total` 内**没有任何计时区间覆盖**的空隙（单步，降序）──')
    acct.reset()
    AC.T.clear()
    AC.CNT.clear()
    acct.trace_on()
    g.advance(dt=1e-8)
    acct.trace_off()
    gaps = acct.trace_gaps(top=20, skip=('adv.total',))
    _tg = sum(x[0] for x in gaps)
    A('    空隙总数 = %d，合计 %.5f s' % (len(gaps), _tg))
    A('    %-10s %-10s %-26s %-26s' % ('秒', '占比', '前一个区间', '后一个区间'))
    _tot_step = T.get('adv.total', 0.0) / STEPS if STEPS else 1.0
    for dtg, a, b, rel in gaps:
        A('    %-10.5f %-10s %-26s %-26s  （在 adv.total 内 +%.4f s 处）'
          % (dtg, '%.2f%%' % (100 * dtg / max(_tot_step, 1e-9)), a, b, rel))

    # ---- 覆盖性判据 ----
    A('')
    _tot2 = T.get('adv.total', 0.0)
    _p1a = (cover / _tot2) if _tot2 > 0 else float('nan')
    A('  P1  覆盖率（顶层合计 / `adv.total`：**函数体口径**，免疫墙钟抖动）= **%.1f%%**'
      % (100 * _p1a))
    A('  P1b 覆盖率（顶层合计 / 记账跑墙钟，含 advance 之外的启动/收尾）= **%.1f%%**'
      % (100 * cover / s_acct))
    A('  ⇒ P1 判据（≥95%%）：%s'
      % ('✅ PASS' if _p1a >= 0.95 else
         '⚠ <95%%：还有块没记账（见上面 GAP 表），**不许据此下结论**'))

    # ---- P2 记账器自证 ----
    A('')
    T_BURN = 2.0e-3
    _mo = W._minmod

    def _burn(a, b):
        t = time.perf_counter()
        while time.perf_counter() - t < T_BURN:
            pass
        return _mo(a, b)
    W.__dict__['_minmod'] = _burn
    acct.reset()
    AC.T.clear()
    AC.CNT.clear()
    t0 = time.perf_counter()
    g.advance(dt=1e-8)
    got = AC.T.get('op._minmod', 0.0)
    n_mm = AC.CNT.get('op._minmod', 0)
    exp = n_mm * T_BURN
    A('  P2 记账器自证：`_minmod` 每次加 %.1f ms；本步 %d 次 ⇒ 预期 ≥ %.3f s，看到 %.3f s ⇒ %s'
      % (T_BURN * 1e3, n_mm, exp, got,
         '✅ PASS' if (n_mm > 0 and got >= 0.8 * exp)
         else '❌ FAIL ⇒ 计时器没挂在热路径上，整张表不可信'))
    W.__dict__['_minmod'] = _mo

    # ---- P2b span 配对 ----
    A('')
    A('  P2b span_begin/span_end 配对自检：corrupt = %r  ⇒ %s'
      % (cor, '✅ PASS（干净）' if not cor else '❌ FAIL ⇒ 时间被记到别人的 tag 上'))

    # ---- P2c 新钩子活性 ----
    A('')
    A('  P2c 新钩子活性（每步次数；缺失 = 静默失效）:')
    alive = True
    for tag, want in (('adv.vel_law', 1.0), ('adv.extend', 1.0),
                      ('adv.region0', 1.0), ('adv.dg_max', 1.0),
                      ('adv.take_ph', 1.0), ('adv.unique_act', 1.0)):
        got_n = C.get(tag, 0) / float(STEPS)
        ok = abs(got_n - want) < 1e-9
        alive = alive and ok
        A('    %-20s %5.2f/步（应 %.2f）  %s' % (tag, got_n, want,
                                                '✅' if ok else '❌ 静默失效'))
    A('  P2c 判定：%s' % ('✅ PASS' if alive else '❌ FAIL'))

    # ---- P3 eps0 路径 ----
    slow = AC.CNT.get('el.eps0_fields', 0)
    fast = AC.CNT.get('el.eps0_fields_idx', 0)
    A('')
    A('  P3 `_r559` 复现：慢路 eps0_fields=%d 次 / 快路=%d 次 ⇒ %s'
      % (slow, fast,
         '✅ 一致（生产走慢路）' if (slow > 0 and fast == 0) else '⚠ 不一致'))

    # ---- P5 构造期记账 ----
    A('')
    A('  ── P5 构造期记账（一次性）──')
    tot_b = 0.0
    tot_mb = 0.0
    for k in sorted(bld, key=lambda x: -bld[x][0]):
        s, nb = bld[k]
        tot_b += s
        tot_mb += nb / 2.0 ** 20
        A('    %-28s %8.3f s   %10.2f MB' % (k, s, nb / 2.0 ** 20))
    A('    %-28s %8.3f s   %10.2f MB' % ('（合计）', tot_b, tot_mb))
    p5 = len(bld) > 0
    A('  P5 判定：%s' % ('✅ PASS（构造期已记账）' if p5 else '❌ FAIL（构造期无数据）'))

    A('')
    A('  P0=%s  P0b=%s  P1=%.1f%%  P1b=%.1f%%  P2=%s  P2b=%s  P2c=%s  P3=%s  P5=%s'
      % ('PASS' if p0 else 'FAIL', 'PASS' if _sent == 1 else 'FAIL',
         100 * _p1a, 100 * cover / s_acct,
         'PASS' if (n_mm > 0 and got >= 0.8 * exp) else 'FAIL',
         'PASS' if not cor else 'FAIL', 'PASS' if alive else 'FAIL',
         'PASS' if (slow > 0 and fast == 0) else 'CHECK',
         'PASS' if p5 else 'FAIL'))

    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, OUT), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
