import io
p = "p1c_prod1d.py"
s = io.open(p, encoding="utf-8").read()
a = s.replace("    dtmin = 1e-13\n", "")
assert a != s, "no dtmin in timestepper block"
b = a.replace("  line_search = bt\n", "  line_search = bt\n  dtmin = 1e-13\n")
assert b != a, "no line_search anchor"
assert b.count("dtmin") == 1, b.count("dtmin")
io.open(p, "w", encoding="utf-8").write(b)
print("patched ok")