#!/bin/bash
set +u
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
nohup env MAXJOB=6 WALL=1500 bash _par.sh _iso1.list > /tmp/iso1.out 2>&1 &
echo "launched pid=$!"
sleep 20
tail -20 /tmp/iso1.out
