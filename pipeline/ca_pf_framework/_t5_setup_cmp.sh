#!/bin/bash
# _t5_setup_cmp.sh --- ★★★ 本次 A/B 与之前大实验的**参数逐项对照**（从日志里取，不凭记忆）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
show() {   # $1=日志文件  $2=标签
  local L=$1 T=$2
  [ -f "$L" ] || { printf '  %-12s （日志不存在）\n' "$T"; return; }
  printf '  ── %-12s ──\n' "$T"
  grep -oE '\-\-dx-nm [0-9.]+|N=[0-9]+|nv=[0-9]+|nvar=[0-9]+|m=[0-9]+|B=[0-9]+|steps=[0-9]+|--var-rule [a-z]+|--nuc-law [a-z]+|--eng-elong [0-9.]+|--facet-proj [0-9]+|--overlap-nm [0-9.]+|盒 *= *[0-9.]+ *µm|板条数 n *= *[0-9]+' "$L" 2>/dev/null \
    | sort -u | head -14 | sed 's/^/      /'
}
echo '════ ① 本次 A/B 与剂量臂（N=80）════'
show _w2_t5_ab_t5AB_A.log 't5AB_A(对照)'
show _w2_t5_ad_t5AD_700.log 't5AD_700(剂量7)'
echo
echo '════ ② 之前的大实验（N=160，长跑）════'
show _w2_t5_short_t5H3.log 't5H3(长跑)'
show _w2_t5_short_t5V2.log 't5V2(长跑)'
echo
echo '════ ③ 直接从启动器日志里抓"命令行"（最可靠）════'
for t in t5AB_A t5AD_700 t5H3 t5V2; do
  L=$(ls _w2_t5_ab_$t.log _w2_t5_ad_$t.log _w2_t5_short_$t.log 2>/dev/null | head -1)
  [ -n "$L" ] && { printf '  ── %s ──\n' "$t"; grep -m1 -oE '(\-\-[a-z0-9-]+ [^ ]+ ?)+' "$L" 2>/dev/null | head -1 | fold -w 150 | sed 's/^/      /'; }
done
