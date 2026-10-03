#!/bin/bash
# _t5_mon_add276F.sh --- 把 `t5N276F` 纳入两路监控（几何 + 块/块间）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python

echo '════ ① 几何监控 TAGS 加入 t5N276F ════'
if ! grep -q "'t5N276F'" _t5_armon.py; then
  $PY - <<'PYEOF'
P = '_t5_armon.py'
s = open(P, encoding='utf-8').read()
old = "        't5N276', 't5NR',"
new = "        't5N276', 't5NR', 't5N276F',"
assert old in s, '锚点没找到'
s = s.replace(old, new, 1)
compile(s, P, 'exec')
open(P, 'w', encoding='utf-8').write(s)
print('  ✅ TAGS 已加入 t5N276F')
PYEOF
else
  echo '  （已存在）'
fi

echo
echo '════ ② 块监控：改为 t5N276,t5NR,t5N276F 并重启 ════'
$PY -m py_compile _t5_blkmon.py && echo '  语法 OK'
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[p]ython _t5_blkmon' | awk '{print $1}'); do
  kill -TERM "$P" 2>/dev/null && echo "  已停旧块监控 pid=$P"
done
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[p]ython _t5_armon' | awk '{print $1}'); do
  kill -TERM "$P" 2>/dev/null && echo "  已停旧几何监控 pid=$P"
done
sleep 3
setsid $PY _t5_armon.py 80 300 < /dev/null >> _w2_t5_ar_monitor.log 2>&1 &
setsid $PY _t5_blkmon.py 200 300 t5N276,t5NR,t5N276F < /dev/null >> _w2_t5_n276_monitor.log 2>&1 &
sleep 18

echo
echo '════ ③ 核对（排除自匹配）════'
SNAP=$(ps -eo pid,args --no-headers 2>/dev/null)
for p in _t5_armon.py _t5_blkmon.py _t5_milewatch.py _t5_arwatch.py _t5_ardist_ts.py _t5_freshwatch.py _t5_keeper_all.sh; do
  printf '  %-22s %s\n' "$p" "$(printf '%s\n' "$SNAP" | grep -c "python .*$p\|bash $p")"
done
printf '  t5N276F 引擎 = %s\n' "$(printf '%s\n' "$SNAP" | grep -c 'bk_exp.py.*--tag t5N276F')"
echo
echo '── 块监控首轮 ──'
grep -E '\[t5N276F\]|\[t5N276\]' _w2_t5_n276_monitor.log 2>/dev/null | tail -3 | sed 's/^/  /'
