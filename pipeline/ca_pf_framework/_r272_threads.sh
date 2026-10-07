#!/bin/bash
# _r272_threads.sh —— ★ **重新验证"advance 有没有正确多核并行"**（用户清单项）。
#
# ## 为什么要重验
# `§107` 曾证过并行逐位一致，但**此后改了 4 个文件**：
# `windowB_surface.py`（加 diag 块）、`windowB_lath.py`（perstep）、
# `_bk_measure.py`（f1_area）、`_bk_exp.py`（多个开关）。
# ⇒ **并行不变性必须用**当前代码**重证**（`AGENTS.md §3.3` 的教训：
#   "传承结论也要能算数才算数"）。
#
# ## 判据（**先写死**）
# * **T-1** 同一配置在不同 `--nthreads` 下，`series.csv` 的**物理列**（排除 `wall_s`）
#   必须**逐位相同**。
# * **T-2** ★ **负对照**：同一 `--nthreads` 跑两次也必须逐位相同
#   ⇒ 否则"不同线程数相同"没有意义（可能是随机性恰好没显出来）。
# * **T-3** 覆盖 1/2/4/8 线程（含 1 线程的**串行基准**）。
# * **T-4** 退化：`--nthreads 8` 但 N 很小（每线程分不到活）不得崩。
# * **T-5** 打印每臂的步时，确认多线程**确实在加速**（否则"并行"是假的）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

# 用**偏重**的配置（N=64、6 场、40 步）让多线程真的有事做
GEO="--arm dry --N 64 --dx-nm 125 --laths 1,1,2,2,3,3 --gap-nm 0 \
     --steps 40 --every 20 --snap-every 40 --pair-every 0 --out _exp/_bk_thr"
rm -rf _exp/_bk_thr

echo "=== advance 并行不变性复验 $(date '+%F %T') ==="
for T in 1 2 4 8; do
  $PY -u _bk_exp.py $GEO --nthreads $T --tag th$T  > "_w2_r272_th${T}.log" 2>&1 &
done
$PY -u _bk_exp.py $GEO --nthreads 2 --tag th2b > _w2_r272_th2b.log 2>&1 &
wait
echo "  全部跑完 $(date '+%T')"
echo
for f in _w2_r272_th1.log _w2_r272_th2.log _w2_r272_th4.log _w2_r272_th8.log _w2_r272_th2b.log; do
  printf '  %-24s rc/步时(末3)=%s ; Traceback=%s\n' "$f" \
    "$(grep -o '[0-9.]*s/步' "$f" | tail -3 | tr '\n' ' ')" \
    "$(grep -c Traceback "$f" || true)"
done
echo
echo "=== T-1/T-2/T-3：逐位比较 ==="
$PY - <<'PY'
import csv, io, os, sys
base = '_exp/_bk_thr'
SKIP = {'wall_s', 't_wall', 'elapsed_s', 'rss_mb', 'step_s'}
def rd(tag):
    p = os.path.join(base, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with io.open(p, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))
ref = rd('th1')
if ref is None:
    print('  ❌ th1 缺失'); sys.exit(1)
cols = [c for c in ref[0] if c not in SKIP and c != 'step']
print('  基准 th1：%d 行、%d 个可比列' % (len(ref), len(cols)))
ok = True
for tag in ('th2', 'th4', 'th8', 'th2b'):
    r = rd(tag)
    if r is None:
        print('  %-5s ❌ 缺失' % tag); ok = False; continue
    if len(r) != len(ref):
        print('  %-5s ⚠ 行数不同 %d vs %d' % (tag, len(r), len(ref))); ok = False; continue
    nd = 0; worst = (0.0, None)
    for i in range(len(ref)):
        for c in cols:
            a, b = ref[i].get(c), r[i].get(c)
            if a == b:
                continue
            try:
                fa, fb = float(a), float(b)
                if fa != fa and fb != fb:
                    continue
                d = abs(fa - fb) / max(abs(fa), abs(fb), 1e-300)
            except (TypeError, ValueError):
                d = 1.0
            nd += 1
            if d > worst[0]:
                worst = (d, c)
    tag_lbl = 'th2（**负对照**同线程两次）' if tag == 'th2b' else tag
    print('  %-28s 不同字段数 = %-6d 最大相对差 = %.3e (%s) ⇒ %s'
          % (tag_lbl, nd, worst[0], worst[1],
             '✅ 逐位相同' if nd == 0 else '❌ 有差异'))
    ok &= (nd == 0)
print()
print('  ⇒ %s' % ('✅ **T-1/T-2/T-3 全过**：advance 的并行实现在**当前代码**下逐位不变'
                   if ok else '❌ 有差异 ⇒ 并行不变性不成立，须查'))
PY
echo
echo "=== T-5：步时（确认多线程真的在加速）==="
$PY - <<'PY'
import re, io, os
for t in (1, 2, 4, 8):
    p = '_w2_r272_th%d.log' % t
    if not os.path.exists(p):
        continue
    txt = io.open(p, encoding='utf-8', errors='replace').read()
    st = [float(x) for x in re.findall(r'([0-9.]+)s/步', txt)]
    if st:
        # 丢掉第 0 步（含初始化）
        use = st[1:] if len(st) > 1 else st
        print('  nthreads=%-2d 步时中位 = %.3f s（共 %d 个样本）'
              % (t, sorted(use)[len(use)//2], len(use)))
PY
