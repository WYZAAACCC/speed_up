#!/bin/bash
# _r578_r3_ab.sh --- R578：goal §(3) 三项（k_loop=act / act=bincount / argmin2=copyto）
#   的**逐个 + 合并**交错配对 A/B（都用 `_r576_prof.py` 的全量记账量具）。
#
# ## ★★ v1 的两个错（都记账，`AGENTS.md` §7.5 P1/P8 同族）
#   ① **臂顺序固定**（BASE, KLOOP, ACTBC, ARG2, ALL3, ALL5 每轮都一样）
#      ⇒ 一个轮次内跨 ~4 min，而宿主在这段时间里会漂 ⇒ **排在最后的臂系统性占便宜**。
#      实测 v1 的 ALL5：r1=0.4267 r2=0.3450 r3=0.2529（单调变快）——**这就是漂移，不是改进**。
#      ⇒ 必须**轮换顺序**（拉丁方），把"位置"这个混杂因子消掉。
#   ② `run_arm` 既 `tee` 到 stdout 又 `echo "$CL"` ⇒ `$(run_arm …)` 抓到**多行**
#      ⇒ 汇总解析崩（参数个数 252 != 18）。⇒ 改为写**全局变量**。
#
# 判据（先写死）：
#   R-1 每一臂 P0/P0b/P1/P2/P2b/P2c/P3/P5 全 PASS；
#   R-2 **计数回归**：`k_loop` 臂的 `adv.step.vnk` 必须从 25.00/步 掉到活跃场数；
#   R-3 墙钟只报**每轮配对比值**的中位与区间；
#   R-4 逐项与合并都要报（goal 成功判据④：给出构成分解）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export R576_N="${R578_N:-64}" R576_NV="${R578_NV:-24}"
export R576_STEPS="${R576_STEPS:-6}" R576_WORKERS="${R576_WORKERS:-4}"
ROUNDS="${R578_ROUNDS:-3}"
SUF="${R576_NV}x${R576_N}_w${R576_WORKERS}"
LOG=_w2_r578_r3ab.log
: > "$LOG"

_ARMS=(BASE KLOOP ACTBC ARG2 ALL3 ALL5)
_env_of() {
  case "$1" in
    BASE)  echo "R578_NOOP=1" ;;
    KLOOP) echo "R561_KLOOP=act" ;;
    ACTBC) echo "R561_ACT=bincount" ;;
    ARG2)  echo "R561_ARG2=copyto" ;;
    ALL3)  echo "R561_KLOOP=act R561_ACT=bincount R561_ARG2=copyto" ;;
    ALL5)  echo "R561_KLOOP=act R561_ACT=bincount R561_ARG2=copyto R561_EPS0=einsum R561_EDPAIR=gather" ;;
  esac
}
_LAST=""
run_arm() {   # run_arm <标签> <ENV字符串>  ⇒ 结果写进全局 _LAST
  local tag="$1"; local ev="$2"
  local OUTF="_w2_r578_r3_${tag}_${SUF}.log"
  env $ev R576_TAG="$tag" R576_OUT="$OUTF" "$PY" _r576_prof.py \
      > "_w2_r578_r3_${tag}_stdout.log" 2>&1
  local CL VN VD
  CL=$(sed -n 's/.*干净单步（钩子关）= \*\*\([0-9.]*\) s.*/\1/p' "$OUTF" | head -1)
  VN=$(grep -E 'adv\.step\.vnk +[0-9]' "$OUTF" | head -1 | grep -oE '[0-9]+\.[0-9]+/步' | head -1)
  VD=$(grep -E '^  P0=' "$OUTF")
  echo "  $tag clean=$CL vnk=$VN  |  $VD" | tee -a "$LOG"
  _LAST="$CL"
}

echo "=== R578 §(3) 逐项 + 合并 A/B（**轮换顺序**，$ROUNDS 轮）N=$R576_N NV=$R576_NV W=$R576_WORKERS ===" | tee -a "$LOG"
$PY _r576_hostfp.py | sed 's/^/  /' | tee -a "$LOG"
echo "  ⚠ 分配器口径：本脚本**不设** MALLOC_*（= PLAIN）。所有臂同一口径 ⇒ 比值有效。" | tee -a "$LOG"
echo "  ⚠ 臂顺序**每轮轮换 2 位**（拉丁方）—— v1 固定顺序时 ALL5 被宿主漂移系统性抬高。" | tee -a "$LOG"

declare -A RES
NA=${#_ARMS[@]}
for r in $(seq 1 "$ROUNDS"); do
  echo "---- round $r（顺序：从左偏移 $(( (r-1)*2 % NA )) 位）----" | tee -a "$LOG"
  for i in $(seq 0 $((NA-1))); do
    tag="${_ARMS[$(( (i + (r-1)*2) % NA ))]}"
    run_arm "${tag}r${r}" "$(_env_of "$tag")"
    RES[$tag]="${RES[$tag]:-}${_LAST} "
  done
done

echo "" | tee -a "$LOG"
echo "--- 汇总（相对 BASE 的每轮配对提速；>1 = 更快）---" | tee -a "$LOG"
$PY - "$ROUNDS" ${RES[BASE]} ${RES[KLOOP]} ${RES[ACTBC]} ${RES[ARG2]} ${RES[ALL3]} ${RES[ALL5]} <<'PYEOF' 2>&1 | tee -a "$LOG"
import sys, statistics
n = int(sys.argv[1]); v = [x for x in sys.argv[2:] if x.strip()]
names = ['BASE', 'KLOOP', 'ACTBC', 'ARG2', 'ALL3', 'ALL5']
assert len(v) == len(names) * n, '参数 %d != %d' % (len(v), len(names) * n)
d = {nm: [float(x) for x in v[i*n:(i+1)*n]] for i, nm in enumerate(names)}
b = d['BASE']
print('  BASE（全默认）  = %s   中位 %.4f s' % (['%.4f' % x for x in b], statistics.median(b)))
DESC = {'KLOOP': 'k_loop=act', 'ACTBC': 'act=bincount', 'ARG2': 'argmin2=copyto',
        'ALL3': '三项合并', 'ALL5': '三项 + einsum + gather'}
for nm in names[1:]:
    r = [x / y for x, y in zip(b, d[nm])]
    print('  %-6s(%-18s) = %s ⇒ **%.4fx**  区间 [%.4f, %.4f]'
          % (nm, DESC[nm], ['%.4f' % x for x in d[nm]],
             statistics.median(r), min(r), max(r)))
print('')
print('  构成分解（相对 BASE 的中位提速）：')
for nm in names[1:]:
    r = [x / y for x, y in zip(b, d[nm])]
    print('     %-6s %+.2f%%' % (nm, 100 * (statistics.median(r) - 1)))
PYEOF
echo "=== R578 §(3) A/B DONE $(date '+%F %T') ===" | tee -a "$LOG"
