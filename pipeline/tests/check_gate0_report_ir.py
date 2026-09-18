#!/usr/bin/env python3
# =============================================================================
# 验证 gate0_report.py 里改过的「界面分辨率 / mu0 自洽」代码路径
# =============================================================================
# 背景：④ 修复把 [Materials]/barrier_mu 拆成了 [barrier_muT]（存 mu_T）
#      与 [mu_barrier_const]（存常数 mu0）。gate0_report.py 的块名扫描用的是
#      `ln.strip() == "[name]"` **精确匹配**，名字对不上会静默返回空串、
#      整段诊断被 except 吞掉 —— 所以必须单独测这一条路径。
#
# 用法: python3 tests/check_gate0_report_ir.py <含 N.i 的目录>
# =============================================================================
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gate0_report as G  # noqa: E402


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    f = os.path.join(d, "N.i")
    if not os.path.exists(f):
        sys.exit("找不到 %s" % f)

    # 找到那个函数（名字可能变，按签名找）
    fn = None
    for name in dir(G):
        if "interface" in name.lower() and callable(getattr(G, name)):
            fn = getattr(G, name)
            break
    if fn is None:
        sys.exit("gate0_report 里找不到 interface_* 函数；现有公开名：%s"
                 % [n for n in dir(G) if not n.startswith("_")])

    print("调用 %s(%r)" % (fn.__name__, d))
    r = fn(d)
    if r is None:
        sys.exit("返回 None —— 说明块名没匹配上（正是本次要防的静默失败）")
    for k in sorted(r):
        print("  %-22s %s" % (k, r[k]))
    assert r["mu0"] == 900000.0, r["mu0"]
    assert r["mu0_consistent"] is True, r
    print("\n✅ 通过：块名匹配正确，mu0 三处一致")


if __name__ == "__main__":
    main()
