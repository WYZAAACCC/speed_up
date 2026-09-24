#!/bin/bash
cd /mnt/f/speed_up/bench/exaca
echo "=== README 里的算例描述段落:"
grep -n -i 'TwoGrain\|Inp_\|example' README.md | head -40
echo; echo "=== 抓 Inconel625.json:"
curl -s -m 20 "https://api.github.com/repos/LLNL/ExaCA/contents/examples/Materials/Inconel625.json" | /root/miniconda3/envs/ml/bin/python -c "import sys,json,base64;print(base64.b64decode(json.load(sys.stdin)['content']).decode())"
echo "=== unit_test 目录:"
curl -s -m 20 "https://api.github.com/repos/LLNL/ExaCA/contents/unit_test" | grep '"name"' | sed 's/.*: "//;s/",//' | tr '\n' ' '
echo; echo "=== analysis 目录:"
curl -s -m 20 "https://api.github.com/repos/LLNL/ExaCA/contents/analysis" | grep '"name"' | sed 's/.*: "//;s/",//' | tr '\n' ' '