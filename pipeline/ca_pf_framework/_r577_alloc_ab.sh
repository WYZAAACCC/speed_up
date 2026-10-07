#!/bin/bash
# _r577_alloc_ab.sh --- R577：**分配器环境变量逐项分解** + 峰值 RSS。
#
# ## 触发这件事的实测
# `_r577_env_ab.sh` 交错配对（PLAIN vs 三个 MALLOC 变量全开）：
#     round1 PLAIN=0.4461  TUNED=0.7858
#     round2 PLAIN=0.4381  TUNED=0.7168
# ⇒ **TUNED 慢 1.6–1.8×**，而且 PLAIN 在两轮之间稳定 ⇒ 不是宿主漂移。
#
# ## 为什么必须逐项拆
# 这三个变量的作用完全不同，混在一起量等于没量（`AGENTS.md` 教训 12：**别一次改两个变量**）：
#   * `MALLOC_MMAP_THRESHOLD_=65536` —— >64 KB 的分配走 `mmap` ⇒ free 时**真的归还**给 OS
#     （`_bk_run_block.sh:10` 的注释写明这是为了**控 RSS**），代价是每次分配都缺页。
#   * `MALLOC_TRIM_THRESHOLD_=65536` —— `free` 时更积极地把堆顶还给 OS。
#   * `MALLOC_ARENA_MAX=2` —— **限制 malloc 的 arena 数**。本引擎是 **4 线程并行** 的
#     ⇒ arena 太少会让多线程在 malloc 锁上排队。**这一条最可能是元凶。**
#
# ## 判据
#   * 墙钟：交错 N 轮，报每轮**配对比值**的中位与区间。
#   * 峰值 RSS：`/usr/bin/time -v` 的 `Maximum resident set size`（单臂各测一次，
#     因为它会干扰计时）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export R576_N="${R577_N:-64}" R576_NV="${R577_NV:-24}"
export R576_STEPS="${R577_STEPS:-6}" R576_WORKERS="${R577_WORKERS:-4}"
ROUNDS="${R577_ROUNDS:-3}"
SUF="${R576_NV}x${R576_N}_w${R576_WORKERS}"
LOG=_w2_r577_allocab.log
: > "$LOG"

# 五个臂
ARMS=(PLAIN MMAP TRIM ARENA ALL)
env_of() {
  case "$1" in
    PLAIN) echo "R577_NOOP=1" ;;
    MMAP)  echo "MALLOC_MMAP_THRESHOLD_=65536" ;;
    TRIM)  echo "MALLOC_TRIM_THRESHOLD_=65536" ;;
    ARENA) echo "MALLOC_ARENA_MAX=2" ;;
    ALL)   echo "MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2" ;;
  esac
}

echo "=== R577 ALLOC 分解（交错）N=$R576_N NV=$R576_NV W=$R576_WORKERS STEPS=$R576_STEPS ROUNDS=$ROUNDS ===" | tee -a "$LOG"
$PY _r576_hostfp.py | sed 's/^/  /' | tee -a "$LOG"

declare -A RES
for r in $(seq 1 "$ROUNDS"); do
  for arm in "${ARMS[@]}"; do
    EV=$(env_of "$arm")
    OUTF="_w2_r577_alloc_${arm}_r${r}_${SUF}.log"
    env $EV R576_TAG="${arm}r${r}" R576_OUT="$OUTF" "$PY" _r576_prof.py \
        > "_w2_r577_alloc_${arm}_r${r}_stdout.log" 2>&1
    CL=$(sed -n 's/.*干净单步（钩子关）= \*\*\([0-9.]*\) s.*/\1/p' "$OUTF" | head -1)
    PJ=$(grep -E '^  P1 ' "$OUTF" | sed -E 's/.*= \*\*([0-9.]+)%.*/\1/')
    echo "round $r $arm clean=$CL P1=$PJ" | tee -a "$LOG"
    RES[$arm]="${RES[$arm]:-}${CL} "
  done
done

echo "" | tee -a "$LOG"
echo "--- 汇总（以 PLAIN 为基准的配对比值；大于 1 = 比 PLAIN 慢）---" | tee -a "$LOG"
$PY - "$ROUNDS" ${RES[PLAIN]} ${RES[MMAP]} ${RES[TRIM]} ${RES[ARENA]} ${RES[ALL]} <<'PYEOF' 2>&1 | tee -a "$LOG"
import sys, statistics
n = int(sys.argv[1]); v = [x for x in sys.argv[2:] if x.strip()]
assert len(v) == 5 * n, '参数个数 %d != %d（★ 自查：v1 因为 `${RES[..]}` 带尾空格多出一个空参数而崩）' % (len(v), 5 * n)
names = ['PLAIN', 'MMAP', 'TRIM', 'ARENA', 'ALL']
arms = {nm: [float(x) for x in v[i*n:(i+1)*n]] for i, nm in enumerate(names)}
base = arms['PLAIN']
print('  PLAIN = %s' % ['%.4f' % x for x in base])
for nm in names[1:]:
    a = arms[nm]
    r = [x / b for x, b in zip(a, base)]
    print('  %-6s(%-6s) = %s ⇒ 相对 PLAIN 中位 **%.3fx**  区间 [%.3f, %.3f]'
          % (nm, {'MMAP': 'MMAP_THR', 'TRIM': 'TRIM_THR', 'ARENA': 'ARENA_MAX',
                  'ALL': '三个全开'}[nm],
             ['%.4f' % x for x in a], statistics.median(r), min(r), max(r)))
print('  PLAIN 中位 = %.4f s' % statistics.median(base))
PYEOF

echo "" | tee -a "$LOG"
echo "--- 峰值 RSS（单臂各一次；用 /usr/bin/time -v）---" | tee -a "$LOG"
for arm in "${ARMS[@]}"; do
  EV=$(env_of "$arm")
  OUTF="_w2_r577_alloc_${arm}_rss_${SUF}.log"
  env $EV R576_TAG="${arm}rss" R576_OUT="$OUTF" \
      /usr/bin/time -v "$PY" _r576_prof.py > "_w2_r577_alloc_${arm}_rss_stdout.log" 2>&1
  RSS=$(grep -m1 'Maximum resident set size' "_w2_r577_alloc_${arm}_rss_stdout.log" | grep -oE '[0-9]+')
  CL=$(sed -n 's/.*干净单步（钩子关）= \*\*\([0-9.]*\) s.*/\1/p' "$OUTF" | head -1)
  echo "  $arm: peakRSS=$(( ${RSS:-0} / 1024 )) MB   clean=$CL" | tee -a "$LOG"
done
echo "=== R577 ALLOC 分解 DONE $(date '+%F %T') ===" | tee -a "$LOG"
