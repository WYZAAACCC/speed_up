#!/bin/bash
# _r581_reverify.sh --- ★★★★★ **改动后的全面复验**（移动检查点块之后必须重跑）
#
# ## 为什么必须重跑（不许假设"默认关所以没事"）
# 本轮把检查点块**从 CSV 块之后挪到了 `advance()` 之后**（因为前者会被
# `if not _every_now: continue` 挡掉）。**位置一变，就有可能动到别的东西**
# （控制流、缩进、`continue` 的落点）⇒ 按本仓库纪律（P2/P3/§3.4），
# **凡改动引用路径，必须重跑逐位回归**，不能靠"我加了 `if` 门控"来推断。
#
# ## 三件事（按代价从小到大）
# | # | 验什么 | 判据 |
# |---|---|---|
# | **A** | **门 0/门 4**（归档路径逐位不变） | `_r30_regress.sh` ⇒ 「差异字段数 = 0」 |
# | **B** | **门 1**（续跑 vs 连续，逐位） | `_r581_resume_smoke.sh` + `_r581_ckpt_cmp.py` ⇒ 「差异字段数 = 0」 |
# | **C** | **`--ckpt-every 0` 真的不建 `ckpt/`** | 产物目录里没有 `ckpt/` |
set -u
cd "$(dirname "$0")" || exit 1
LOG=_w2_r581_reverify.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

say '════ A. 门 0 / 门 4：归档路径逐位回归（N=96 / 200 步）════'
timeout 2400 bash _r30_regress.sh > /dev/null 2>&1
say "  _r30_regress.sh exit=$?"
say '  ── 关键判据行 ──'
grep -E '差异字段数|共有列逐位一致|Traceback 行数|PASS|FAIL' _w2_r30_regress.log 2>/dev/null \
  | tail -12 | sed 's/^/    /'

say '════ C. `--ckpt-every 0` 真的不建 `ckpt/` ════'
if [ -d _exp/_bk_eng/dry_r30reg/ckpt ]; then
  say '  ❌ **出现了 `ckpt/` 目录** ⇒ 门 0 被破坏（默认关没生效）'
  ls -la _exp/_bk_eng/dry_r30reg/ckpt | sed 's/^/    /'
else
  say '  ✅ 没有 `ckpt/` 目录 ⇒ **默认关真的不执行任何检查点代码**'
fi

say '════ B. 门 1：续跑 vs 连续（逐位）════'
timeout 2400 bash _r581_resume_smoke.sh > /dev/null 2>&1
say "  smoke exit=$?"
taskset -c 16-19 /root/miniconda3/envs/ml/bin/python _r581_ckpt_cmp.py \
  _exp/_bk_rsmoke/dry_rs2/series.csv _exp/_bk_rsmoke/dry_rs3/series.csv step 2>&1 \
  | grep -E '差异字段数|共有列逐位一致|Vt |f_var|nslab_n1|nf3 |nf2 ' | sed 's/^/    /'

say '════ 汇总 ════'
G0=$(grep -c '差异字段数 = 0' _w2_r30_regress.log 2>/dev/null | head -1)
G1=$(taskset -c 16-19 /root/miniconda3/envs/ml/bin/python _r581_ckpt_cmp.py \
      _exp/_bk_rsmoke/dry_rs2/series.csv _exp/_bk_rsmoke/dry_rs3/series.csv step 2>/dev/null \
      | grep -c '差异字段数 = 0' | head -1)
say "  门0（归档逐位）= $([ "${G0:-0}" -ge 1 ] && echo '✅ 通过' || echo '❌ 未通过')"
say "  门1（续跑逐位）= $([ "${G1:-0}" -ge 1 ] && echo '✅ 通过' || echo '❌ 未通过')"
say '=== REVERIFY DONE ==='
