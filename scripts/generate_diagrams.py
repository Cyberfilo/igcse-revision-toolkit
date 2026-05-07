#!/usr/bin/env python3
"""Generate IGCSE 0654 revision diagrams with matplotlib.

Each diagram is saved at notes/_diagrams/<key>.png with a paired sidecar JSON
describing where it should be embedded (target HTML file + caption + section
anchor). embed_diagrams.py reads the sidecar and inserts the image into the
right note.

Run:
    python scripts/generate_diagrams.py
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field

import matplotlib.pyplot as plt
import numpy as np

OUT = pathlib.Path("notes/_diagrams")
OUT.mkdir(parents=True, exist_ok=True)

# ---------- Light theme matching the dashboard ----------
PALETTE = {
    "bg":       "#ffffff",
    "axes_bg":  "#ffffff",
    "grid":     "#e1e4ec",
    "edge":     "#c8ccd6",
    "text":     "#1a1d24",
    "label":    "#3d4250",
    "muted":    "#6b7180",
    "accent":   "#0a8c8c",
    "bio":      "#2da55b",
    "chem":     "#4078e6",
    "phys":     "#d97e2c",
    "warn":     "#d94343",
}
plt.rcParams.update({
    "figure.facecolor": PALETTE["bg"],
    "savefig.facecolor": PALETTE["bg"],
    "axes.facecolor": PALETTE["axes_bg"],
    "axes.edgecolor": PALETTE["edge"],
    "axes.labelcolor": PALETTE["label"],
    "axes.titlecolor": PALETTE["text"],
    "axes.titlesize": 12,
    "axes.titlepad": 14,
    "axes.labelsize": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": PALETTE["grid"],
    "grid.alpha": 0.5,
    "grid.linewidth": 0.6,
    "xtick.color": PALETTE["label"],
    "ytick.color": PALETTE["label"],
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.facecolor": PALETTE["axes_bg"],
    "legend.edgecolor": PALETTE["edge"],
    "legend.fontsize": 9,
    "text.color": PALETTE["text"],
    "font.family": "sans-serif",
    "font.size": 10,
    "figure.dpi": 110,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.2,
})


@dataclass
class Diagram:
    key: str
    target_html: str        # relative to notes/
    section: str            # title shown in the note for this group
    caption: str            # caption below the figure
    builder: callable = field(repr=False)


REGISTRY: list[Diagram] = []


def register(key, target_html, section, caption):
    def decorator(fn):
        REGISTRY.append(Diagram(key, target_html, section, caption, fn))
        return fn
    return decorator


def save(fig, key):
    path = OUT / f"{key}.png"
    fig.savefig(path)
    plt.close(fig)
    return path


# ============== BIOLOGY ==============

@register("B5.1_enzyme_temperature", "biology/08_enzymes.html",
          "Effect of temperature & pH",
          "Enzyme rate vs temperature: rises with kinetic energy until denaturation around 40°C.")
def _():
    fig, ax = plt.subplots(figsize=(6, 3.6))
    T = np.linspace(0, 80, 400)
    # Bell-ish curve peaking ~37°C, sharp drop after denaturation
    rate = np.exp(-((T - 37) / 14) ** 2) * (T > 0)
    rate = np.where(T > 45, rate * np.exp(-(T - 45) / 4), rate)
    ax.plot(T, rate, color=PALETTE["bio"], linewidth=2.4)
    ax.axvline(37, color=PALETTE["accent"], linestyle="--", linewidth=1, alpha=0.7)
    ax.text(37.6, 0.95, "optimum\n~37 °C", color=PALETTE["accent"], fontsize=9, va="top")
    ax.text(60, 0.4, "denaturation", color=PALETTE["warn"], fontsize=9)
    ax.set_xlabel("Temperature (°C)")
    ax.set_ylabel("Rate of reaction")
    ax.set_xlim(0, 80); ax.set_ylim(0, 1.1)
    ax.set_yticks([])
    return save(fig, "B5.1_enzyme_temperature")


@register("B5.1_enzyme_ph", "biology/08_enzymes.html",
          "Effect of temperature & pH",
          "Enzyme rate vs pH: pepsin (acidic ~2), amylase (~7), trypsin (~8) all peak at their optimum and drop sharply on either side.")
def _():
    fig, ax = plt.subplots(figsize=(6, 3.6))
    pH = np.linspace(0, 14, 400)
    pepsin   = np.exp(-((pH - 2) / 1.0) ** 2)
    amylase  = np.exp(-((pH - 7) / 1.2) ** 2)
    trypsin  = np.exp(-((pH - 8) / 1.0) ** 2)
    ax.plot(pH, pepsin,  color=PALETTE["warn"],   label="Pepsin (stomach)",         linewidth=2.2)
    ax.plot(pH, amylase, color=PALETTE["bio"],    label="Amylase (saliva)",         linewidth=2.2)
    ax.plot(pH, trypsin, color=PALETTE["accent"], label="Trypsin (small intestine)", linewidth=2.2)
    ax.set_xlabel("pH")
    ax.set_ylabel("Rate of reaction")
    ax.set_xlim(0, 14); ax.set_ylim(0, 1.15)
    ax.set_yticks([])
    ax.legend(loc="upper right")
    return save(fig, "B5.1_enzyme_ph")


@register("B6.1_photosynthesis_light", "biology/09_photosynthesis.html",
          "Limiting factors",
          "Photosynthesis rate vs light intensity: rises linearly then plateaus when another factor (CO₂ or temperature) becomes limiting.")
def _():
    fig, ax = plt.subplots(figsize=(6, 3.6))
    I = np.linspace(0, 10, 400)
    # Two curves: low CO2 and high CO2
    low  = 1.4 * (1 - np.exp(-I / 1.4))
    high = 2.4 * (1 - np.exp(-I / 1.6))
    ax.plot(I, low,  color=PALETTE["bio"],    label="0.04% CO₂ (atmospheric)", linewidth=2.2)
    ax.plot(I, high, color=PALETTE["accent"], label="0.4% CO₂ (enriched)",     linewidth=2.2)
    ax.set_xlabel("Light intensity")
    ax.set_ylabel("Rate of photosynthesis")
    ax.set_xlim(0, 10); ax.set_ylim(0, 2.7)
    ax.set_yticks([]); ax.set_xticks([])
    ax.legend(loc="lower right")
    return save(fig, "B6.1_photosynthesis_light")


@register("B17.1_variation_distributions", "biology/29_variation-selection.html",
          "Continuous vs discontinuous variation",
          "Continuous variation (e.g. height) → smooth distribution. Discontinuous (e.g. blood group) → distinct categories.")
def _():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.6))
    # Continuous
    rng = np.random.default_rng(42)
    heights = rng.normal(165, 10, 4000)
    ax1.hist(heights, bins=30, color=PALETTE["bio"], alpha=0.85, edgecolor=PALETTE["bg"], linewidth=1)
    ax1.set_title("Continuous — height")
    ax1.set_xlabel("Height (cm)")
    ax1.set_ylabel("Frequency")
    # Discontinuous
    cats = ["A", "B", "AB", "O"]
    counts = [42, 10, 4, 44]
    bars = ax2.bar(cats, counts, color=[PALETTE["accent"], PALETTE["chem"], PALETTE["phys"], PALETTE["bio"]],
                   edgecolor=PALETTE["bg"], linewidth=1)
    ax2.set_title("Discontinuous — blood group")
    ax2.set_xlabel("Blood group")
    ax2.set_ylabel("% of population")
    for b, c in zip(bars, counts):
        ax2.text(b.get_x() + b.get_width()/2, c + 1, f"{c}%", ha="center", color=PALETTE["label"], fontsize=9)
    fig.tight_layout()
    return save(fig, "B17.1_variation_distributions")


# ============== CHEMISTRY ==============

@register("C5.1_reaction_profile_exo", "chemistry/43_energetics.html",
          "Reaction profiles",
          "Exothermic profile: products at lower energy than reactants. ΔH is negative.")
def _():
    fig, ax = plt.subplots(figsize=(6, 3.6))
    x = np.linspace(0, 1, 400)
    # Hump in middle
    ea_height = 1.0
    reactant_E, product_E = 0.7, 0.2
    base = reactant_E + (product_E - reactant_E) * x
    bump = ea_height * np.exp(-((x - 0.5) / 0.12) ** 2)
    y = np.maximum(base, base + bump - 0)  # blend the bump
    y = base + bump * np.exp(-((x - 0.5) / 0.18) ** 2)
    ax.plot(x, y, color=PALETTE["chem"], linewidth=2.6)
    ax.annotate("", xy=(0.05, reactant_E), xytext=(0.05, max(y)),
                arrowprops=dict(arrowstyle="<->", color=PALETTE["accent"]))
    ax.text(0.07, (reactant_E + max(y)) / 2, "Eₐ (activation)", color=PALETTE["accent"], fontsize=9, va="center")
    ax.annotate("", xy=(0.95, reactant_E), xytext=(0.95, product_E),
                arrowprops=dict(arrowstyle="<->", color=PALETTE["bio"]))
    ax.text(0.85, (reactant_E + product_E) / 2, "ΔH < 0", color=PALETTE["bio"], fontsize=9, ha="right", va="center")
    ax.text(0.0, reactant_E + 0.05, "reactants", color=PALETTE["label"], fontsize=9)
    ax.text(0.78, product_E + 0.05, "products", color=PALETTE["label"], fontsize=9)
    ax.set_xlabel("Reaction progress →")
    ax.set_ylabel("Energy")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("Exothermic reaction profile")
    return save(fig, "C5.1_reaction_profile_exo")


@register("C5.1_reaction_profile_endo", "chemistry/43_energetics.html",
          "Reaction profiles",
          "Endothermic profile: products at higher energy than reactants. ΔH is positive.")
def _():
    fig, ax = plt.subplots(figsize=(6, 3.6))
    x = np.linspace(0, 1, 400)
    reactant_E, product_E = 0.2, 0.6
    base = reactant_E + (product_E - reactant_E) * x
    bump = 0.7 * np.exp(-((x - 0.5) / 0.18) ** 2)
    y = base + bump
    ax.plot(x, y, color=PALETTE["phys"], linewidth=2.6)
    ax.annotate("", xy=(0.05, reactant_E), xytext=(0.05, max(y)),
                arrowprops=dict(arrowstyle="<->", color=PALETTE["accent"]))
    ax.text(0.07, (reactant_E + max(y)) / 2, "Eₐ", color=PALETTE["accent"], fontsize=9, va="center")
    ax.annotate("", xy=(0.95, reactant_E), xytext=(0.95, product_E),
                arrowprops=dict(arrowstyle="<->", color=PALETTE["warn"]))
    ax.text(0.85, (reactant_E + product_E) / 2, "ΔH > 0", color=PALETTE["warn"], fontsize=9, ha="right", va="center")
    ax.text(0.0, reactant_E + 0.05, "reactants", color=PALETTE["label"], fontsize=9)
    ax.text(0.78, product_E + 0.05, "products", color=PALETTE["label"], fontsize=9)
    ax.set_xlabel("Reaction progress →")
    ax.set_ylabel("Energy")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("Endothermic reaction profile")
    return save(fig, "C5.1_reaction_profile_endo")


@register("C6.2_rate_concentration_time", "chemistry/45_rate-of-reaction.html",
          "Rate from a graph",
          "Concentration of product vs time — gradient is the rate; reaction slows as reactants are consumed.")
def _():
    fig, ax = plt.subplots(figsize=(6, 3.6))
    t = np.linspace(0, 60, 400)
    # First-order-like
    c_high = 1 - np.exp(-t / 8)
    c_low  = 1 - np.exp(-t / 18)
    ax.plot(t, c_high, color=PALETTE["chem"],  label="higher T or +catalyst", linewidth=2.4)
    ax.plot(t, c_low,  color=PALETTE["accent"], label="baseline",              linewidth=2.4)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("[product]")
    ax.legend(loc="lower right")
    ax.set_yticks([])
    return save(fig, "C6.2_rate_concentration_time")


@register("C6.2_rate_factors", "chemistry/45_rate-of-reaction.html",
          "Effect of factors on rate",
          "Increasing temperature, concentration, surface area, or adding a catalyst — all raise the rate. Catalyst lowers Eₐ so more particles have enough energy.")
def _():
    fig, ax = plt.subplots(figsize=(6, 3.6))
    E = np.linspace(0, 5, 400)
    # Maxwell-Boltzmann-ish curves
    f_low  = E * np.exp(-E / 1.0)
    f_high = E * np.exp(-E / 1.6)
    f_low  /= f_low.max();  f_high /= f_high.max()
    Ea, Ea_cat = 2.5, 1.4
    ax.plot(E, f_low,  color=PALETTE["chem"],   label="lower temperature", linewidth=2.2)
    ax.plot(E, f_high, color=PALETTE["phys"],   label="higher temperature", linewidth=2.2)
    ax.axvline(Ea,     color=PALETTE["warn"],   linestyle="--", linewidth=1.2, label="Eₐ (no catalyst)")
    ax.axvline(Ea_cat, color=PALETTE["bio"],    linestyle="--", linewidth=1.2, label="Eₐ (with catalyst)")
    ax.fill_between(E, 0, f_high, where=(E >= Ea), color=PALETTE["phys"], alpha=0.15)
    ax.fill_between(E, 0, f_high, where=(E >= Ea_cat), color=PALETTE["bio"], alpha=0.10)
    ax.set_xlabel("Particle energy")
    ax.set_ylabel("Number of particles")
    ax.set_xticks([]); ax.set_yticks([])
    ax.legend(loc="upper right")
    return save(fig, "C6.2_rate_factors")


# ============== PHYSICS ==============

@register("P1.2_motion_distance_time", "physics/60_motion.html",
          "Motion graphs",
          "Distance–time: gradient = speed. Straight line = constant speed; curve = changing speed.")
def _():
    fig, ax = plt.subplots(figsize=(6, 3.6))
    t = np.linspace(0, 10, 400)
    constant_v = 3 * t
    accel = 0.5 * t**2
    ax.plot(t, constant_v, color=PALETTE["bio"],    label="constant velocity", linewidth=2.4)
    ax.plot(t, accel,      color=PALETTE["accent"], label="accelerating",       linewidth=2.4)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Distance (m)")
    ax.legend(loc="upper left")
    ax.set_xlim(0, 10)
    return save(fig, "P1.2_motion_distance_time")


@register("P1.2_motion_velocity_time", "physics/60_motion.html",
          "Motion graphs",
          "Velocity–time: gradient = acceleration; area under curve = displacement.")
def _():
    fig, ax = plt.subplots(figsize=(6, 3.6))
    t = np.linspace(0, 10, 400)
    v = np.piecewise(t, [t < 3, (t >= 3) & (t < 7), t >= 7],
                        [lambda t: 5 * t, lambda t: 15, lambda t: 15 - 4 * (t - 7)])
    ax.plot(t, v, color=PALETTE["phys"], linewidth=2.6)
    ax.fill_between(t, 0, v, alpha=0.18, color=PALETTE["phys"])
    ax.text(1.5, 4, "accelerating\n(positive grad.)", color=PALETTE["bio"], fontsize=8.5, ha="center")
    ax.text(5,   13, "constant velocity", color=PALETTE["label"], fontsize=8.5, ha="center")
    ax.text(8.5, 5, "decelerating", color=PALETTE["warn"], fontsize=8.5, ha="center")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Velocity (m/s)")
    ax.set_xlim(0, 10); ax.set_ylim(0, 18)
    return save(fig, "P1.2_motion_velocity_time")


@register("P1.5_hookes_law", "physics/62_effects-of-forces.html",
          "Hooke's law",
          "Force–extension: linear up to the limit of proportionality, then deformation becomes plastic.")
def _():
    fig, ax = plt.subplots(figsize=(6, 3.6))
    x = np.linspace(0, 10, 400)
    F = np.where(x < 6, 1.5 * x, 9 + 0.6 * (x - 6) ** 0.6)
    ax.plot(x, F, color=PALETTE["accent"], linewidth=2.6)
    ax.axvline(6, color=PALETTE["warn"], linestyle="--", linewidth=1)
    ax.text(6.2, 2, "limit of\nproportionality", color=PALETTE["warn"], fontsize=8.5)
    ax.text(2, 7, "F = kx\n(linear region)", color=PALETTE["bio"], fontsize=9)
    ax.set_xlabel("Extension x (cm)")
    ax.set_ylabel("Force F (N)")
    ax.set_xlim(0, 10); ax.set_ylim(0, 14)
    return save(fig, "P1.5_hookes_law")


@register("P3.1_wave_anatomy", "physics/73_waves-properties.html",
          "Wave anatomy",
          "Sine wave with wavelength λ and amplitude A labelled. Frequency = waves per second; v = fλ.")
def _():
    fig, ax = plt.subplots(figsize=(6, 3.6))
    x = np.linspace(0, 4 * np.pi, 600)
    y = np.sin(x)
    ax.plot(x, y, color=PALETTE["accent"], linewidth=2.6)
    ax.axhline(0, color=PALETTE["edge"], linewidth=0.8)
    # Amplitude
    ax.annotate("", xy=(np.pi/2, 0), xytext=(np.pi/2, 1),
                arrowprops=dict(arrowstyle="<->", color=PALETTE["bio"]))
    ax.text(np.pi/2 + 0.15, 0.5, "A (amplitude)", color=PALETTE["bio"], fontsize=9, va="center")
    # Wavelength
    ax.annotate("", xy=(0, -1.3), xytext=(2 * np.pi, -1.3),
                arrowprops=dict(arrowstyle="<->", color=PALETTE["phys"]))
    ax.text(np.pi, -1.45, "λ (wavelength)", color=PALETTE["phys"], fontsize=9, ha="center", va="top")
    ax.set_xlabel("Distance / time")
    ax.set_ylabel("Displacement")
    ax.set_xlim(0, 4 * np.pi); ax.set_ylim(-1.7, 1.7)
    ax.set_xticks([]); ax.set_yticks([])
    return save(fig, "P3.1_wave_anatomy")


@register("P4.2_iv_characteristics", "physics/81_voltage-resistance.html",
          "I–V characteristics",
          "Current vs voltage: ohmic resistor (straight, V=IR), filament lamp (curves as it heats and resistance rises), diode (zero until ~0.7 V, then steeply rises).")
def _():
    fig, ax = plt.subplots(figsize=(6, 3.6))
    V = np.linspace(-3, 3, 600)
    ohmic = V / 1.5
    lamp  = np.sign(V) * np.abs(V) ** 0.55 * 0.9
    diode = np.where(V > 0.7, 1.6 * (np.exp((V - 0.7) * 1.8) - 1), 0)
    diode = np.clip(diode, -0.05, 2.5)
    ax.plot(V, ohmic, color=PALETTE["bio"],    label="Ohmic resistor", linewidth=2.4)
    ax.plot(V, lamp,  color=PALETTE["phys"],   label="Filament lamp",   linewidth=2.4)
    ax.plot(V, diode, color=PALETTE["accent"], label="Diode",           linewidth=2.4)
    ax.axhline(0, color=PALETTE["edge"], linewidth=0.6)
    ax.axvline(0, color=PALETTE["edge"], linewidth=0.6)
    ax.set_xlabel("Voltage V (V)")
    ax.set_ylabel("Current I (A)")
    ax.set_xlim(-3, 3); ax.set_ylim(-2.5, 2.5)
    ax.legend(loc="lower right")
    return save(fig, "P4.2_iv_characteristics")


@register("P5.2_radioactive_decay", "physics/87_half-life.html",
          "Radioactive decay",
          "Activity halves every half-life T½. After n half-lives, activity = N₀ × (½)ⁿ.")
def _():
    fig, ax = plt.subplots(figsize=(6, 3.6))
    half_life = 5
    t = np.linspace(0, 30, 600)
    N = 100 * (0.5) ** (t / half_life)
    ax.plot(t, N, color=PALETTE["warn"], linewidth=2.6)
    for n in range(1, 5):
        x = n * half_life
        y = 100 * (0.5) ** n
        ax.plot([x, x], [0, y], color=PALETTE["edge"], linestyle=":", linewidth=0.8)
        ax.plot([0, x], [y, y], color=PALETTE["edge"], linestyle=":", linewidth=0.8)
        ax.text(x + 0.2, y + 2, f"{int(y)}%", color=PALETTE["accent"], fontsize=9)
    ax.axvline(half_life, color=PALETTE["accent"], linestyle="--", alpha=0.6, linewidth=1)
    ax.text(half_life + 0.3, 95, f"T½ = {half_life} units", color=PALETTE["accent"], fontsize=9)
    ax.set_xlabel("Time")
    ax.set_ylabel("Activity (% of original)")
    ax.set_xlim(0, 30); ax.set_ylim(0, 110)
    return save(fig, "P5.2_radioactive_decay")


# ============== Run ==============

def main():
    sidecars = []
    for d in REGISTRY:
        path = d.builder()
        sidecars.append({
            "key": d.key,
            "image": str(path.relative_to(pathlib.Path("."))),
            "target_html": d.target_html,
            "section": d.section,
            "caption": d.caption,
        })
        print(f"  ✓ {path}")
    manifest_path = OUT / "manifest.json"
    manifest_path.write_text(json.dumps(sidecars, indent=2, ensure_ascii=False))
    print(f"\nwrote {len(sidecars)} diagrams + {manifest_path}")


if __name__ == "__main__":
    main()
