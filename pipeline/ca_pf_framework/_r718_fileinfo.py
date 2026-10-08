#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib
import sys

for p in sys.argv[1:]:
    b = open(p, 'rb').read()
    print('%-28s bytes=%8d  LF=%6d  CR=%6d  CRLF=%6d  sha256=%s'
          % (p, len(b), b.count(b'\n'), b.count(b'\r'), b.count(b'\r\n'),
             hashlib.sha256(b).hexdigest()[:16]))
