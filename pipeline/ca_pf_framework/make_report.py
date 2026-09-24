#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 verify_framework.py 的原始输出整理成 VERIFY_REPORT.md
用法: python make_report.py    (需先跑 verify_framework.py)"""
import io, os, json

BT = chr(96)
here = os.path.dirname(os.path.abspath(__file__))
raw = io.open(os.path.join(here, "_raw_output.txt"), encoding="utf-8").read()
raw_thermal = ""
tp = os.path.join(here, "_raw_thermal.txt")
if os.path.exists(tp):
    raw_thermal = io.open(tp, encoding="utf-8").read()
rows = json.load(io.open(os.path.join(here, "verify_results.json"), encoding="utf-8"))
cnt = {}
for r in rows:
    cnt[r["verdict"]] = cnt.get(r["verdict"], 0) + 1

def block(v):
    out = ["- **{}** :: {}".format(r["name"], r["detail"]) for r in rows if r["verdict"] == v]
    return "\n".join(out) if out else "(无)"

fence = BT * 3
hdr = "\n".join([
 "# 数学框架自检报告", "",
 "> 由 @@verify_framework.py@@ 自动生成。判据、阈值、参数来源全部写在脚本里，本报告只是快照。",
 "> 复跑：",
 "> @@/root/miniconda3/envs/ml/bin/python verify_framework.py@@",
 "> @@/root/miniconda3/envs/ml/bin/python make_report.py@@", "",
 "读法：",
 "- **PASS** = 已验证成立（有数值证据）",
 "- **WARN** = 有前提或数据缺口，结论只在给定前提下成立",
 "- **FAIL** = 当前框架或参数不一致/不足，**必须处理**",
 "- **RULE** = 设计禁令（必须遵守的写法），不是缺陷", "",
 "## 判定汇总", "",
 "共 **{total}** 项：PASS {p} / WARN {w} / FAIL {f} / RULE {ru}".format(
     total=len(rows), p=cnt.get("PASS", 0), w=cnt.get("WARN", 0),
     f=cnt.get("FAIL", 0), ru=cnt.get("RULE", 0)), "",
 "### FAIL（必须处理）", "", block("FAIL"), "",
 "### WARN（有前提）", "", block("WARN"), "",
 "### RULE（设计禁令）", "", block("RULE"), "",
 "---", "", "## 附 A：verify_framework.py 完整输出", "", fence, raw, fence, "",
 "## 附 B：thermal_layer.py 完整输出（L1-T 层，D3 的交付证据）", "", fence, raw_thermal, fence, ""])

hdr = hdr.replace("@@", BT)
io.open(os.path.join(here, "VERIFY_REPORT.md"), "w", encoding="utf-8").write(hdr)
print("VERIFY_REPORT.md 写入完成;", len(rows), "项判据,", len(hdr), "bytes")
