#!/usr/bin/env bash
# R518 —— 找 abA/abB 的 stdout 日志（R516 的 find_log 没找到 ⇒ 自查错误 #104）
set -u
cd "$(dirname "$0")"
echo "=== 1. 所有含 'tag abA' 或 'tag abB' 的文件 ==="
grep -rl -- '--tag abA' . --include='*.log' --include='*.sh' 2>/dev/null | head -10
echo "---"
grep -rl -- '--tag abB' . --include='*.log' --include='*.sh' 2>/dev/null | head -10

echo
echo "=== 2. 启动 abA 的脚本 ==="
grep -rln 'tag abA' *.sh 2>/dev/null | head -5

echo
echo "=== 3. 按 mtime 找 07:06 前后的日志（abA 起跑时间） ==="
ls -la --time-style=+%m-%d_%H:%M _w2_*.log 2>/dev/null | awk '$6 ~ /10-01_0[6-9]/' | head -12

echo
echo "=== 4. abA 的 nuc_dbg.json 内容 ==="
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import json
for t in ('dry_abA', 'dry_abB'):
    try:
        with open('_exp/_bk_mb/%s/nuc_dbg.json' % t) as fh:
            d = json.load(fh)
        print('  %s: %s' % (t, json.dumps(d, ensure_ascii=False)[:400]))
    except Exception as e:
        print('  %s: %r' % (t, e))
PYEOF
