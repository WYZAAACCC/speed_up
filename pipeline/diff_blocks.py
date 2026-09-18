#!/usr/bin/env python3
"""
把 C 版与 D 版 .i 做结构化逐块对比。

动机：核 bug（缺 TimeDerivative / v 含自己 / 缺 variable_L）是"藏在明处"的那类
问题 —— 我靠症状反推找了好几轮才找到。正确做法是**系统地把两个文件的结构差异
列出来**，逐条判断哪些是"有意为之"（材料换成各向异性），哪些是"意外丢失"。

用法： python3 diff_blocks.py stage1_meltpool_c.i stage1_meltpool_d.i
"""

import re
import sys
from collections import OrderedDict


def parse_blocks(text):
    """
    返回 {顶层块名: {子块名: 参数dict}}，以及顶层的裸参数。
    只处理两层，够用。
    """
    tops = OrderedDict()
    cur_top = None
    cur_sub = None
    for raw in text.splitlines():
        line = raw.split("#")[0].rstrip() if raw.lstrip().startswith("#") else raw.rstrip()
        if not line.strip():
            continue
        s = line.strip()
        # 顶层块开始
        m = re.match(r"^\[([A-Za-z_][\w/]*)\]$", s)
        if m and not line.startswith(" "):
            cur_top = m.group(1)
            tops.setdefault(cur_top, OrderedDict())
            cur_sub = None
            continue
        if s == "[]":
            if cur_sub is not None:
                cur_sub = None
            else:
                cur_top = None
            continue
        # 子块开始
        m = re.match(r"^\[([A-Za-z_][\w/]*)\]$", s)
        if m and line.startswith(" ") and cur_top:
            cur_sub = m.group(1)
            tops[cur_top].setdefault(cur_sub, {})
            continue
        # 参数
        if "=" in s:
            k, v = s.split("=", 1)
            k, v = k.strip(), v.strip()
            if cur_sub is not None and cur_top:
                tops[cur_top][cur_sub][k] = v
            elif cur_top:
                tops[cur_top].setdefault("__params__", {})[k] = v
    return tops


# 这些顶层块**本来就该不同**：D 版把材料换成各向异性、加了梯度辅助变量、
# 删了 Modules（改为显式核）。其余一律要逐条核对。
EXPECTED_DIFF = {
    "Materials", "Functions", "AuxVariables", "AuxKernels", "Modules", "Kernels",
    "Postprocessors",
}


def pa_or_pb_differs(ta, tb):
    """两个顶层块的顶层裸参数或任一子块参数是否有差异。"""
    if ta.get("__params__", {}) != tb.get("__params__", {}):
        return True
    for sub in set(ta) & set(tb):
        if sub == "__params__":
            continue
        if ta[sub] != tb[sub]:
            return True
    return False


def main():
    fa, fb = sys.argv[1], sys.argv[2]
    A = parse_blocks(open(fa, encoding="utf-8").read())
    B = parse_blocks(open(fb, encoding="utf-8").read())

    print("=" * 78)
    print(f"A = {fa}")
    print(f"B = {fb}")
    print("=" * 78)

    print("\n--- 顶层块清单 ---")
    only_a = [k for k in A if k not in B]
    only_b = [k for k in B if k not in A]
    print(f"  相同: {[k for k in A if k in B]}")
    if only_a:
        print(f"  **只在 A: {only_a}")
    if only_b:
        print(f"  **只在 B: {only_b}")

    for top in A:
        if top not in B:
            continue
        subs_a, subs_b = set(A[top]), set(B[top])
        sa = {k for k in subs_a if k != "__params__"}
        sb = {k for k in subs_b if k != "__params__"}
        # 【坑】不要用 `if sa != sb or top in EXPECTED_DIFF` 做闸门 ——
        # 那样会**整块跳过子块同名的块**（Mesh/GlobalParams/Variables/ICs/
        # UserObjects/Preconditioning/Executioner 都是这种），
        # 它们的参数差异就全漏了。实测漏掉了 Outputs/exo 的 file_base。
        # 正确做法：无条件比较，只把"哪些差异可接受"留给人判断。
        interesting = sa != sb or (pa_or_pb_differs(A[top], B[top]))
        if interesting:
            flag = "" if top in EXPECTED_DIFF else "   <== 不在预期差异清单里，逐条核对！"
            print(f"\n--- [{top}] {flag}")
            if sa - sb:
                print(f"    只在 A: {sorted(sa - sb)}")
            if sb - sa:
                print(f"    只在 B: {sorted(sb - sa)}")
            # 同名子块的参数差异 —— 无条件比较
            for sub in sorted(sa & sb):
                pa, pb = A[top][sub], B[top][sub]
                keys = set(pa) | set(pb)
                d = [(k, pa.get(k), pb.get(k)) for k in sorted(keys)
                     if pa.get(k) != pb.get(k)]
                if d:
                    print(f"    [{sub}] 参数差异:")
                    for k, va, vb in d:
                        print(f"      {k}:\n        A: {(va or '')[:88]}\n        B: {(vb or '')[:88]}")
        # 顶层裸参数
        pa = A[top].get("__params__", {})
        pb = B[top].get("__params__", {})
        if pa or pb:
            d = [(k, pa.get(k), pb.get(k)) for k in sorted(set(pa) | set(pb))
                 if pa.get(k) != pb.get(k)]
            if d:
                flag = "" if top in EXPECTED_DIFF else "   <== 注意"
                print(f"\n--- [{top}] 顶层参数差异{flag}")
                for k, va, vb in d:
                    print(f"      {k}: A={va}  B={vb}")


if __name__ == "__main__":
    main()
