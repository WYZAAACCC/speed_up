import io
p = '/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py'
s = io.open(p, encoding='utf-8').read()
mark = '        if self.capture == "envelope":\n            # ---- 新默认：逐晶粒连续包络'
i = s.index(mark)
head, tail = s[:i], s[i:]
dup = '        if self.capture == "envelope":\n            self.grow_envelopes(dt, V, front)      # 逐晶粒 l_g 推进（新默认）'
j1 = head.index(dup)
j2 = head.index(dup, j1 + 1)
head = head[:j2]
s = head + tail
io.open(p, 'w', encoding='utf-8').write(s)
print('已删除重复段; 行数 =', s.count(chr(10)) + 1)
import ast; ast.parse(s); print('syntax OK')
print('现在 grow_envelopes 调用次数 =', s.count('self.grow_envelopes(dt, V, front)'))
print('现在 capture=="cell" 分支数 =', s.count('if self.capture == "cell":'))