import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_envelope.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace('"打乱后不同 %s 胞（旧版 30.16% / 32.84%）" % ds, ds)',
              '"打乱后不同 %s 胞（旧版 30.16%% / 32.84%%）" % ds, ds)')
s = s.replace('"基底 c = %.4f (c0=%.4f)" % (ca.c[sub].mean(), C0_V), ca.c[sub].mean())',
              '"基底 c = %.4f (c0=%.4f)" % (ca.c[sub].mean(), C0_V), ca.c[sub].mean())')
s = s.replace('"基底成分 = c0（旧版给 k*c0，低 37%）"', '"基底成分 = c0（旧版给 k*c0，低 37%%）"')
io.open(P, "w", encoding="utf-8").write(s)
print("ok")