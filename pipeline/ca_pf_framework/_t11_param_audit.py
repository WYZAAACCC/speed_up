#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_param_audit.py —— ① 「文献 → 参数」映射表（自动生成 + 生效值对齐）。

做三件事：
  1. 从 `windowB_closure.param_table()` 取**代码自记的**出处/分级表（tier ∈ [借][推][标][数][实]）；
  2. 与算例 `meta.json` 的**生效值**逐条对齐（硬步骤 A：生效值才是权威）；
  3. 输出 `R618_PARAM_MAP.md`：每参数一行，**并把"必须去文献补的"单独列出来**。

用法: _t11_param_audit.py [tag1 tag2 ...]   （默认 dry_t10B9）
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import windowB_closure as CL  # noqa: E402

EXP = os.path.join(ROOT, "_exp", "_bk_t5")

# 参数名 → meta.json / exp_args 里的键（生效值口径）
ALIAS = {
    'gamma0 (F1, α′/β)': 'gamma0',
    'gamma0 (F2, 异变体)': 'gamma0',
    'df (引擎常数)': 'DF',
    'MOB': 'Mob',
    'cfl': None,
    'beta_h': 'beta_h',
    'beta_w': 'beta_w',
    'nv (场数)': 'nv',
    'q (冷速)': 'cool_rate',
    'eps0_v (×12)': None,
    'C (β-Ti cubic)': None,
    'R_nuc': 'eng_r_nm',
    't_nuc': 'eng_t_nm',
    'overlap': 'nuc_overlap_nm',
    'nuc cadence': 'eng_cadence',
    'elong': 'eng_elong',
    'alpha_KM': 'alpha_km',
    'Ms': None,
    'T0': None,
    'T_beta': None,
}

TIER_NOTE = {
    '借': '借来的文献值（**必须**带出处 + 误差带 + 敏感度）',
    '推': '由已锚定量推导',
    '标': '**标定/占位** —— 没有文献出处，靠反推或取值',
    '数': '数值/约定（非物理量）',
    '实': '实测',
}


def main() -> int:
    tags = sys.argv[1:] or ["dry_t10B9"]
    metas = {}
    for t in tags:
        p = os.path.join(EXP, t, "meta.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
            metas[t] = dict(d.get("exp_args", {}), **{k: v for k, v in d.items()
                                                      if not isinstance(v, (dict, list))})

    rows = CL.params()
    print(f"参数表 {len(rows)} 条；对齐算例 {list(metas)}")

    out = []
    out.append("# R618 —— 「文献 → 参数」映射表（自动生成）\n")
    out.append(f"生成工具：`_t11_param_audit.py`（解析 `windowB_closure.params()`）\n")
    out.append(f"生效值来源：**算例自己的 `meta.json` / `exp_args`**（硬步骤 A），"
               f"算例 = {', '.join(tags)}\n")
    out.append("\n分级含义：\n")
    for k, v in TIER_NOTE.items():
        out.append(f"- **[{k}]** {v}\n")
    out.append("\n> ⚠ **本表只做汇总与对齐，不做判定。** 标 [标] 的条目就是 ③ 要去文献补的清单。\n")

    out.append("\n## 1. 全表（含生效值对齐）\n\n")
    out.append("| 参数 | 代码值 | 单位 | 位置 | 作用 | 分级 | 生效值 | 出处/说明 |\n")
    out.append("|---|---|---|---|---|---|---|---|\n")
    n_match = n_mismatch = n_missing = 0
    for r in rows:
        key = ALIAS.get(r['name'], r['name'])
        eff = "—"
        if key and metas:
            for t, m in metas.items():
                if key in m:
                    eff = f"`{m[key]}`"
                    break
            if eff != "—":
                cv = r['value']
                try:
                    same = abs(float(cv) - float(eff.strip('`'))) < 1e-12 * max(1.0, abs(float(cv)))
                except Exception:  # noqa: BLE001
                    same = None
                if same is True:
                    n_match += 1
                elif same is False:
                    eff += " ⚠**不同**"
                    n_mismatch += 1
            else:
                n_missing += 1
        out.append(f"| `{r['name']}` | {r['value']} | {r['unit']} | `{r['where']}` | "
                   f"{r['role']} | **[{r['tier']}]** | {eff} | {r['source']} |\n")

    out.append(f"\n**对齐统计**：与生效值相同 {n_match} 条、**不同 {n_mismatch} 条**、"
               f"未在 meta 中出现 {n_missing} 条。\n")

    out.append("\n## 2. ★ ③ 的待办清单：所有 [标]（无文献出处）\n\n")
    biao = [r for r in rows if r['tier'] == '标']
    out.append(f"共 **{len(biao)}** 条 —— 这些就是「必须先查文献、查不到才推导、再不行才标定」的对象。\n\n")
    out.append("| 参数 | 代码值 | 位置 | 代码自记的出处现状 |\n|---|---|---|---|\n")
    for r in biao:
        out.append(f"| `{r['name']}` | {r['value']} | `{r['where']}` | {r['source']} |\n")

    out.append("\n## 3. [借] 的清单（有文献，但要核对**是不是同一个物理量**）\n\n")
    jie = [r for r in rows if r['tier'] == '借']
    out.append(f"共 **{len(jie)}** 条。\n\n")
    out.append("| 参数 | 代码值 | 单位 | 出处 |\n|---|---|---|---|\n")
    for r in jie:
        out.append(f"| `{r['name']}` | {r['value']} | {r['unit']} | {r['source']} |\n")

    out.append("\n## 4. `limitations()` 全文（必须随任何结论一起报）\n\n")
    for i, s in enumerate(CL.limitations(), 1):
        out.append(f"{i}. {s}\n")

    p = os.path.join(ROOT, "R618_PARAM_MAP.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("".join(out))
    print(f"写入 {p}")
    print(f"  分级统计: " + ", ".join(
        f"[{k}]={sum(1 for r in rows if r['tier']==k)}" for k in ('借', '推', '标', '数', '实')))
    print(f"  生效值对齐: 同={n_match} 异={n_mismatch} 未出现={n_missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
