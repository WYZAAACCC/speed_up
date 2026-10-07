#!/bin/bash
# _t5_fix3.sh --- ★★★★★ 修复臂 t5G3 的**正确启动方式**（脚本必须 `wait`，否则臂随会话被收走）
#
# ## 为什么前两次都死了（**记账：我的启动方式错，不是引擎错**）
# `_t5_fix1.sh` / `_t5_fix2.sh` 都写成：
#     python _t5_short.py ... &     ← 后台起臂
#     sleep 90                       ← 看一眼
#     （脚本结束）                    ← ★ pwsh 调用返回 ⇒ WSL 命令结束 ⇒ **后台子进程被收走**
# **证据**：`t5F4` 只留下启动横幅；`t5G3` 跑了约 90 s 后同样消失；而最初的
# `_t5_long.sh` **活了 48 分钟**，区别就是它末尾有 `wait`。
# ⇒ **本脚本末尾 `wait`，且由 pwsh 以后台作业方式跑**（双保险）。
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LG=_w2_t5_fix3.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LG"; }

say '════ 检查：还有臂在跑吗 ════'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | cut -c1-70 | sed 's/^/  /'
[ -z "$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py')" ] && say '  ✅ 无残留（可以安全起新臂）'
free -m | sed -n 2p | sed 's/^/  /'

say '════ 起修复臂 t5G3（N=160 / nv=72 / B=3 ⇒ 69 ≤ 72 ✅）并且**等它** ════'
$PY _t5_short.py --tag t5G3 \
   --N 160 --nvar 12 --m 6 --B 3 --steps 6000 --cores 0-7 --mem-limit-gb 14.0 \
   --overlap-nm 62.5 --every 20 --snap-every 40 --pair-every 50 \
   --ckpt-every 20 --ckpt-keep 2 --archive-old > _w2_t5_fix3_A.log 2>&1 &
NP=$!
say "  ★ pid=$NP（tag=t5G3）—— 本脚本会**一直等它**（不再提前退出）"
# ★★ 关键：等待。这样 pwsh 调用不会返回 ⇒ WSL 会话不结束 ⇒ 臂不被收走。
wait $NP
RC=$?
say "  臂结束：exit=$RC"
say '  ── 末态 ──'
$PY - <<'PYEOF' 2>&1 | tee -a "$LG"
import csv, os, glob
for t in ('t5G3',):
    p = '_exp/_bk_t5/dry_%s/series.csv' % t
    if not os.path.exists(p):
        print('  %s ⚠ 无 series' % t); continue
    r = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    L = r[-1]
    print('  %s：%d 行，末步 %s' % (t, len(r), L['step']))
    for c in ('Vt','nslab_n','nslab_n1','nf3','nf3_col','nf2','nblk_sig',
              'f_var','n_var_sig','r_selfac','box_touch','blk_alen_nm','blk_wlen_nm'):
        if c in L:
            print('     %-14s = %s' % (c, (L[c] or '')[:50]))
    ns = [(x['step'], x.get('nslab_n')) for x in r if (x.get('nslab_n') or '').strip()]
    print('     nslab_n 轨迹: %s' % ns[:10])
PYEOF
say '  ── 形核计数（**判据**：被拒应显著下降）──'
grep -c 'athermal 形核' _w2_t5_short_t5G3.log 2>/dev/null | sed 's/^/    形核公告: /'
grep -c '被引擎拒' _w2_t5_short_t5G3.log 2>/dev/null | sed 's/^/    被拒: /'
grep -oE 'nfsv_nofield[^,}]*' _exp/_bk_t5/dry_t5G3/nuc_dbg.json 2>/dev/null | head -2 | sed 's/^/    /'
say '=== FIX3 DONE ==='
