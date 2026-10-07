#!/usr/bin/env bash
# _r375_rate.sh -- 量每条臂的真实 s/步，判断是不是过度并发
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
date '+现在 %T'
for t in permB1_400 saSet2DT200 permB4_200 permB5_200; do
  f="_w2_r370_${t}.log"; [ -f "$f" ] || f="_w2_r372_${t}.log"
  line=$(grep -oE '^  \[ *[0-9]+\].*' "$f" 2>/dev/null | tail -1)
  sp=$(printf '%s' "$line" | grep -oE '[0-9.]+s/步' | tail -1)
  st=$(printf '%s' "$line" | grep -oE '^  \[ *[0-9]+\]' | tr -d ' []')
  printf '  %-14s 末步=%-5s s/步=%-8s\n' "$t" "${st:-?}" "${sp:-?}"
done
echo "--- 负载 ---"
uptime
echo "_bk_exp 进程数: $(pgrep -c -f '_bk_exp[.]py' || echo 0)"
free -g | head -2
