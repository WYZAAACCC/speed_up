#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_param_audit2.py --- ★ 参数出处总账 v2（修 argv 提取 + 补扫 *.py）

## v1 的缺陷（自查所得，先修量具再谈结论）
* **argv 提取返回 0 字符**：匹配条件是 `"--tag %s " % TAG`（要求尾随空格），
  在 `/proc/<pid>/cmdline` 里 tag 之后可能是 `\\0`（末尾）或别的顺序 ⇒ **匹配失败**。
  ⇒ 改为：**按 NUL 切分**再用集合判断，兼容任意顺序。
* **只扫了 `*.md`**：出处可能写在 `*.py` 注释里 ⇒ 补扫。
* **只报"有没有命中"**：没区分出处**类型** ⇒ v2 报**最强级别**：
  `文献/DOI` > `推导` > `实测` > `标定` > 无。
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = os.environ.get("TAG", "t10PRT2")

PARAMS = {
    "ed-eta": "弹性驱动的塑性折减因子 η",
    "eng-elong": "板条长宽比 elong", "eng-r-nm": "籽晶半径 R",
    "plate-L": "籽晶长 L", "plate-W": "籽晶宽 W", "plate-T": "籽晶厚 T",
    "overlap-nm": "籽晶咬入深度", "nuc-overlap-nm": "形核咬入深度",
    "alpha-km": "KM 分数律系数 α",
    "M_S_TI64": "马氏体开始温度 Ms", "T0_TI64": "T0 温度",
    "DS_REF": "参考扩散系数", "C11": "弹性常数 C11", "C12": "C12", "C44": "C44",
    "gamma": "界面能 γ", "mob": "相场迁移率 M",
    "nvar": "变体数", "m": "每变体场数", "B": "每块板条数", "dx-nm": "网格步长",
    "sigma_y": "母相屈服强度 σ_y",
}
LV = {"文献": 4, "DOI": 4, "doi": 4, "推导": 3, "实测": 2, "measure": 2,
      "标定": 1, "calibrat": 1, "来源": 2, "出处": 2, "引自": 3, "依据": 2}

# ── 1) argv：按 NUL 切分，集合判断（修 v1 的匹配失败）──
argv = []
for P in os.listdir("/proc"):
    if not P.isdigit():
        continue
    try:
        raw = open("/proc/%s/cmdline" % P, "rb").read().decode("utf-8", "replace")
    except Exception:
        continue
    if "bk_exp.py" not in raw:
        continue
    toks = [t for t in raw.split("\0") if t]
    if TAG in toks:
        argv = toks
        break
print("══ 参数出处总账 v2  tag=%s ══" % TAG)
print("  ★ argv 提取：token 数 = %d %s" % (len(argv), "✓" if argv else "❌ 仍失败"))
cli = {}
for i, t in enumerate(argv):
    if t.startswith("--") and i + 1 < len(argv) and not argv[i + 1].startswith("--"):
        cli[t[2:]] = argv[i + 1]
print("  argv 显式参数 = %d 个" % len(cli))
for k in sorted(cli):
    print("    --%-20s = %s" % (k, cli[k]))

# ── 2) 收集文本：*.md + *.py ──
texts = {}
# ★ 修（本会话第 14 次自查）：自污染的范围比第一版以为的**广**。
#   第一次只排除 `_t10_param_audit*.py`，结果扫描器又在
#   `_t10_prov_ctx.py`（含 TARGETS + KEY 表）与 `_t10_nvar_derive.py` 里
#   "找到"了 `mob` / `nvar` 的出处 ⇒ **假阳性换了个文件继续出现**。
#   ⇒ 规则：**排除全部会话工具脚本**（`_t10_*.py` / `_t10_*.sh`），
#     因为这类脚本天生同时含"参数名"与"出处关键词"。
def _is_instrument(fn):
    return fn.startswith("_t10_") or fn in ("_t5_patch_seeddbg.py",)

for fn in os.listdir(HERE):
    if _is_instrument(fn):
        continue
    if fn.endswith(".md") or fn.endswith(".py"):
        try:
            p = os.path.join(HERE, fn)
            if os.path.getsize(p) > 4_000_000:
                continue
            _t = open(p, encoding="utf-8", errors="replace").read()
            if "__SELFTEST_KEYWORDS__" in _t:
                continue
            texts[fn] = _t
        except Exception:
            pass
print("\n  扫描文本：%d 个（*.md + *.py，**已排除全部会话工具脚本**）" % len(texts))

def best(pname):
    """返回 (最强级别名, 证据串)

    ★ 修（本会话第 13 次自查）：v2 首版用 `re.escape(pname)` 做**子串**匹配
      ⇒ `mob` 命中 `_prodmob_mid60` / `mob_beta` / `mobility` 等**巧合子串**，
      把"无出处"错判成"文献/DOI"（假阳性）。
      ⇒ 改用**词边界**：参数名两侧不得紧邻字母/数字/下划线。
      正对照：`sigma_y` 应仍为"无出处"、`DS_REF` 应仍为"文献/DOI"（已读原文确认）。
    """
    pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(pname) + r"(?![A-Za-z0-9_])")
    bi, ev = 0, []
    for fn, txt in texts.items():
        for m in pat.finditer(txt):
            seg = txt[max(0, m.start() - 300): m.start() + 300]
            for kw, lv in LV.items():
                if kw in seg and lv > bi:
                    bi = lv
                    ev = ["%s:%s" % (fn, kw)]
                elif kw in seg and lv == bi and len(ev) < 3:
                    ev.append("%s:%s" % (fn, kw))
    name = {4: "文献/DOI", 3: "推导", 2: "实测/来源", 1: "**仅标定**", 0: "❌ **无出处**"}[bi]
    return bi, name, "；".join(sorted(set(ev))[:3])

rows = []
for p, desc in PARAMS.items():
    bi, name, ev = best(p)
    rows.append((bi, p, desc, name, ev))
rows.sort(key=lambda r: r[0])          # 最弱的排前面 ⇒ 先处理
print("\n  ★ 按出处强度升序（最弱的在最前，即新规则要优先处理的）")
print("  %-14s %-26s %-12s %s" % ("参数", "说明", "最强出处", "证据"))
for bi, p, desc, name, ev in rows:
    print("  %-14s %-26s %-12s %s" % (p, desc, name, ev or "-"))
print("\n  ⚠ 仍只是筛查：命中的需读原文确认；未命中的也未必真无出处。")
