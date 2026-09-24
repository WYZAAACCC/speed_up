import io
P = "/mnt/f/speed_up/_ti64_stats.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("    for m in re.finditer(tag + r' seed\\s+\\d+: ", "    for m in re.finditer(tag + r'\\s+seed\\s+\\d+: ")
io.open(P, "w", encoding="utf-8").write(s)
print('fixed')