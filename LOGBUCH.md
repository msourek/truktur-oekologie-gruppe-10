# Logbuch

Pro Etappe ein Eintrag. Kurz reicht. Das Logbuch ist Teil der Abgabe und Grundlage eurer Demo.
One entry per stage. Short is fine. The log is part of the submission and the basis for your demo.

## Etappe 0

- **Was wir gemacht haben:**
- **Wichtigste Prompts** (wörtlich kopieren):
- **Was schiefging und woran wir es gemerkt haben:**
- **Was wir selbst geprüft haben** (von Hand, im Plan, im Modell):

---

# Sprint 1: Carbon-Inventur Pavillon Stockerau

## Etappe 1: Modell lesen

**Test:** Wie viele Stäbe hat der Pavillon? Prüft die Zahl am Modell nach.

**Ergebnis:** 736 eindeutige RFEM-BeamIds im Modellinventar: 561 Stäbe mit Brep und zugehöriger Achse sowie 175 axis-only Zugstäbe (RD 12). Automatische CSV-Prüfungen: alle bestanden; keine doppelten IDs.

**Learning oder Besonderheit:** Analytische Achsen und 3D-Körper dürfen nicht doppelt gezählt werden. Die 175 RD-12-Achsen haben keine zugeordneten Körper oder Materialangaben und müssen vor einer CO₂-Berechnung visuell bzw. im RFEM-Modell geprüft werden.


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
