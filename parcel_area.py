"""Υπολογισμός εμβαδού και περιμέτρου τεμαχίων από αρχείο DXF.

Διαβάζει κλειστές πολυγραμμές (LWPOLYLINE / POLYLINE) και τυπώνει
εμβαδόν (m²) και περίμετρο (m) για καθεμία.

Χρήση:
    python parcel_area.py αρχείο.dxf [--layer ΟΝΟΜΑ] [--csv έξοδος.csv]
"""
import argparse
import csv
import math
import sys

import ezdxf


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


def polyline_points(entity):
    if entity.dxftype() == "LWPOLYLINE":
        if any(b != 0 for *_, b in entity.get_points("xyb")):
            raise ValueError("περιέχει τόξα (bulge) — δεν υποστηρίζεται ακόμη")
        return [(x, y) for x, y in entity.get_points("xy")], entity.closed
    pts = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
    return pts, entity.is_closed


def measure(path, layer=None):
    doc = ezdxf.readfile(path)
    results = []
    for e in doc.modelspace().query("LWPOLYLINE POLYLINE"):
        if layer and e.dxf.layer != layer:
            continue
        try:
            pts, closed = polyline_points(e)
        except ValueError as err:
            print(f"Παράλειψη {e.dxf.handle}: {err}", file=sys.stderr)
            continue
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
    args = ap.parse_args()

    rows = measure(args.dxf, args.layer)
    if not rows:
        print("Δεν βρέθηκαν κλειστές πολυγραμμές.")
        return
    print(f"{'Handle':<8}{'Layer':<15}{'Κορυφές':>8}{'Εμβαδόν m²':>14}{'Περίμετρος m':>15}")
    for r in rows:
        print(f"{r['handle']:<8}{r['layer']:<15}{r['vertices']:>8}{r['area_m2']:>14.2f}{r['perimeter_m']:>15.2f}")
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        print(f"Αποθηκεύτηκε: {args.csv}")


if __name__ == "__main__":
    main()
