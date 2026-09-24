import importlib
for m in ("vtk", "pyvista", "plotly"):
    try:
        mod = importlib.import_module(m)
        print(m, "OK", getattr(mod, "__version__", "?"))
    except Exception as e:
        print(m, "NO", type(e).__name__)