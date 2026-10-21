import csv
import os

output_dir = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\output"
os.makedirs(output_dir, exist_ok=True)

# Summary totals
summary_path = os.path.join(output_dir, "member_summary.csv")
with open(summary_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Member Type", "Count", "Notes"])
    writer.writerow(["Beams (horizontal)", 174, "Flat Bar profiles oriented horizontally"])
    writer.writerow(["Columns (vertical)", 12, "RO 139.7x8.0 | EN 10210-2:2006"])
    writer.writerow(["Other / diagonal / bracing", 375, "Various Flat Bar and Rectangle profiles"])
    writer.writerow(["RD 12 (curve-only, bracing rods)", 175, "Only in MemberAxes representation"])
    writer.writerow(["TOTAL unique members", 736, "561 Breps + 175 RD 12 curves"])

# Beams breakdown
beams_path = os.path.join(output_dir, "beams_breakdown.csv")
with open(beams_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Profile", "Count"])
    writer.writerow(["Flat Bar 275/12", 35])
    writer.writerow(["Flat Bar 175/12", 35])
    writer.writerow(["Flat Bar 225/12", 35])
    writer.writerow(["Flat Bar 275/20", 23])
    writer.writerow(["Flat Bar 175/20", 23])
    writer.writerow(["Flat Bar 225/20", 23])

# Columns breakdown
columns_path = os.path.join(output_dir, "columns_breakdown.csv")
with open(columns_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Profile", "Count"])
    writer.writerow(["RO 139.7x8.0 | EN 10210-2:2006", 12])

# Other breakdown
other_path = os.path.join(output_dir, "other_breakdown.csv")
with open(other_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Profile", "Count"])
    writer.writerow(["Flat Bar 33.3/20", 116])
    writer.writerow(["Rectangle 500/500", 47])
    writer.writerow(["Flat Bar 275/12", 35])
    writer.writerow(["Flat Bar 162.5/12", 35])
    writer.writerow(["Flat Bar 200/12", 35])
    writer.writerow(["Flat Bar 237.5/12", 35])
    writer.writerow(["Flat Bar 275/20", 18])
    writer.writerow(["Flat Bar 162.5/20", 18])
    writer.writerow(["Flat Bar 237.5/20", 18])
    writer.writerow(["Flat Bar 200/20", 18])

# Profile comparison (Brep vs Curve)
comparison_path = os.path.join(output_dir, "profile_comparison.csv")
with open(comparison_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Profile", "Brep Count", "Curve Count", "Duplicated"])
    data = [
        ("Flat Bar 162.5/12", 35, 35, True),
        ("Flat Bar 162.5/20", 18, 18, True),
        ("Flat Bar 175/12", 35, 35, True),
        ("Flat Bar 175/20", 23, 23, True),
        ("Flat Bar 200/12", 35, 35, True),
        ("Flat Bar 200/20", 18, 18, True),
        ("Flat Bar 225/12", 35, 35, True),
        ("Flat Bar 225/20", 23, 23, True),
        ("Flat Bar 237.5/12", 35, 35, True),
        ("Flat Bar 237.5/20", 18, 18, True),
        ("Flat Bar 275/12", 70, 70, True),
        ("Flat Bar 275/20", 41, 41, True),
        ("Flat Bar 33.3/20", 116, 116, True),
        ("RD 12", 0, 175, False),
        ("RO 139.7x8.0 | EN 10210-2:2006", 12, 12, True),
        ("Rectangle 500/500", 47, 47, True),
    ]
    for row in data:
        writer.writerow(row)

print("CSV files created in:", output_dir)
print("  - member_summary.csv")
print("  - beams_breakdown.csv")
print("  - columns_breakdown.csv")
print("  - other_breakdown.csv")
print("  - profile_comparison.csv")