import io, os, subprocess, sys
BIN = "/root/moose/modules/phase_field/phase_field-opt"
os.environ["PATH"] = "/root/miniconda3/envs/moose/bin:" + os.environ.get("PATH", "")
vals = sys.argv[1:] if len(sys.argv) > 1 else ["0.0", "1.0", "2.0", "3.0"]
res = []
for v in vals:
    lines = io.open("p1c_alpha2.i", encoding="utf-8").read().split(chr(10))
    hit = False
    for i, l in enumerate(lines):
        if "3.0e-8 0.6303" in l:
            lines[i] = "    constant_expressions = \"" + v + " 3.0e-8 0.6303\""
            hit = True
            break
    assert hit, "no line to patch"
    io.open("p1c_alpha2.i", "w", encoding="utf-8").write(chr(10).join(lines))
    if os.path.exists("p1c_alpha2_out.csv"):
        os.remove("p1c_alpha2_out.csv")
    rc, err = -1, True
    try:
        r = subprocess.run([BIN, "-i", "p1c_alpha2.i"], capture_output=True, text=True, timeout=900)
        rc = r.returncode
        err = ("ERROR" in r.stdout)
        if err:
            for l in r.stdout.splitlines():
                if "ERROR" in l:
                    print("   " + l.strip()[:110]); break
    except Exception as e:
        print("   exc: " + str(e)[:100])
    line = io.open("p1c_alpha2_out.csv").read().strip().splitlines()[-1] if os.path.exists("p1c_alpha2_out.csv") else "(no csv)"
    print("ALPHA=" + v + "  exit=" + str(rc) + "  err=" + str(err) + "  " + line, flush=True)
    res.append((v, line))
print("")
print("列: time, c_1700, c_1750, c_1800, c_2000 ; 判据: 界面正前方液相应 = c_inf/k_e = 0.0571")
for v, line in res:
    print("  ALPHA=" + v + " -> " + line)
