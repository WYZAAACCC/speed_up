#!/bin/bash
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t10_lathcount.sh pipeline/ca_pf_framework/_t10_b9run.sh \
        pipeline/ca_pf_framework/_t10_b9run2.sh pipeline/ca_pf_framework/_t10_b9chk.sh
git commit -q -F - <<'MSG'
★ 新要求「最终应有 200+ 根板条（≤ nv）」的诊断与解决：

诊断（用代码自己的记账）：总根数 = **B · n(T_end) = 3 × 23 = 69** ← 当前上限。逐项对账：首档目标 45 = 3×15、第二档 63 = 3×21 ✓ 与 B=3 完全一致。而**形核与生长都没有问题**（t10PRT2 实测 39 事件 → 39 存活、死核 0、场号唯一性 1.000；step100 有带内胞场 = 40）⇒ **短缺纯粹来自 --nuc-block-target 3 这个上限**，不是形核或生长的缺陷。

解决：B × 23 ≥ 200 且 ≤ nv=220 ⇒ **B = 9 ⇒ 9 × 23 = 207** ✓。改造为 `--B 9`（nv 保持 10×22 = 220 不变）。

★ 记账：v1 误用 `--nuc-block-target 9` 启动 ⇒ `_t5_short.py` 不声明该参数 ⇒ 立即崩（unrecognized arguments，未进入构造）。真相是启动器第 100 行把 `--B` 透传成 `--nuc-block-target`（`'--nuc-block-target', str(a.B)`）⇒ 必须用 `--B`。v2 已修正并确认引擎在跑：pid=75555、开关 `--nuc-block-target 9` 生效、VmSwap=0。

数据保留：t10PRT2 → dry_t10PRT2_b3_1005_1213（B=3 那一跑，七项全绿基线）。
MSG
git log --oneline -1
