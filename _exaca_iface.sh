#!/bin/bash
cd /root/bench/ExaCA-master
echo "=== createNewOctahedron:"; sed -n '/void createNewOctahedron/,/^    }$/p' src/CAinterface.hpp
echo; echo "=== calcCritDiagonalLength:"; sed -n '/void calcCritDiagonalLength/,/^    }$/p' src/CAinterface.hpp