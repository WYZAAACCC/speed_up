#!/bin/bash
# _r581_recollect.sh --- ★★★★★★ **把全部判据证据重新收集到磁盘**（然后审计才有东西可查）
#
# ## 为什么需要它（**审计抓出来的我自己的错**）
# 第一次审计报「7 条无证据」。根因**不是判据没过**，而是：
# 那些比较的输出是 `... | sed 's/^/    /'` **打到终端**的，
# **从来没经过 `say()`** ⇒ **没落进 `_w2_*.log`** ⇒ 审计在磁盘上**找不到**。
# **⇒ 这正是 P48 的同族**：**审计要量它真正要管的那个量，且证据必须**持久化****。
#
# ## 本脚本做什么（**不跑仿真，只重算**）
# 所有 `series.csv` 都还在 ⇒ 把 8 组比较**重跑一遍并落盘**到
# `_w2_r581_evidence.log`，供 `_r581_final_audit.sh` 机械核对。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
EV=_w2_r581_evidence.log
: > "$EV"
say() { echo "$*" | tee -a "$EV"; }

cmp_pair() {  # $1=判据名  $2=A(续跑/被破坏)  $3=B(真值)
  local name="$1" a="$2" b="$3"
  say "────────────────────────────────────────────────────────────────────"
  say "判据：$name"
  say "  A = $a"
  say "  B = $b"
  if [ ! -f "$a" ] || [ ! -f "$b" ]; then
    say "  ⚠ **缺文件** ⇒ 无法判定（记 ❌）"
    say "  ⇒ 差异字段数 = 缺文件"
    return
  fi
  taskset -c 16-19 $PY _r581_ckpt_cmp.py "$a" "$b" step 2>&1 \
    | grep -E '差异字段数|共有列逐位一致|共有 step|A 行数|Vt |f_var|nslab_n1|nf3 |nf2 |有差异的列|^    [A-Za-z_]+ +[0-9]+ 处' \
    | sed 's/^/  /' | tee -a "$EV"
}

say '════════════════════════════════════════════════════════════════════════'
say '  R581-ckpt 判据证据汇总（**从磁盘上的 series.csv 重算**）'"$(date '+%F %T')"
say '════════════════════════════════════════════════════════════════════════'

say ''
say '★★ ① 门 1：**续跑** vs **一次跑完**（N=64，从 step 10 续跑到 16）'
cmp_pair '① 门1（续跑 vs 连续）' \
  _exp/_bk_rsmoke/dry_rs2/series.csv _exp/_bk_rsmoke/dry_rs3/series.csv

say ''
say '★★ ④-2b 门 2b：**带 `--ckpt-every 2`** vs **不带**（同配置 ⇒ 必须逐位相同）'
cmp_pair '④ 门2b（带 vs 不带 ckpt）' \
  _exp/_bk_g23/dry_g23_on/series.csv _exp/_bk_g23/dry_g23_off/series.csv

say ''
say '★★ ④-3 门 3：从**里程碑@10** 续跑 vs 一次跑完'
cmp_pair '④ 门3（里程碑续跑 vs 连续）' \
  _exp/_bk_g3b/dry_g3b_rs/series.csv _exp/_bk_g3b/dry_g3b_true/series.csv

say ''
say '★★★ 头号场景：**真 `kill -9`** 后从检查点恢复 vs **从未中断**'
cmp_pair '★ kill9（被杀后恢复 vs 从未中断）' \
  _exp/_bk_kill/dry_killC/series.csv _exp/_bk_kill/dry_killA/series.csv

say ''
say '★★ 风险#4 甲：`--pf-phi materialized` 档下 续跑 vs 连续'
cmp_pair '★ materialized 档（续跑 vs 连续）' \
  _exp/_bk_seg/dry_ma_rs/series.csv _exp/_bk_seg/dry_ma_true/series.csv

say ''
say '★★ 任务4 乙：**3 段接续** vs 一次跑完（门 1 的加强版）'
cmp_pair '★ 3 段接续 vs 一次跑完' \
  _exp/_bk_seg/dry_seg_p3/series.csv _exp/_bk_seg/dry_seg_true/series.csv

say ''
say '★★ 负对照 1：**φ 只存带内** vs 真值（**必须 FAIL**）'
cmp_pair '② 负1 φ只存带内（必须 FAIL）' \
  _exp/_bk_nc3/dry_nc3_n1/series.csv _exp/_bk_nc3/dry_nc3_s3/series.csv

say ''
say '★★ 负对照 3：**不恢 `_cnt`/`_t_since_reinit`** vs 真值（**必须 FAIL**）'
cmp_pair '② 负3 不恢_cnt（必须 FAIL）' \
  _exp/_bk_nc5/dry_nc5_n3/series.csv _exp/_bk_nc5/dry_nc5_s3/series.csv

say ''
say '★★ 负对照 2：不恢 RNG vs 真值（**机制上无法 FAIL**，仍记录）'
cmp_pair '② 负2 不恢RNG' \
  _exp/_bk_nc3/dry_nc3_n2/series.csv _exp/_bk_nc3/dry_nc3_s3/series.csv

say ''
say '★★ 负对照 4：不恢 `dbg[ok]`（**翻转奇偶**）vs 真值'
cmp_pair '② 负4 dbg[ok]（翻转奇偶）' \
  _exp/_bk_nc6/dry_nc6_n4/series.csv _exp/_bk_nc6/dry_nc6_s3/series.csv

say ''
say '════════════════════════════════════════════════════════════════════════'
say '  ★ 全部证据已落盘：'"$EV"
say '════════════════════════════════════════════════════════════════════════'
