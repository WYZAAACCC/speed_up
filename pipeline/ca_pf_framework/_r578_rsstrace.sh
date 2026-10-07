#!/bin/bash
# _r578_rsstrace.sh --- R578：分配器 A/B 的**长跑 RSS 轨迹**（R577 §2.5 第①条）。
#
# ## 为什么必须做这一条
# R577 实测：`MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536`（仓库 124 个脚本的写法）
#   让**引擎单步慢 1.78×**、**真实路径慢 1.64×**，而**峰值 RSS 只省 10–19%**。
#   但那两个变量当年是为**控内存**加的（`_bk_run_block.sh:10`：「大块走 mmap ⇒ free 时真的归还」，
#   担心的是**长跑 RSS 越滚越大 ⇒ WSL 24 GB 撞 swap**）。
#   ⇒ **峰值降 10% 不等于长跑不涨。** 必须看**轨迹**，不是峰值。
#
# ## 判据（先写死，必须能失败）
#   T-1 两臂 exit 0、Traceback = 0；
#   T-2 采样点数 ≥ 20（否则轨迹没有分辨力）；
#   T-3 报每条轨迹的 `RSS_first / RSS_last / RSS_max / 线性斜率(MB/100步)`；
#   T-4 **两臂 `series.csv` 共有列逐位一致**（分配器不参与数值）。
#   判据本身**不预设结论**：既可能"PLAIN 会涨"（那 mmap 阈值必须保留），
#   也可能"PLAIN 不涨"（那 1.64× 就是白送的）。**两种结论都接受，但必须实测。**
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1

STEPS="${R578_STEPS:-200}"
N="${R578_N:-96}"
SAMPLE_S="${R578_SAMPLE:-5}"
OUT="${R578_OUT:-_w2_r578_rss}"

# 与 `_r30_regress.sh` **同一条命令行**（这样轨迹可以直接与回归产物对账）
COMMON="--N $N --dx-nm 62.5 --steps $STEPS --every 10 --snap-every $STEPS \
        --pair-every 10 --norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
        --grow-stack --eng-cadence 30 --nuc-overlap-nm 62.5 --out _exp/_bk_eng"

LOG=${OUT}.log
: > "$LOG"
echo "=== R578 RSS TRACE  N=$N steps=$STEPS sample=${SAMPLE_S}s  $(date '+%F %T') ===" | tee -a "$LOG"
$PY _r576_hostfp.py | sed 's/^/  /' | tee -a "$LOG"

for arm in plain tuned; do
  if [ "$arm" = tuned ]; then
    EV="MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2"
  else
    EV="R578_NOOP=1"
  fi
  TAG="r578${arm}"
  L="${OUT}_${arm}_run.log"
  TR="${OUT}_${arm}.trace"
  rm -rf "_exp/_bk_eng/dry_${TAG}"
  : > "$TR"
  echo "" | tee -a "$LOG"
  echo "---- 臂 $arm ----" | tee -a "$LOG"
  env $EV "$PY" -u _bk_exp.py $COMMON --tag "$TAG" > "$L" 2>&1 &
  PID=$!
  # ★ 采样：读 `/proc/<pid>/status` 的 VmRSS（内核直接给，不走 9p，没有缓存问题）
  while kill -0 "$PID" 2>/dev/null; do
    R=$(awk '/^VmRSS:/{print $2}' "/proc/$PID/status" 2>/dev/null)
    S=$(grep -oE '\[ *[0-9]+\]' "$L" 2>/dev/null | tail -1 | tr -dc '0-9')
    [ -n "$R" ] && echo "$(date +%s) ${S:-0} $R" >> "$TR"
    sleep "$SAMPLE_S"
  done
  wait "$PID"; RC=$?
  TB=$(grep -c 'Traceback' "$L" || true)
  echo "  rc=$RC  traceback=$TB  采样点=$(wc -l < "$TR")" | tee -a "$LOG"
  tail -2 "$L" | sed 's/^/    /' | tee -a "$LOG"
done

echo "" | tee -a "$LOG"
echo "--- 轨迹统计 ---" | tee -a "$LOG"
$PY - "$OUT" <<'PYEOF' 2>&1 | tee -a "$LOG"
import os, sys
out = sys.argv[1]
for arm in ('plain', 'tuned'):
    tr = '%s_%s.trace' % (out, arm)
    if not os.path.exists(tr):
        print('  %s: 缺轨迹文件' % arm); continue
    rows = []
    for ln in open(tr):
        p = ln.split()
        if len(p) == 3:
            rows.append((int(p[0]), int(p[1]), int(p[2])))
    if not rows:
        print('  %s: 轨迹为空' % arm); continue
    t0 = rows[0][0]
    rss = [r for _, _, r in rows]
    st = [s for _, s, _ in rows]
    print('  %-6s 采样 %3d 点  step %d→%d  RSS 首=%d MB 末=%d MB 峰=%d MB  '
          'Δ(末−首)=%+d MB'
          % (arm, len(rows), st[0], st[-1], rss[0] // 1024, rss[-1] // 1024,
             max(rss) // 1024, (rss[-1] - rss[0]) // 1024))
    # 线性斜率（MB / 100 步），只用后半段（前半段还在长场）
    half = rows[len(rows) // 2:]
    if len(half) >= 4 and half[-1][1] != half[0][1]:
        k = (half[-1][2] - half[0][2]) / 1024.0 / (half[-1][1] - half[0][1]) * 100.0
        print('         后半段斜率 = **%+.2f MB / 100 步**（step %d→%d）'
              % (k, half[0][1], half[-1][1]))
    print('         轨迹(MB)：%s'
          % ' '.join('%d' % (r // 1024) for _, _, r in rows[::max(1, len(rows) // 14)]))
PYEOF

echo "" | tee -a "$LOG"
echo "--- T-4 共有列逐位一致 ---" | tee -a "$LOG"
$PY - <<'PYEOF' 2>&1 | tee -a "$LOG"
import os
import numpy as np
R = '_exp/_bk_eng'


def rd(tag):
    p = os.path.join(R, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None, None
    with open(p) as fh:
        hdr = fh.readline().strip().split(',')
    return hdr, p


h1, p1 = rd('r578plain')
h2, p2 = rd('r578tuned')
if not p1 or not p2:
    print('  ❌ 缺文件：%s / %s' % (p1, p2))
else:
    a1 = np.genfromtxt(p1, delimiter=',', names=True)
    a2 = np.genfromtxt(p2, delimiter=',', names=True)
    common = [c for c in h1 if c in h2 and c != 'wall_s']
    worst, wc = 0.0, None
    for c in common:
        x = np.atleast_1d(a1[c]).astype(float)
        y = np.atleast_1d(a2[c]).astype(float)
        m = min(len(x), len(y))
        if m == 0:
            continue
        mx = float(np.max(np.abs(y[:m])))
        d = 0.0 if mx == 0.0 else float(np.max(np.abs(x[:m] - y[:m]))) / mx
        if d > worst:
            worst, wc = d, c
    print('  共有列 %d 个；最大相对差 = %.3e（%s）⇒ %s'
          % (len(common), worst, wc, '✅ 逐位一致' if worst == 0.0 else '❌ 有差异'))
PYEOF
echo "=== R578 RSS TRACE DONE $(date '+%F %T') ===" | tee -a "$LOG"
