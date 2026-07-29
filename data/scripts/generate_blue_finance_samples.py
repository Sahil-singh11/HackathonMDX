#!/usr/bin/env python3
"""Generate the Blue Finance pillar's sample corpus (constructed, not real).

Task 6b's own instruction: "If you cannot obtain real ones, use clearly
labelled constructed examples with data_kind: 'sample' - and say so on the
surface, not just in a comment." A real, public, redistributable blue-bond
framework document was not obtained for this repo, so these three PDFs are
deliberately fabricated to exercise the deterministic criteria checker across
a compliant, a partial, and an ineligible case. Every page says "CONSTRUCTED
SAMPLE" - this is not a real bond and must never be presented as one.
"""
from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "pillars" / "finance" / "samples"

BANNER = "CONSTRUCTED SAMPLE - fabricated for testing/demo only, not a real bond framework"


def _doc(title: str, sections: list[tuple[str, str]]) -> FPDF:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(200, 30, 30)
    pdf.cell(0, 6, BANNER, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    for heading, body in sections:
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 7, heading, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 6, body, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
    return pdf


def compliant() -> FPDF:
    return _doc(
        "Sample Blue Bond Framework - Compliant Illustration",
        [
            ("Use of Proceeds",
             "Net proceeds will exclusively finance or refinance eligible projects supporting "
             "sustainable seafood value chains, including responsibly managed aquaculture and "
             "fishery improvement projects certified against recognised standards."),
            ("Process for Project Evaluation and Selection",
             "An internal Sustainability Committee, comprising representatives from Treasury, "
             "Risk and Environmental Affairs, reviews and approves each candidate project against "
             "the eligibility criteria above before inclusion in the eligible project portfolio."),
            ("Management of Proceeds",
             "Proceeds are tracked in a sub-ledger and allocated to the eligible portfolio within "
             "24 months of issuance. Unallocated proceeds are held in cash or cash equivalents."),
            ("Impact Metrics",
             "The issuer will report annually on: tonnes of certified sustainable seafood produced, "
             "hectares of marine habitat under improved management, and number of fishery "
             "improvement projects supported."),
            ("Reporting",
             "The issuer commits to publish an annual allocation and impact report on its investor "
             "relations website until full allocation, and annually thereafter while the bond is outstanding."),
            ("External Review",
             "A second-party opinion on this framework has been obtained from an independent "
             "sustainability ratings provider, and is available on the issuer's website."),
        ],
    )


def partial() -> FPDF:
    return _doc(
        "Sample Blue Bond Framework - Partial Illustration",
        [
            ("Use of Proceeds",
             "Proceeds will finance projects supporting coastal and marine tourism infrastructure "
             "improvements, including waste management upgrades at coastal resort facilities."),
            ("Process for Project Evaluation and Selection",
             "Candidate projects are reviewed by the issuer's finance department prior to allocation."),
            ("Management of Proceeds",
             "Proceeds are held in the issuer's general treasury account pending allocation."),
            # Impact metrics section deliberately omitted.
            ("Reporting",
             "The issuer intends to provide periodic updates to bondholders as available."),
            # External review section deliberately omitted.
        ],
    )


def ineligible() -> FPDF:
    return _doc(
        "Sample Corporate Bond Framework - Ineligible Illustration",
        [
            ("Use of Proceeds",
             "Net proceeds will be used for general corporate purposes, including working capital "
             "and the refinancing of existing indebtedness across the issuer's operations."),
            ("Process for Project Evaluation and Selection",
             "Not applicable - proceeds are not earmarked to specific projects."),
            ("Management of Proceeds",
             "Proceeds are commingled with the issuer's general funds."),
            ("Reporting",
             "Standard periodic financial reporting as required by applicable securities law."),
        ],
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    docs = {
        "sample_blue_bond_compliant.pdf": compliant(),
        "sample_blue_bond_partial.pdf": partial(),
        "sample_bond_ineligible.pdf": ineligible(),
    }
    for name, pdf in docs.items():
        path = OUT / name
        pdf.output(str(path))
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
