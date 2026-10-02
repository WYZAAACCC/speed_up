#!/bin/bash
# _r581_ask_state2.sh --- 补：负对照部分的证据 + 那个"1 个进程"到底是谁
cd "$(dirname "$0")" || exit 1
echo '════ ④（续）负对照部分的逐位证据 ════'
grep -E '^判据：|差异字段数|共有 step' _w2_r581_evidence.log | tail -14 | sed 's/^/  /'
echo
echo '════ ⑤ 那个"_bk_exp.py 进程数 = 1"是谁 ════'
ps -eo pid,ppid,etime,args --no-headers 2>/dev/null | grep '_bk_exp' | grep -v grep | cut -c1-140 | sed 's/^/  /'
echo '  （若上面为空 ⇒ 那个 1 是 grep/ps 自己，**没有算例在跑**）'
echo
echo '════ ⑥ 用 kill 那一组**当场再算一遍**（不读旧结论）════'
PY=/root/miniconda3/envs/ml/bin/python
echo '  A = dry_killC（**被杀后从 ckpt@4 恢复**）'
echo '  B = dry_killA（**从未中断**）'
taskset -c 16-19 $PY _r581_ckpt_cmp.py \
  _exp/_bk_kill/dry_killC/series.csv _exp/_bk_kill/dry_killA/series.csv step 2>&1 \
  | grep -E '共有 step|差异字段数|共有列逐位一致|Vt |f_var |nslab_n1|nf3 |nf2 ' | sed 's/^/    /'
echo
echo '════ ⑦ 两组 series.csv 的**原始字节**对比（旁证）════'
for c in Vt f_var nslab_n1; do
  echo "  ── 列 $c ──"
  paste -d'|' \
    <(cut -d, -f1,"$(head -1 _exp/_bk_kill/dry_killA/series.csv | tr ',' '\n' | grep -n "^$c$" | cut -d: -f1)" _exp/_bk_kill/dry_killA/series.csv | tail -8) \
    <(cut -d, -f1,"$(head -1 _exp/_bk_kill/dry_killC/series.csv | tr ',' '\n' | grep -n "^$c$" | cut -d: -f1)" _exp/_bk_kill/dry_killC/series.csv | tail -8) \
    2>/dev/null | sed 's/^/    A|C: /'
done
