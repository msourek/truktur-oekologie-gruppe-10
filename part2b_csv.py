import pickle
import csv
import os
from collections import defaultdict

exec(open(r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\part2a_recommend.py").read())

output_dir = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\output"
os.makedirs(output_dir, exist_ok=True)

# Detailed CSV
detail_path = os.path.join(output_dir, "material_assignment_detailed.csv")
with open(detail_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["BeamId","Profile","Profile_End","Layer","RFEM_Type","Rotation",
        "Structural_Function","Dlubal_Material","Current_BG_Material",
        "Rec_BG_Idx","Rec_BG_Material","Dlubal_Appropriate","Dlubal_Note",
        "Change_Recommended","Change_Reason","Length_m","Volume_m3","CS_Area_mm2","Representation"])
    for bid in sorted(unique.keys()):
        m = unique[bid]; rec = recommend(m)
        w.writerow([m["beam_id"], m["profile"], m["profile_end"], m["layer_name"],
            m["rfem_type"], m["rotation"], m["structural_function"],
            m["dlubal_material"] if m["dlubal_material"] else "(empty)",
            m["current_bg_material"], rec["rec_idx"], rec["rec_name"],
            "Yes" if rec["dlubal_appropriate"] else "No", rec["dlubal_note"],
            "Yes" if rec["change"] else "No", rec["change_reason"],
            round(m["length_m"],3), round(m["volume_m3"],6),
            round(m["cs_area_mm2"],1), m["representation"]])

print("Created detailed CSV")

# Summary CSV
func_stats = defaultdict(lambda: {"count":0,"volume":0.0,"length":0.0,"dlubal_mats":set(),"rec_mat":set()})
for m in unique.values():
    rec = recommend(m); func = m["structural_function"]
    func_stats[func]["count"] += 1
    func_stats[func]["volume"] += m["volume_m3"]
    func_stats[func]["length"] += m["length_m"]
    func_stats[func]["dlubal_mats"].add(m["dlubal_material"] if m["dlubal_material"] else "(empty)")
    func_stats[func]["rec_mat"].add(rec["rec_name"])

summary_path = os.path.join(output_dir, "material_assignment_summary.csv")
with open(summary_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Structural_Function","Count","Recommended_Material",
        "Dlubal_Materials_Found","Total_Volume_m3","Total_Length_m"])
    for func in sorted(func_stats.keys()):
        s = func_stats[func]
        w.writerow([func, s["count"], "; ".join(sorted(s["rec_mat"])),
            "; ".join(sorted(s["dlubal_mats"])), round(s["volume"],4), round(s["length"],2)])

print("Created summary CSV")

# Console output
print("\n=== Summary ===")
for func in sorted(func_stats.keys()):
    s = func_stats[func]
    print(func + ": " + str(s["count"]) + " | Rec: " + ", ".join(sorted(s["rec_mat"])) + 
          " | Dlubal: " + ", ".join(sorted(s["dlubal_mats"])) +
          " | Vol: " + str(round(s["volume"],4)) + " m3")

print("\n=== Dlubal Material Evaluation ===")
for bid in sorted(unique.keys()):
    m = unique[bid]
    if m["dlubal_material"]:
        rec = recommend(m)
        status = "OK" if rec["dlubal_appropriate"] else "REVIEW"
        print("  BeamId " + str(bid).rjust(3) + " | " + m["profile"].ljust(30) + " | " + 
              m["structural_function"].ljust(20) + " | Dlubal: " + m["dlubal_material"].ljust(15) + " | " + status)