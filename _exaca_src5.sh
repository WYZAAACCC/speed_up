#!/bin/bash
cd /root/bench/ExaCA-master
grep -n -B3 -A16 'intralayer' src/CAinputs.hpp | head -60