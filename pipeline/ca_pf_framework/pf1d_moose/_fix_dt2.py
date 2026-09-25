import io
p = "p1c_prod1d.py"
s = io.open(p, encoding="utf-8").read()

old = '''[Executioner]
  type = Transient
  solve_type = NEWTON
  end_time = %(tend).6e
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = %(dt).6e
    optimal_iterations = 8
    iteration_window = 2
    cutback_factor = 0.5
    growth_factor = 1.5
  []
  nl_rel_tol = 1e-6
  nl_abs_tol = 1e-7
  l_tol = 1e-10
  line_search = bt
  dtmin = 1e-13
[]'''
new = '''[Executioner]
  type = Transient
  solve_type = NEWTON
  end_time = %(tend).6e
  dt = %(dt).6e
%(stepper)s
  nl_rel_tol = 1e-6
  nl_abs_tol = 1e-7
  nl_max_its = 120
  l_tol = 1e-10
  line_search = bt
  dtmin = 1e-14
[]'''
assert old in s, "executioner anchor not found"
s = s.replace(old, new)

# dt / stepper selection: default = FIXED dt = 0.05 dx^2/D_L (the value used by the
# 2026-09-25 fixdt runs).  IterationAdaptiveDT was tried and REVERTED because it
# roughens dt to ~1e-6 s >> l_D^2/D_L = 3.3e-6/30, which under-resolves the
# boundary-layer relaxation in time and shifts c_int by ~35 points of percent.
old2 = '''           dt=0.05 * dx ** 2 / 1.2e-6, tend=tend, xmid=(x0 + V * tend) - 0.0,'''
new2 = '''           dt=DT, stepper=STEPPER, tend=tend, xmid=(x0 + V * tend) - 0.0,'''
assert old2 in s, "dt anchor not found"
s = s.replace(old2, new2)

old3 = '''if __name__ == "__main__":
    A = float(sys.argv[1]); WF = float(sys.argv[2]); KC = float(sys.argv[3])'''
new3 = '''ADAPTIVE_STEPPER = """  [TimeStepper]
    type = IterationAdaptiveDT
    dt = %(dt).6e
    optimal_iterations = 8
    iteration_window = 2
    cutback_factor = 0.5
    growth_factor = 1.5
  []"""

if __name__ == "__main__":
    A = float(sys.argv[1]); WF = float(sys.argv[2]); KC = float(sys.argv[3])'''
assert old3 in s, "main anchor not found"
s = s.replace(old3, new3)

old4 = '''    tag = "A%g_W%g_kc%g" % (A, WF * 1e6, KC)'''
new4 = '''    global DT, STEPPER
    DT = float(os.environ.get("PROD1D_DT", "0") or (0.05 * dx ** 2 / 1.2e-6))
    STEPPER = ADAPTIVE_STEPPER if os.environ.get("PROD1D_ADAPT", "0") == "1" else ""
    print("dt = %.4e s (fixed=%s)  dt/(l_D^2/D_L) = %.4f"
          % (DT, not STEPPER, DT / ((1.2e-6 / V) ** 2 / 1.2e-6)))
    tag = "A%g_W%g_kc%g" % (A, WF * 1e6, KC)'''
assert old4 in s, "tag anchor not found"
s = s.replace(old4, new4)
io.open(p, "w", encoding="utf-8").write(s)
print("patched ok")