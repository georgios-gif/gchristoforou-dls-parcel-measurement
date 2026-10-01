"""Υπολογισμός εμβαδού και περιμέτρου τεμαχίων από αρχείο DXF.

Διαβάζει κλειστές πολυγραμμές (LWPOLYLINE / POLYLINE) και τυπώνει
εμβαδόν (m²) και περίμετρο (m) για καθεμία. Οι μονάδες του σχεδίου
($INSUNITS: mm, cm, m) μετατρέπονται σε μέτρα· τα τόξα προσεγγίζονται
με χορδές ακρίβειας 1 mm.

Χρήση:
    python parcel_area.py αρχείο.dxf [--layer ΟΝΟΜΑ] [--csv έξοδος.csv]
"""
import argparse
import csv
import math

import ezdxf
from ezdxf import path as ezpath

# $INSUNITS -> συντελεστής μετατροπής σε μέτρα
UNIT_TO_M = {0: 1.0, 4: 0.001, 5: 0.01, 6: 1.0}


def shoelace_area(points):
    n = len(points)
    s = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def perimeter(points):
    n = len(points)
    return sum(math.dist(points[i], points[(i + 1) % n]) for i in range(n))


def polyline_points(entity, scale):
    closed = entity.closed if entity.dxftype() == "LWPOLYLINE" else entity.is_closed
    pts = []
    for v in ezpath.make_path(entity).flattening(0.001 / scale):
        p = (v.x * scale, v.y * scale)
        if not pts or math.dist(p, pts[-1]) > 1e-6:
            pts.append(p)
    if len(pts) > 1 and math.dist(pts[0], pts[-1]) <= 1e-6:
        pts.pop()
    return pts, closed


def measure(path, layer=None):
    doc = ezdxf.readfile(path)
    units = doc.header.get("$INSUNITS", 0)
    if units not in UNIT_TO_M:
        raise SystemExit(f"Μη υποστηριζόμενες μονάδες σχεδίου ($INSUNITS={units})")
    scale = UNIT_TO_M[units]
    results = []
    for e in doc.modelspace().query("LWPOLYLINE POLYLINE"):
        if layer and e.dxf.layer != layer:
            continue
        pts, closed = polyline_points(e, scale)
        if not closed or len(pts) < 3:
            continue
        results.append({
            "handle": e.dxf.handle,
            "layer": e.dxf.layer,
            "vertices": len(pts),
            "area_m2": round(shoelace_area(pts), 2),
            "perimeter_m": round(perimeter(pts), 2),
        })
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dxf")
    ap.add_argument("--layer")
    ap.add_argument("--csv")
    ap.add_argument("--min-area", type=float, default=0.0, help="ελάχιστο εμβαδόν m²")
    args = ap.parse_args()

    rows = [r for r in measure(args.dxf, args.layer) if r["area_m2"] >= args.min_area]
    if not rows:
        print("Δεν βρέθηκαν κλειστές πολυγραμμές.")
        return
    print(f"{'Handle':<10}{'Layer':<15}{'Κορυφές':>8}{'Εμβαδόν m²':>14}{'Περίμετρος m':>15}")
    for r in rows:
        print(f"{r['handle']:<10}{r['layer']:<15}{r['vertices']:>8}{r['area_m2']:>14.2f}{r['perimeter_m']:>15.2f}")
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        print(f"Αποθηκεύτηκε: {args.csv}")


if __name__ == "__main__":
    main()
