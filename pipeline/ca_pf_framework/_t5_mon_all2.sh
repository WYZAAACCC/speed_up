#!/bin/bash
# _t5_mon_all2.sh --- 把 `t5NR` 纳入两路监控（几何 + 块/块间）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python

echo '════ ① 几何监控：TAGS 加入 t5NR ════'
# 幂等插入（若已存在则不重复）
if ! grep -q "'t5NR'" _t5_armon.py; then
  $PY - <<'PYEOF'
P = '_t5_armon.py'
s = open(P, encoding='utf-8').read()
old = "        't5N276',"
new = "        't5N276', 't5NR',"
assert old in s, '锚点没找到'
s = s.replace(old, new, 1)
compile(s, P, 'exec')
open(P, 'w', encoding='utf-8').write(s)
print('  ✅ TAGS 已加入 t5NR')
PYEOF
else
  echo '  （已存在，跳过）'
fi

echo
echo '════ ② 块监控：改为**多臂**并重启（t5N276,t5NR）════'
$PY -m py_compile _t5_blkmon.py && echo '  语法 OK'
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[p]ython _t5_blkmon' | awk '{print $1}'); do
  kill -TERM "$P" 2>/dev/null && echo "  已停旧块监控 pid=$P"
done
sleep 3

echo
echo '════ ③ 重启几何监控（让新 TAGS 生效）════'
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[p]ython _t5_armon' | awk '{print $1}'); do
  kill -TERM "$P" 2>/dev/null && echo "  已停旧几何监控 pid=$P"
done
sleep 3
setsid $PY _t5_armon.py 80 300 < /dev/null >> _w2_t5_ar_monitor.log 2>&1 &
setsid $PY _t5_blkmon.py 200 300 t5N276,t5NR < /dev/null >> _w2_t5_n276_monitor.log 2>&1 &
sleep 20

echo
echo '════ 核对（排除自匹配）════'
SNAP=$(ps -eo pid,args --no-headers 2>/dev/null)
for p in _t5_armon.py _t5_blkmon.py _t5_milewatch.py _t5_keeper_all.sh; do
  printf '  %-22s %s\n' "$p" "$(printf '%s\n' "$SNAP" | grep -c "$p")"
done
printf '  t5NR 引擎 = %s   t5N276 引擎 = %s\n' \
  "$(printf '%s\n' "$SNAP" | grep -c 'bk_exp.py.*--tag t5NR')" \
  "$(printf '%s\n' "$SNAP" | grep -c 'bk_exp.py.*--tag t5N276')"
echo
echo '── 块监控首轮（应同时报两臂）──'
grep -E '\[t5NR\]|\[t5N276\]' _w2_t5_n276_monitor.log 2>/dev/null | tail -4 | sed 's/^/  /'
