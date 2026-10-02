#!/bin/bash
# _r581_crit5.sh --- ★★★★★ **判据⑤：滑动窗口真的恒定了磁盘**（要**曲线**，不是一句"恒定"）
#
# ## goal 判据⑤ 逐字
# > 「滑动窗口真的恒定了磁盘 | **跑 ≥3 个窗口周期，报 `ckpt` 目录大小随步数的曲线
# >   ⇒ 必须**平台化****」
#
# ## 设计
# * `--ckpt-every 2`、`--ckpt-keep 2`、`--steps 20` ⇒ **10 次写出 = 5 个窗口周期** ✓
# * **每次 `[ckpt ...]` 落盘后立刻采一次 `ckpt/` 的 `du`** ⇒ 得到**曲线**
# * **同时报** `ckpt/` 的**文件数**（A/B 应当恒为 ≤2）
#
# ## 判据（**预先写死**）
# | 观察 | 判定 |
# |---|---|
# | 写出 ≥5 次后，`ckpt/` 体积**不再单调增长**（后段与中段同量级，比值 ≤1.1） | **✅ 平台化** |
# | 体积**随写出次数线性增长** | **❌ 没平台化 ⇒ 滑动窗口失效** |
# | 文件数 > 2（`keep=2` 时） | **❌ A/B 交替失效** |
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT=_exp/_bk_nc7
TAG=nc7_s
LOG=_w2_r581_nc7.log
CURVE=_w2_r581_nc7_curve.tsv
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

say '=== 判据⑤：滑动窗口磁盘曲线（--ckpt-every 2 / --ckpt-keep 2 / 20 步 = 5 个周期）==='
[ -d "$ROOT/dry_$TAG" ] && mv "$ROOT/dry_$TAG" "$ROOT/dry_${TAG}_superseded_$(date '+%Y%m%d_%H%M%S')"
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range(20)))")
: > "$CURVE"
printf 'step\tMB\tfiles\n' >> "$CURVE"

CDIR="$ROOT/dry_$TAG/ckpt"
(
  # ★ 采样器：每 2 s 采一次 `ckpt/` 的体积与文件数（**不改仿真**）
  for _i in $(seq 1 900); do
    if [ -d "$CDIR" ]; then
      _mb=$(du -sm "$CDIR" 2>/dev/null | cut -f1)
      _nf=$(ls -1 "$CDIR" 2>/dev/null | wc -l)
      # 用 ckpt 文件的 mtime 近似"第几次写出"
      _last=$(ls -1t "$CDIR"/ckpt*.npz 2>/dev/null | head -1)
      _st=$(basename "$_last" 2>/dev/null | grep -oE '[0-9]{6}' | head -1)
      printf '%s\t%s\t%s\n' "${_st:-?}" "${_mb:-0}" "${_nf:-0}" >> "$CURVE"
    fi
    sleep 2
  done
) &
SAMP=$!

timeout 2400 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
  taskset -c 0-7 $PY -u _bk_exp.py \
  --N 64 --dx-nm 62.5 --steps 20 --every 20 --snap-every 200 --pair-every 50 \
  --nthreads 4 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 5 \
  --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --reinit-dt 1e-4 --reinit-band 6.0 \
  --nuc-overlap-nm 62.5 --pf-phi onfly --h-chunk 4 \
  --ckpt-every 2 --ckpt-keep 2 --ckpt-atomic 1 \
  --out "$ROOT" --tag "$TAG" --laths "$laths" > "_w2_r581_nc7_${TAG}.log" 2>&1
say "  跑完：exit=$?  Traceback=$(grep -c '^Traceback' _w2_r581_nc7_${TAG}.log 2>/dev/null | head -1)"
kill "$SAMP" 2>/dev/null

say '── 引擎的 [ckpt …] 日志（每次写出）──'
grep '\[ckpt' "_w2_r581_nc7_${TAG}.log" 2>/dev/null | sed 's/^/  /'
say '── 最终 ckpt/ 内容 ──'
ls -la "$CDIR" 2>/dev/null | sed 's/^/  /'

say '── ★ 磁盘曲线（去重后的采样点）──'
$PY - "$CURVE" <<'PYEOF' 2>&1 | tee -a "$LOG"
import csv, sys
rows = list(csv.DictReader(open(sys.argv[1], encoding='utf-8', errors='replace'),
                           delimiter='\t'))
seen = {}
for r in rows:
    k = (r['step'], r['MB'], r['files'])
    seen[k] = seen.get(k, 0) + 1
pts = sorted(seen, key=lambda x: (x[0] == '?', x[0]))
print('  %-10s %-10s %-8s %s' % ('末帧步号', 'ckpt MB', '文件数', '采样次数'))
print('  ' + '-' * 44)
for k in pts[:24]:
    print('  %-10s %-10s %-8s %d' % (k[0], k[1], k[2], seen[k]))
mbs = [int(k[1]) for k in pts if k[1].isdigit()]
nfs = [int(k[2]) for k in pts if k[2].isdigit()]
print()
if len(mbs) >= 3:
    mid = mbs[len(mbs) // 3]
    end = mbs[-1]
    print('  ★ 前 1/3 中位体积 = %d MB ；末态 = %d MB ；比值 = %.2f'
          % (mid, end, end / max(mid, 1)))
    if end <= max(mid, 1) * 1.1:
        print('     ⇒ ✅ **平台化**（末态未显著超过前段 ⇒ 滑动窗口生效）')
    else:
        print('     ⇒ ❌ **没平台化**（末态仍显著增长）')
    print('  ★ 文件数：最大 %d（keep=2 ⇒ 应 ≤2+A/B 各一）%s'
          % (max(nfs), '✅' if max(nfs) <= 2 else '❌'))
else:
    print('  ⚠ 采样点不足（%d 个）⇒ 无法判定' % len(mbs))
PYEOF
say '=== CRIT5 DONE ==='
