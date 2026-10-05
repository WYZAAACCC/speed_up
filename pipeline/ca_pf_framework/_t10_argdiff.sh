#!/bin/bash
# 对比各启动器的 _t5_short.py 参数，找 t10B9 与"能跑通"那几跑的差异
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for f in _t10_eta253.sh _t10_fix_run.sh _t10_cl2run.sh _t10_prtrun.sh _t10_b9run2.sh; do
  echo "════ $f ════"
  if [ -f "$f" ]; then
    # 取从 _t5_short.py 开始到行尾（含续行）的参数串
    awk '/_t5_short\.py/{p=1} p{printf "%s ", $0} p&&!/\\$/{exit}' "$f" \
      | tr -s ' ' | sed 's/  */ /g' | cut -c1-400
    echo
    echo -n "  含 --nuc-sites-refill ？ "; grep -c 'nuc-sites-refill' "$f"
    echo -n "  含 --nuc-init ？        "; grep -c 'nuc-init' "$f"
    echo -n "  含 --B ？               "; grep -cE '\-\-B [0-9]' "$f"
    echo -n "  含 SEED_ ？             "; grep -c 'SEED_' "$f"
  else
    echo "  （不存在）"
  fi
  echo
done
echo "════ 参数集合差异（t10B9 vs t10PRT2）════"
for f in _t10_prtrun.sh _t10_b9run2.sh; do
  [ -f "$f" ] && awk '/_t5_short\.py/{p=1} p{printf "%s ", $0} p&&!/\\$/{exit}' "$f" \
    | tr ' ' '\n' | grep -E '^--' | sort -u > /tmp/args_$(basename $f .sh).txt
done
if [ -f /tmp/args__t10_prtrun.txt ] && [ -f /tmp/args__t10_b9run2.txt ]; then
  echo "  只在 t10PRT2 有（★ = t10B9 缺的）："
  comm -23 /tmp/args__t10_prtrun.txt /tmp/args__t10_b9run2.txt | sed 's/^/    ★ /'
  echo "  只在 t10B9 有："
  comm -13 /tmp/args__t10_prtrun.txt /tmp/args__t10_b9run2.txt | sed 's/^/      /'
fi
echo
echo "════ R481_NUC_SITES.md 的结论段（前 60 行）════"
head -60 R481_NUC_SITES.md 2>/dev/null | sed 's/^/  /'
