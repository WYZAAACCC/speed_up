# α′ lath WIDTH provenance for LPBF Ti-6Al-4V as-built — literature search report

**Purpose:** anchor `β_w` in `M(n) = M0 · exp[−β_h·(n·n*)² − β_w·(n·w)²]`
(`n*` = wide-face normal / thickness direction; `w` = width direction; `a` = length direction)
⇒ design growth rates `length : width : thickness = 1 : e^{−β_w} : e^{−β_h}`.

**Date:** 2026-09-28 · **Searcher:** delegated literature agent
**Rule applied throughout:** every number is tied to a specific figure/table and quoted verbatim;
`retrieved full text?` is stated for every source; nothing is interpolated or borrowed from steel /
wrought / non-LPBF Ti-64.

---

## 1. PRIMARY ANSWER — the α′ lath WIDTH anchor

### **NOT FOUND.** No 3D-measured α′ lath width (or 3D length:width aspect ratio) exists in the open
literature for **LPBF/SLM Ti-6Al-4V in the as-built α′ condition**.

I found **zero** studies that measured α′ lath dimensions in LPBF Ti-64 by any genuinely
three-dimensional technique — no FIB/plasma-FIB serial-sectioning tomography, no 3D-EBSD, no TEM
tomography, no X-ray tomography / DCT / nf-HEDM. A second, independent search agent reached the same
conclusion from a separately-designed query set.

**Everything that exists is a 2D-section measurement**, and — this is the decisive point — **no source
reports a lath width *and* a lath thickness as two separate dimensions.** Each study reports one long
dimension and one short dimension of the acicular feature seen in section.

### Best available same-material + same-process anchor (2D, explicitly not 3D)

**Xie et al. 2026, *Materials* 19, 1945 — doi 10.3390/ma19101945** (PMC13208675) — **full text retrieved.**

- Process: LPBF (BLT-A300, Bright Laser Technologies), Ti-6Al-4V, argon-atomised powder, laser power
  190 W, layer thickness 30 µm, scan speed 90 mm/s, hatch 140 µm; "the samples were naturally cooled to
  room temperature in the argon-filled build chamber before removal" (no heat treatment) ⇒ **as-built α′**.
- Method (§2.3, verbatim): "metallographic samples were prepared from the gauge sections. After standard
  grinding and polishing, the samples were lightly etched with Kroll's reagent … Backscattered electron
  (BSE) imaging was subsequently performed using a scanning electron microscope (Thermo Scientific Scios 2…)"
- Sampling (verbatim): "To quantitatively assess microstructural variations, **fifty α′ laths were randomly
  selected and measured for each specimen.** The average lath width and length are summarized in Table 2"
- **2D section (BSE) measurement. No stereological correction is stated. No length pre-filtering.**
- As-built confirmed: no heat treatment is applied to the metallurgical specimens; the paper's only use of
  the phrase "heat treatment" is a generic literature citation about oxygen diffusion. Note also that the
  same paper **explicitly warns about stereological bias for its pore measurements** ("the two-dimensional
  measurements are limited to the inspected cross-sections and cannot fully represent the overall
  three-dimensional pore distributions … may introduce stereological bias") — **but does not apply that
  caveat to its α′ lath dimensions**, which are measured the same 2D way.

**Table 2** ("Average α′ lath dimensions for specimens with different thicknesses"), verbatim values:

| Specimen thickness (mm) | Average Length (µm) | Average Width (µm) |
|---|---|---|
| 0.2 | 5.065 | 0.239 |
| 0.25 | 5.109 | 0.256 |
| 0.3 | 5.419 | 0.251 |
| 0.4 | 5.499 | 0.262 |
| 0.5 | 5.471 | 0.241 |
| 0.6 | 5.430 | 0.253 |
| 0.7 | 5.454 | 0.262 |
| 0.8 | 5.539 | 0.247 |
| 0.9 | 5.501 | 0.270 |
| 1.0 | 5.685 | 0.304 |

⇒ mean length 5.417 µm, mean width 0.259 µm, **2D length:width = 16.7–23.8, mean 20.9**.

### The two sources named in the brief — full-text corrections

**(a) Shuai et al. 2026, *Materials* 19, 1049 — doi 10.3390/ma19061049** (PMC13027919) — **full text retrieved.**

The paper uses **"lath width" and "lath thickness" interchangeably for ONE measurement.** Verbatim:

- §2.2: "EBSD was used primarily for crystallographic orientation and texture analyses, whereas the
  α/α’ lath morphology and **lath width** were measured and quantified from the BSE micrographs."
- §2.2: "The α’ martensite **lath thickness** was measured from BSE images using the **linear intercept
  method specified in the GB/T 6394-2017**. For each sample, at least n ≥ 300 intercepts were collected…"
- §3.2: "All samples displayed dense networks of acicular α’ martensite, with **lath widths between
  0.51 and 0.68 μm**."
- §3.2 (Fig. 6 text): "At P = 173 W, the measured **lath thicknesses** span approximately **0.51–0.88 μm**."
- §3.2: "Among the AB samples, #1 contained the coarsest α’ martensite laths (**0.68 ± 0.27 μm**) … In
  contrast, #4 presented the finest laths (**0.51 ± 0.14 μm**)."
- Figure 5 caption: "BSE micrographs of the six selected samples in as-built (AB) states … The average
  α’ lath **thickness** was labeled."

⇒ **0.51–0.88 µm is a 2D BSE linear-intercept measurement** (GB/T 6394-2017 = Chinese "Metal — Methods for
Estimating the Average Grain Size"). It is **not** a thickness, and it is **not** a width — it is the one
short dimension the 2D section exposes. The paper contains **no** occurrence of "three-dimensional",
"tomograph" or "serial section" (verified by text search of the full text).

**(b) Wang et al. 2026, *Microstructures* 6, 2026047 — doi 10.20517/microstructures.2025.144** —
**full text retrieved.**

- Results, §1: verbatim — "Figure 1A presents an EBSD inverse-pole figure (IPF) map of an as-fabricated
  specimen, presenting acicular α' martensitic phase. **The average length and width of these platelets
  are 8.1 ± 2.0 µm and 0.9 ± 0.4 µm, respectively.**"
- Method: plane-view specimen "cut perpendicular to the build direction", EBSD step size 25 nm.
  ⇒ **2D section (plane-view EBSD)**, not 3D.
- The authors call the short dimension **"width"**, not "thickness".
- Individual laths: Fig. 2A (TKD, top layer) "Lath A (yellow) measures **1.2 µm in width**";
  Fig. 3A (TKD, bottom layer) "The width of lath A is **860 nm**."
- Not lath widths (do not use): Fig. 2A allotriomorphic α′ bands 98 ± 27 nm; linked twins 73 ± 14 nm,
  non-linked twins 34 ± 11 nm.

⇒ The brief's "8.1 ± 2.0 µm long × 0.9 ± 0.4 µm thick, i.e. length:thickness ≈ 9:1" is really
**2D length:short-dimension = 9.0**; the paper says "width".

### Direct consequence for the model (this is the actionable finding)

The literature exposes **two apparent dimensions** per α′ lath, not three. Therefore **a 2D section
cannot separate `width` from `thickness`**, and the data constrain only **one** exponent, not two.
The current parameter pair, however, asserts a specific cross-sectional anisotropy:

- `β_h = 3.5` ⇒ length/thickness = e^3.5 = **33.1**
- `β_w = 2.3` ⇒ length/width = e^2.3 = **10.0**
- ⇒ implied **width/thickness = e^(3.5−2.3) = e^1.2 = 3.32**

**No source found in this search reports a lath width and thickness separately, so the assumed 3.3:1
rectangular cross-section is unsupported by any same-material same-process measurement.**
And `β_h = 3.5` (length:thickness ≈ 33) is larger than *every* 2D length:short ratio I found
(9.0 – 23.8), i.e. it is not corroborated either.

---

## 2. TABLE — all α′/α lath dimensions found

### (a) Same material (Ti-6Al-4V) AND same process (LPBF/SLM), as-built α′

| value | quantity | material | process | method | source + DOI | figure/table | full text? | caveats |
|---|---|---|---|---|---|---|---|---|
| **0.239–0.304 µm** (mean 0.259) paired with **5.065–5.685 µm** (mean 5.417); 2D L:W = 16.7–23.8, mean 20.9 | α′ lath **width** + **length** | Ti-6Al-4V | LPBF, as-built (BLT-A300; 190 W, 30 µm, 90 mm/s, 140 µm) | **2D section** — BSE on Kroll-etched metallographic section; 50 laths randomly selected per specimen; 10 specimens | Xie et al. 2026, *Materials* 19:1945, doi **10.3390/ma19101945** (PMC13208675) | **Table 2** | **yes** | **Best unbiased 2D pair found.** No length pre-filter. Still 2D; single build orientation; apparent length truncated by the section plane |
| **0.51–0.88 µm** (0.68 ± 0.27; 0.51 ± 0.14) | α′ lath short dimension — paper says **both "width" and "thickness"** | Ti-6Al-4V | LPBF, as-built (AmPro SP100; 173–193 W, 664–1200 mm/s, h 0.06–0.16 mm) | **2D section** — BSE, **linear intercept, GB/T 6394-2017**, n ≥ 300 intercepts/sample, 56 conditions | Shuai et al. 2026, *Materials* 19:1049, doi **10.3390/ma19061049** (PMC13027919) | §3.2 text; **Figure 5** (labelled values); **Figure 6** (0.51–0.88 µm at 173 W) | **yes** | "width"/"thickness" used interchangeably for ONE measurement. A linear intercept gives a mean chord, not a plate thickness or width |
| **length 8.1 ± 2.0 µm; short dim 0.9 ± 0.4 µm**; 2D L:W = 9.0 | α′ platelet length + **width** | Ti-6Al-4V | L-PBF, as-built (SLM 250 HL; 100 W, 375 mm/s, 30 µm, 120 µm) | **2D section** — EBSD IPF map, **plane-view** specimen ⊥ build direction, step 25 nm | Wang et al. 2026, *Microstructures* 6:2026047, doi **10.20517/microstructures.2025.144** | Results §1, **Figure 1A** | **yes** | 2D. Also: Lath A = 1.2 µm wide (TKD, Fig 2A, top layer); Lath A = 860 nm (Fig 3A, bottom layer) |
| **≈0.7 µm** | "ultrafine martensitic laths … average **thickness**" | Ti-6Al-4V | L-PBF, as-built α′ | **2D section** — BSE image | Ren et al. 2026, *Materials* 19:3300, doi **10.3390/ma19153300** (PMC13468040) | **Figure 1c** (Fig. 1 caption: "(a–c) L-PBF and (d–f) [EB-PBF]") | **yes** | "approximately"; no n, no distribution; sample-level statement, not a statistic |
| **649 nm** (unmodified LPBF Ti-64) → 143 nm (Ti-64 + 5 wt% CoCrNi) | α′ lath **width** | Ti-6Al-4V model alloy (and CoCrNi-modified) | LPBF, as-built (EOS M100; 100 W, 20 µm, 60 µm, 1800 mm/s) | **method not stated in main text** — measurement deferred to Supplementary Fig. 8 | Chen et al. 2026, *Nat Commun* 17:959, doi **10.1038/s41467-025-67683-8** (PMC12848114) | Discussion, "Multifunctional contributions of CoCrNi additives"; **Supplementary Fig. 8** | **yes** (main text) | **649 nm is the UNMODIFIED LPBF Ti-6Al-4V baseline** — usable as a same-material/process value. But the technique is not described in the main text, so I cannot verify whether it is 2D SEM, TEM or 3D. ⚠ The 26.3 nm "martensitic lath width" elsewhere in the same paper is a **deformation-induced TRIP** lath at 2.5 % strain — NOT the as-built α′ lath |
| prior-β grain width **124.59–143.52 µm**; aspect ratio **4.5–17.4** | prior-β grain (host, not lath) | Ti-6Al-4V | LPBF, as-built | 2D OM, ImageJ, 15 images/sample | Shuai et al. 2026, doi 10.3390/ma19061049 | §3.1; **Figures 3, 4** | **yes** | Block/packet-scale host only. Columnar grains "lengths exceeding 1.00 mm" |
| basket-weave: "These α’ martensite laths form a **basket-weave structure** within the prior-β grains" | morphology — **no size given** | Ti-6Al-4V | LPBF, as-built | BSE | Shuai et al. 2026, doi 10.3390/ma19061049 | §3.2 | **yes** | No basket-weave / colony / packet dimension is reported |
| **no numeric α′ lath width of any kind** | — | Ti-6Al-4V | LPBF, as-built | — | — | — | — | This is the primary result (see §1) |

---

## 3. NOT USABLE as anchor — cross-material / cross-process / cross-condition

| value | quantity | material | process | method | source + DOI | figure/table | full text? | why unusable |
|---|---|---|---|---|---|---|---|---|
| **100–300 nm** α-lath width | α lath in **partly decomposed α′** (early stage) | Ti-6Al-4V | LPBF, but **intrinsically heat-treated down-skin region** | 2D SEM | Zhou et al. 2025, *Materials* 18:3756, doi **10.3390/ma18163756** (PMC12387259) | §3, **Figure 7e** | **yes** | Same material+process but the phase state is **decomposed α+β**, not as-built α′. Verbatim: "it seems to be at a very early stage of α′ martensite decomposition, featuring a 100–300 nm α-lath width" |
| **0.4–0.8 µm**; also "< 0.5 µm" | α-lath width, lamellar α+β / Widmanstätten | Ti-6Al-4V | LPBF, down-skin region | 2D SEM | Zhou et al. 2025, doi 10.3390/ma18163756 | **Figure 7e**, §3 | **yes** | α+β, not α′ |
| **0.65–1.32 µm** mean α-lath width | α lath width vs heat input | Ti-6Al-4V | **wire-laser DED** | 2D (Fig. 6) | Wang et al. 2026, *Materials* 19:3885, doi **10.3390/ma19183885** (PMC13608371) | **Figure 6** | **yes** | **Cross-process** (DED, not LPBF) |
| **0.84 ± 0.10** (∥BD) / **0.97 ± 0.14** (⊥BD) µm, avg 0.91 | α lath thickness, **as-built EBM** | Ti-6Al-4V | **EB-PBF / EBM** | 2D LOM at 1000×, ImageJ; interlamellar-spacing method (Ridley) | Jeffs et al. 2021, *Materials* 14:5376, doi **10.3390/ma14185376** (PMC8466331) | **Table 2** | **yes** | **Cross-process.** ⚠ Note it is the one study that measured in **two orthogonal planes** (∥ and ⊥ BD) — a good methodological template, but its values are EBM |
| **≈1.9 µm** α lath thickness | α laths + retained V-enriched β | Ti-6Al-4V | **EB-PBF** | 2D BSE | Ren et al. 2026, doi 10.3390/ma19153300 | **Figure 1f** | **yes** | **Cross-process** |
| **0.28 → 1.55 µm** α′ lath width (0.28 ± 0.07 … 1.55 ± 0.35) | α′ lath width vs wall thickness | **TA15 (Ti-6Al-2Zr-1Mo-1V)** | LPBF | 2D SEM | Zhang et al. 2026, *Materials* 19:2341, doi **10.3390/ma19112341** (PMC13257545) | **Figure 5a–l** | **yes** | **Cross-material** (TA15 ≠ Ti-6Al-4V) |
| lath-like α′ **thickness ≈1 µm, length 10–50 µm**; needle-like α′ **thickness ≈0.2 µm, length 2–5 µm** | two distinct as-built α′ populations | **TA15** | LPBF, as-built | 2D | *Materials* 2024, 17:3361, doi **10.3390/ma17133361** (PMC11243706) | **Figure 2a** | **yes** | **Cross-material.** ⚠ But conceptually important: as-built LPBF α′ contains **two morphologically distinct populations**. This is a plausible explanation for the factor ~3 spread among the Ti-64 sources in §4 |
| **0.71–2.62 µm** α lath thickness | α lath thickness, "Widmanstätten" | Ti-6Al-4V | LPBF **+ heat treatment** | EBSD α orientation maps | *Nat Commun* 2025, doi **10.1038/s41467-025-56267-1** (PMC11754831) | Fig. 6a1–d1; **Supplementary Fig. 9** | **yes** | State ambiguous — the paper optimises process **and** heat-treatment parameters; described as Widmanstätten α laths in an α matrix, i.e. **not** as-built α′ |
| **0.1–0.3 µm** lath thickness | lath martensite thickness | **steel** | — | — | unsourced in the project code | — | **no** | **Cross-material.** This is the classic steel lath-martensite thickness the audit already flagged; it must not be used |
| **2D aspect ratios 8.37 ± 3.86 (XY) / 2.83 ± 1.41 (ZX)** | 2D section aspect ratio of **primary** laths | Ti-6Al-4V | LPBF | 2D section | Ter Haar & Becker 2021, *Mater. Sci. Eng. A* (2021), doi **10.1016/j.msea.2021.141185** | unknown | **NO — not independently verified** | **⚠ I could NOT verify these numbers.** ScienceDirect is paywalled and the Stellenbosch repository returns HTTP 403 to every retrieval route I tried (direct, proxy, referer, mirror). Reported as **UNVERIFIED**; do not cite. (Bibliographic existence verified via Crossref; the volume/page is not re-verified here.) Independently of verification: the study **pre-filtered to primary laths longer than 20 µm**, which removes the short-lath population and inflates the ratio. Compare Xie's unfiltered mean 20.9 |
| **3D-EBSD α lath morphology** (no width/aspect ratio stated in abstract) | α lath morphology | Ti-6Al-4V | **E-PBF / EBM** | **3D** — plasma-FIB serial-sectioning 3D-EBSD | DeMott et al. 2020, *Ultramicroscopy* 218:113073, doi **10.1016/j.ultramic.2020.113073** | — | **abstract/metadata only** | **Cross-process.** This is the **only genuinely 3D α-lath metrology** found anywhere in this search — and it is EBM, not LPBF. (Related: *Ultramicroscopy* 230:113394, doi 10.1016/j.ultramic.2021.113394 = 3D-EBSD *methods* paper; DeMott UNSW PhD thesis, doi 10.26190/unsworks/22752.) |
| — (qualitative only) | α platelet width, 3D | Ti-6Al-4V | E-PBF / EBM | 3D-EBSD | DeMott UNSW PhD thesis (DOI 10.26190/unsworks/22752, per a parallel Crossref/Unpaywall lookup — not independently re-verified here; thesis identity confirmed from its own title page) | Ch. 2.5 / Ch. 4 | **yes** (PDF retrieved and text-mined) | **Cross-process.** I downloaded and text-mined the full 160-page thesis: it argues *why* platelet width matters and **explicitly warns that 2D sections misrepresent interconnected platelets as discrete particles**, but it **does not report a quantitative 3D α-lath width.** Its value to you is methodological, not numerical |

† (removed — DOI verified as 10.3390/ma19183885)

---

## 4. Contradictions between sources

1. **The short dimension of LPBF Ti-64 as-built α′ spans a factor of ~3.7 across studies:**
   0.239–0.304 µm (Xie, BSE, n=50/specimen, random) · 0.51–0.88 µm (Shuai, BSE linear intercept,
   n≥300) · 0.649 µm (Chen, method unspecified) · ≈0.7 µm (Ren, BSE) · 0.9 ± 0.4 µm (Wang, EBSD).
   Plausible causes, none verifiable from the papers as written: (i) **different feature populations**
   — the TA15 study, cross-material but same process, explicitly resolves two populations (coarse
   lath-like ≈1 µm thick / 10–50 µm long and fine needle-like ≈0.2 µm thick / 2–5 µm long);
   (ii) **different resolution cut-offs** (Xie's BSE at high magnification vs Wang's 25 nm-step EBSD);
   (iii) **different section orientations** (Xie: gauge section; Wang: plane view ⊥ BD);
   (iv) **different measurement definitions** (individual-lath vs linear intercept).
   **This spread cannot be resolved without 3D data.**

2. **2D length:short ratio disagrees by a factor 2.3 between the two LPBF Ti-64 studies that report
   both dimensions:** ≈9 (Wang) vs ≈21 (Xie). Both are 2D; neither applied a stereological correction.

3. **Terminology contradiction inside a single paper:** Shuai et al. use "lath width" and "lath
   thickness" for the *same* measurement (see §1). Any downstream reader tabulating "width" from that
   paper is silently double-counting one number as two.

4. **Ter Haar 2021 vs Xie 2026:** 8.37 (XY) / 2.83 (ZX) vs 20.9. Ter Haar's numbers are not comparable
   because of the >20 µm length pre-filter (and are independently unverified here). **Do not use.**

5. **Internal inconsistency in the current code parameters:** `β_h = 3.5` implies length:thickness ≈ 33,
   but no 2D measurement in this search exceeds 24. So `β_h` is as unsupported as `β_w`.

---

## 5. Search log — exact queries run, and what the nulls mean

**Structured APIs (full-text search):**
- Europe PMC REST (`/search`, full-text index): `"lath width" AND "Ti-6Al-4V"` (24 hits) ·
  `"lath width" AND "laser powder bed fusion"` (8) · `"lath thickness" AND "Ti-6Al-4V"` (34) ·
  `"lath width" AND titanium AND additive` (32) · `"lath width" AND "selective laser melting"` (16) ·
  `"lath width" AND martensite AND "additive manufacturing"` (20) · `"lath width" AND "electron backscatter"` (20) ·
  `"aspect ratio" AND lath AND titanium AND martensite` (40) · `"basket-weave" AND "Ti-6Al-4V"` (77) ·
  `"three-dimensional" AND lath AND "Ti-6Al-4V"` (48) · `"martensitic lath" AND "Ti-6Al-4V" AND "laser powder bed fusion"` (3) ·
  `"lath" AND "FIB" AND "tomography" AND "Ti-6Al-4V"` (**4, none relevant**) ·
  `"atom probe" AND "alpha prime" AND "Ti-6Al-4V"` (**0**) ·
  `"serial sectioning" AND titanium AND lath` (**3, none LPBF/Ti-64**) ·
  `"lath width" AND "laser powder bed fusion"` (8) · `"average length" AND "average width" AND lath` (8) ·
  `lath AND "colony size" AND "Ti-6Al-4V" AND additive` (6) ·
  `packet AND block AND martensite AND "Ti-6Al-4V" AND "laser powder bed fusion"` (**1, irrelevant**)
- Crossref `query.bibliographic` and OpenAlex `search` for the named sources; Semantic Scholar Graph API
  for OA status of every closed-access candidate; Unpaywall-style OA resolution.

**Web / free-text:** `α′ lath width LPBF Ti-6Al-4V as-built martensite dimensions` ·
`3D lath dimensions FIB tomography Ti-6Al-4V laser powder bed fusion martensite` ·
`"aspect ratio" α′ martensite lath SLM Ti64 length width` · `TEM bright field alpha prime martensite lath width nm as-built SLM Ti-6Al-4V measurement` ·
`"3D" alpha prime lath width laser powder bed fusion titanium X-ray tomography measurement nm` ·
`"nf-HEDM" OR "diffraction contrast tomography" alpha lath laser powder bed fusion Ti-6Al-4V martensite 3D` ·
**Chinese-language:** `激光选区熔化 TC4 Ti-6Al-4V α′马氏体 板条宽度 尺寸 测量` ·
`选区激光熔化 Ti-6Al-4V 马氏体板条 宽度 nm 透射电镜` ·
`材料科学与工艺 2019 α/α' 板条宽度 表 激光选区熔化 Ti-6Al-4V 综述`

**Full texts actually retrieved and text-mined (not just abstracts):** PMC13027919 (Shuai 2026) ·
the *Microstructures* HTML (Wang 2026) · PMC13208675 (Xie 2026) · PMC13468040 (Ren 2026) ·
PMC12848114 (Chen 2026) · PMC12387259 (Zhou 2025) · PMC13257545 (Zhang 2026, TA15) ·
PMC13608371 (Wang 2026, DED) · PMC8466331 (Jeffs 2021, EBM) · PMC9146263 (EBM) · PMC11901288 (ANN/wrought) ·
PMC11243706 (TA15) · PMC11754831 (Nat Commun active learning) · PMC13363186 (PBF-LB as-built vs
stress-relief — **no numeric α′ lath width**) · PMC12787245, PMC12430090, PMC12430167, PMC13468040,
PMC13363627, PMC12525584, PMC12848114, PMC13058786, PMC12372868 · DeMott UNSW PhD thesis PDF ·
Glasgow PhD thesis PDF · UCLouvain FSP paper PDF.

**What the nulls mean (deliberately checked, with negative controls):**
- `"FIB tomography" AND titanium AND lath` → 0; `"serial sectioning" AND titanium AND lath` → 3, none
  LPBF/Ti-64; `"atom probe" AND "alpha prime" AND "Ti-6Al-4V"` → 0. **Genuinely 3D α′ lath metrology
  in LPBF Ti-64 does not appear to exist.**
- The only genuinely 3D α-lath work found is on **E-PBF/EBM** (DeMott). Its existence is a *positive
  control*: the technique is publishable and the literature does contain 3D α-lath studies — they are
  simply on a different process.
- `basket-weave` is abundant (77 hits) but overwhelmingly qualitative; **no basket-weave/colony/packet
  size for LPBF Ti-64 as-built α′ was found.**
- A Chinese-language review table with an "α/α′ lath width /µm" column was located at
  `hit.alljournals.cn` (file_no=20190201, 2019 issue 2) but the site's JavaScript guard blocked every
  retrieval route (direct, proxied curl, referer, `web_fetch`). **This is the single most promising
  un-retrieved lead** and is worth a manual browser visit.

**Sources I could NOT retrieve:** Yang et al. 2016 *Mater. Des.* 108:308, doi 10.1016/j.matdes.2016.06.117
(closed; ScienceDirect 403) — a standard LPBF Ti-64 α′ reference; Saumitra et al. 2025 *Materialia*,
doi 10.1016/j.mtla.2025.102579 and 10.1016/j.mtla.2025.102463 (closed); Ter Haar & Becker 2021
*MSEA* 814:141185 (closed; Stellenbosch repo 403). For these I have **title/venue/DOI only — no
numbers are reported from them anywhere in this document.**

---

## 6. BOTTOM LINE

**Can `β_w` be anchored from literature?**

**Not rigorously. No 3D α′ lath width exists for LPBF Ti-64 as-built, so `β_w` cannot be anchored
independently.** The best that 2D data supports:

| source | 2D length:short | implied exponent ln(L/W) |
|---|---|---|
| Xie et al. 2026 (unfiltered, n=50 × 10 specimens, BSE) | 16.7 – 23.8; mean 20.9 | **2.81 – 3.17** (mean **3.04**) |
| Wang et al. 2026 (EBSD plane view, 8.1±2.0 / 0.9±0.4) | 9.0 (range 4.7 – 20.2 from the ± SDs) | **1.55 – 3.01** (central **2.20**) |

⇒ **`β_w ≈ 2.2 – 3.2`, central estimate ≈ 2.2 (Wang) to ≈ 3.0 (Xie)** — i.e. **an uncertainty of ~±0.5
in the exponent, a factor ~2.3 in length:width.** Note this range happens to bracket the incumbent
`β_w = 2.3`, but that agreement is **coincidental**: the incumbent came from an unsourced
"length/width ≈ 10", which matches Wang's 9.0 and not Xie's 20.9.

**The important structural conclusion: the literature constrains only ONE exponent, not two.**
Because a 2D section cannot separate width from thickness, two consistent readings are possible and
the literature cannot currently distinguish them:

- **If the α′ lath cross-section is near-equiaxed** (width ≈ thickness) → `β_w ≈ β_h ≈ 2.2 – 3.0`, and
  the current split (3.5 / 2.3, implying a 3.3:1 rectangular cross-section) is **wrong**.
- **If the lath is ribbon-like** (width ≫ thickness) → the 2D short dimension mostly samples the
  thickness, so `β_h ≈ 2.2 – 3.0` and **`β_w` is essentially unconstrained** (could be far below 2.3).

**Also flagged:** `β_h = 3.5` implies length:thickness ≈ 33 while no 2D measurement found exceeds 24 —
so `β_h` currently rests on no better evidence than `β_w` does.

**What measurement would settle it.** A single specimen could resolve the ambiguity, because the
required information is the *shape of the lath cross-section*:

1. **Preferred — 3D:** plasma-FIB serial-sectioning **3D-EBSD** (the DeMott protocol, applied to
   **LPBF** rather than EBM Ti-64) or FIB-SEM tomography of a Kroll-etched/backscatter-contrasted
   volume. Deliverable: for each reconstructed lath, the three principal dimensions ⇒ true
   3D length:width:thickness and hence both `β_w` and `β_h` with real error bars. This is the only
   route that gives a defensible `β_w`.
2. **Cheap surrogate — two orthogonal 2D sections with stereological correction.** Measure lath
   dimensions on a plane **containing the build direction** *and* on a plane **normal to it**, on the
   same specimen, with ≥300 individual laths per plane and a stated lower resolution cut-off
   (the Jeffs 2021 EBM study is the methodological template). If the apparent short dimension differs
   strongly between the two planes, the cross-section is anisotropic and width ≠ thickness; if it does
   not, the near-equiaxed reading is favoured and `β_w ≈ β_h`.
3. **Diagnostic to run on existing micrographs first (free):** plot the *distribution* of the 2D short
   dimension, not just its mean. A single population suggests one lath family; a bimodal distribution
   (as explicitly seen in LPBF TA15, doi 10.3390/ma17133361) means the "width" numbers from different
   papers are sampling different features, which would explain the factor ~3.7 spread in §4.1 and
   means **no single literature value should be used as an anchor at all**.

**Recommendation:** do not re-calibrate `β_w` to a single literature number. Either (i) run the
two-plane measurement in (2) — cheap and decisive for the equiaxed-vs-ribbon question — or
(ii) treat `β_w` and `β_h` as a **single fitted parameter with an explicit degeneracy**, state that the
literature constrains only `ln(length/short-dimension) ≈ 2.2 – 3.2`, and report the width/thickness
cross-sectional anisotropy as an **assumed, unsupported** modelling choice.
