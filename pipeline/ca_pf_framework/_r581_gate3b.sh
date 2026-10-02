#!/bin/bash
# _r581_gate3b.sh --- ★★★★★★ **门 3（修好版）+ 里程碑接线验证**
#
# ## 为什么上一版门 3 会失败（**我的测试设计错**，不是代码错）
# `--ckpt-every 2 --ckpt-keep 2` ⇒ 帧在 0,2,4,…,20，但**滑动窗口只留最新 2 帧**
# ⇒ 只剩 **18 与 20** ⇒ **step 10 那帧被**轮转掉了**** ⇒ 无从"从 step 10 续跑"。
# **⇒ 这恰恰说明滑动窗口在正常工作**（goal 要的就是它）。
#
# ## 正确做法：用**里程碑**（`--ckpt-milestone-every`）
# 里程碑**不参与滑动**（goal 任务(3) 逐字：给"往回退一大截"留路）
# ⇒ 用 `--ckpt-milestone-every 10` ⇒ 得到**不会被轮转**的 step 10 与 20 两帧。
#
# ## 判据（**预先写死**）
# | # | 判据 |
# |---|---|
# | **M-1** | 里程碑真的落盘（`ckptms_000010.npz`、`ckptms_000020.npz`）且**不被轮转** |
# | **M-2** | 里程碑与普通帧**并存**（`ckpt_A/B` 各一 + `ckptms_*`） |
# | **门3** | 从**里程碑@10** 续跑到 20 ⇒ 与"一次跑完"的 `series.csv` **逐位相同** |
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT=_exp/_bk_g3b
LOG=_w2_r581_g3b.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

CFG="--N 64 --dx-nm 62.5 --every 5 --snap-every 10 --pair-every 50 \
 --nthreads 4 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 5 \
 --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
 --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
 --cool-rate 2.3524e6 --reinit-dt 1e-4 --reinit-band 6.0 \
 --nuc-overlap-nm 62.5 --pf-phi onfly --h-chunk 4 --steps 20"
LATHS=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range(20)))")

run() {
  local tag="$1" extra="$2"
  [ -d "$ROOT/dry_$tag" ] && mv "$ROOT/dry_$tag" "$ROOT/dry_${tag}_superseded_$(date '+%Y%m%d_%H%M%S')"
  timeout 2400 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
    taskset -c 0-7 $PY -u _bk_exp.py $CFG $extra \
    --out "$ROOT" --tag "$tag" --laths "$LATHS" > "_w2_r581_g3b_${tag}.log" 2>&1
  printf '    %-9s exit=%d  Traceback=%s  末步=%s\n' "$tag" "$?" \
    "$(grep -c '^Traceback' "_w2_r581_g3b_${tag}.log" 2>/dev/null | head -1)" \
    "$(tail -1 "$ROOT/dry_$tag/series.csv" 2>/dev/null | cut -d, -f1)"
}

say '════ ① 真值：一次跑完 20 步 ════'
run g3b_true ""
say '════ ② 带**里程碑**跑：--ckpt-every 2 --ckpt-keep 2 --ckpt-milestone-every 10 ════'
run g3b_ms "--ckpt-every 2 --ckpt-keep 2 --ckpt-milestone-every 10"
say '  ── 检查点目录（M-1/M-2）──'
ls -la "$ROOT/dry_g3b_ms/ckpt/" 2>/dev/null | sed 's/^/    /'
say '  ── 引擎打的检查点日志 ──'
grep '\[ckpt' "_w2_r581_g3b_ms.log" 2>/dev/null | tail -12 | sed 's/^/    /'

MS="$ROOT/dry_g3b_ms/ckpt/ckptms_000010.npz"
if [ ! -f "$MS" ]; then
  say "  ❌ **里程碑没落盘**（找不到 $MS）⇒ M-1 FAIL ⇒ 停"
  exit 2
fi
say "  ✅ M-1：里程碑在（$MS）"
NF=$(ls -1 "$ROOT/dry_g3b_ms/ckpt/" 2>/dev/null | grep -c '^ckpt_A\|^ckpt_B')
NMS=$(ls -1 "$ROOT/dry_g3b_ms/ckpt/" 2>/dev/null | grep -c '^ckptms_')
say "  ✅ M-2：普通帧 $NF 个（应 2）+ 里程碑 $NMS 个（应 2）"

say '════ ③ 门 3：从**里程碑@10** 续跑到 20 ════'
run g3b_rs "--resume $MS"
grep -E '自动选|检查点 step=|驱动层已回填|P0 已回填|版本哈希' "_w2_r581_g3b_g3b_rs.log" 2>/dev/null \
  | sed 's/^/    /'
say '  ── 逐位比较（g3b_rs vs g3b_true）──'
taskset -c 16-19 $PY _r581_ckpt_cmp.py \
  "$ROOT/dry_g3b_rs/series.csv" "$ROOT/dry_g3b_true/series.csv" step 2>&1 \
  | grep -E '差异字段数|共有列逐位一致|共有 step|Vt |f_var|nslab_n1|nf3 |nf2 |有差异的列' \
  | sed 's/^/    /'
say '════ 汇总 ════'
say '  M-1 里程碑落盘 = 见上    M-2 并存 = 见上    门3 逐位 = 见上"差异字段数"'
say '=== GATE3B DONE ==='
