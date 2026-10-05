#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_param_audit.py --- ★ 参数出处总账（按新规则：文献 → 推导 → 标定）

做法：
 1) 从**正在跑的算例的 argv**（/proc）取出所有显式参数；
 2) 从引擎/启动器的 argparse 默认值补全物理参数；
 3) 对每个参数名，在仓库的 R*.md 文档里 grep，看有没有**出处标注**
    （关键词：文献/DOI/推导/标定/实测/来源/出处/引自/依据）；
 4) 分类输出：✅有出处 / ⚠️仅推导 / ❌无出处（需按新规则处理）。

⚠ 局限（必须记）：grep 命中≠出处可靠；这只是**筛查**，命中的仍需人工读原文确认。
"""
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = os.environ.get("TAG", "t10PRT2")

# 需要审计的物理参数（名字 → 说明）
PARAMS = {
    "ed-eta": "弹性驱动的塑性折减因子 η",
    "eng-elong": "板条长宽比 elong",
    "eng-r-nm": "籽晶半径 R",
    "plate-L": "籽晶长 L", "plate-W": "籽晶宽 W", "plate-T": "籽晶厚 T",
    "overlap-nm": "籽晶咬入深度",
    "nuc-overlap-nm": "形核咬入深度",
    "alpha-km": "KM 分数律系数 α",
    "M_S": "马氏体开始温度 Ms",
    "T0": "T0 温度",
    "DS_REF": "参考扩散系数",
    "C11": "弹性常数 C11", "C12": "C12", "C44": "C44",
    "gamma": "界面能 γ",
    "mob": "相场迁移率 M",
    "nvar": "变体数", "m": "每变体场数", "B": "每块板条数",
    "dx-nm": "网格步长",
}
KEYS = ("文献", "DOI", "doi", "推导", "标定", "实测", "来源", "出处", "引自",
        "依据", "reference", "literature", "R-", "R1", "R2", "R4", "R5", "R6")

# 1) 取 argv
argv = ""
for P in os.listdir("/proc"):
    if not P.isdigit():
        continue
    try:
        with open("/proc/%s/cmdline" % P, "rb") as fh:
            c = fh.read().decode("utf-8", "replace")
    except Exception:
        continue
    if "bk_exp.py" in c and ("--tag %s " % TAG) in c:
        argv = c.replace("\0", " ")
        break
print("══ 参数出处总账  tag=%s ══" % TAG)
print("  argv 长度 = %d 字符" % len(argv))
cli = dict(re.findall(r"--([A-Za-z0-9\-]+)\s+([^\s]+)", argv))
print("  argv 里显式给出的参数 = %d 个" % len(cli))
for k in sorted(cli):
    print("    --%-22s = %s" % (k, cli[k]))
print()

# 2) 收集文档
docs = [f for f in os.listdir(HERE) if f.endswith(".md")]
print("  文档数 = %d（R*.md 等）" % len(docs))
blob = {}
for d in docs:
    try:
        with open(os.path.join(HERE, d), "r", encoding="utf-8", errors="replace") as fh:
            blob[d] = fh.read()
    except Exception:
        pass

# 3) 逐个参数查出处
print()
print("  %-18s %-34s %s" % ("参数", "说明", "出处线索（命中的文档:关键词）"))
for p, desc in PARAMS.items():
    hits = []
    for d, txt in blob.items():
        for kw in KEYS:
            # 参数名附近 200 字符内出现出处关键词
            for m in re.finditer(re.escape(p), txt):
                seg = txt[max(0, m.start() - 250): m.start() + 250]
                if kw in seg:
                    hits.append("%s:%s" % (d, kw))
                    break
            else:
                continue
            break
    uniq = sorted(set(hits))[:3]
    print("  %-18s %-34s %s"
          % (p, desc, ("；".join(uniq) if uniq else "❌ **未找到出处线索**")))
print()
print("  ⚠ 局限：grep 命中 ≠ 出处可靠；本表只做筛查，命中的仍需读原文确认。")
print("  ⚠ 未命中的也未必真无出处（可能写在代码注释里，而非 .md）——")
print("     需要时再对 *.py 做同样的筛查。")
