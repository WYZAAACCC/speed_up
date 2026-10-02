#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_vmapchk.py --- ★★★ **直接核实 R48 的更正**：变体分布到底均不均匀？

## 要回答的一件事（**用运行自己的落盘配置，不靠推理**）
R46/R47 我说「`ed` 让变体聚簇」；R48 更正为「**变体分布是 `--laths` 构造出来的、本来就均匀**」。
**⇒ 本量具直接从 `nuc_dbg.json` 读运行**实际**用的配置，验四件事：**

1. `nuc_cfg.laths`（或等价的字段）到底是什么？
2. 由它算出的 **每变体场数** 是不是恰好 `m`？
3. `nuc_cfg.vgroup`（= `vmap`）是不是就是「场 → 变体」的那个映射？
4. **场号 → 变体号** 的完整表（前 24 个场），核对"场 1–4 → 变体 1"是不是构造出来的。

## 判据（**预先写死**）
* 每变体场数**全等于 `m`** ⇒ **R48 的更正成立**（均匀，构造保证）；
* 出现**任何**变体多/少于 `m` ⇒ **R46/R47 的"聚簇"成立**（我撤回 R48）。
"""
import json
import os
import sys
from collections import Counter

ROOT = '_exp/_bk_p2'
TAGS = sys.argv[1:] or ['p2_b5', 'p2_b5ov']


def main():
    print('=' * 100)
    print('核实 R48 的更正：变体分布是「构造均匀」还是「`ed` 聚簇」？')
    print('=' * 100)
    for tag in TAGS:
        p = os.path.join(ROOT, 'dry_' + tag, 'nuc_dbg.json')
        if not os.path.exists(p):
            print('  %-9s ❌ 无 `nuc_dbg.json`' % tag); continue
        j = json.load(open(p, encoding='utf-8'))
        cfg = j.get('nuc_cfg', {})
        print()
        print('#' * 100)
        print('# %s' % tag)
        print('#' * 100)
        print('  `nuc_cfg` 的键：%s' % sorted(cfg.keys()))
        for k in ('laths', 'nv', 'vgroup', 'seed', 'block_target', 'shape', 'law'):
            if k in cfg:
                v = cfg[k]
                s = str(v)
                print('  `%s` = %s' % (k, s[:200] + ('…' if len(s) > 200 else '')))
        vg = cfg.get('vgroup')
        if not isinstance(vg, dict):
            print('  ⚠ `vgroup` 不是 dict（类型 %s）⇒ 本量具跳过' % type(vg).__name__)
            continue
        # 归一化键
        vg = {int(a): int(b) for a, b in vg.items()}
        nv = len(vg)
        cnt = Counter(vg.values())
        m = nv / 12.0
        print()
        print('  ── ① 每变体占的场数 ──')
        print('     nv = %d ⇒ 每变体应有 **%.0f** 个场' % (nv, m))
        print('     %s' % dict(sorted(cnt.items())))
        uniform = all(c == cnt[sorted(cnt)[0]] for c in cnt.values())
        print('     ⇒ 全部等于 %.0f ？ **%s**' % (m, '✅ 是 ⇒ 分布均匀（构造保证）' if uniform else '❌ 否'))
        # 变异度
        lo, hi = min(cnt.values()), max(cnt.values())
        print('     min/max = %d / %d ⇒ 极差 %d' % (lo, hi, hi - lo))
        print()
        print('  ── ② 场号 → 变体号（前 24 个场）──')
        rows = []
        for f in sorted(vg)[:24]:
            rows.append('%d→%d' % (f, vg[f]))
        print('     %s' % '  '.join(rows))
        # 与 laths 构造对照
        print()
        print('  ── ③ 与 `laths(m)` 构造对照（`_r581_p2.py:50-51` 的公式）──')
        exp = []
        for v in range(1, 13):
            for _ in range(int(m)):
                exp.append(v)
        got = [vg[f] for f in sorted(vg)]
        ok = (exp == got)
        print('     预期（`1,1,1,1,2,2,2,2,…`）：%s' % exp[:16])
        print('     实得　　　　　　　　　　　：%s' % got[:16])
        print('     ⇒ **逐位相同？ %s**' % ('✅ 是 ⇒ **变体分布完全是构造出来的**（R48 成立）'
                                          if ok else '❌ 否 ⇒ 有别的机制在改变体（需查）'))
        print()
        print('  ── ④ R48 结论 ··················································')
        if uniform and ok:
            print('     ✅ **R48 的更正成立**：变体分布 = `--laths` 构造，**每变体恰好 `m` 个场**。')
            print('        ⇒ **C5 的唯一约束是 `m`**（同变体板条数上限），而 `m` **可调**。')
            print('        ⇒ **R46/R47 的「`ed` 聚簇」说法应予撤回**（已在 `R581_TASK5_VERDICT.md §1.18` 撤回）。')
        else:
            print('     ❌ **R48 的更正不成立** ⇒ 需要重新审视（并撤回 R48）。')
    print()
    print('=' * 100)


if __name__ == '__main__':
    main()
