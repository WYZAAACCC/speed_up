#!/bin/bash
# _r239_edvtest.sh —— `--diag-edv`（`§135.6` 条件③主线）的接线测试。
#
# ## 判据（**先写死**）
# * **V-0** 语法通过。
# * **V-1** 开着时：日志出现 `★★ **逐变体 \`ed\``，且 `diag_edv.json` 落盘。
# * **V-2** **负对照**：不传时**不得**有打印、**不得**有文件。
# * **V-3** ★ **内建正对照**：所有变体的**体积之和**必须 ≈ 该步的 `Vt`
#   （因每个 `karr==v` 的胞恰好属于变体 v）—— 这是白送的精确对照。
# * **V-4** 变体号必须是**真实变体**（来自 `vmap`），不是场号；
#   且**同变体的多个场**必须出现（本算例 `1,1,2,2` ⇒ 场1/场2 都是 V1）。
# * **V-5** 退化：`--laths 1`（单场）时不得崩。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

echo "=== V-0 语法 ==="
"$PY" -m py_compile windowB_surface.py _bk_exp.py && echo "  ✅ OK" || exit 1

COMMON="--arm dry --N 32 --dx-nm 125 --laths 1,1,2,2 --gap-nm 0 \
        --steps 6 --every 2 --snap-every 6 --pair-every 0 --nthreads 2"
rm -rf _exp/_bk_edv

echo
echo "=== V-1/V-3/V-4：开着 --diag-edv ==="
"$PY" -u _bk_exp.py $COMMON --diag-edv --tag edvON --out _exp/_bk_edv \
      > _w2_r239_on.log 2>&1
echo "  退出码 = $?"
grep -c '逐变体' _w2_r239_on.log
echo "  --- 最后一次明细 ---"
grep -A8 '逐变体 `ed`' _w2_r239_on.log | tail -9

echo
echo "=== V-2：负对照（不传）==="
"$PY" -u _bk_exp.py $COMMON --tag edvOFF --out _exp/_bk_edv \
      > _w2_r239_off.log 2>&1
echo "  退出码 = $?；'逐变体' 命中 = $(grep -c '逐变体' _w2_r239_off.log || true)"

echo
echo "=== 判据汇总 ==="
F=_exp/_bk_edv/dry_edvON/diag_edv.json
[ -f "$F" ] && echo "  V-1 落盘 ✅" || echo "  V-1 落盘 ❌"
[ -f _exp/_bk_edv/dry_edvOFF/diag_edv.json ] && echo "  V-2 负对照 ❌ 不该有文件" \
  || echo "  V-2 负对照 ✅ 无文件"
if [ -f "$F" ]; then
  "$PY" - "$F" "_exp/_bk_edv/dry_edvON/series.csv" <<'PY'
import json, sys, csv
d = json.load(open(sys.argv[1]))
rows = list(csv.DictReader(open(sys.argv[2])))
Vt = {int(float(r['step'])): float(r['Vt']) for r in rows}
print('  V-1 记录条数 = %d' % d['n_rec'])
last = d['rec'][-1]
pf = last['per_field']
vol = sum(v['vol_um3'] for v in pf.values())
st = last['step']
print('  末条 step=%s：%d 个场' % (st, len(pf)))
for k in sorted(pf, key=lambda x: int(x)):
    v = pf[k]
    print('     场%-3d → V%-3d  体积 %-9.4f µm³  ed 中位 %+.4e'
          % (v['field'], v['variant'], v['vol_um3'], v['med']))
print('  V-3 Σ体积 = %.4f µm³ ；该步 Vt = %.4f µm³ ⇒ 相对差 %.3f%% ⇒ %s'
      % (vol, Vt.get(st, float('nan')) * 1e18,
         100 * abs(vol - Vt.get(st, 0) * 1e18) / max(Vt.get(st, 1e-30) * 1e18, 1e-30),
         '✅ 通过' if abs(vol - Vt.get(st, 0) * 1e18)
         / max(Vt.get(st, 1e-30) * 1e18, 1e-30) < 0.05 else '❌'))
print('  ⚠ 记账（**第 22 个自查错误**）：第一版拿 `vol`（**µm³**）直接和')
print('     `series.csv` 的 `Vt`（**m³**）比 ⇒ 打出 1e20% 的荒谬相对差。')
print('     **单位不同的量不能直接比** —— 与硬规则⑫（同精度）同源，此处是"同单位"。')
vs = sorted(set(v['variant'] for v in pf.values()))
print('  V-4 出现的变体 = %s（应为 [1,2]）；场数 %d（>变体数 ⇒ 同变体多场）⇒ %s'
      % (vs, len(pf), '✅' if vs == [1, 2] and len(pf) > len(vs) else '⚠ 检查'))
PY
fi
echo
echo "=== V-5 退化：--laths 1 ==="
"$PY" -u _bk_exp.py --arm dry --N 24 --dx-nm 125 --laths 1 --gap-nm 0 \
  --steps 2 --every 1 --snap-every 2 --pair-every 0 --nthreads 2 \
  --diag-edv --tag edvN1 --out _exp/_bk_edv > _w2_r239_n1.log 2>&1
echo "  退出码 = $? · Traceback=$(grep -c Traceback _w2_r239_n1.log || true)"
