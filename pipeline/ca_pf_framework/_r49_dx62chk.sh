#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '--- _r47_dx62.sh'
cat _r47_dx62.sh
echo '--- meta keys of mb1s62'
/root/miniconda3/envs/ml/bin/python - <<'PY'
import json
m = json.load(open('/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_mb/dry_mb1s62/meta.json'))
print(sorted(m.keys()))
PY
echo '--- dir now'
ls -la _exp/_bk_mb/dry_mb1s62/
echo '--- CLI args of the live proc'
ps -eo args --no-headers | grep -F '_bk_exp.py' | grep -F '62.5'
