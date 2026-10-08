/*
 * _r581_ufv.c --- R581-L6 的 C 扩展：`_minmod` 的**单趟**实现。
 *
 * ## 为什么只做 `_minmod`
 * 生产口径记账表（N=96/nv=48/onfly）实测：
 *     op.upwind_flux_vec  16.9% 单步
 *       op.ufv.minmod     12.2%
 *         op._minmod       7.58%     ← 就是它
 * `_minmod` 的 numpy 实现
 *     `0.5*(np.sign(a) + np.sign(b)) * np.minimum(np.abs(a), np.abs(b))`
 * 要 **8 趟 N³**（sign×2 / add / ×0.5 / abs×2 / minimum / ×）并造 7 个临时量；
 * 本扩展把它压成 **1 趟**（读 a、读 b、写 out）。
 *
 * ## 逐位相同是**硬判据**，所以这里逐条复刻 numpy 的语义
 * 1. `np.sign(x)`：**实测（`_r581_npedge.py`）`sign(±0.0) = +0.0`（符号位都是 0）**，
 *    对 NaN 返回 NaN ⇒ 写成 `isnan(x)?x:((x>0)?1:((x<0)?-1:0.0))`。
 *    ⚠ 第一版按"返回 x 本身"写（以为 `-0.0` 会保留）⇒ 被边缘用例判据抓到。
 * 2. `np.minimum(|a|,|b|)`：**传播 NaN**（实测 `minimum(nan,1)=nan`；
 *    C 的 `fmin` **不传播** ⇒ 不能直接用 `fmin`）。
 * 3. 运算次序与括号：归档是 `0.5 * (sign(a) + sign(b)) * minimum(...)`，
 *    C 里写成 `(0.5 * (sx + sy)) * m` —— **同一个次序**。
 *    （`sx+sy ∈ {−2,−1,0,1,2}` 精确，`×0.5` 是 2 的幂、也精确 ⇒ 全程只有 `*m` 一次舍入。）
 * 4. ⚠ **必须禁掉 FMA 收缩**（`-ffp-contract=off`）：否则编译器可能把
 *    `a*b` 与相邻的 `+` 融合成 `fma` ⇒ 舍入次数变了 ⇒ 不再逐位。
 *    构建脚本里已写死该选项，并在运行时打印编译命令供审计。
 * 5. `fabs(-0.0) = +0.0` ⇒ `m ≥ 0`，不会引入 `-0.0` 的分歧。
 *
 * ## 并行
 * 本模块**单线程**（无 OpenMP）。调用它的 `upwind_flux_vec` 已经在 4 个
 * Python 工作线程里跑 ⇒ 再开 OpenMP 只会超额订阅。
 * 「单线程 vs OpenMP」的实测见 `_w2_r581_L6c.log`。
 */
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#include <Python.h>
#include <math.h>
#include <numpy/arrayobject.h>

/* 与 numpy `np.sign` 逐位一致的符号函数
 *
 * ★★★ 实测（`_r581_npedge.py`，numpy 2.5.3）：
 *     sign( 0.0) =  0.0   符号位 False
 *     sign(-0.0) =  0.0   符号位 **False**   ← ★ 不是 -0.0！
 *     sign(nan ) = nan
 *   ⇒ **零一律返回 `+0.0`**。本文件第一版按"返回 x 本身"写（以为 -0.0 会保留），
 *     被边缘用例判据当场抓到：`(-0.0, -0.0)` 处 numpy 给 `+0.0`、C 给 `-0.0`。
 */
static inline double np_sign(double x)
{
    if (isnan(x)) return x;       /* np.sign(nan) = nan，符号位为 0 */
    if (x > 0.0) return 1.0;
    if (x < 0.0) return -1.0;
    return 0.0;                   /* ±0.0 都归一到 +0.0（与 numpy 逐位一致） */
}

/* 与 numpy `np.minimum` 逐位一致（**传播 NaN**；实测 minimum(nan,1)=nan） */
static inline double np_minimum(double x, double y)
{
    if (isnan(x)) return x;
    if (isnan(y)) return y;
    return (x < y) ? x : y;
}

static PyObject *py_minmod(PyObject *self, PyObject *args)
{
    PyObject *ao, *bo;
    if (!PyArg_ParseTuple(args, "OO", &ao, &bo)) return NULL;

    PyArrayObject *a = (PyArrayObject *)PyArray_FROM_OTF(
        ao, NPY_DOUBLE, NPY_ARRAY_IN_ARRAY);
    if (!a) return NULL;
    PyArrayObject *b = (PyArrayObject *)PyArray_FROM_OTF(
        bo, NPY_DOUBLE, NPY_ARRAY_IN_ARRAY);
    if (!b) { Py_DECREF(a); return NULL; }

    if (PyArray_NDIM(a) != PyArray_NDIM(b) ||
        !PyArray_CompareLists(PyArray_DIMS(a), PyArray_DIMS(b),
                              PyArray_NDIM(a))) {
        PyErr_SetString(PyExc_ValueError, "_r581_ufv.minmod: 形状必须相同");
        Py_DECREF(a); Py_DECREF(b);
        return NULL;
    }

    PyArrayObject *out = (PyArrayObject *)PyArray_NewLikeArray(
        a, NPY_CORDER, NULL, 0);
    if (!out) { Py_DECREF(a); Py_DECREF(b); return NULL; }

    const double *pa = (const double *)PyArray_DATA(a);
    const double *pb = (const double *)PyArray_DATA(b);
    double *po = (double *)PyArray_DATA(out);
    npy_intp n = PyArray_SIZE(a);
    npy_intp i;

    for (i = 0; i < n; ++i) {
        double x = pa[i], y = pb[i];
        double sx = np_sign(x), sy = np_sign(y);
        double m = np_minimum(fabs(x), fabs(y));
        po[i] = (0.5 * (sx + sy)) * m;
    }

    Py_DECREF(a); Py_DECREF(b);
    return (PyObject *)out;
}

/* ======================================================================
 *  ufv_accum --- `upwind_flux_vec` 的**整轴融合**核（order=1/2）
 *
 *  ## 为什么这才是真收益
 *  Python 版每个轴 ≈ **37 趟 N³**（roll×4 / sub / div / minmod×2 各 8 趟 / where …），
 *  三个轴 ≈ 111 趟；而其中绝大多数是**中间临时量**的读写。
 *  融合后：读 `phi`（含 4 个邻居面，都是顺序流）+ 读 `Va` + 写 `out`
 *  ⇒ **≈4–6 趟**。目标是把 `upwind_flux_vec`（生产口径 **16.9% 单步**）压下来。
 *
 *  ## 逐位复刻的要点（与 `windowB_surface.upwind_flux_vec` 一字不差）
 *  ```python
 *  dm  = (phi - roll(phi,1,ax)) / dx        # dm[i]  = (phi[i]   - phi[i-1]) / dx
 *  dp  = (roll(phi,-1,ax) - phi) / dx       # dp[i]  = (phi[i+1] - phi[i]  ) / dx
 *  dmm = roll(dm, 1, ax)                    # dmm[i] = dm[i-1] = (phi[i-1]-phi[i-2])/dx
 *  dpp = roll(dp, -1, ax)                   # dpp[i] = dp[i+1] = (phi[i+2]-phi[i+1])/dx
 *  dm  = dm + 0.5*_minmod(dm - dmm, dp - dm)
 *  dp  = dp - 0.5*_minmod(dpp - dp, dp - dm)     # ★ 第二个用的是**更新后**的 dm
 *  acc = acc + np.where(Va > 0, Va*dm, Va*dp)
 *  ```
 *  ⚠ 注意：C 里把 `np.where(Va>0, Va*dm, Va*dp)` 写成 `Va * (Va>0 ? dm : dp)`
 *    —— 这里是**逐元素**同一个乘积，且**不是** L6 微基准里那个"提前把 Va 提出来"
 *    的重写（那个在 `_r581_L6_ufv.py` 里被证明**只是**因为 `Va*dm` 与 `Va*dp`
 *    同时对 NaN/±0 的处理差异；本实现两支都只在选定后乘一次，与归档完全一致）。
 *    ⇒ 判据以 `_r581_L6c.py` 的**逐位**为准，不靠这段文字。
 *  ⚠ `-ffp-contract=off` 是**必需**的（FMA 会改舍入次数）。
 *  ⚠ `acc` 的起点：Python 是 `acc = 0.0`，然后 `acc = acc + term`；
 *    第一次 `0.0 + t == t`（IEEE 精确）⇒ C 里首轴直接 `out = term` 等价。
 * ====================================================================== */

static void ufv_accum(const double *phi, const double *Va, double *out,
                      npy_intp N, double dx, int axis, int first, int order)
{
    const npy_intp sx = N * N, sy = N, sz = 1;
    const npy_intp st = (axis == 0) ? sx : ((axis == 1) ? sy : sz);
    npy_intp i, j, k;
    npy_intp dm1, dm2, dp1, dp2;

    for (i = 0; i < N; ++i) {
        const npy_intp i_m1 = (i == 0) ? N - 1 : i - 1;
        const npy_intp i_m2 = (i < 2) ? i - 2 + N : i - 2;
        const npy_intp i_p1 = (i + 1 == N) ? 0 : i + 1;
        const npy_intp i_p2 = (i + 2 >= N) ? i + 2 - N : i + 2;
        for (j = 0; j < N; ++j) {
            const npy_intp j_m1 = (j == 0) ? N - 1 : j - 1;
            const npy_intp j_m2 = (j < 2) ? j - 2 + N : j - 2;
            const npy_intp j_p1 = (j + 1 == N) ? 0 : j + 1;
            const npy_intp j_p2 = (j + 2 >= N) ? j + 2 - N : j + 2;
            for (k = 0; k < N; ++k) {
                const npy_intp k_m1 = (k == 0) ? N - 1 : k - 1;
                const npy_intp k_m2 = (k < 2) ? k - 2 + N : k - 2;
                const npy_intp k_p1 = (k + 1 == N) ? 0 : k + 1;
                const npy_intp k_p2 = (k + 2 >= N) ? k + 2 - N : k + 2;
                const npy_intp idx = i * sx + j * sy + k;
                double ph, dm, dp, dmn, dpn, term;
                double va;

                /* 邻居相对 idx 的**带符号偏移**（按被差分轴取） */
                if (axis == 0) {
                    dm1 = (i - i_m1) * st; dm2 = (i - i_m2) * st;
                    dp1 = (i_p1 - i) * st; dp2 = (i_p2 - i) * st;
                } else if (axis == 1) {
                    dm1 = (j - j_m1) * st; dm2 = (j - j_m2) * st;
                    dp1 = (j_p1 - j) * st; dp2 = (j_p2 - j) * st;
                } else {
                    dm1 = (k - k_m1) * st; dm2 = (k - k_m2) * st;
                    dp1 = (k_p1 - k) * st; dp2 = (k_p2 - k) * st;
                }

                ph = phi[idx];
                dm = (ph - phi[idx - dm1]) / dx;
                dp = (phi[idx + dp1] - ph) / dx;

                if (order >= 2) {
                    double a1, b1, a2, b2, m1, m2, s1, s2;
                    const double dmm = (phi[idx - dm1] - phi[idx - dm2]) / dx;
                    const double dpp = (phi[idx + dp2] - phi[idx + dp1]) / dx;

                    /* ⚠ 归档原文是
                     *     dm = dm + 0.5 * _minmod(dm - dmm, dp - dm)
                     *   而 `_minmod(a,b) = 0.5*(sign(a)+sign(b))*minimum(|a|,|b|)`
                     *   **自带一个 0.5** ⇒ 完整式子是 `dm + 0.5*((0.5*(sa+sb))*m)`。
                     *   ★ 第一版漏了**外层**那个 0.5（写成 `dm + (0.5*s1)*m1`）
                     *     ⇒ order=2 差 310287 个元素，而 order=1（没有 minmod）**全对**
                     *     —— 这个"只有 order=2 错"的指纹直接把范围锁到了 minmod 上。
                     *   `0.5*s` 与最外层的 `0.5*` 都是 2 的幂 ⇒ 精确；只有 `*m` 一次舍入。
                     */
                    a1 = dm - dmm;  b1 = dp - dm;
                    s1 = np_sign(a1) + np_sign(b1);
                    m1 = np_minimum(fabs(a1), fabs(b1));
                    dmn = dm + (0.5 * ((0.5 * s1) * m1));

                    a2 = dpp - dp;  b2 = dp - dmn;      /* ★ 用更新后的 dm */
                    s2 = np_sign(a2) + np_sign(b2);
                    m2 = np_minimum(fabs(a2), fabs(b2));
                    dpn = dp - (0.5 * ((0.5 * s2) * m2));
                } else {
                    dmn = dm; dpn = dp;
                }

                va = Va[idx];
                /* = np.where(Va > 0, Va*dm, Va*dp) 的逐元素等价写法 */
                term = (va > 0.0) ? (va * dmn) : (va * dpn);
                /* ★ 首轴也必须写成 `0.0 + term`（**不是**直接存 `term`）：
                 *   归档是 `acc = 0.0` 然后 `acc = acc + term` ⇒ 当 `term` 是 `-0.0`
                 *   时（`Va == 0` 且 `dm/dp < 0` 就会出现），`0.0 + (-0.0) = +0.0`，
                 *   符号位被翻正。第一版直接存 `term` ⇒ 两者在**±0 的符号位**上不同。
                 *   ⚠ 这个差异用 `x != y` **看不出来**（`-0.0 == 0.0` 为真）；
                 *     本仓判据用"NaN 感知 + 符号位"三重比较才抓到（`_r581_L6fuse.py`）。
                 *   实测：order=1 差的 27430 个元素**全部**是这一类。 */
                out[idx] = first ? (0.0 + term) : (out[idx] + term);
            }
        }
    }
}

static PyObject *py_ufv_accum(PyObject *self, PyObject *args)
{
    PyObject *po, *pv, *pu;
    double dx;
    int axis, first, order;
    if (!PyArg_ParseTuple(args, "OOdiiiO", &po, &pv, &dx, &axis, &first,
                          &order, &pu))
        return NULL;

    PyArrayObject *phi = (PyArrayObject *)PyArray_FROM_OTF(
        po, NPY_DOUBLE, NPY_ARRAY_IN_ARRAY);
    if (!phi) return NULL;
    PyArrayObject *Va = (PyArrayObject *)PyArray_FROM_OTF(
        pv, NPY_DOUBLE, NPY_ARRAY_IN_ARRAY);
    if (!Va) { Py_DECREF(phi); return NULL; }
    PyArrayObject *out = (PyArrayObject *)PyArray_FROM_OTF(
        pu, NPY_DOUBLE, NPY_ARRAY_INOUT_ARRAY2);
    if (!out) { Py_DECREF(phi); Py_DECREF(Va); return NULL; }

    if (PyArray_NDIM(phi) != 3 || !PyArray_IS_C_CONTIGUOUS(phi) ||
        PyArray_SIZE(phi) != PyArray_SIZE(Va) ||
        PyArray_SIZE(phi) != PyArray_SIZE(out)) {
        PyErr_SetString(PyExc_ValueError,
                        "_r581_ufv.ufv_accum: phi/Va/out 必须是同尺寸的 C 连续 3D 数组");
        Py_DECREF(phi); Py_DECREF(Va);
        PyArray_ResolveWritebackIfCopy(out); Py_DECREF(out);
        return NULL;
    }

    ufv_accum((const double *)PyArray_DATA(phi),
              (const double *)PyArray_DATA(Va),
              (double *)PyArray_DATA(out),
              (npy_intp)PyArray_DIM(phi, 0), dx, axis, first, order);

    Py_DECREF(phi); Py_DECREF(Va);
    PyArray_ResolveWritebackIfCopy(out);
    Py_DECREF(out);
    Py_RETURN_NONE;
}

static PyMethodDef Methods[] = {
    {"minmod", py_minmod, METH_VARARGS,
     "minmod(a, b) -> ndarray：与 windowB_surface._minmod 逐位相同（单趟 C 实现）"},
    {"ufv_accum", py_ufv_accum, METH_VARARGS,
     "ufv_accum(phi, Va, dx, axis, first, order, out) -> None："
     "把 upwind_flux_vec 的**一个轴**融合进 out（逐位等价；first=1 时覆盖、否则累加）"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef moddef = {
    PyModuleDef_HEAD_INIT, "_r581_ufv",
    "R581-L6：_minmod 的单趟 C 实现（逐位等价；构建见 _r581_buildc.sh）",
    -1, Methods, NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC PyInit__r581_ufv(void)
{
    import_array();
    return PyModule_Create(&moddef);
}
