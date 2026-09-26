#!/bin/bash
set +u
F=/root/moose/framework
ls $F/include/utils/ | grep -i parser
echo "=== grep max in parser ==="
grep -rn "\"max\"\|'max'" $F/src/utils/*Parser* $F/include/utils/*Parser* 2>/dev/null | head -20
