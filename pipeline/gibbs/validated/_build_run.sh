#!/bin/bash
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
echo "=== 编译 ==="
sed "s/\r$//" /mnt/f/speed_up/pipeline/gibbs/app/build_app.sh > /tmp/ba.sh
bash /tmp/ba.sh 2>&1 | grep -E "^== |error:|Error [0-9]|fatal" | head -8
echo "=== 跑 ==="
sed "s/\r$//" /mnt/f/speed_up/pipeline/gibbs/validated/run_p3coupled.sh > /tmp/p3c.sh
bash /tmp/p3c.sh 2>&1 | tail -10