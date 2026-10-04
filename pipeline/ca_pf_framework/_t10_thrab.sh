#!/bin/bash
# _t10_thrab.sh --- 判 `--nthreads`（workers）是否影响**逐位结果**
#
# ## 为什么要先判
# 实测主算例 `%CPU=260`（2.6 核）而 `--cores 0-15` 允许 16 核 ⇒ 提线程数是最大杠杆。
# 但 `workers=a.nthreads` 控制**空间切片分工**；`AGENTS.md` **P15** 只说
# 「空间切片的判据必须在 `workers > 1` 下跑」（暗示可复现），**没有**给出逐位判据。
# ⇒ 提线程数前必须先证逐位一致，否则主算例的可比性会被污染。
#
# ## 做法（**便宜的小构型，机制与 N 无关**）
# N=64 · nv=2×12=24 · 40 步 · 同一 seed ⇒ 只差 `--nthreads`。
# 判据：两个 `series.csv` 的 `Vt` / `nslab_n` / `ncomp_max` 列**逐位相同**，
#       且快照的 `region` 校验和相同。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t10_thrab.log
: > "$LOG"
{
  echo "════ `--nthreads` 逐位 A/B（N=64 · nv=24 · 40 步） $(date '+%m-%d %H:%M:%S') ════"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

for TH in 2 8; do
  TAG=thrab$TH
  rm -rf "_exp/_bk_t5/dry_$TAG" 2>/dev/null
  $PY _t5_short.py --tag $TAG --N 64 --dx-nm 62.5 --nvar 2 --m 12 --B 0 \
      --steps 40 --every 10 --snap-every 40 --pair-every 1000 --ckpt-every 0 \
      --overlap-nm 62.5 --eng-elong 7.00 --nthreads $TH --cores 0-7 \
      --mem-limit-gb 6 > _w2_t5_short_$TAG.log 2>&1
  echo "  [$TAG] 退出码=$?" >> "$LOG"
done

{
  echo ""
  echo "════ 逐位判据 ════"
} >> "$LOG"
$PY - >> "$LOG" 2>&1 <<'PY'
import csv, os, hashlib
import numpy as np
def rows(tag):
    p = '_exp/_bk_t5/dry_%s/series.csv' % tag
    if not os.path.exists(p): return None
    with open(p, newline='', encoding='utf-8', errors='replace') as fh:
        return list(csv.DictReader(fh))
A, B = rows('thrab2'), rows('thrab8')
if A is None or B is None:
    print("  ⚠ 缺 CSV：A=%s B=%s" % (A is not None, B is not None)); raise SystemExit
print("  行数 A=%d B=%d %s" % (len(A), len(B), "✓" if len(A)==len(B) else "❌"))
COLS = ['step','Vt','nslab_n','ncomp_max','nf3_col','nreg_used']
bad = 0
for i,(a,b) in enumerate(zip(A,B)):
    for c in COLS:
        if (a.get(c) or '') != (b.get(c) or ''):
            bad += 1
            if bad <= 6:
                print("    ❌ step=%s 列 %s : A=%r B=%r" % (a.get('step'), c, a.get(c), b.get(c)))
print("  CSV 逐位：不同处 = %d %s" % (bad, "✅ **逐位相同**" if bad==0 else "❌ **有差异 ⇒ 不可提线程数**"))
# 快照 region 校验和
for st in (0, 40):
    hs = []
    for tag in ('thrab2','thrab8'):
        f = '_exp/_bk_t5/dry_%s/snap_%05d.npz' % (tag, st)
        if not os.path.exists(f): hs.append(None); continue
        with np.load(f, allow_pickle=False) as z:
            r = np.asarray(z['region'])
            hs.append(hashlib.sha256(r.tobytes()).hexdigest()[:16])
    ok = hs[0] is not None and hs[0]==hs[1]
    print("  step=%d region sha256: A=%s B=%s %s" % (st, hs[0], hs[1], "✅" if ok else "❌"))
PY
echo "done $(date '+%H:%M:%S')" >> "$LOG"
