#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_apply.py —— **B2 的代码改动**（5 处，最小化，原子性）。

## 纪律（`B2-D1..D7`）
* **只改这 5 处**（`B2-D7` 单变量）；
* 新参数**默认 = 现状**（`pre`）⇒ 关闭时归档路径逐位不变（`B2-D2`）；
* **锚点用"唯一子串"匹配**，缩进**从实际行取**（不手抄空白 —— `R694` 的教训）；
* 任一锚点不唯一/未命中 ⇒ **整体放弃**（原子性，不写半个文件）;
* 写入前自动存 `.b2orig` 备份。

## 用法
  `_b2_apply.py --dry`   只验证锚点
  `_b2_apply.py --apply` 真正写入
"""
import os
import shutil
import sys

FW = "/mnt/f/speed_up/pipeline/ca_pf_framework"
SURF = os.path.join(FW, "windowB_surface.py")
EXP = os.path.join(FW, "_bk_exp.py")
DRY = "--apply" not in sys.argv

# 每处：(文件, 唯一子串, 出现次数必须=, 'after'|'replace', 新行模板（{ I } = 该行缩进）)
EDITS = [
    # ---- 改动 1/5：advance() 签名加参数 ----
    (SURF, "mob_iform='exp2', mob_ratio=9.0, el_scale=1.0, facet_proj=0,", 1, 'after',
     ["{I}facet_proj_order='pre',   # * B2 (default pre = current: project at step head)"]),

    # ---- 改动 2/5：步首加 order 条件 ----
    #   ⛔ 第一版用 'replace' 直接换掉 `if facet_proj and int(facet_proj) > 0:` 那一行
    #      ⇒ **IndentationError**（原 `if` 下面的缩进体还在 ⇒ "if 后无缩进块"）。
    #   ✅ 正确做法：**在它之前插入一条守卫**，用 `if False:` 包住整段（缩进不变）：
    #        if facet_proj_order == 'post':      # post 模式下不在步首投影
    #            facet_proj = 0                  # 让原 `if facet_proj ...` 恒假
    (SURF, "if facet_proj and int(facet_proj) > 0:", 1, 'before',
     ["{I}# * B2: in 'post' mode we do NOT project at the step head; instead we",
      "{I}#   force the original guard below to be false, so the whole original",
      "{I}#   block (indentation untouched) is skipped. Default 'pre' => no-op.",
      "{I}if str(facet_proj_order) == 'post':",
      "{I}    facet_proj = 0"]),

    # ---- 改动 3/5：步尾加 post 投影段 ----
    #   ⚠ `_r576_res = ...` 在 `advance()` 里有**两处**（两条返回路径）：
    #     :4549 是 `per_field=True` 的特化路径；:5558 是主路径。
    #     两处都要加（否则 `per_field` 用户拿到不一致行为）⇒ 用 'after_both'。
    (SURF, "_r576_res = self._finish_advance(reg0, dt)", 2, 'after_both',
     ["{I}# ***** B2 (user 2026-10-07 approved, plan R693): move the geometric",
      "{I}#   constraint to the END of the step (reverse the causal direction).",
      "{I}#   Why: projecting at the step head makes the physics run on an",
      "{I}#     already-rewritten shape => kinetics changed by 2.27x (R674).",
      "{I}#   Now: physics runs on the REAL shape; geometry only keeps facets flat.",
      "{I}#   Default 'pre' => this block never runs => archive path bit-identical.",
      "{I}if (facet_proj and int(facet_proj) > 0",
      "{I}        and str(facet_proj_order) == 'post'",
      "{I}        and int(getattr(self, '_fp_cnt', 0)) % int(facet_proj) == 0):",
      "{I}    self.facet_project()"]),

    # ---- 改动 4/5：_bk_exp.py 新 CLI ----
    #   ⛔ 两版锚点都错：① 用 `ap.add_argument(...` 首行 ⇒ 插进调用中间（SyntaxError）；
    #      ② 用 `help=...')` 那行 ⇒ 它是**续行**（缩进 20）⇒ 新语句被缩进 20 ⇒ IndentationError。
    #   ✅ 用**该语句的结束行 `')'`**（缩进 = 语句级 4 空格）作锚点。
    (EXP, "help='每多少步做一次面片投影；0 = 关（默认）')", 1, 'after_at_base',
     ["{I}# ***** B2 (user 2026-10-07 approved): causal direction of facet projection.",
      "{I}#   'pre'  = project at the step head (DEFAULT = current behaviour).",
      "{I}#   'post' = project at the step tail (B2: physics first, geometry after).",
      "{I}#   Default 'pre' => archive path bit-identical (_r30_regress.sh gates it).",
      "{I}#   NOTE: argparse does `help %% params`, so a literal percent must be escaped.",
      "{I}ap.add_argument('--facet-proj-order', default='pre', choices=('pre', 'post'),",
      "{I}                help='facet projection causal direction: pre=head (default), '",
      "{I}                     + 'post=tail (physics first, then geometry; B2). '",
      "{I}                     + 'Has no effect when --facet-proj is 0.')"]),

    # ---- 改动 5/5：_bk_exp.py kwargs ----
    (EXP, "facet_proj=int(a.facet_proj),", 1, 'after',
     ["{I}facet_proj_order=str(a.facet_proj_order),   # * B2 (default pre = current)"]),
]


def indent_of(line):
    return line[:len(line) - len(line.lstrip())]


def main():
    print("=" * 100)
    print("B2 改动（%d 处）—— %s" % (len(EDITS), "DRY-RUN" if DRY else "**APPLY**"))
    print("=" * 100)
    files = {}
    plan = []          # (path, idx, where, expanded_lines)
    for path, sub, want, where, tmpl in EDITS:
        if path not in files:
            with open(path, encoding="utf-8", newline="") as fh:
                files[path] = fh.read().split("\n")
        lines = files[path]
        hits = [i for i, l in enumerate(lines) if sub in l]
        if len(hits) != want:
            print("  ⛔ %-20s 锚点命中 %d 处（要求 %d）：%s"
                  % (os.path.basename(path), len(hits), want, sub[:56]))
            return 2
        idxs = hits if where == 'after_both' else [hits[0]]
        for idx in idxs:
            if where == 'after_at_base':
                # ★ 锚点是**缩进很深的续行**（如 `help=...')`）⇒ 新语句必须回到
                #   **语句级缩进**（= 从当前行往上找第一条缩进更浅的行）—— `R694` 记账。
                base = None
                for j in range(idx, -1, -1):
                    lj = lines[j]
                    if lj.strip() and len(indent_of(lj)) < len(indent_of(lines[idx])):
                        base = indent_of(lj)
                        break
                I = base if base is not None else indent_of(lines[idx])
            else:
                I = indent_of(lines[idx])
            exp = [t.replace('{I}', I) for t in tmpl]
            plan.append((path, idx, 'before' if where == 'before' else 'after', exp))
            print("  ✅ %-20s :%-5d 缩进=%d空格  %-6s %s"
                  % (os.path.basename(path), idx + 1, len(I),
                     'before' if where == 'before' else 'after', sub[:44]))
    if DRY:
        print("\n  ⇒ DRY-RUN 通过：5 处锚点全部按要求命中。加 `--apply` 才写入。")
        return 0
    # 从后往前插（避免行号漂移）
    #   ⛔ bug 记账（`R694`）：第一版把 `'before'` 也当 `'after'` 处理
    #      ⇒ **误删了原 `if facet_proj and int(facet_proj) > 0:` 那一行**
    #      ⇒ 原 `if` 的缩进体变成无条件执行 ⇒ **`facet_proj=0` 时也会投影**（破坏归档）。
    #   ✅ 修法：`before` 必须**插入到 idx 之前且保留该行**。
    for path, idx, where, exp in sorted(plan, key=lambda p: -p[1]):
        lines = files[path]
        if where == 'before':
            lines[idx:idx] = exp          # ← 保留原行（不删）
        else:
            lines[idx + 1:idx + 1] = exp
    for path, txt in files.items():
        bak = path + ".b2orig"
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
            print("  已备份 → %s" % os.path.basename(bak))
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("\n".join(txt))
        print("  已写入 %s" % os.path.basename(path))
    print("\n  ⇒ 完成。请跑 `git diff` 逐行核对（`B2-D7`）。")
    return 0


sys.exit(main())
