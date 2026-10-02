#!/bin/bash
# _r581_rfftresume.sh --- ★★★★★ 唯一**非逐位**的算子开关（`--fft-mode rfft`）与续跑的关系
#
# ## 为什么单测它
# `_r581_optresume.sh` 已证：**七项逐位等价的算子开关**开着或关着，续跑结果都一样
# ⇒ **检查点在这些开关之间可搬运**（好消息）。
# **但 `--fft-mode : c2c | rfft` 是例外** —— 按 `AGENTS.md §7.5` 的实测表，
# `rfft` **不是逐位的**（**σ 差 2.2e-16**）。
# ⇒ 本脚本回答：**换 FFT 档会不会把"续跑逐位一致"打破？**
#
# ## 三段
# | 段 | 配置 | 判据 |
# |---|---|---|
# | **A** | `rfft`，一次跑完 16 步 | 真值 |
# | **B** | `rfft` 跑到 8 步存检查点 ⇒ **同档（rfft）续跑**到 16 | **必须 diff = 0**（同档自洽） |
# | **C** | 从**同一个 rfft 检查点**续跑，但切成 `c2c` | **预期 diff ≠ 0**（⇒ 证明这一档**必须逐字相同**） |
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT=_exp/_bk_rfftrs
LOG=_w2_r581_rfftrs.log
STEPS=16
CUT=8
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

BASE="--N 64 --dx-nm 62.5 --every 2 --snap-every 100 --pair-every 50 \
 --nthreads 4 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 5 \
 --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
 --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
 --cool-rate 2.3524e6 --reinit-dt 1e-4 --reinit-band 6.0 \
 --nuc-overlap-nm 62.5 --pf-phi onfly --h-chunk 4"
LATHS=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range(20)))")
clean() { [ -d "$ROOT/dry_$1" ] && mv "$ROOT/dry_$1" "$ROOT/dry_$1_superseded_$(date '+%Y%m%d_%H%M%S')"; }
run() {
  clean "$1"
  timeout 2400 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
    taskset -c 0-7 $PY -u _bk_exp.py $BASE $2 --steps "$3" \
    --out "$ROOT" --tag "$1" --laths "$LATHS" > "_w2_r581_rfftrs_$1.log" 2>&1
  printf '    %-9s exit=%d  Traceback=%s  末步=%s\n' "$1" "$?" \
    "$(grep -c '^Traceback' "_w2_r581_rfftrs_$1.log" 2>/dev/null | head -1)" \
    "$(tail -1 "$ROOT/dry_$1/series.csv" 2>/dev/null | cut -d, -f1)"
}

say '════ ① A 路：`--fft-mode rfft`，一次跑完 16 步 ════'
run rA "--fft-mode rfft" $STEPS
grep '算子开关' _w2_r581_rfftrs_rA.log 2>/dev/null | sed 's/^/    /'
say '════ ② B 路：`rfft` 跑到 8 步存检查点 ════'
run rB "--fft-mode rfft --ckpt-every $CUT --ckpt-keep 2" $CUT
say '════ ③ B 路续跑：**同档 rfft** 跑到 16 ════'
run rBrs "--fft-mode rfft --resume $ROOT/dry_rB/ckpt" $STEPS
grep -E '检查点 step=|从 step' _w2_r581_rfftrs_rBrs.log 2>/dev/null | head -2 | sed 's/^/    /'
say '════ ④ ★ 同档自洽：B续跑(rfft) vs A(rfft) ⇒ **必须 diff = 0** ════'
taskset -c 16-19 $PY _r581_ckpt_cmp.py \
  "$ROOT/dry_rBrs/series.csv" "$ROOT/dry_rA/series.csv" step 2>&1 \
  | grep -E '共有 step|差异字段数|共有列逐位一致|Vt |f_var |nslab_n1|nf3 |nf2 |有差异的列' \
  | sed 's/^/    /'
say '════ ⑤ ★ 换档：从**同一个 rfft 检查点**续跑，但切 `c2c` ════'
run rCrs "--resume $ROOT/dry_rB/ckpt" $STEPS
grep '算子开关' _w2_r581_rfftrs_rCrs.log 2>/dev/null | sed 's/^/    /'
say '  ── C(c2c续跑) vs A(rfft一次跑完) ──'
taskset -c 16-19 $PY _r581_ckpt_cmp.py \
  "$ROOT/dry_rCrs/series.csv" "$ROOT/dry_rA/series.csv" step 2>&1 \
  | grep -E '共有 step|差异字段数|共有列逐位一致|有差异的列|^    [A-Za-z_]+ +[0-9]+ 处' | head -8 \
  | sed 's/^/    /'
say '  ── 附带：C(c2c续跑) vs **c2c 一次跑完**（若有）──'
say '     （本条不另跑；判读见下：若 ⑤ 的 diff≠0 ⇒ 该档**必须逐字相同**）'
say '════ 汇总 ════'
say '=== RFFTRESUME DONE ==='
