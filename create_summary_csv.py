import csv
import os

output_dir = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\output"
os.makedirs(output_dir, exist_ok=True)

# Detailed summary: each individual member type/profile with its count
summary_path = os.path.join(output_dir, "member_summary_detailed.csv")
with open(summary_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Member Category", "Profile / Type", "Count", "Details"])
    
    # Beams
    writer.writerow(["Beam", "Flat Bar 275/12", 35, "Horizontal beam"])
    writer.writerow(["Beam", "Flat Bar 175/12", 35, "Horizontal beam"])
    writer.writerow(["Beam", "Flat Bar 225/12", 35, "Horizontal beam"])
    writer.writerow(["Beam", "Flat Bar 275/20", 23, "Horizontal beam"])
    writer.writerow(["Beam", "Flat Bar 175/20", 23, "Horizontal beam"])
    writer.writerow(["Beam", "Flat Bar 225/20", 23, "Horizontal beam"])
    writer.writerow(["Beam", "TOTAL", 174, "All horizontal beams"])
    
    # Columns
    writer.writerow(["Column", "RO 139.7x8.0 | EN 10210-2:2006", 12, "Vertical column"])
    writer.writerow(["Column", "TOTAL", 12, "All vertical columns"])
    
    # Other / diagonal / bracing
    writer.writerow(["Other / diagonal / bracing", "Flat Bar 33.3/20", 116, "Diagonal/bracing member"])
    writer.writerow(["Other / diagonal / bracing", "Rectangle 500/500", 47, "Diagonal/bracing member"])
    writer.writerow(["Other / diagonal / bracing", "Flat Bar 275/12", 35, "Diagonal/bracing member"])
    writer.writerow(["Other / diagonal / bracing", "Flat Bar 162.5/12", 35, "Diagonal/bracing member"])
    writer.writerow(["Other / diagonal / bracing", "Flat Bar 200/12", 35, "Diagonal/bracing member"])
    writer.writerow(["Other / diagonal / bracing", "Flat Bar 237.5/12", 35, "Diagonal/bracing member"])
    writer.writerow(["Other / diagonal / bracing", "Flat Bar 275/20", 18, "Diagonal/bracing member"])
    writer.writerow(["Other / diagonal / bracing", "Flat Bar 162.5/20", 18, "Diagonal/bracing member"])
    writer.writerow(["Other / diagonal / bracing", "Flat Bar 237.5/20", 18, "Diagonal/bracing member"])
    writer.writerow(["Other / diagonal / bracing", "Flat Bar 200/20", 18, "Diagonal/bracing member"])
    writer.writerow(["Other / diagonal / bracing", "TOTAL", 375, "All other/diagonal members"])
    
    # RD 12 (curve-only)
    writer.writerow(["Bracing rod (curve-only)", "RD 12", 175, "Centerline only, no solid Brep"])
    writer.writerow(["Bracing rod (curve-only)", "TOTAL", 175, "RD 12 curves only"])
    
    # Grand total
    writer.writerow(["GRAND TOTAL", "All unique members", 736, "561 Breps + 175 RD 12 curves"])

print(f"Created: {summary_path}")

# Also create the original aggregated summary for reference
agg_path = os.path.join(output_dir, "member_summary.csv")
with open(agg_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Member Type", "Count", "Notes"])
    writer.writerow(["Beams (horizontal)", 174, "Flat Bar profiles oriented horizontally"])
    writer.writerow(["Columns (vertical)", 12, "RO 139.7x8.0 | EN 10210-2:2006"])
    writer.writerow(["Other / diagonal / bracing", 375, "Various Flat Bar and Rectangle profiles"])
    writer.writerow(["RD 12 (curve-only, bracing rods)", 175, "Only in MemberAxes representation"])
    writer.writerow(["TOTAL unique members", 736, "561 Breps + 175 RD 12 curves"])

print(f"Created: {agg_path}")