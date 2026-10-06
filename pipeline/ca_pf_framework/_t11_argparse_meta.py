#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_argparse_meta.py —— 从 `_bk_exp.py` 的 `main()` **源码**里派生 argparse 元信息。

## 为什么要它（我这一轮犯的错的根因）
  `_t11_prod_cmd.py` 第一版**手抄参数键清单** ⇒ 漏了 `burst_km`
  ⇒ 生产跑档目标被钉死在 9（见 `R623 §16.1`）。
  改全量透传后**又踩第二个坑**：`--ckpt-dir`/`--resume` 的值是**空串**，
  空串会被 argparse 当成"没给值" ⇒ **吞掉后面的 token**
  ⇒ `error: unrecognized arguments: 0 0 0 1 0 0 0 1 0 0 0`（退出码 2）。
  另外 `store_true` 型开关**不能带值**。

## 做法
  用 `ast` 解析 `_bk_exp.py`，在 `main()` 里找 `add_argument` 调用，抽出
  **选项名 → (是否开关, 是否可选值, 类型)**。
  ⚠ 用 AST 而不是正则：`add_argument` 的参数里有跨行的长帮助文本，正则容易错。
"""
import ast
import json
import sys

SRC = "_bk_exp.py"


def build_meta(src=SRC):
    tree = ast.parse(open(src, encoding="utf-8").read())
    # 找 main()
    main = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            main = node
            break
    if main is None:
        sys.exit("**找不到 main()**")
    meta = {}
    for node in ast.walk(main):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"):
            continue
        opts = [a.value for a in node.args
                if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if not opts:
            continue
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        # 是否开关（store_true/store_false 不带值）
        is_flag = False
        act = kw.get("action")
        if isinstance(act, ast.Constant) and act.value in ("store_true",
                                                           "store_false"):
            is_flag = True
        # nargs
        nargs = None
        if isinstance(kw.get("nargs"), ast.Constant):
            nargs = kw["nargs"].value
        # 长选项名（--xxx）
        longs = [o for o in opts if o.startswith("--")]
        if not longs:
            continue
        meta[longs[0].lstrip("-")] = dict(
            flag=is_flag, nargs=nargs,
            default=(kw["default"].value
                     if isinstance(kw.get("default"), ast.Constant) else None),
            aliases=opts)
    return meta


if __name__ == "__main__":
    m = build_meta()
    print(f"共 {len(m)} 个长选项")
    if len(sys.argv) > 1 and sys.argv[1] == "--flags":
        fl = sorted(k for k, v in m.items() if v["flag"])
        print(f"\n**开关型（store_true/store_false，不带值）共 {len(fl)} 个**：")
        for k in fl:
            print("   --%s" % k)
    if len(sys.argv) > 2 and sys.argv[2] == "--json":
        print(json.dumps(m, ensure_ascii=False))
