#!/bin/bash
# _r581_ask_state.sh --- 回答用户："当前有断帧续跑的实验吗？逐位一致吗？"
#   —— 只从**磁盘上真实存在的东西**取证
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '════ ① 现在有正在跑的算例吗 ════'
N=$(ps -eo pid,etime,args --no-headers 2>/dev/null | grep -c '_bk_exp.py')
echo "  当前 _bk_exp.py 进程数 = $N"
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '_bk_exp.py' | grep -v grep | cut -c1-96 | sed 's/^/    /'
[ "$N" = 0 ] && echo '  （0 = 当前没有在跑的算例；下面全是**已经跑完、留在磁盘上**的实验）'
echo
echo '════ ② 断点续跑实验的**运行目录**（存在于磁盘上吗）════'
for d in _exp/_bk_rsmoke/dry_rs2 _exp/_bk_rsmoke/dry_rs3 \
         _exp/_bk_g3b/dry_g3b_ms _exp/_bk_g3b/dry_g3b_true _exp/_bk_g3b/dry_g3b_rs \
         _exp/_bk_kill/dry_killA _exp/_bk_kill/dry_killB _exp/_bk_kill/dry_killC \
         _exp/_bk_seg/dry_ma_true _exp/_bk_seg/dry_ma_rs \
         _exp/_bk_seg/dry_seg_true _exp/_bk_seg/dry_seg_p3; do
  if [ -f "$d/series.csv" ]; then
    printf '  ✅ %-34s series %3s 行  末步 %-4s  mtime %s\n' "$d" \
      "$(wc -l < "$d/series.csv")" \
      "$(tail -1 "$d/series.csv" | cut -d, -f1)" \
      "$(stat -c %y "$d/series.csv" | cut -c1-19)"
  else
    printf '  ❌ %-34s **不存在**\n' "$d"
  fi
done
echo
echo '════ ③ 检查点文件（续跑就是从这里恢复的）════'
for d in _exp/_bk_kill/dry_killB/ckpt _exp/_bk_g3b/dry_g3b_ms/ckpt; do
  echo "  ── $d ──"
  ls -la "$d" 2>/dev/null | tail -n +4 | awk '{printf "     %-22s %8.2f MB  %s %s\n", $9, $5/1048576, $6, $7}' 
done
echo
echo '════ ④ ★ 逐位比较的**证据文件**（落盘的，不是终端输出）════'
if [ -f _w2_r581_evidence.log ]; then
  echo "  $ 文件：_w2_r581_evidence.log（$(wc -l < _w2_r581_evidence.log) 行，mtime $(stat -c %y _w2_r581_evidence.log | cut -c1-19)）"
  echo
  grep -E '^判据：|差异字段数|共有 step|Vt |f_var |nslab_n1|nf3 |nf2 ' _w2_r581_evidence.log \
    | sed 's/^/    /'
else
  echo '  ❌ 证据文件不在'
fi
