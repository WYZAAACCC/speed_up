#!/bin/bash
# _r581_optresume.sh --- ★★★★★ 回答："能断帧续跑的那份代码，是**算子优化后**的代码吗？"
#
# ## 为什么要实测而不是推理
# 检查点代码加在 `_bk_exp.py`（**和那 8 个算子开关同一个文件**），
# 但**我此前所有续跑实验都把算子开关留在默认（归档旧路）**，只动过 `--pf-phi`。
# ⇒ "它当然也能在优化路径下工作"是**推理**，不是实测。**这里补上。**
#
# ## 三段
# | 段 | 配置 | 判据 |
# |---|---|---|
# | **A** | **七项算子全开**，一次跑完 16 步 | 真值 |
# | **B** | 同上，跑到 8 步存检查点 ⇒ **同开关续跑**到 16 | **必须 diff = 0** |
# | **C** | 从 **B 的检查点**续跑，但**退回归档开关** | **必须 diff ≠ 0**（负对照：证明开关是"逐字相同"的一部分） |
#
# ## ★ 前置断言：开关必须**真的生效**（否则整段作废）
# 引擎会打一行 `[WindowB] 算子开关：…` ⇒ 逐项核对七项都在。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT=_exp/_bk_optrs
LOG=_w2_r581_optrs.log
STEPS=16
CUT=8
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# ★ 七项**逐位等价**的算子开关（`--fft-mode rfft` 被排除：它 σ 差 2.2e-16，不逐位）
OPT="--eps0-mode einsum --ed-pair gather --k-loop act --act-mode bincount \
 --argmin2-mode copyto --grad-mode sliced --pf-phi onfly"

BASE="--N 64 --dx-nm 62.5 --every 2 --snap-every 100 --pair-every 50 \
 --nthreads 4 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 5 \
 --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
 --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
 --cool-rate 2.3524e6 --reinit-dt 1e-4 --reinit-band 6.0 \
 --nuc-overlap-nm 62.5 --h-chunk 4"
LATHS=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range(20)))")
clean() { [ -d "$ROOT/dry_$1" ] && mv "$ROOT/dry_$1" "$ROOT/dry_$1_superseded_$(date '+%Y%m%d_%H%M%S')"; }
run() {  # tag  extra  steps
  clean "$1"
  timeout 2400 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
    taskset -c 0-7 $PY -u _bk_exp.py $BASE $2 --steps "$3" \
    --out "$ROOT" --tag "$1" --laths "$LATHS" > "_w2_r581_optrs_$1.log" 2>&1
  printf '    %-9s exit=%d  Traceback=%s  末步=%s\n' "$1" "$?" \
    "$(grep -c '^Traceback' "_w2_r581_optrs_$1.log" 2>/dev/null | head -1)" \
    "$(tail -1 "$ROOT/dry_$1/series.csv" 2>/dev/null | cut -d, -f1)"
}

say '════ ① A 路：**七项算子全开**，一次跑完 16 步（真值）════'
run optA "$OPT" $STEPS
say '  ── ★ 前置断言：引擎自报的开关状态（必须逐项生效）──'
grep '算子开关' _w2_r581_optrs_optA.log 2>/dev/null | sed 's/^/    /'
NOSW=$(grep -oE 'einsum|gather|act|bincount|copyto|sliced|onfly' _w2_r581_optrs_optA.log 2>/dev/null | sort -u | wc -l)
say "    生效关键词命中数 = $NOSW（期望 ≥5；若只有 0-1 ⇒ **开关没生效 ⇒ 本实验作废**）"

say '════ ② B 路：同开关跑到 8 步存检查点 ════'
run optB "$OPT --ckpt-every $CUT --ckpt-keep 2" $CUT
ls -la "$ROOT/dry_optB/ckpt/" 2>/dev/null | tail -n +4 | awk '{printf "    %-20s %8.2f MB\n", $9, $5/1048576}'

say '════ ③ B 路续跑：**同开关**跑到 16 ════'
run optBrs "$OPT --resume $ROOT/dry_optB/ckpt" $STEPS
grep -E '自动选|检查点 step=|从 step|驱动层已回填' _w2_r581_optrs_optBrs.log 2>/dev/null | head -3 | sed 's/^/    /'

say '════ ④ ★ 正判据：B续跑 vs A（**必须 diff = 0**）════'
taskset -c 16-19 $PY _r581_ckpt_cmp.py \
  "$ROOT/dry_optBrs/series.csv" "$ROOT/dry_optA/series.csv" step 2>&1 \
  | grep -E '共有 step|差异字段数|共有列逐位一致|Vt |f_var |nslab_n1|nf3 |nf2 |有差异的列' \
  | sed 's/^/    /'

say '════ ⑤ ★ 负对照 C：从同一检查点续跑，但**退回归档开关** ════'
say '  （若这一路也 diff=0 ⇒ 说明算子开关对结果无影响 ⇒ 那 1.215× 就有问题；'
say '    若 diff≠0 ⇒ 证明**开关是"逐位相同"要求的一部分**）'
run optCrs "--resume $ROOT/dry_optB/ckpt" $STEPS
taskset -c 16-19 $PY _r581_ckpt_cmp.py \
  "$ROOT/dry_optCrs/series.csv" "$ROOT/dry_optA/series.csv" step 2>&1 \
  | grep -E '共有 step|差异字段数|共有列逐位一致|有差异的列|^    [A-Za-z_]+ +[0-9]+ 处' | head -8 \
  | sed 's/^/    /'

say '════ 汇总 ════'
say '  A = 算子全开一次跑完；B续跑 = 同开关续跑；C续跑 = 退回归档开关续跑'
say '=== OPTRESUME DONE ==='
