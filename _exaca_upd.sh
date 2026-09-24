#!/bin/bash
cd /root/bench/ExaCA-master
echo "=== CAupdate.hpp 里捕获相关函数名:"; grep -n 'void \|double \|int ' src/CAupdate.hpp | head -20
echo; echo "=== 捕获判定主体:"; sed -n '/void cellCapture/,/^    }$/p' src/CAupdate.hpp | head -90