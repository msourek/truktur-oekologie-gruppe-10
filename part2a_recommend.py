import pickle
import csv
import os
from collections import defaultdict

with open(r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\unique_members.pkl", "rb") as f:
    unique = pickle.load(f)

print("Loaded:", len(unique))

materials = {0: "B+G steel", 1: "B+G glass", 2: "B+G concrete light", 3: "B+G timber",
 4: "B+G concrete-02", 5: "B+G concrete-01", 6: "B+G concrete-00",
 7: "B+G steel-02", 8: "B+G steel-01", 9: "B+G steel-00",
 10: "B+G steel-03", 11: "B+G default", 12: "B+G timber-00",
 13: "B+G timber-01", 14: "B+G timber-02"}

def recommend(m):
    func = m["structural_function"]; profile = m["profile"]; dlubal = m["dlubal_material"]
    current_bg = m["current_bg_material"]
    
    if func == "Bracing Rod (Tension)":
        rec_idx, rec_name = 0, "B+G steel"
        reason = "Tension-only bracing rod (round bar 12mm) - requires high tensile strength steel"
    elif func == "Column":
        if "RO" in profile or "CHS" in profile or "Hollow" in profile:
            rec_idx, rec_name = 0, "B+G steel"
            reason = "Column with hollow circular section (" + profile + ") - steel CHS standard for compression"
        elif "Rectangle 500" in profile:
            rec_idx, rec_name = 4, "B+G concrete-02"
            reason = "Large rectangular section (500x500) - likely concrete core; Concrete C25/30 appropriate"
        else:
            rec_idx, rec_name = 0, "B+G steel"
            reason = "Column with flat bar section (" + profile + ") - steel"
    elif func == "Beam":
        rec_idx, rec_name = 0, "B+G steel"
        reason = "Beam with flat bar section (" + profile + ") - structural steel for bending resistance"
    elif func == "Diagonal/Bracing":
        rec_idx, rec_name = 0, "B+G steel"
        reason = "Diagonal bracing member (" + profile + ") - steel for tension/compression cycles"
    else:
        rec_idx, rec_name = 11, "B+G default"
        reason = "Unknown structural function"
    
    dlubal_appropriate = False
    if func in ["Column", "Beam", "Diagonal/Bracing"] and dlubal == "Steel S 355":
        dlubal_appropriate = True; dlubal_note = "Dlubal material 'Steel S 355' matches recommendation"
    elif func == "Column" and "Rectangle 500" in profile and dlubal == "Concrete C25/30":
        dlubal_appropriate = True; dlubal_note = "Dlubal material 'Concrete C25/30' matches recommendation for concrete core"
    elif func == "Bracing Rod (Tension)" and dlubal == "Steel S 355":
        dlubal_appropriate = True; dlubal_note = "Dlubal material 'Steel S 355' matches recommendation"
    elif dlubal == "":
        dlubal_appropriate = False; dlubal_note = "No Dlubal material assigned (empty)"
    else:
        dlubal_appropriate = False; dlubal_note = "Dlubal material '" + dlubal + "' may not be optimal for " + func
    
    current_assigned = current_bg != "None"
    change = (not current_assigned) or (not dlubal_appropriate)
    
    return {"rec_idx": rec_idx, "rec_name": rec_name, "reason": reason,
            "dlubal": dlubal if dlubal else "(empty)", "dlubal_appropriate": dlubal_appropriate,
            "dlubal_note": dlubal_note, "current_bg": current_bg, "change": change,
            "change_reason": "Current B+G: " + current_bg + ". Dlubal: " + (dlubal if dlubal else "(empty)") + ". " + dlubal_note + ". Rec: " + rec_name + " (" + reason + ")"}

print("Recommend function ready")