import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/_timewin.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("""    def rec_ab(margin=None):
        b = orig_ab(margin); box[0] = b; return b""",
"""    def rec_ab(margin=None, front=None, **kw):
        b = orig_ab(margin, front=front) if front is not None else orig_ab(margin)
        box[0] = b; return b""")
io.open(P, "w", encoding="utf-8").write(s)
print("ok")