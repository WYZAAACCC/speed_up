#!/bin/bash
# _t5_waitany.sh --- 阻塞等到**任一**报警/里程碑（③④⑤ 跃迁 · ② 衰减 · 算例异常），然后打印现场
# 用法：bash _t5_waitany.sh <最多等秒>
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
LIM=${1:-1800}
M=_w2_t5_n276_milestones.log      # ③④⑤ 跃迁
D=_w2_t5_ar_decay.log             # ② 衰减（E1-E3）
K=_w2_t5_keeper_all.log           # 守护
F=_w2_t5_fresh.log                # ★ fresh 通道（④⑤ 的**直接前兆**）

# ★ P48 纪律：计数一律用 awk（`grep -c` 可能返回多行 ⇒ `[ -gt ]` 静默失效）
c_m() { awk '/★M[0-9]/{n++} END{print n+0}' "$M" 2>/dev/null; }
c_d() { awk '/★E[123]/{n++} END{print n+0}' "$D" 2>/dev/null; }
# ★ s250：`fresh` 报警行以 ★★★ 标记（由 `_t5_freshwatch.py` 写）
c_f() { awk '/★★★/{n++} END{print n+0}' "$F" 2>/dev/null; }
alive() { ps -eo args --no-headers 2>/dev/null | awk -v q="--tag $1" 'index($0,q){n++} END{print n+0}'; }

B_M=$(c_m); B_D=$(c_d); B_F=$(c_f)
echo "  起等：★M=$B_M  ★E=$B_D  ★fresh=$B_F   最多 ${LIM} s"
T=0; WHY=""
while [ "$T" -lt "$LIM" ]; do
  [ "$(c_f)" -gt "$B_F" ] && { WHY="★ fresh 通道触发（④⑤ 的前兆）"; break; }
  [ "$(c_m)" -gt "$B_M" ] && { WHY="③④⑤ 里程碑"; break; }
  [ "$(c_d)" -gt "$B_D" ] && { WHY="② 长宽比衰减"; break; }
  if [ "$(alive t5N276)" -eq 0 ]; then WHY="⚠ t5N276 进程消失"; break; fi
  if [ "$(alive t5NR)" -eq 0 ]; then WHY="⚠ t5NR 进程消失"; break; fi
  sleep 30; T=$((T + 30))
done
echo "NOW = $(date '+%F %T')  等了 ${T} s   触发原因：${WHY:-（超时，无报警）}"
echo
echo '════ ★ ③④⑤ 里程碑（全部）════'
grep -E '★M[0-9]' "$M" 2>/dev/null | tail -6 | sed 's/^/  /' || true
echo '════ ★ ② 衰减（全部）════'
grep -E '★E[123]|♥' "$D" 2>/dev/null | sort -u | tail -4 | sed 's/^/  /' || true
echo '════ ★ fresh 通道（④⑤ 的直接前兆）════'
grep -E '★★★|模式计数变化|♥' "$F" 2>/dev/null | sort -u | tail -3 | sed 's/^/  /' || true
echo '════ 两臂块表（最新）════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import csv, os
print('  %-8s %-7s %-8s %-7s %-5s %-9s %-10s %s'
      % ('臂','step','nslab_n','nf3_col','nf2','nblk_sig','n_var_sig','blk_laths'))
for t in ('t5N276','t5NR'):
    p='_exp/_bk_t5/dry_%s/series.csv'%t
    if not os.path.exists(p): continue
    rows=list(csv.DictReader(open(p,newline='')))
    last=None
    for r in rows:
        if (r.get('nblk_sig') or '').strip(): last=r
    if last:
        print('  %-8s %-7s %-8s %-7s %-5s %-9s %-10s %s'
              % (t,last['step'],last.get('nslab_n'),last.get('nf3_col'),
                 (last.get('nf2') or '').strip(),(last.get('nblk_sig') or '').strip(),
                 (last.get('n_var_sig') or '').strip(),(last.get('blk_laths') or '')[:10]))
    print('     （%s 末步 = %s）' % (t, rows[-1]['step'] if rows else '?'))
PYEOF
echo '════ 监控链路 ════'
SNAP=$(ps -eo pid,args --no-headers 2>/dev/null)
for p in _t5_armon.py _t5_blkmon.py _t5_milewatch.py _t5_arwatch.py _t5_keeper_all.sh; do
  printf '  %-22s %s\n' "$p" "$(printf '%s\n' "$SNAP" | grep -c "$p")"
done
