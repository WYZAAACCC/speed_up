#!/usr/bin/env python3
"""
T6：溶质迁移率分层的**与代码逐行核对**。

不手算、不抄公式：直接把 `.i` 文件里 `[free_energy]` 与 `[solute_mobility]`
的**表达式原文**取出来数值求导，检查
        D = M · ∂²f_loc/∂c²
在 液相 / 晶粒内 / 固固晶界 三种状态下是否等于输入的 D_L / D_S / D_GB。

为什么这样核对：本项目的一贯要求是「一定要与代码相核对」。
手抄公式去比对手抄公式没有意义 —— 两边可能同时错。
这里左边（∂²f/∂c²）从 **f_loc 的原文**数值求导得到，
右边（M）从 **solute_mobility 的原文**求值得到，两边都是代码里的字符串。

用法：
    python3 check_D_layering.py <分支输入.i> [--dl D_L --ds D_S --dgb D_GB]
    python3 check_D_layering.py ../stage1_meltpool_c.i        # 旧模型（应给出 1.5867）
"""

import argparse
import math
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass


# MOOSE parsed 表达式里可用的数学函数（Python 侧的白名单）。
# eval 的沙箱把 builtins 清空了，这些必须显式给，否则 NameError。
_SAFE = {
    "min": min, "max": max, "abs": abs, "pow": pow, "round": round,
    "exp": math.exp, "log": math.log, "log10": math.log10,
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "tanh": math.tanh, "sinh": math.sinh, "cosh": math.cosh,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "floor": math.floor, "ceil": math.ceil, "pi": math.pi, "e": math.e,
}


def block(text: str, name: str) -> str:
    """按行扫描取 [name] ... [] 之间的内容（比正则稳）。"""
    out, inside = [], False
    for ln in text.splitlines():
        if not inside:
            if ln.strip() == f"[{name}]":
                inside = True
            continue
        if ln.strip() == "[]":
            break
        out.append(ln)
    return "\n".join(out)


def get_param(blk: str, key: str) -> str:
    """
    取参数值。

    ⚠ 必须处理**跨行的引号字符串** —— 例如 [free_energy] 的 expression 写成
        expression = 'k_c/2*(c-c0)^2
                      + A_part*c^2*(gr0^2+...)'
    MOOSE 会把引号内的换行折叠掉，所以这里也按空白拼接。
    用 `^\\s*key\\s*=\\s*(.+?)$` 那种逐行正则只能拿到第一行，会在
    `**` 那里留下一个未闭合的字符串 —— 这个坑踩过一次。
    """
    m = re.search(rf"^\s*{re.escape(key)}\s*=\s*'", blk, re.M)
    if m:
        end = blk.find("'", m.end())
        if end < 0:
            sys.exit(f"错误：{key} 的引号没有闭合")
        return " ".join(blk[m.end():end].split())
    m = re.search(rf"^\s*{re.escape(key)}\s*=\s*(\S+)\s*$", blk, re.M)
    if not m:
        sys.exit(f"错误：块里找不到 {key}")
    return m.group(1)


def make_eval(expr: str, consts: dict, mats: dict | None = None):
    """把 MOOSE 的 parsed 表达式变成可求值的 Python 函数。"""
    e = expr.replace("^", "**")
    # ⚠ 必须迭代到不动点：h_gb 展开后会**引入新的 S_eta2**，
    #   一趟 dict 遍历（S_eta2 在前、h_gb 在后）会留下未展开的 S_eta2。
    for _ in range(10):
        before = e
        for k, v in (mats or {}).items():
            e = re.sub(rf"\b{k}\b", f"({v})", e)
        if e == before:
            break
    else:
        sys.exit("错误：材料属性展开没有收敛（存在循环引用？）")

    def f(**vars_):
        env = dict(consts)
        env.update(vars_)
        env.setdefault("pi", math.pi)
        # MOOSE 的 parsed 表达式支持 min/max/abs/pow/exp/tanh…，
        # 这些在 eval 的沙箱里必须显式放进 builtins，否则 NameError。
        # （踩过一次：h_solid = min(1, 2*S) 一加进来就崩。）
        return eval(e, {"__builtins__": _SAFE}, env)  # noqa: S307

    return f, e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--dl", type=float)
    ap.add_argument("--ds", type=float)
    ap.add_argument("--dgb", type=float)
    args = ap.parse_args()

    s = open(args.src, encoding="utf-8").read()
    ns = ["gr0", "gr1", "gr2", "gr3", "gr4", "gr5", "gr6", "gr7"]

    # ---- f_loc ----
    fe = block(s, "free_energy")
    f_expr = get_param(fe, "expression")
    cn = get_param(fe, "constant_names").split()
    ce = [float(x) for x in get_param(fe, "constant_expressions").split()]
    fconst = dict(zip(cn, ce))
    f_loc, f_loc_e = make_eval(f_expr, fconst)

    print(f"文件：{args.src}")
    print(f"  f_loc  : {f_loc_e}")
    print(f"  常数   : {fconst}")

    # ---- M 及其依赖的派生材料 ----
    # 不硬编码材料名：把所有 property_name 有定义的块都解析出来，
    # 迭代展开。这样换名字/加中间层都不用改本脚本。
    mats = {}
    for m in re.finditer(r"^\s*\[(\w+)\]\s*$", s, re.M):
        blk = block(s, m.group(1))
        if "property_name" not in blk:
            continue
        try:
            pn = get_param(blk, "property_name")
            ex = get_param(blk, "expression")
        except SystemExit:
            continue
        if pn and ex:
            mats[pn] = ex.replace("^", "**")

    # f_loc 本身不是待展开的中间量
    mats.pop("f_loc", None)

    if "solute_mobility" in s:
        sm = block(s, "solute_mobility")
        m_expr = get_param(sm, "expression")
        mcn = get_param(sm, "constant_names").split()
        mce = [float(x) for x in get_param(sm, "constant_expressions").split()]
        mconst = dict(zip(mcn, mce))
        M, m_e = make_eval(m_expr, mconst, mats)
        layered = True
        print(f"  M      : 分层（常数 {mconst}）")
        print(f"  中间材料: {sorted(mats)}")
    else:
        cp = block(s, "ch_params")
        pn = get_param(cp, "prop_names").split()
        pv = [float(x) for x in get_param(cp, "prop_values").split()]
        mconst = dict(zip(pn, pv))
        M = lambda **_kw: mconst["M"]  # noqa: E731
        layered = False
        print(f"  M      : 常数 {mconst['M']:g}（未分层）")

    # ---- 三种状态 ----
    def state(name, etas):
        v = {n: 0.0 for n in ns}
        v.update(etas)
        return name, v

    STATES = [
        state("液相      (Σ η² = 0)  ", {}),
        state("晶粒内    (Σ η² = 1)  ", {"gr0": 1.0}),
        state("固固晶界  (η₀=η₁=0.5) ", {"gr0": 0.5, "gr1": 0.5}),
        # ⚠ 这一态是**回归守卫**：第一版草稿的 h_gb = 4S(1−S) 在这里会误判成
        #   晶界（因为 Ση²=0.25 附近它也非零），把 D_GB 错误地加到固液界面上。
        #   固液界面只有 1 个 η 非零 ⇒ h_gb 必须严格为 0。
        state("固液界面  (η₀=0.5)    ", {"gr0": 0.5}),
    ]

    c = fconst.get("c0", 0.036)
    # f_loc 是 c 的**二次多项式** ⇒ 二阶中心差分对任意 h 都精确，
    # 误差只来自浮点消去（~1e-16·|f|/h²）。h 取 1e-6 时相对误差约 1e-8，
    # 会被误判成"不达标"；取 1e-3 把它压到 1e-13 以下。
    h = 1e-3

    print()
    print(f"{'状态':<26} {'Ση²':>6} {'f_cc':>12} {'M':>14} {'D = M·f_cc':>14}")
    print("-" * 78)
    rows = []
    for name, v in STATES:
        S = sum(v[n] ** 2 for n in ns)
        fcc = (f_loc(c=c + h, **v) - 2 * f_loc(c=c, **v) + f_loc(c=c - h, **v)) / h**2
        m = M(**v)
        d = m * fcc
        rows.append((name, S, fcc, m, d))
        print(f"{name:<26} {S:>6.2f} {fcc:>12.6f} {m:>14.6e} {d:>14.6e}")

    print()
    if "h_gb" in mats:
        hgb, _ = make_eval(mats["h_gb"], {}, mats)
        print("晶界指示 h_gb 的三态核对（固液界面必须严格为 0）：")
        want_hgb = [0.0, 0.0, 1.0, 0.0]
        okh = True
        for (name, S, fcc, m, d), (_sn, sv), want in zip(rows, STATES, want_hgb):
            got = hgb(**sv)
            flag = "OK " if abs(got - want) < 1e-12 else "失败"
            okh &= abs(got - want) < 1e-12
            print(f"  [{flag}] {name:<24} h_gb = {got:12.8f}   期望 {want}")
        if not okh:
            sys.exit("失败：h_gb 指示函数在某个状态上不等于期望值"
                     "（固液界面非零 = 会把 D_GB 错误地加到固液界面上）")
        print()

    if layered:
        exp = [args.dl, args.ds, args.dgb]
        if any(e is None for e in exp):
            print("（未给 --dl/--ds/--dgb，跳过判据）")
            return
        names = ["液相 D_L", "固相 D_S", "晶界 D_GB"]
        ok = True
        for (name, S, fcc, m, d), want, wn in zip(rows, exp, names):
            rel = abs(d - want) / abs(want)
            flag = "OK " if rel < 1e-10 else "失败"
            ok &= rel < 1e-10
            print(f"  [{flag}] {wn:<10} 期望 {want:.6e}  实得 {d:.6e}  相对偏差 {rel:.2e}")
        if not ok:
            sys.exit("T6 失败：D = M·f_cc 与输入的 D_L/D_S/D_GB 不一致")
        print("  ⇒ T6 通过：D = M·∂²f/∂c² 在三态逐点等于输入定义")
    else:
        ds, dl = rows[1][4], rows[0][4]
        print(f"  旧模型：D_固/D_液 = {ds/dl:.4f}")
        print(f"          D_液={dl:.4e}  D_固={ds:.4e}  D_晶界={rows[2][4]:.4e}")
        if ds > dl:
            print("  ⚠ **物理上反了**：固相扩散比液相快 —— 审计 P0-4 / 本报告 P22")

    # =====================================================================
    # 沿二元晶界剖面扫一遍 D(x)
    # =====================================================================
    # 【为什么必须做这一步】
    #   上面那张表只看了**三个孤立状态**（液相 / 晶粒内 / 晶界中点），
    #   它们全都"通过"了 —— 而实现里仍然可能有严重缺陷。
    #   实测抓到过一次：h_solid = S + h_gb(1−S) 在三态上全对，
    #   但在**晶界两翼**把液相项漏进固相，导致
    #       (a) 固相里 D 比 D_S 大 2.6~584 倍；
    #       (b) **D 的最大值不在晶界中心，而在两侧翼上**（6.26e-10 > 4.00e-10）。
    #   三态表完全看不出这两条。所以必须扫**连续剖面**。
    #
    #   判据（两条，都很直观）：
    #     ① D 的最大值应当出现在**晶界中心**（而不是两翼）；
    #     ② 远离晶界处 D 应当等于 D_S。
    if layered and "h_gb" in mats:
        hgb_fn, _ = make_eval(mats["h_gb"], {}, mats)
        c0v = fconst.get("c0", 0.036)
        h = 1e-3
        xg, wg, L = 2.0e-6, 0.4e-6, 4.0e-6
        print()
        print("沿二元晶界剖面扫 D(x)（GB 在 2.0 µm，w_gb = 0.4 µm）：")
        print(f"{'x (µm)':>8} {'eta0':>9} {'S':>9} {'h_gb':>8} {'D (m²/s)':>13} {'D/D_S':>9}")
        print("-" * 62)
        prof = []
        for i in range(41):
            x = L * i / 40.0
            th = math.tanh((x - xg) / wg)
            e0, e1 = 0.5 * (1 - th), 0.5 * (1 + th)
            v = {n: 0.0 for n in ns}
            v["gr0"], v["gr1"] = e0, e1
            S = e0 ** 2 + e1 ** 2
            fcc = (f_loc(c=c0v + h, **v) - 2 * f_loc(c=c0v, **v)
                   + f_loc(c=c0v - h, **v)) / h ** 2
            d = M(**v) * fcc
            hg = hgb_fn(**v)
            prof.append((x, e0, S, hg, d))
            if i % 4 == 0:
                print(f"{x*1e6:>8.3f} {e0:>9.5f} {S:>9.5f} {hg:>8.4f} "
                      f"{d:>13.5e} {d/args.ds:>9.2f}")
        xmax = max(prof, key=lambda r: r[4])[0]
        d_far = prof[0][4]
        ok_pos = abs(xmax - xg) < 0.15e-6
        ok_grain = abs(d_far - args.ds) / args.ds < 0.02
        print()
        print(f"  [{'OK ' if ok_pos else '失败'}] D 的极大值在 x = {xmax*1e6:.3f} µm "
              f"（晶界在 {xg*1e6:.3f} µm）")
        print(f"  [{'OK ' if ok_grain else '失败'}] 远离晶界处 D = {d_far:.4e}"
              f"，期望 D_S = {args.ds:.4e}（偏差 {abs(d_far-args.ds)/args.ds*100:.2f}%）")
        if not (ok_pos and ok_grain):
            sys.exit("剖面判据失败：D(x) 的形状不对。"
                     "常见根因是 h_solid 在晶界处没有饱和到 1，"
                     "导致 (1−h_solid) 的尾巴把 D_L 泄漏进固相。")


if __name__ == "__main__":
    main()
