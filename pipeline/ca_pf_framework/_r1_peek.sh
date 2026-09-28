#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "### iters log"
tail -40 _w2_r1reinit_iters.log 2>/dev/null || echo "(missing)"
echo
echo "### band log"
tail -30 _w2_r1reinit_band.log 2>/dev/null || echo "(missing)"
echo
echo "### audit md"
ls -la R1_REINIT_AUDIT.md 2>/dev/null || echo "(not yet)"
echo
echo "### scale"
tail -14 _w2_r1scale192.log
echo
echo "### mem"; free -g | head -2
