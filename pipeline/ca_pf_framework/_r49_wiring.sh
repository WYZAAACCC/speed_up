#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== box_touch 出现处（判据侧应改用 box_touch_core）==='
grep -n 'box_touch' _bk_verdict.py | head -30
echo
echo '=== box_touch 在 _bk_exp.py 的 COLS / row ==='
grep -n 'box_touch' _bk_exp.py | head -20
echo
echo '=== t_wf / wide_face_thickness 接线状态 ==='
grep -n 't_wf\|wide_face_thickness' _bk_measure.py _bk_exp.py _bk_verdict.py | head -30
echo
echo '=== COLS / _BLK_EMPTY 附近 ==='
grep -n 'COLS = \|_BLK_EMPTY = ' _bk_exp.py
