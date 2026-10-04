#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== nucleate(): 模式分支与落位失败点 ==="
awk 'NR>=1887 && NR<=2130' windowB_surface.py | grep -nE "mode|'stack'|'attach'|'fresh'|return \[\]|return None|continue|n_stack|n_fresh|cap|overlap|_p is None|place" | cut -c1-165 | head -60
