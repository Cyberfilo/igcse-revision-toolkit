#!/usr/bin/env python3
"""Integrate the 88 HTML notes from 0654_html/ into the notes/ tree.

For each HTML file it:
  1. Looks up the syllabus topic + subtopics it covers (hand-curated mapping below).
  2. Prepends an HTML-comment metadata block (parsed by the dashboard).
  3. Writes the result to notes/<subject>/<original-filename>.
  4. Leaves the source file in place so re-running is idempotent.

Run once after dropping the html folder:
    python scripts/integrate_html_notes.py
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "0654_html"
NOTES = ROOT / "notes"

# (filename_prefix → (subject, code, subtopics, title))
# subtopics is the list of subtopic codes covered. code is the parent topic.
MAP: dict[str, tuple[str, str, list[str], str]] = {
    # --- Biology ---
    "01_characteristics-of-living":   ("biology", "B1",  ["B1.1"],                                  "Characteristics of living organisms"),
    "02_cell-structure":              ("biology", "B2",  ["B2.1"],                                  "Cell structure"),
    "03_specialised-cells":           ("biology", "B2",  ["B2.1"],                                  "Specialised cells"),
    "04_diffusion":                   ("biology", "B3",  ["B3.1"],                                  "Diffusion"),
    "05_osmosis":                     ("biology", "B3",  ["B3.2"],                                  "Osmosis"),
    "06_active-transport":            ("biology", "B3",  ["B3.3"],                                  "Active transport"),
    "07_biological-molecules":        ("biology", "B4",  ["B4.1"],                                  "Biological molecules"),
    "08_enzymes":                     ("biology", "B5",  ["B5.1"],                                  "Enzymes"),
    "09_photosynthesis":              ("biology", "B6",  ["B6.1"],                                  "Photosynthesis"),
    "10_leaf-structure":              ("biology", "B6",  ["B6.2"],                                  "Leaf structure"),
    "11_diet":                        ("biology", "B7",  ["B7.1"],                                  "Diet"),
    "12_digestive-system":            ("biology", "B7",  ["B7.2"],                                  "Digestive system"),
    "13_digestion-absorption":        ("biology", "B7",  ["B7.3"],                                  "Digestion and absorption"),
    "14_transport-in-plants":         ("biology", "B8",  ["B8.1","B8.2","B8.3","B8.4"],             "Transport in plants"),
    "15_heart-circulation":           ("biology", "B9",  ["B9.1","B9.2"],                           "Heart and circulation"),
    "16_blood-vessels-blood":         ("biology", "B9",  ["B9.3","B9.4"],                           "Blood vessels and blood"),
    "17_diseases-immunity":           ("biology", "B10", ["B10.1"],                                 "Diseases and immunity"),
    "18_gas-exchange":                ("biology", "B11", ["B11.1"],                                 "Gas exchange in humans"),
    "19_respiration":                 ("biology", "B12", ["B12.1"],                                 "Respiration"),
    "20_nervous-system":              ("biology", "B13", ["B13.1"],                                 "Nervous system"),
    "21_hormones":                    ("biology", "B13", ["B13.2"],                                 "Hormones"),
    "22_homeostasis":                 ("biology", "B13", ["B13.3"],                                 "Homeostasis"),
    "23_drugs":                       ("biology", "B14", ["B14.1"],                                 "Drugs"),
    "24_asexual-sexual-reproduction": ("biology", "B15", ["B15.1","B15.2"],                         "Asexual and sexual reproduction"),
    "25_plant-reproduction":          ("biology", "B15", ["B15.3"],                                 "Sexual reproduction in plants"),
    "26_human-reproduction":          ("biology", "B15", ["B15.4","B15.5"],                         "Sexual reproduction in humans"),
    "27_chromosomes-cell-division":   ("biology", "B16", ["B16.1","B16.2"],                         "Chromosomes & cell division"),
    "28_monohybrid-inheritance":      ("biology", "B16", ["B16.3"],                                 "Monohybrid inheritance"),
    "29_variation-selection":         ("biology", "B17", ["B17.1","B17.2"],                         "Variation and selection"),
    "30_ecosystems":                  ("biology", "B18", ["B18.1","B18.2","B18.3","B19.1"],         "Ecosystems"),
    # --- Chemistry ---
    "31_states-of-matter":            ("chemistry", "C1",  ["C1.1"],                                "States of matter"),
    "32_diffusion-chem":              ("chemistry", "C1",  ["C1.2"],                                "Diffusion (chemistry)"),
    "33_elements-compounds-mixtures": ("chemistry", "C2",  ["C2.1"],                                "Elements, compounds and mixtures"),
    "34_atomic-structure":            ("chemistry", "C2",  ["C2.2"],                                "Atomic structure"),
    "35_isotopes":                    ("chemistry", "C2",  ["C2.3"],                                "Isotopes"),
    "36_ions-ionic-bonds":            ("chemistry", "C2",  ["C2.4"],                                "Ions and ionic bonds"),
    "37_covalent-bonds":              ("chemistry", "C2",  ["C2.5"],                                "Covalent bonds"),
    "38_giant-metallic":              ("chemistry", "C2",  ["C2.6","C2.7"],                         "Giant covalent and metallic structures"),
    "39_formulas-equations":          ("chemistry", "C3",  ["C3.1"],                                "Formulas and equations"),
    "40_moles":                       ("chemistry", "C3",  ["C3.2","C3.3"],                         "Moles and Avogadro"),
    "41_electrolysis":                ("chemistry", "C4",  ["C4.1"],                                "Electrolysis"),
    "42_fuel-cells":                  ("chemistry", "C4",  ["C4.2"],                                "Hydrogen-oxygen fuel cells"),
    "43_energetics":                  ("chemistry", "C5",  ["C5.1"],                                "Energetics (exo/endothermic)"),
    "44_physical-vs-chemical":        ("chemistry", "C6",  ["C6.1"],                                "Physical vs chemical changes"),
    "45_rate-of-reaction":            ("chemistry", "C6",  ["C6.2"],                                "Rate of reaction"),
    "46_redox":                       ("chemistry", "C6",  ["C6.3"],                                "Redox"),
    "47_acids-bases-salts":           ("chemistry", "C7",  ["C7.1","C7.2","C7.3"],                  "Acids, bases and salts"),
    "48_periodic-table":              ("chemistry", "C8",  ["C8.1","C8.2","C8.3","C8.4","C8.5"],    "The Periodic Table"),
    "49_properties-uses-metals":      ("chemistry", "C9",  ["C9.1","C9.2"],                         "Properties and uses of metals"),
    "50_alloys":                      ("chemistry", "C9",  ["C9.3"],                                "Alloys"),
    "51_reactivity-series":           ("chemistry", "C9",  ["C9.4"],                                "Reactivity series"),
    "52_corrosion-extraction":        ("chemistry", "C9",  ["C9.5","C9.6"],                         "Corrosion and extraction"),
    "53_air-water-quality":           ("chemistry", "C10", ["C10.1","C10.2"],                       "Air and water quality"),
    "54_alkanes":                     ("chemistry", "C11", ["C11.1","C11.2","C11.3","C11.4"],       "Alkanes (and organic intro)"),
    "55_alkenes-alcohols":            ("chemistry", "C11", ["C11.5","C11.6"],                       "Alkenes and alcohols"),
    "56_polymers":                    ("chemistry", "C11", ["C11.7"],                               "Polymers"),
    "57_separation-techniques":       ("chemistry", "C12", ["C12.3","C12.4"],                      "Separation techniques"),
    "58_ion-identification":          ("chemistry", "C12", ["C12.5"],                              "Identification of ions"),
    # --- Physics ---
    "59_physical-quantities":         ("physics", "P1",  ["P1.1"],                                  "Physical quantities and measurement"),
    "60_motion":                      ("physics", "P1",  ["P1.2"],                                  "Motion"),
    "61_mass-weight-density":         ("physics", "P1",  ["P1.3","P1.4"],                           "Mass, weight, density"),
    "62_effects-of-forces":           ("physics", "P1",  ["P1.5"],                                  "Effects of forces"),
    "63_moments":                     ("physics", "P1",  ["P1.5"],                                  "Moments"),
    "64_centre-of-gravity":           ("physics", "P1",  ["P1.5"],                                  "Centre of gravity"),
    "65_energy":                      ("physics", "P1",  ["P1.6"],                                  "Energy"),
    "66_work-power":                  ("physics", "P1",  ["P1.6"],                                  "Work and power"),
    "67_energy-resources":            ("physics", "P1",  ["P1.6"],                                  "Energy resources"),
    "68_pressure":                    ("physics", "P1",  ["P1.7"],                                  "Pressure"),
    "69_kinetic-particle-model":      ("physics", "P2",  ["P2.1"],                                  "Kinetic particle model"),
    "70_thermal-expansion":           ("physics", "P2",  ["P2.2"],                                  "Thermal expansion"),
    "71_phase-change":                ("physics", "P2",  ["P2.2"],                                  "Phase change"),
    "72_heat-transfer":               ("physics", "P2",  ["P2.3"],                                  "Heat transfer"),
    "73_waves-properties":            ("physics", "P3",  ["P3.1"],                                  "Wave properties"),
    "74_reflection-refraction":       ("physics", "P3",  ["P3.2"],                                  "Reflection and refraction"),
    "75_lenses":                      ("physics", "P3",  ["P3.2"],                                  "Lenses"),
    "76_dispersion":                  ("physics", "P3",  ["P3.2"],                                  "Dispersion"),
    "77_em-spectrum":                 ("physics", "P3",  ["P3.3"],                                  "EM spectrum"),
    "78_sound":                       ("physics", "P3",  ["P3.4"],                                  "Sound"),
    "79_magnetism":                   ("physics", "P4",  ["P4.1"],                                  "Magnetism"),
    "80_charge-current":              ("physics", "P4",  ["P4.2"],                                  "Charge and current"),
    "81_voltage-resistance":          ("physics", "P4",  ["P4.2"],                                  "Voltage and resistance"),
    "82_electrical-power":            ("physics", "P4",  ["P4.2","P4.4"],                           "Electrical power and safety"),
    "83_circuits":                    ("physics", "P4",  ["P4.3"],                                  "Circuits"),
    "84_electromagnetic-induction":   ("physics", "P4",  ["P4.5"],                                  "Electromagnetic induction"),
    "85_nuclear-atoms":               ("physics", "P5",  ["P5.1"],                                  "Nuclear atoms"),
    "86_radioactivity":               ("physics", "P5",  ["P5.2"],                                  "Radioactivity"),
    "87_half-life":                   ("physics", "P5",  ["P5.2"],                                  "Half-life"),
    "88_space":                       ("physics", "P6",  ["P6.1","P6.2"],                           "Space"),
}

META_HEAD = "<!--meta"
META_TAIL = "-->"
META_RE = re.compile(r"^<!--meta\s*\n(.*?)\n-->\s*\n?", re.S)


def build_meta(code: str, subject: str, title: str, subtopics: list[str], source_name: str) -> str:
    subs = "[" + ", ".join(subtopics) + "]"
    return (
        f"{META_HEAD}\n"
        f"code: {code}\n"
        f"title: {title}\n"
        f"subject: {subject}\n"
        f"papers: [22, 42]\n"
        f"subtopics: {subs}\n"
        f"kind: html-note\n"
        f"source: 0654_html/{source_name}\n"
        f"{META_TAIL}\n\n"
    )


def main():
    if not SRC_DIR.exists():
        sys.exit(f"missing {SRC_DIR}")

    moved = 0; skipped = 0; unmapped = []
    for src in sorted(SRC_DIR.glob("*.html")):
        prefix = src.stem  # e.g. "01_characteristics-of-living"
        if prefix not in MAP:
            unmapped.append(src.name)
            continue
        subject, code, subtopics, title = MAP[prefix]
        dest_dir = NOTES / subject
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name

        body = src.read_text(encoding="utf-8")
        # Strip any pre-existing meta block (idempotent)
        body = META_RE.sub("", body, count=1).lstrip()
        meta = build_meta(code, subject, title, subtopics, src.name)
        dest.write_text(meta + body, encoding="utf-8")
        moved += 1

    print(f"integrated: {moved} files")
    if unmapped:
        print(f"unmapped:   {len(unmapped)}")
        for n in unmapped: print(f"  - {n}")


if __name__ == "__main__":
    main()
