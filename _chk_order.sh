#!/bin/bash
cd /root/bench/ExaCA-master
echo "=== domain.deltat 在哪赋值 / parseIRF 在哪调用（行号）:"
grep -n 'domain.deltat\|domain.deltax\|parseIRF(id)\|domain\.nx' src/CAinputs.hpp | head -14