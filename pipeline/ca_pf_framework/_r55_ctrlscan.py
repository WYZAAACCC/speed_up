#!/usr/bin/env python3
"""R55: **引擎有没有"各向异性速度律"的正对照？** —— 查仓库里所有对照脚本覆盖面。

`AGENTS.md §3` 教训 14：「设计验证算例前，先问**这个测试能不能看到目标现象**」。
现有对照（引擎注释里那条）验的是 **平界面 + 常数驱动 ⇒ `v/MΔf = 1.000`**
—— 那是**各向同性**的检验，**原理上看不到 `v_a/v_w`**。

本脚本搜仓库里是否有任何算例/脚本**量过** `v_a/v_w` 或"各向异性形状演化"。
"""
import glob
import os
import re

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
PAT = [
    (r'v_a\s*/\s*v_w', 'v_a/v_w 比值'),
    (r'aspect|长径比|纵横比', '长径比'),
    (r'elong', 'elongation'),
    (r'band\s*=|band_cells|扩展带|EDT', '速度扩展带宽'),
    (r'pin_min', 'pin_min'),
    (r'mob_beta', 'mob_beta'),
    (r'各向异性.*(正对照|对照)|正对照.*各向异性', '各向异性正对照'),
]
files = sorted(set(glob.glob('*.py') + glob.glob('*.sh')))
hits = {k: [] for _, k in PAT}
for f in files:
    try:
        t = open(f, encoding='utf-8', errors='replace').read()
    except OSError:
        continue
    for pat, lab in PAT:
        if re.search(pat, t):
            hits[lab].append(f)
for _, lab in PAT:
    fs = hits[lab]
    print('  %-18s %2d 个文件: %s' % (lab, len(fs), ', '.join(fs[:8])))
print()
print('=== 结论要点')
print('  · 若"v_a/v_w 比值"只出现在**测量/审计**脚本（`_r53_*`/`_r54_*`/`_r55_*`）')
print('    而**没有**任何"从矩形出发、只留 M(n) 各向异性、量 v_a/v_w"的**引擎内**对照')
print('    ⇒ 那么"引擎兑现速度律"这件事**从未被正对照**，P1-31 成立。')
print()
print('=== 全仓搜索 "EDT"/band 相关实现位置')
for f in files:
    try:
        t = open(f, encoding='utf-8', errors='replace').read()
    except OSError:
        continue
    for m in re.finditer(r'^.*\b(EDT|ext_band|band=)\b.*$', t, re.M):
        line = m.group(0).strip()
        if len(line) < 200 and ('band' in line.lower() or 'EDT' in line):
            print('  %-24s %s' % (f, line[:120]))
