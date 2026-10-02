#!/bin/bash
# _r30_regress.sh —— R30 改动的**回归**：证明"加了新列 + 自适应柱半径"之后
#   **归档默认路径的动力学与旧量具口径逐位不变**。
#
# 为什么必须跑：R30 改了 `_bk_measure.measure_state`（新增 `nslab_n1`/`runs1`/
#   `nf3_col1`/`r_col_nm`/`col_cover_*`）与 `_bk_exp.py` 的 `COLS`。
#   按本仓库纪律（`R8`）：**凡改动引用路径，必须留逐位回归**。
#
# 判据（预先写死）：
#   G-1 与归档 `eng12` 的**共有列**逐位一致（忽略 wall_s）
#   G-2 新列存在且非空（`nslab_n1`/`runs1`/`nf3_col1`/`r_col_nm`/`col_cover_min`）
#   G-3 量具自检 `_bk_measure.py --selftest` FAIL=0
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
LOG=_w2_r30_regress.log
: > "$LOG"
{
  echo "################ ⓪ 清掉上一次的产物（★ R49 修：这里原先**没有** rm）  $(date '+%F %T')"
  # ★★★ R49（**自检脚本自己的静默失效**，`AGENTS.md §3.4` 的同类）：
  #   本脚本原先**不删** `_exp/_bk_eng/dry_r30reg`，而 `_bk_exp.py` 会**复用**
  #   已存在的目录 ⇒ 第二次以后运行**根本不重跑**，而是拿上一次的 `series.csv`
  #   去和 `eng12` 比 —— 于是"差异 = 0"**恒成立**，回归**静默变成空操作**。
  #   实测后果：R49 中途我连跑两次回归，第二次（10:28）实际比的是**10:22 的旧产物**
  #   （表头里没有新列 `dG_tip_p90`/`v_tip_nabs`，这就是线索）。
  #   ⇒ 两处修：① 跑前 `rm -rf`；② 跑后**断言 CSV 是刚刚写的**（见 ①c）。
  rm -rf _exp/_bk_eng/dry_r30reg
  _T0=$(date +%s)
  echo "    已删除旧产物，_T0=$_T0"
  echo
  echo "################ ① 归档默认路径重跑（tag=r30reg）  $(date '+%F %T')"
  "$PY" -u _bk_exp.py --N 96 --dx-nm 62.5 --steps 200 --every 10 --snap-every 50 \
    --pair-every 10 --norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
    --grow-stack --eng-cadence 30 --nuc-overlap-nm 62.5 \
    --tag r30reg --out _exp/_bk_eng > _w2_r30_regress_stdout.log 2>&1
  tail -4 _w2_r30_regress_stdout.log
  echo
  echo "################ ①a2 ★ 运行日志断言（R152 新增）"
  # ★★★ R152（`R30_AUDIT_LEDGER.md` §92 / §108）：**回归全绿 ≠ 改动无 bug**。
  #   依据：R76 那次 `_blk_verdict` 的 `ValueError` **只出现在终态判决处**，
  #   CSV 已写完 ⇒ 逐位比较**照样 PASS**、量具自检**照样 PASS**，
  #   **只有日志里那一行 Traceback 能看出来**；而原脚本把输出 `tail -4` 掉了。
  #   §108 又把"块内界面自检"加进驱动 ⇒ 也必须确认它**真的打了**（否则是静默失效）。
  #   ⇒ 本次改为：**完整日志落盘** + 三条硬断言。
  _RLOG=_w2_r30_regress_stdout.log
  if [ ! -f "$_RLOG" ]; then
    echo "  **FAIL**：$_RLOG 不存在 ⇒ 无法断言运行日志（本段作废）"
  else
    _TB=$(grep -c 'Traceback' "$_RLOG" || true)
    _ER=$(grep -cE '^(ValueError|TypeError|NameError|KeyError|IndexError|RuntimeError):' "$_RLOG" || true)
    _SC=$(grep -c '块内界面自检' "$_RLOG" || true)
    echo "  Traceback 行数 = $_TB（应 0）  ;  顶层异常行数 = $_ER（应 0）"
    echo "  '块内界面自检' 出现次数 = $_SC（应 ≥1 —— §108 的接线**真的生效**）"
    grep -m1 '块内界面自检' "$_RLOG" || true
    grep -m1 'cov_norm' "$_RLOG" || true
    if [ "$_TB" -eq 0 ] && [ "$_ER" -eq 0 ] && [ "$_SC" -ge 1 ]; then
      echo "  **PASS**：无 Traceback / 无顶层异常 / 自检已生效"
    else
      echo "  **FAIL**：见上（回归即使逐位一致，也必须过这三条）"
    fi
  fi
  echo
  echo "################ ①c ★ 新鲜度断言（R49 新增；不过就整段作废）"
  _CSV=_exp/_bk_eng/dry_r30reg/series.csv
  if [ ! -f "$_CSV" ]; then
    echo "  **FAIL**：$_CSV 不存在 ⇒ 本次回归无产物，结论无效"
  else
    _MT=$(stat -c %Y "$_CSV")
    echo "  CSV mtime=$(date -d @$_MT '+%F %T')   _T0=$(date -d @$_T0 '+%F %T')"
    if [ "$_MT" -ge "$_T0" ]; then
      echo "  **PASS**：产物确实是本次新写的"
    else
      echo "  **FAIL**：产物比本次启动还旧 ⇒ **回归是空操作**，结论无效"
    fi
    echo -n "  新列在位检查（应为 3）： "
    head -1 "$_CSV" | tr ',' '\n' | grep -cE '^(dG_tip_p90|v_tip_nabs|n_tip)$'
  fi
  echo
  echo "################ ①b 与归档 eng12 逐位比较（忽略 wall_s）"
  "$PY" -u _bk_defcheck.py r30reg 2>&1 | tail -8
  echo
  echo "################ ② 新列非空核对"
  "$PY" -u _r30_csv.py _exp/_bk_eng/dry_r30reg/series.csv \
      step,nslab_n,nslab_n1,nf3_col,nf3_col1,r_col_nm,col_cover_min 2>&1 | tail -6
  echo
  echo "################ ③ 量具自检"
  "$PY" _bk_measure.py --selftest 2>&1 | tail -3
  echo
  # ★★★ 2026-10-01 新增（`§180`）：**弹性求解器的自检也要进回归**。
  #   为什么：`windowB_pf3d.py` 的 `test_F2` 从 T1/P0-1 符号修复（2026-09-28）起
  #   **一直是 FAIL**（测试过期：`forces()` 改成了 `+ε⁰:σ`，而测试仍按 `−ε⁰:σ` 比），
  #   却**没人发现** —— 因为这个自检**从来没被接进任何回归**。
  #   ⇒ 一个坏掉的守卫等于没有守卫。现在把它接上。
  #   ⚠ 判据：末尾必须出现 `总判定: ALL PASS`；出现 FAIL 就红。
  echo "################ ④ 弹性求解器自检（windowB_pf3d）"
  _PF3D_OUT=$("$PY" -u windowB_pf3d.py 2>&1 | tail -40)
  printf '%s\n' "$_PF3D_OUT" | grep -E '总判定|FAIL|PASS' | tail -12
  if printf '%s' "$_PF3D_OUT" | grep -q '总判定: ALL PASS'; then
    echo "  ⇒ ✅ windowB_pf3d 自检 ALL PASS"
  else
    echo "  ⇒ ❌❌ **windowB_pf3d 自检未全过** —— 见上"
  fi
} >> "$LOG" 2>&1
echo "=== R30 REGRESS DONE $(date '+%F %T') ===" >> "$LOG"
tail -30 "$LOG"
