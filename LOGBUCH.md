# Logbook

One entry per stage. Keep it brief. The logbook is part of the submission and serves as the basis for your demo.

## Stage 0

- **What we did:**
It involved setting up the work environment in Visual Studio Code, as well as creating a shared space on GitHub for both group members to work on the project.

---

# Sprint 1: Carbon Inventory – Stockerau Pavilion

## Stage 1: Reading the Model

**Test:** How many members does the pavilion have? Verify the count using the model.

**Prompt:** Please analyze the Rhino file located in the 'data' folder and provide a file with the count of each type of member present in the rhino file. Examine both representations contained within the file, but take care not to double-count any member, as some elements appear in both representations.

**Result:** We obtain a total of 736 unique RFEM BeamIDs in the model inventory:
- 561 members with a B-Rep (boundary representation) consisting of 174 horizontal beams (Flat Bar 275/12 (35), 175/12 (35), 225/12 (35), 275/20 (23), 175/20 (23), 225/20 (23)), 12 columns (RO 139.7×8.0) and 375 diagonal/bracing rods (Flat Bar 33.3/20 (116), Rectangle 500/500 (47), and various other profiles).
- 175 RD 12 curves (only appears in MemberAxes representation).

**What we have checked ourselves:** We have confirmed that the result is correct by verifying it in Rhinoceros,specifically within the layer named "members" and also by including the members from the "MemberAxes" layer, which were not part of the "members" layer but nonetheless needed to be accounted for.

**Insight/Note:** We have learned that it is essential to keep Rhinoceros layers well-organized, clearly identified, and properly named, so that the AI ​​model can recognize them accurately and avoid errors. 
Furthermore, we have learned that it is important to provide the AI ​​with the right guidance to ensure it performs its task correctly, for example, by instructing it not to double-count elements that appear represented twice (in both 3D and 2D). This stage has been important to obtain information about the stuctural members that we have to consider to calculate the CO2 emisions.


## Stage 2: Understanding Cross-Sections

**Test:** Perform a manual calculation for a structural member whose cross-section varies along its length, and compare the result with your program’s output.

**Prompt 1:** I need you calculate the cross-sectional area and volume for each type of member you have obtained before. Put the results for each type of member  in a unique csv file in the "output" folder and also create a python file to create that csv file.

**What went wrong?:** After manually verifying the results using Rhinoceros, we realized that the volume calculation was incorrect, even though the cross-sectional area had been calculated correctly.

**Prompt 2:** the results are not correct, recalculate again the cross-sectional area and the volume of each member in cubic meters analyzing the rhino file to check the coherence of the results.

**Result:** This time, we have obtained the correct measurement results (cross-section and volume in m³) for each of the members. As an example, we provide the data obtained for one member: Flat Bar 237.5/12,  133 (Layer index),0.439942 (Lenght (m)),0.00101944 (Volume (m^3)),0.00231722 (Cross-Sectional Area (m^2)),2317.22 (Cross-Sectional Area (mm^2)),0.18454 (Surface Area (m^2)),True (Is Solid)

**What we have checked ourselves:** In Rhinoceros, we selected the member "Flat Bar 237.5/12", whose cross-section varies along its length, and using the "volume" command we verified that the results obtained were correct.

**Key Insight or Special Feature:** We have come to realize that AI sometimes makes mistakes, so we must verify the results rather than relying on them blindly. Furthermore, at this stage, we have determined the volume of each structural element, which will assist us in calculating CO2 emissions.


## Stage 3: Assigning Materials

**Test:** Are the material specifications already present in the model plausible? Demonstrate how you verified this, using one of the structural members as an example.

**Prompt:** Assign the best material for each member according to the rules that determine the material to choose depending on the structural function of the member and its dimmensions (cross section, length and volume), justifying it. There are members that already have a material assigned in the Rhinoceros file (you can find the data in the attribute user text of each member), evaluate them and tell if they are appropriate or you recommend to change them explaining the reasons.

**Result:** After reviewing the materials assigned to the differentmembers by the AI ​​model and those already assigned in Rhinoceros, the following decisions have been made: the columns will be made of S355 steel; the flat beams will be made of steel (even in cases where concrete had been assigned as material in rhinoceros); the Rectangle 500/500 members will be made of C25/30 concrete; and the bracing rods (tensors) will be made of steel.

**What we have checked ourselves:** We have decided to retain steel for the circular hollow sections, given their slender, hollow, and circular profile. Furthermore, although some of the flat beams were assigned concrete as a material in Rhinoceros, we have determined that steel is a better choice, since this way they can be securely tied to one another, a conclusion that aligns with the selection made by the AI ​​model. Regarding both the bracing rods and the Rectangle 500/500 members, we concur with the materials selected by the AI ​​model.

**Insight or Notable Detail:** The data obtained in this stage, together with the volumes calculated in previous stage, will allow us to provide data to the IA agent to estimate the CO2 emissions


## Etappe 4: Embodied Carbon aus der ÖKOBAUDAT

**Test:** Rechnet einen Stab von seiner Länge bis zu kg CO₂e (A1–A3) von Hand nach.


**Learning oder Besonderheit:**


## Etappe 5: Web-App

**Test:** Schaltet beim Stahl auf die Alternative um. Was erwartet ihr vorher, was passiert, und warum?


**Learning oder Besonderheit:**


## Zum Schluss

Wie habt ihr mit dem Agenten gearbeitet, und was würdet ihr der nächsten Gruppe mitgeben?
