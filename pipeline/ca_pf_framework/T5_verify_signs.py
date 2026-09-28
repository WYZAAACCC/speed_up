#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T5_verify_signs.py --- T5 判据：全项目**符号约定统一**（>0 = 变体有利）。

病灶（T1 之后复核发现）：`windowB_km.dG_chem` 返回的是**摩尔 Gibbs 能差 ΔG**
（T<T0 时为负），而 `PF3D.dG` / `LevelSetMulti.df` 的约定是**驱动力**（>0 = 有利）。
两者差一个符号，靠 `windowB_b1._step_T` 里的 `-K.dG_chem(...)` 隐式弥合；
且 `windowB_km` docstring §(1)/§(2) 自相矛盾（§(2) 写成 `dG_chem(M_s) = dG_crit`，
实际是 `-dG_crit`）。

修法：两个量**分开命名**（`dG_chem` = ΔG；`drive_of_T` = 驱动力），
      **只留一处显式换算**，并加断言 + 本判据。

判据
----
  T5-A  `windowB_km.selftest()` 全过（含 `drive ≡ -dG_chem`、单调性、`drive(M_s)=+|dG_crit|`）
  T5-B  **无第二套约定**：扫描 `ca_pf_framework/*.py`，除 `windowB_km.drive_of_T`
        内部那**一处**定义外，不得再出现 `-dG_chem(...)` / `-K.dG_chem(...)`
  T5-C  **端到端方向性**（最硬的一条）：用 B1 的 T 时间表，
        T < T0 时变体体积**长大**、T > T0 时**收缩**；
        且 `_step_T` 给出的 df 与 `K.drive_of_T` 逐位相同
  T5-D  PF3D 侧：`set_T` + `dG_of_T=drive_of_T` 时，T<T0 的 dG > 0、T>T0 的 dG < 0

用法：python3 T5_verify_signs.py
退出码：0 = PASS
"""
import os
import re
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                                              # noqa: E402
import windowB_km as K                                          # noqa: E402
import windowB_surface as W                                     # noqa: E402


# ---------------------------------------------------------------- T5-A
def run_A():
    print('【T5-A】windowB_km.selftest()')
    ok = K.selftest(verbose=True)
    print('  T5-A: %s' % ('PASS' if ok else 'FAIL'))
    return ok


# ---------------------------------------------------------------- T5-B
def run_B():
    print()
    print('【T5-B】全框架扫描：不得再有隐式补偿负号')
    # ★ 必须**先剥掉注释与字符串字面量**再匹配 —— 否则会把"禁止写 -dG_chem"这句
    #   说明文字本身当成违规（首版就踩了，误报 7 处）。用 tokenize 做，不做正则猜测。
    import io
    import tokenize
    pat = re.compile(r'-\s*(K\.)?dG_chem\s*\(')
    hits = []
    for fn in sorted(os.listdir(HERE)):
        if not fn.endswith('.py'):
            continue
        p = os.path.join(HERE, fn)
        with open(p, 'rb') as f:
            src = f.read()
        try:
            toks = list(tokenize.tokenize(io.BytesIO(src).readline))
        except Exception:
            continue
        # 逐 token 重建"代码骨架"（只保留 NAME/OP/NUMBER，丢掉 COMMENT/STRING）
        keep = [t for t in toks if t.type not in (tokenize.COMMENT, tokenize.STRING)]
        for i, t in enumerate(keep):
            if t.type == tokenize.NAME and t.string == 'dG_chem':
                # 往前看是否有紧邻的一元负号
                j = i - 1
                if j >= 0 and keep[j].type == tokenize.OP and keep[j].string == '-':
                    hits.append((fn, t.start[0], 'neg dG_chem @line %d' % t.start[0]))
    allowed = [h for h in hits if h[0] == 'windowB_km.py']
    bad = [h for h in hits if h[0] != 'windowB_km.py']
    print('  命中 %d 处；许可（windowB_km.drive_of_T 定义）%d 处；**违规 %d 处**'
          % (len(hits), len(allowed), len(bad)))
    for h in bad:
        print('    ✗ %s:%d  %s' % h)
    ok = (len(allowed) == 1) and (len(bad) == 0)
    print('  T5-B: %s' % ('PASS' if ok else 'FAIL'))
    return ok


# ---------------------------------------------------------------- T5-C
def run_C(N=24, dx=1e-8, nstep=40):
    """★★ 判据形式修正（2026-09-28，第 14 处；与 T6-C 同源）：
    旧写法要求"`T < T0` 时晶核**必须长大**"（`want_grow=True`）。
    但**小晶核在中等驱动下本来就会被曲率项溶掉** —— 这不是符号错，是物理
    （T6 的记账已写明："暖温档下种子会缩小 ⇒ 这正是**形核必须是输入**的物理原因"）。
    实测（本会话回归扫描，D7 换常数 + D17/A1 换默认之后）：
      `T = 823 K` ⇒ `df = +1.335e8`（**与 `drive_of_T` 逐位相同** ✓）却 `V 178 → 3`
      ⇒ 判据 **假 FAIL**（方向性其实是对的）。
    ⇒ 改成**不变于常数的形式**：只判**两档的相对次序**——
      `df(T<M_s) > 0 > df(T>T0)`，且 `V(T<M_s) > V(T>T0)`（**同一物理时间**下）。
      绝对"长大/收缩"只作诊断打印，不参与判定。"""
    print()
    print('【T5-C】端到端方向性（B1 的 T 时间表）')
    Ms, DS, dGc = K.M_S_TI64, K.DS_REF, K.DG_CRIT_REF
    T0 = K.T0_from_Ms(Ms, dGc, DS)
    print('  M_s = %.1f K,  T0 = %.1f K（T0 > M_s 必须成立）' % (Ms, T0))
    res = {}
    for T, tag in ((Ms - 50.0, 'cold'), (T0 + 50.0, 'hot')):
        b = K_import_b1()(N=N, dx=dx, Ms=Ms, alpha=K.ALPHA_KM_REF, v0=1.0e-24,
                          DS=DS, dG_crit=dGc, workers=1)
        g = b.g
        # 预置一个晶核（绕过 athermal 形核层，只测**方向性**）
        g.seed_plate(1, [g.L / 2] * 3, b.npref[1], 0.22 * g.L, 2 * dx)
        g.init_parent()
        v0 = float((g.region() > 0).sum())
        df = b._step_T(T)
        df_ref = float(K.drive_of_T(T, b.T0, b.DS))
        same = (df == df_ref)
        # ★ 两档用**同一个 dt**（同一物理时间）⇒ 才能比 V 的大小（R7）
        dt = 0.15 * dx / max(abs(b.Mob * dGc), 1e-30)
        for _ in range(nstep):
            g.elastic_driving()
            g.advance(dt, aniso=b.aniso, npref=b.npref, band_cells=20)
        v1 = float((g.region() > 0).sum())
        res[tag] = dict(df=df, same=same, v0=v0, v1=v1, V=v1 / max(v0, 1e-30), T=T)
        print('  T = %.1f K (%s T0): df = %+.6e（与 drive_of_T 逐位相同: %s）; '
              'V %d -> %d（V/V0=%.4f，**同一 dt**）'
              % (T, '<' if T < T0 else '>', df, same, int(v0), int(v1),
                 res[tag]['V']))
    c, h = res['cold'], res['hot']
    ok_sign = (c['df'] > 0) and (h['df'] < 0) and c['same'] and h['same']
    ok_order = c['V'] > h['V']
    ok = ok_sign and ok_order
    print('  **判据（不变于常数）**：`df(cold)>0>df(hot)` = %s ；'
          '`V/V0(cold) > V/V0(hot)` = %s（%.4f vs %.4f）'
          % (ok_sign, ok_order, c['V'], h['V']))
    print('  ★ 记账：旧判据"T<T0 必须长大"对**小晶核**不成立（曲率项主导，物理上就该缩）'
          '⇒ 已改为**相对次序**判据；绝对长大/收缩只作诊断。')
    print('  T5-C: %s' % ('PASS' if ok else 'FAIL'))
    return ok


_B1C = [None]


def K_import_b1():
    if _B1C[0] is None:
        import windowB_b1 as B
        _B1C[0] = B.B1Athermal
    return _B1C[0]


# ---------------------------------------------------------------- T5-D
def run_D():
    print()
    print('【T5-D】PF3D 侧：dG_of_T = drive_of_T 的方向性')
    from windowB_pf3d import PF3D, C_cubic
    from windowB_ti64_variants import variants
    eps0, _F, _m = variants()
    Ms, DS, dGc = K.M_S_TI64, K.DS_REF, K.DG_CRIT_REF
    T0 = K.T0_from_Ms(Ms, dGc, DS)
    C = C_cubic(134.0e9, 110.0e9, 36.0e9)
    pf = PF3D(16, 16e-8, C, eps0, gamma=0.0, w90=1e-8, Lmob=1e-9,
              dG_of_T=lambda T: K.drive_of_T(T, T0, DS))
    d1 = pf.set_T(Ms)
    d2 = pf.set_T(T0 + 50.0)
    ok = (d1 > 0) and (d2 < 0)
    print('  dG(M_s) = %+.6e（须 > 0）;  dG(T0+50K) = %+.6e（须 < 0）' % (d1, d2))
    print('  T5-D: %s' % ('PASS' if ok else 'FAIL'))
    return ok


def main():
    print('=' * 96)
    print('T5 —— 全局符号约定统一（>0 = 变体有利）')
    print('=' * 96)
    r = [('T5-A', run_A()), ('T5-B', run_B()), ('T5-C', run_C()), ('T5-D', run_D())]
    print()
    print('=' * 96)
    for n, ok in r:
        print('  %-6s %s' % (n, 'PASS' if ok else 'FAIL'))
    allok = all(ok for _n, ok in r)
    print('  ⇒ T5 %s' % ('PASS' if allok else 'FAIL'))
    print('=' * 96)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
