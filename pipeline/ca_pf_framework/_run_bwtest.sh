#!/usr/bin/env bash
# _run_bwtest.sh --- K 路并发聚合吞吐检验：`advance` 是算力受限还是带宽受限？
#
# 判据：
#   聚合 steps/s 随 K **线性**增长  ⇒ 算力受限（并行化值得做）
#   聚合 steps/s 随 K **持平**      ⇒ 带宽受限（并行化白干）
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
DX=${1:-250}
N0=${2:-64}
ST=${3:-8}
echo "########## 带宽/并行检验  Δx=${DX}nm n0=${N0} steps=${ST}  start=$(date -Is) ##########"
free -g | head -2
# K 列表可由环境变量覆盖（默认 1 2 4）。K=1→2 是判"线性 vs 持平"最关键的一步；
# 若机器上还有别的重作业在跑，先只跑 "1 2"，避免把那个作业挤成 OOM。
KLIST="${KLIST:-1 2 4}"

for K in $KLIST; do
  echo ""
  echo "===== K=${K} 路并发 ====="
  rm -f _bw_K${K}_*.log
  T0=$(date +%s.%N)
  for i in $(seq 1 "$K"); do
    "$PY" -u _bench_adv.py --L-um 24 --dx-nm "$DX" --n0 "$N0" --steps "$ST" \
        --no-bw --tag "K${K}-${i}" > "_bw_K${K}_${i}.log" 2>&1 &
  done
  wait
  T1=$(date +%s.%N)
  "$PY" -u - "$K" "$T0" "$T1" <<'PYEOF'
import re, sys, glob
K = int(sys.argv[1]); T0 = float(sys.argv[2]); T1 = float(sys.argv[3])
wall = T1 - T0
sps = []
build = []
for f in sorted(glob.glob('_bw_K%d_*.log' % K)):
    txt = open(f, errors='replace').read()
    m = re.search(r'sps=([\d.]+)', txt)
    b = re.search(r'build=([\d.]+)s', txt)
    if m:
        sps.append(float(m.group(1)))
    if b:
        build.append(float(b.group(1)))
print('   K=%d  各进程 steps/s = %s' % (K, ' '.join('%.4f' % x for x in sps)))
if build:
    print('        （各自构造耗时 %.0f s，不计入 steps/s）' % (sum(build) / len(build)))
if sps:
    print('   K=%d  **聚合 steps/s = %.4f**   总墙钟 = %.1f s（含构造）'
          % (K, sum(sps), wall))
PYEOF
  sleep 5
done

echo ""
echo "--- 汇总 ---"
grep -h -e "^BENCH_BW" _bw_K1_1.log 2>/dev/null || true
"$PY" -u - <<'PYEOF'
import re, glob
rows = []
for K in (1, 2, 4):
    sps = []
    for f in sorted(glob.glob('_bw_K%d_*.log' % K)):
        m = re.search(r'sps=([\d.]+)', open(f, errors='replace').read())
        if m:
            sps.append(float(m.group(1)))
    if sps:
        rows.append((K, len(sps), sum(sps)))
print('   %-4s %-6s %s' % ('K', '成功', '聚合 steps/s'))
base = None
for K, n, tot in rows:
    if base is None:
        base = tot
    print('   %-4d %-6d %.4f   （相对 K=1：×%.2f，线性应为 ×%d）'
          % (K, n, tot, tot / base, K))
if len(rows) >= 2:
    eff = rows[-1][2] / base / rows[-1][0]
    print('')
    print('   ⇒ 并行效率 = %.2f（1.00 = 完美线性；≈0 = 完全带宽受限）' % eff)
    if eff > 0.7:
        print('   ⇒ **算力受限** ⇒ 并行化 `advance` 值得做')
    elif eff < 0.35:
        print('   ⇒ **带宽受限** ⇒ 并行化 `advance` 收益有限')
    else:
        print('   ⇒ 混合：部分收益')
PYEOF
echo "########## 结束 end=$(date -Is) ##########"
