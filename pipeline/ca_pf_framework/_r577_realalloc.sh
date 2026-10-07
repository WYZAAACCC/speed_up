#!/bin/bash
# _r577_realalloc.sh --- R577 §2.4 第①②③条：把分配器效应搬到**真实路径**（`_bk_exp.py`）上验证。
#
# 为什么必须做：`_r577_alloc_ab.sh` 量的是**引擎单步**。真实路径还有形核/测量/落盘/CSV，
#   占比会被稀释；而且 `_r569_smoke.sh`（真实路径冒烟）**本身就设了那三个变量**
#   ⇒ R561–R576 的所有"真实路径"数字**都是在慢路上量的**。
#   按项目纪律：**单元量具过 ≠ 真实路径过。**
#
# 判据（先写死）：
#   R-1 两臂都 exit 0、Traceback = 0；
#   R-2 两臂的 `series.csv` **共有列逐位一致**（分配器不参与数值 ⇒ 必须逐位相同）；
#   R-3 报**每轮配对**的 s/步 比值（末 6 次打印的中位），不报单点。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1

COMMON="--N 64 --dx-nm 62.5 --steps 30 --every 5 --snap-every 30 \
        --pair-every 30 --norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
        --grow-stack --eng-cadence 30 --nuc-overlap-nm 62.5 --out _exp/_bk_eng"

ROUNDS="${R577_ROUNDS:-2}"
LOG=_w2_r577_realalloc.log
: > "$LOG"
echo "=== R577 REAL-ALLOC A/B  ROUNDS=$ROUNDS  $(date '+%F %T') ===" | tee -a "$LOG"
$PY _r576_hostfp.py | sed 's/^/  /' | tee -a "$LOG"

med() { grep -oE '[0-9]+\.[0-9]+s/步' "$1" | tail -6 | sed 's#s/步##' | sort -n | \
        awk '{a[NR]=$1} END{if(NR>0) printf "%.4f", (a[int((NR+1)/2)]+a[int((NR+2)/2)])/2}'; }

for r in $(seq 1 "$ROUNDS"); do
  for arm in plain tuned; do
    if [ "$arm" = tuned ]; then
      EV="MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2"
    else
      EV="R577_NOOP=1"
    fi
    TAG="r577_${arm}${r}"
    L="_w2_r577_real_${TAG}.log"
    rm -rf "_exp/_bk_eng/dry_${TAG}"
    env $EV /usr/bin/time -v "$PY" -u _bk_exp.py $COMMON --tag "$TAG" > "$L" 2>&1
    RC=$?
    RSS=$(grep -m1 'Maximum resident set size' "$L" | grep -oE '[0-9]+')
    TB=$(grep -c 'Traceback' "$L" || true)
    M=$(med "$L")
    echo "round $r $arm rc=$RC s/step=$M peakRSS=$(( ${RSS:-0} / 1024 ))MB traceback=$TB" \
      | tee -a "$LOG"
  done
done

echo "" | tee -a "$LOG"
echo "--- R-2 共有列逐位一致（分配器不参与数值，必须 0）---" | tee -a "$LOG"
$PY - "$ROUNDS" <<'PYEOF' 2>&1 | tee -a "$LOG"
import os, sys
import numpy as np
R = '_exp/_bk_eng'
n = int(sys.argv[1])


def rd(tag):
    p = os.path.join(R, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None, None
    with open(p) as fh:
        hdr = fh.readline().strip().split(',')
    return hdr, p


bad = False
for r in range(1, n + 1):
    h1, p1 = rd('r577_plain%d' % r)
    h2, p2 = rd('r577_tuned%d' % r)
    if not p1 or not p2:
        print('  ❌ 缺文件 round %d（%s / %s）' % (r, p1, p2)); bad = True; continue
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
    print('  round %d：共有列 %d 个；最大相对差 = %.3e（%s）⇒ %s'
          % (r, len(common), worst, wc,
             '✅ 逐位一致' if worst == 0.0 else '❌ 有差异'))
    bad = bad or (worst != 0.0)
print('  ⇒ R-2 总判定：%s' % ('✅ PASS' if not bad else '❌ FAIL'))
PYEOF
echo "=== R577 REAL-ALLOC DONE $(date '+%F %T') ===" | tee -a "$LOG"
