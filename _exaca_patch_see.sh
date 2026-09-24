#!/bin/bash
cd /root/bench/ExaCA-master
echo "=== CAinputs.hpp parseIRF 区段 (900-960):"; sed -n '900,960p' src/CAinputs.hpp
echo; echo "=== CAinterfacialresponse.hpp compute 尾部 (52,100):"; sed -n '52,100p' src/CAinterfacialresponse.hpp