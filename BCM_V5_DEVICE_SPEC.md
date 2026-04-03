# BCM v5 — Substrate Mode Selection Device (SMSD)
# Engineering Specification — Benchtop Prototype
# Stephen Justin Burdick Sr. — Emerald Entities LLC
# 2026-03-31

---

## Purpose

Test BCM's core prediction: H(m) = (c_s - Omega*R/m)^2 selects azimuthal modes
in any rotating conductive system with a shear boundary. The tachocline gate
predicts that removing the shear boundary locks the system to m=1.

This is Path A from peer review: prove it's physics with a lab analog.

---

## Design: Modified Taylor-Couette Cell with MHD Mode Detection

Two concentric cylinders. Conductive liquid between them. Inner cylinder
rotates (variable speed). Outer cylinder stationary. External magnetic field
from permanent magnets. Hall sensors around circumference detect which
azimuthal mode (m) the fluid selects.

The differential rotation between inner and outer cylinder IS the tachocline.
The gap between them IS the convective zone. The outer wall IS the radiative
boundary.

---

## Bill of Materials

| Component                        | Source            | Est. Cost |
|----------------------------------|-------------------|-----------|
| Galinstan (GaInSn) 50g           | United Nuclear    |    $15.00 |
| Galinstan (GaInSn) 50g (spare)   | United Nuclear    |    $15.00 |
| Acrylic tube, 4" OD, 12" long    | Amazon/McMaster   |    $15.00 |
| Acrylic rod, 2" OD (inner cyl)   | Amazon/McMaster   |    $10.00 |
| Sealed bearings (2x 608ZZ)       | Amazon            |     $5.00 |
| DC motor 12V with PWM controller | Amazon            |    $25.00 |
| Motor coupling to inner cylinder | 3D print or shaft |     $5.00 |
| N52 neodymium magnets (10 pack)  | Amazon            |    $20.00 |
| Arduino Mega 2560                | Amazon            |    $35.00 |
| 49E Hall sensors (12 pack)       | AliExpress        |    $10.00 |
| ADS1115 16-bit ADC modules (3x)  | Amazon            |    $15.00 |
| Breadboard, jumper wires, misc   | Amazon            |    $15.00 |
| 12V power supply                 | Amazon            |    $12.00 |
| Silicone gaskets / O-rings       | McMaster          |     $8.00 |
| Epoxy, sealant, mounting         | Hardware store    |    $10.00 |
| Tachometer / optical encoder     | Amazon            |    $10.00 |
|                                  |                   |           |
| **TOTAL**                        |                   | **$225.00** |

Under $250. Maintenance: replace gaskets and galinstan annually (~$30/yr).

---

## Engineering Challenges — Honest Assessment

### Challenge 1: Magnetic Reynolds Number

MHD modes only form when the magnetic Reynolds number Rm = mu_0 * sigma * V * L
is large enough. For galinstan:

    sigma = 3.46e6 S/m (electrical conductivity)
    mu_0  = 4*pi*1e-7
    V     = Omega * R_inner (tangential velocity)
    L     = gap width (~2.5 cm = 0.025 m)

At 1000 RPM (Omega = 104.7 rad/s), R_inner = 0.025 m:
    V = 104.7 * 0.025 = 2.62 m/s
    Rm = 4*pi*1e-7 * 3.46e6 * 2.62 * 0.025 = 0.285

PROBLEM: Rm < 1. MHD modes require Rm >> 1 for self-excited dynamo.

RESPONSE: BCM doesn't require self-excited dynamo. BCM requires externally
forced mode selection. The external magnets provide B. The fluid doesn't
generate its own field — it responds to the imposed field by organizing into
azimuthal patterns. This is closer to magnetized Taylor-Couette flow, where
Rm ~ 0.1-1 is sufficient for MRI (magnetorotational instability) onset.

The Princeton MRI experiment (Goodman & Ji 2002) detected MRI at Rm ~ 0.1
using gallium. We're in the same regime.

BCM prediction: the fluid doesn't need to self-excite. It needs to SELECT
a mode from the externally imposed field. H(m) minimization is a selection
criterion, not a generation criterion.

VERDICT: Proceed. But this is the first thing a reviewer will attack.
Document Rm explicitly and cite Princeton MRI.

### Challenge 2: Mode Detection Sensitivity

Hall sensors (49E) have resolution ~1 mT. The azimuthal field perturbations
from MHD mode selection in a 5cm cell will be weak — possibly microtesla.

RESPONSE: Two mitigations.
1. Use external field from strong N52 magnets (B ~ 0.5 T at surface,
   ~0.05 T in fluid gap). Mode perturbations on a 50 mT background
   are detectable as relative modulation, not absolute field.
2. Use 16-bit ADC (ADS1115, 0.0078 mV resolution) instead of Arduino's
   10-bit analog. At 3.3V reference, that's ~50 uT resolution with
   the 49E sensor's 1.4 mV/G sensitivity.

Place 8 hall sensors at 45-degree intervals around circumference.
m=1 shows one peak. m=2 shows two peaks. m=4 shows four.
Signal processing: FFT on 8-sensor array gives azimuthal mode number directly.

VERDICT: Marginal but feasible. If signal is too weak, upgrade to
fluxgate magnetometers (~$40 each, 0.1 uT resolution).

### Challenge 3: Galinstan Wetting and Containment

Galinstan wets most metals aggressively (amalgamation). It will destroy
aluminum, zinc, and attack copper. The inner cylinder cannot be metal.

RESPONSE: Use acrylic for both cylinders. Galinstan does not wet plastics
or glass. Seal with silicone gaskets. The fluid sits in a plastic annular
gap — no metal contact except the hall sensor tips, which are encapsulated
in epoxy.

VERDICT: Solved. Standard practice in liquid metal labs.

### Challenge 4: The Tachocline Gate Test

BCM predicts: remove the shear boundary, system locks to m=1.

TEST: Run two configurations.
Config A — Inner cylinder rotates, outer stationary (differential rotation
           = tachocline present). Vary Omega, record m vs RPM.
Config B — Both cylinders rotate at same speed (solid body rotation =
           no tachocline, fully convective analog). Record m.

BCM predicts Config B always gives m=1 regardless of Omega or B.
Standard MHD predicts Config B can still support higher modes from
Kelvin-Helmholtz or other instabilities if Rm is sufficient.

This is the decisive test. If Config B locks to m=1 and Config A shows
variable m depending on Omega, BCM wins.

VERDICT: This is the experiment. Everything else is setup for this one test.

### Challenge 5: Distinguishing BCM from Standard MHD

A skeptic will say: "Mode selection in Taylor-Couette MHD is well understood.
You're just seeing normal MHD instabilities, not substrate coupling."

RESPONSE: BCM makes a specific quantitative prediction that standard MHD
does not. At resonance:

    m = Omega * R / c_s

where c_s is the substrate phase speed. Standard MHD predicts mode selection
based on Rm, Hartmann number Ha, and geometry — but does NOT predict a
specific m as a function of rotation rate from a single formula.

THE TEST: Scan Omega from 100 RPM to 3000 RPM. Record m at each speed.
Plot m vs Omega. BCM predicts a staircase function:

    m = round(Omega * R / c_s)

with discrete jumps at specific Omega values. Standard MHD predicts smooth
transitions or chaotic mode competition.

If the data shows discrete mode jumps at the Omega values BCM predicts
(after fitting c_s from the first transition), that's confirmation.
If the transitions are smooth or don't match the predicted Omega values,
BCM fails.

VERDICT: Clean falsifiable test. One free parameter (c_s for this
specific geometry), then all subsequent transitions are predictions.

---

## Measurement Protocol

1. Fill cell with galinstan. Seal. Zero all hall sensors.
2. Apply external B field (magnets mounted on frame around outer cylinder).
3. CONFIG A (tachocline present):
   a. Sweep inner cylinder from 0 to 3000 RPM in 50 RPM steps.
   b. At each step, wait 30 seconds for settle.
   c. Record 8 hall sensors at 1 kHz for 10 seconds.
   d. FFT each sweep. Extract dominant azimuthal mode number.
   e. Plot m vs Omega. Look for staircase.
4. CONFIG B (no tachocline):
   a. Couple both cylinders to same motor (solid body).
   b. Repeat sweep.
   c. BCM predicts m=1 at all speeds.
5. CONFIG C (variable tachocline depth):
   a. Use a sleeve to change gap width (analog to conv_depth_frac).
   b. Narrow gap = deep tachocline = high modes accessible.
   c. Wide gap = shallow tachocline = approaching gate threshold.
   d. Find the gap width where mode selection becomes unstable
      (the EV Lac boundary analog).

---

## What Success Looks Like

1. Config A shows discrete m values (staircase) as Omega increases.
2. Config B shows m=1 at all rotation rates (tachocline gate confirmed).
3. The transition Omega values in Config A match m = round(Omega*R/c_s)
   after fitting c_s from the first transition.
4. Config C identifies a gap width where mode selection becomes bistable
   (the EV Lac analog — flickering between two m values at the boundary).

## What Failure Looks Like

1. Config A shows smooth/chaotic mode evolution (no staircase).
2. Config B shows modes other than m=1 (gate fails).
3. Transition points don't match the predicted Omega staircase.
4. No signal above noise floor in hall sensors.

Both outcomes are publishable. Success validates BCM at lab scale.
Failure constrains where BCM applies and where it doesn't.

---

## Timeline

Week 1: Order parts. Design mount in CAD or hand-sketch.
Week 2: Assemble cell. Wire sensors. Test motor/PWM.
Week 3: Fill with galinstan. Run Config B first (simpler, decisive).
Week 4: Run Config A sweep. Analyze data.

Total: one month from parts to first data.

---

*$225 in parts. One equation. One month. Either it works or it doesn't.*
*That's how you prove it's physics.*
