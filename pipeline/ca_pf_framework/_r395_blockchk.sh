#!/usr/bin/env bash
# _r395_blockchk.sh —— 逐块判据在**最近的臂**上的实测（不凭记忆）
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
for f in _w2_r386_run.log _w2_r361_run.log _w2_r370_permB1_400.log \
         _w2_r370_saSet2DT200.log _w2_r372_permB4_200.log _w2_r372_permB5_200.log; do
  [ -f "$f" ] || continue
  echo "######## $f"
  echo "  末步: $(grep -oE '^  \[ *[0-9]*\]' "$f" | tail -1 | tr -d ' []')"
  grep -E '每块板条数\(定义\)|逐块柱剖面\*\*不同场数\*\*|逐块柱剖面\*\*段数\*\*|该块分量覆盖的场数|每块内板条全部可分辨|块内界面自检|cov_norm' "$f" | tail -7
  echo
done
echo "######## 同变体（F3）面数的时间轨迹（region 基，从 series.csv）"
/root/miniconda3/envs/ml/bin/python - <<'PY'
import csv, io, os
MB = '_exp/_bk_mb'
for tag in ('saSet2', 'permB1_400', 'saSet2DT200', 'permB4_200', 'permB5_200'):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        continue
    R = list(csv.DictReader(io.open(p, encoding='utf-8')))
    col = 'nf3' if 'nf3' in R[0] else ('f3_faces' if 'f3_faces' in R[0] else None)
    if col is None:
        print('  %-14s ⚠ 无 F3 列（列名：%s）' % (tag, list(R[0])[:12])); continue
    v = [(int(float(r['step'])), r[col]) for r in R]
    print('  %-14s %s : %s' % (tag, col, [x[1] for x in v[::max(len(v)//6,1)]] + [v[-1][1]]))
PY
