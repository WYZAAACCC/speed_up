#!/bin/bash
# _t5_blkcol.sh --- 核实"块表列"出现在哪些 step（修监控判据）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ series.csv 里 `nblk_sig` **有值**的行（step, nblk_sig, n_var_sig, blk_laths, nf2）════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import csv
P = '_exp/_bk_t5/dry_t5N276/series.csv'
rows = list(csv.DictReader(open(P, newline='')))
print('  总行数 = %d' % len(rows))
print()
print('  ── 所有行的 step 与关键列（只列前 12 行 + 有块表的行）──')
hits = 0
for r in rows:
    nb = (r.get('nblk_sig') or '').strip()
    nv = (r.get('n_var_sig') or '').strip()
    nf2 = (r.get('nf2') or '').strip()
    if nb or nv:
        hits += 1
        print('    step=%-6s nblk_sig=%-4s n_var_sig=%-4s blk_laths=%-10s nf2=%s'
              % (r['step'], nb or '(空)', nv or '(空)', (r.get('blk_laths') or '(空)')[:10], nf2 or '(空)'))
print()
print('  ⇒ **块表列有值的行数 = %d**（总 %d 行）' % (hits, len(rows)))
if hits:
    st = [int(r['step']) for r in rows if (r.get('nblk_sig') or '').strip()]
    print('  ⇒ 出现块表的 step = %s' % st[:14])
    print('  ⇒ **判据修正：块表行 = `nblk_sig` 非空**（不是 `nf2` 非空）')
else:
    print('  ⚠ 还没有任何行有块表值 ⇒ 需等 step 到 100 的倍数（且引擎已写出块表）')
PYEOF
