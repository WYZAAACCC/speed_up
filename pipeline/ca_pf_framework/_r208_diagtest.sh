#!/bin/bash
# _r208_diagtest.sh —— `--diag-terms`（`§135.7` 的决定性检验）的**接线测试**。
#
# ## 判据（**先写死**）
# * **D-0** 两个文件 `py_compile` 通过（语法）。
# * **D-1** ★ **内建正对照**：诊断里的 `med_df` 必须**恰好 0.000e+00** ——
#   因为 `_bk_exp.py:586` 给**所有** α′ 变体同一个 `df` ⇒ `df_k−df_l ≡ 0`。
#   **若不为 0 ⇒ 我的 `karr/larr` 索引接错了**（这是白送的精确对照）。
# * **D-2** 开着 `--diag-terms` 时：日志出现 `★★ **三项量级**`，且 `diag_terms.json` 落盘。
# * **D-3** **负对照**：**不**开时，日志里**不得**出现 `三项量级`，且**不得**有
#   `diag_terms.json`（否则打印没门控 ⇒ 会误导读数的人）。
# * **D-4** `med_sk ≥ 0` 且有限；`med_ed` 有限且 > 0（有界面就该有驱动）。
# * **D-5** 有变体-变体界面（`karr>0 & larr>0`）时 `n_vv > 0`（否则口径没生效）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

echo "=== D-0 语法 ==="
"$PY" -m py_compile windowB_surface.py _bk_exp.py && echo "  ✅ 两个文件语法 OK" \
  || { echo "  ❌ 语法错误"; exit 1; }

COMMON="--arm dry --N 32 --dx-nm 125 --laths 1,1,2,2 --gap-nm 0 \
        --steps 6 --every 2 --snap-every 6 --pair-every 0 --nthreads 2"
rm -rf _exp/_bk_dt

echo
echo "=== D-2/D-4/D-5：开着 --diag-terms ==="
"$PY" -u _bk_exp.py $COMMON --diag-terms --tag dtON --out _exp/_bk_dt \
      > _w2_r208_on.log 2>&1
RC1=$?
echo "  退出码 = $RC1"
grep -E '三项量级' _w2_r208_on.log | head -4 | sed 's/^/  /'
NON=$(grep -c '三项量级' _w2_r208_on.log || true); NON=${NON:-0}
echo "  '三项量级' 行数 = $NON"

echo
echo "=== D-3：负对照（不传 --diag-terms）==="
"$PY" -u _bk_exp.py $COMMON --tag dtOFF --out _exp/_bk_dt \
      > _w2_r208_off.log 2>&1
RC2=$?
echo "  退出码 = $RC2"
NOFF=$(grep -c '三项量级' _w2_r208_off.log || true); NOFF=${NOFF:-0}
echo "  '三项量级' 行数 = $NOFF（应为 0）"

echo
echo "=== 判据汇总 ==="
F_ON=_exp/_bk_dt/dry_dtON/diag_terms.json
F_OFF=_exp/_bk_dt/dry_dtOFF/diag_terms.json
[ "$NON" -ge 1 ] && echo "  D-2 开着时有打印        ✅" || echo "  D-2 开着时有打印        ❌"
[ -f "$F_ON" ] && echo "  D-2 diag_terms.json 落盘 ✅" || echo "  D-2 diag_terms.json 落盘 ❌"
[ "$NOFF" = "0" ] && echo "  D-3 关着时无打印        ✅ 门控正确" || echo "  D-3 关着时无打印        ❌ 打印没门控"
[ -f "$F_OFF" ] && echo "  D-3 关着时无落盘        ❌ 不该有文件" || echo "  D-3 关着时无落盘        ✅"

echo
echo "=== D-1/D-4/D-5：读 diag_terms.json ==="
if [ -f "$F_ON" ]; then
  "$PY" - "$F_ON" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
rec = d.get('rec') or []
print('  记录条数 = %d' % len(rec))
if not rec:
    print('  ❌ 没有记录'); sys.exit(1)
last = rec[-1]
for k in ('step', 'n_vv', 'med_df', 'med_ed', 'med_sk', 'med_ratio'):
    print('    %-10s = %s' % (k, last.get(k)))
ok1 = all(abs(r.get('med_df') if isinstance(r.get('med_df'), (int, float))
              else 1.0) < 1e-12
          for r in (x.get('vv') or {} for x in rec) if 'med_df' in r)
print('  D-1 `F2` 的 `med_df` 全部恰好 0（期望，因所有变体同 df）⇒ %s'
      % ('✅ 通过' if ok1 else '❌ **失败 ⇒ karr/larr 索引接错了**'))
ok4 = all((r.get('med_sk') if isinstance(r.get('med_sk'), (int, float)) else -1) >= 0
          and (r.get('med_ed') if isinstance(r.get('med_ed'), (int, float)) else 0) > 0
          for r in (x.get('vv') or {} for x in rec) if 'med_sk' in r)
print('  D-4 F2 的 med_sk≥0 且 med_ed>0 ⇒ %s' % ('✅' if ok4 else '❌'))
ok5 = any((x.get('vv') or {}).get('n', 0) > 0 for x in rec)
print('  D-5 出现过 **F2（异变体）** 界面胞 ⇒ %s' % ('✅' if ok5 else '❌ 口径没生效'))
ok6 = any(x.get('vmap_split') for x in rec)
print('  D-6 `vmap` 拆分生效（F2/F3 分开了）⇒ %s' % ('✅' if ok6 else '❌ 没拆开'))
PY
else
  echo "  ❌ 无 diag_terms.json，D-1/D-4/D-5 无法判"
fi
echo
echo "=== 结束 ==="
