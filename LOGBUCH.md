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


## Etappe 2: Querschnitte verstehen

**Test:** Rechnet einen Stab, dessen Querschnitt sich über die Länge ändert, von Hand nach und vergleicht mit eurem Programm.


**Learning oder Besonderheit:**


## Etappe 3: Material zuordnen

**Test:** Sind die Materialangaben, die schon im Modell stehen, plausibel? Zeigt an einem Stab, wie ihr das geprüft habt.


**Learning oder Besonderheit:**


## Etappe 4: Embodied Carbon aus der ÖKOBAUDAT

**Test:** Rechnet einen Stab von seiner Länge bis zu kg CO₂e (A1–A3) von Hand nach.


**Learning oder Besonderheit:**


## Etappe 5: Web-App

**Test:** Schaltet beim Stahl auf die Alternative um. Was erwartet ihr vorher, was passiert, und warum?


**Learning oder Besonderheit:**


## Zum Schluss

Wie habt ihr mit dem Agenten gearbeitet, und was würdet ihr der nächsten Gruppe mitgeben?
