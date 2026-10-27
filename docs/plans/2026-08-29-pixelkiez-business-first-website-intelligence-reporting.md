# Pixelkiez Business-First Website Intelligence & Reporting Implementation Plan

Plan path: `docs/plans/2026-08-29-pixelkiez-business-first-website-intelligence-reporting.md`
Status: **ready-for-execution**
Owner/Executor: coding agent + reviewer
Last updated: 2026-08-29

Goal: Pixelkiez Websiteanalyse als unternehmerisches Entscheidungssystem

Ziel. Den Skill `pixelkiez-website-diagnosis` so erweitern, dass jede Website evidenzbasiert und vollständig analysiert wird, während der Kunde eine hochwertige, einheitlich gebrandete und visuell verständliche Präsentation erhält. Die technische Analyse bleibt vollständig in JSON und Markdown erhalten; das Kunden-PDF zeigt ausschließlich unternehmerisch relevante Erkenntnisse: Wo verliert die Website Sichtbarkeit, Verständnis, Vertrauen oder Anfragenpotenzial, welche vier Hebel sind am wichtigsten und welche konkrete Maßnahme folgt daraus.

Scope. Beibehalten werden die bestehende Evidence-/Truth-Discipline, v1.3-Batch-/Voice-Kompatibilität und der vollständige technische Metric Layer. Ergänzt bzw. gehärtet werden vollständiger Analysebericht, Business-Interpretation, Visualisierungssystem, Benchmarking, Rankingdarstellung, Brand Rendering, PDF-Story, Chart Selection, Business-Lever Selection und finale semantische/visuelle Freigabe.

Bedingungen (hart).

- Technische Analyseinformationen und Kundenkommunikation bleiben getrennte Ebenen.
- Im Kunden-PDF erscheinen keine Begriffe oder Angaben über Tests, Testverfahren, Coverage/Messabdeckung, Evidence Grades, Measurement Classes, QA, Validatoren, interne IDs, Tools oder fehlgeschlagene Prüfungen.
- Jede kundenrelevante Aussage muss auf kanonischer Evidenz beruhen.
- Zahlen werden nach Möglichkeit als Zahl, Chart, Vergleich, Matrix oder Statusvisual dargestellt und nicht in Fließtext versteckt.
- Qualitative Website-Probleme werden in kurzer, natürlicher deutscher Sprache formuliert.
- Das Kunden-PDF konzentriert sich auf maximal vier priorisierte Business-Hebel.
- JSON und Markdown enthalten dagegen die vollständige Analyse aller bearbeiteten Metriken.
- Pixelkiez Brand Design, Typografie, Farben, Mindestschriftgrößen und Komponenten werden zentral definiert und fail-closed validiert.
- Wettbewerbs- oder Rankingvergleiche dürfen nur aus reproduzierbaren aktuellen Daten entstehen; fehlende Benchmarks werden nicht erfunden.

Akzeptanzkriterien.

- Eine vollständige Analyse erzeugt mindestens `analysis_report.json`, `analysis_report.md` und `pixelkiez-website-analysis.pdf`.
- JSON und Markdown enthalten jede im Lauf bearbeitete Metrik mit Ergebnis, Evidenz, Interpretation und gegebenenfalls Maßnahme.
- Das Kunden-PDF enthält keine interne Test-/Coverage-/Methodensprache.
- Das Kunden-PDF zeigt exakt die höchstens vier wichtigsten Business-Hebel.
- Jede numerisch geeignete Kernaussage nutzt eine definierte Visualform statt unnötigen Fließtexts.
- Brand Font bzw. freigegebene Fallback-Font, Größen, Farben und Layouttokens entsprechen dem kanonischen Pixelkiez Design Contract.
- Kein kundenrelevanter Text wird durch kleinere Schrift passend gemacht.
- Ranking-/Benchmarkaussagen sind query-, markt- und zeitgebunden und niemals als allgemeine Marktposition formuliert.
- Semantic Customer QA und Visual Brand QA müssen auf dem final gerenderten PDF PASS sein.
- Bestehende Truth-, v1.3-, Batch- und Voice-Handoff-Gates bleiben grün.

Explizit out-of-scope.

- Garantierte Umsatz-, Lead-, Ranking- oder Conversionprognosen ohne reale Unternehmensdaten.
- Erfundene Branchenbenchmarks oder Wettbewerbswerte.
- Penetration Testing, Rechtsberatung oder vollständige WCAG-Zertifizierung.
- Änderung des bestehenden 96-Feld-v1.3-Voice-Contracts.
- Austausch der Websiteanalyse durch eine reine Designbewertung.

Done-Definition. Der installierte Skill erzeugt aus einer Website einen vollständigen evidenzgebundenen internen Analysebestand und daraus deterministisch eine Pixelkiez-gebrandete, unternehmerisch verständliche, datenvisualisierte Kundenpräsentation. Vollständigkeits-, Business-Semantik-, Brand-, Chart-, Truth-, Cross-Skill-, Release- und Provenienz-Gates sind auf demselben finalen Snapshot grün.

Reference-Doc: `docs/plans/2026-08-29-pixelkiez-business-first-website-intelligence-reporting.md`

# 1. Evidence and source boundary

## Provided / established requirements

Der Zielzustand besteht aus zwei bewusst unterschiedlichen Informationsebenen:

### Interne Wahrheitsebene

Vollständige Analyse mit:

- allen bearbeiteten Metriken;
- gemessenen oder beobachteten Werten;
- Evidenz;
- technischen Details;
- Unsicherheiten;
- Findings;
- Prioritäten;
- Business-Interpretation;
- Maßnahmen.

Diese Ebene darf technisch sein.

### Kundenebene

Ausschließlich:

- Geschäftsbedeutung;
- relevante Zahlen;
- verständliche Vergleiche;
- vier Haupthebel;
- Handlungsempfehlungen;
- Priorität;
- erwartbare qualitative Wirkung.

Nicht sichtbar:

- Coverage;
- Testumfang;
- Testverfahren;
- Validatoren;
- Evidence Grades;
- Measurement Classes;
- interne Metric IDs;
- Toolnamen;
- QA-Begriffe;
- `SOURCE_NEEDED`;
- `not_assessed`;
- technische Pipelineinformationen.

## Existing architecture to preserve

Die bestehende Architektur besitzt bereits:

- kanonische Website-Metriken;
- Evidence-/Truth-Discipline;
- Client Story Layer;
- Chart-System;
- PDF Renderer;
- Visual QA;
- Semantic Customer QA;
- v1.3 ElevenLabs Contract;
- provider-neutralen Audit-Handoff.

Diese Bestandteile werden erweitert, nicht durch ein zweites paralleles Audit-System ersetzt.

---

# 2. Assumptions, missing information and boundaries

## ASSUMPTION

- Der bestehende Pixelkiez Brand-/PDF-Assetbestand enthält die aktuell beabsichtigte visuelle Richtung.
- `diagnosis-report.json` bleibt zunächst die kanonische technische Wahrheit, um bestehende v1.3- und Voice-Abhängigkeiten nicht unnötig zu brechen.
- `analysis_report.json` wird daraus als vollständiges Distributionsartefakt erzeugt und muss semantisch/digest-seitig mit der kanonischen Analyse übereinstimmen.
- `analysis_report.md` wird ausschließlich aus dem kanonischen JSON erzeugt und nie unabhängig davon gepflegt.

## MISSING

- Exakte kanonische Pixelkiez-Schriftfamilie und Lizenz-/Embedding-Regel müssen bei Implementierungsbeginn aus den vorhandenen Brand Assets bzw. Designvorgaben verifiziert werden.
- Ein verbindlicher aktueller Datenprovider für Google-/Suchranking und Branchenbenchmarks ist nicht Bestandteil dieses Plans als bereits verifizierte Capability.

## SOURCE\_NEEDED

Für echte Wettbewerbsbenchmarks muss später für jede Datenklasse eine belastbare Quelle vorhanden sein. Insbesondere:

- Suchposition pro Query;
- Suchsichtbarkeit;
- Wettbewerbervergleich;
- Branchenmedian;
- Performancevergleich mit Branchenwebsites.

Ohne eine solche Quelle darf der Skill nur die eigene Website bzw. direkt beobachtete Vergleichsseiten darstellen.

## BLOCKER

Kein Blocker für die Architektur- und Kernimplementierung.

**Release-Blocker Brand:** Wenn die kanonische Pixelkiez-Schrift nicht bestimmt oder rechtmäßig im Renderer nutzbar ist, darf keine vollständige Brand-Konformität behauptet werden.

---

# 3. Requirements

| IDTypRequirementQuelleVerifikation |                |                                                                                                   |                       |                                   |
| ---------------------------------- | -------------- | ------------------------------------------------------------------------------------------------- | --------------------- | --------------------------------- |
| REQ-F-001                          | Functional     | Jede relevante Website-Metrik wird analysiert und im vollständigen internen Bericht dokumentiert. | User                  | Metric parity JSON/MD             |
| REQ-F-002                          | Functional     | Jede relevante Erkenntnis erhält eine unternehmerische Interpretation.                            | User                  | Business interpretation validator |
| REQ-F-003                          | Functional     | Maximal vier Business-Hebel werden für die Kundenpräsentation priorisiert.                        | User                  | Client model validator            |
| REQ-F-004                          | Functional     | Numerisch geeignete Erkenntnisse werden bevorzugt visualisiert.                                   | User                  | Visualization eligibility evals   |
| REQ-F-005                          | Functional     | Qualitative Probleme werden kurz und natürlich formuliert.                                        | User                  | Semantic authoring evals          |
| REQ-F-006                          | Functional     | Ranking wird query-spezifisch statt pauschal dargestellt.                                         | User                  | Ranking contract                  |
| REQ-F-007                          | Functional     | Vergleichsdaten werden nur bei belegbarer Vergleichbarkeit dargestellt.                           | Evidence policy       | Benchmark validator               |
| REQ-D-001                          | Data           | `analysis_report.json` enthält den vollständigen Analysebestand.                                  | User                  | Schema + parity                   |
| REQ-D-002                          | Data           | `analysis_report.md` enthält jede relevante Metrik und Empfehlung.                                | User                  | MD completeness validator         |
| REQ-D-003                          | Data           | PDF, MD und JSON referenzieren denselben Audit-/Report-Digest.                                    | Architecture          | Digest validation                 |
| REQ-A-001                          | Architecture   | Technische Analyse und Kundenprojektion bleiben getrennte Layer.                                  | User                  | architecture checks               |
| REQ-A-002                          | Architecture   | Kein zweiter konkurrierender Metric Store wird eingeführt.                                        | Craftsmanship         | source-of-truth validator         |
| REQ-A-003                          | Architecture   | Visualisierung wird aus strukturierten Daten geplant, nicht aus freiem PDF-Text.                  | User                  | render-model validation           |
| REQ-NF-001                         | Non-functional | Kundentexte dürfen nicht durch Font-Shrinking passend gemacht werden.                             | User                  | PDF typography validator          |
| REQ-NF-002                         | Non-functional | PDF verwendet ein konsistentes Pixelkiez Designsystem.                                            | User                  | Brand QA                          |
| REQ-NF-003                         | Non-functional | Jede zentrale Kundenfolie ist in wenigen Sekunden erfassbar.                                      | User                  | rendered semantic review          |
| REQ-S-001                          | Safety         | Keine unbelegten Geschäftswirkungen oder Benchmarks.                                              | Existing truth policy | countertests                      |
| REQ-O-001                          | Operations     | Release-Evidenz ist an exakt gerenderte Artefakte und finalen Skill-Digest gebunden.              | Existing provenance   | pipeline ledger                   |

---

# 4. Unternehmerisches Informationsmodell

Die interne technische Taxonomie darf erhalten bleiben. Die Kundenpräsentation bekommt jedoch ein eigenes Business-Vokabular.

## Unternehmerische Kernfragen

Jede Analyse soll am Ende beantworten:

### 1. Werden potenzielle Kunden auf das Unternehmen aufmerksam?

Beispiele:

- Suchauffindbarkeit;
- Suchpositionen;
- wichtige Leistungsseiten;
- lokale Auffindbarkeit;
- maschinelle Auffindbarkeit.

### 2. Versteht ein Besucher sofort, was angeboten wird?

Beispiele:

- Leistungsversprechen;
- Zielgruppe;
- Leistungsstruktur;
- Preis-/Prozessklarheit;
- Informationsarchitektur.

### 3. Wird aus Interesse einfach eine Anfrage?

Beispiele:

- CTA;
- Kontaktwege;
- Formulare;
- Navigation;
- mobile Bedienung;
- Reibung.

### 4. Erzeugt die Website Vertrauen?

Beispiele:

- Referenzen;
- reale Unternehmensdaten;
- Konsistenz;
- Aktualität;
- Ansprechpartner;
- Transparenz.

### 5. Funktioniert die Website technisch ohne unnötige Reibung?

Beispiele:

- Ladegeschwindigkeit;
- mobile Darstellung;
- technische Fehler;
- Zugänglichkeit.

### 6. Können KI-Systeme das Unternehmen eindeutig verstehen?

Beispiele:

- Entity Clarity;
- Antwortbarkeit;
- strukturierte Informationen;
- eindeutige Leistungen;
- konsistente Unternehmensfakten.

Die Kundenebene soll diese Geschäftsdimensionen verwenden statt interner Metric-Namen.

---

# 5. Business-Value Layer

## Neues Modul

Create:

`scripts/business_value.py`

Aufgabe:

Technische Findings deterministisch in Business-Bedeutung überführen.

Struktur pro Finding:

```text
business_question
business_effect_channel
business_priority
business_explanation
recommended_action
action_type
effort_class
evidence_refs

```

## Zulässige Effect Channels

- `FINDABILITY`
- `UNDERSTANDING`
- `TRUST`
- `CONTACT_FRICTION`
- `TECHNICAL_FRICTION`
- `AI_DISCOVERABILITY`
- `RISK_REDUCTION`

Keine direkte Kategorie:

- `REVENUE_GAIN`
- `CONVERSION_UPLIFT`
- `LEAD_INCREASE`

ohne entsprechende Unternehmensdaten.

### Formulierungsprinzip

Nicht:

> „Die Non-Brand-Coverage ist unzureichend.“

Sondern:

> „Bei wichtigen Suchanfragen ohne Firmennamen ist das Unternehmen kaum sichtbar.“

Nicht:

> „Die H1-/Title-Konsistenz ist schwach.“

Sondern:

> „Mehrere Seiten sagen Suchmaschinen und Besuchern nicht eindeutig, welche Leistung dort angeboten wird.“

Nicht:

> „LCP liegt bei 4,1 Sekunden.“

Nur als Satz wäre ebenfalls schwach.

Besser:

**4,1 s**

> „Die wichtigste Seitenansicht erscheint deutlich später als empfohlen.“

Zahl und Aussage werden getrennt dargestellt.

---

# 6. Output Architecture

Jeder vollständige Run erzeugt verpflichtend:

## A. `analysis_report.json`

Zweck: vollständige maschinenlesbare Wahrheit.

Enthält mindestens:

```text
meta
business_profile
score_summary
categories
metrics[]
findings[]
business_implications[]
recommendations[]
benchmarks[]
ranking_observations[]
visual_candidates[]
roadmap
sources
limitations
missing
source_needed

```

Jeder Metric Record enthält mindestens:

```text
metric_id
category
value
unit
status
evidence
technical_interpretation
business_interpretation
recommendation
priority

```

## B. `analysis_report.md`

Zweck: vollständige interne Beratungsunterlage.

Struktur:

1. Unternehmen und Website
2. Executive Internal Summary
3. Gesamtbild
4. alle Kategorien
5. vollständige Metrikliste
6. wesentliche Findings
7. Business-Bedeutung
8. Handlungsempfehlungen
9. Priorisierte Roadmap
10. Such-/Rankingdaten
11. Wettbewerbsvergleich, wenn valide
12. Evidenz und Quellen
13. Grenzen / offene Daten

Kein Metric Record darf im JSON existieren und im Markdown still verschwinden.

## C. `pixelkiez-website-analysis.pdf`

Zweck: Kundenentscheidung.

Nicht vollständige Analyse.

Enthält ausschließlich:

- unternehmerisches Gesamtbild;
- relevante Scores/Zahlen;
- vier Haupthebel;
- Visualisierungen;
- konkrete Maßnahmen;
- Priorisierung;
- nächster sinnvoller Schritt.

---

# 7. Harte Customer-PDF-Semantik

## Verbotene Informationsebene

Folgende Inhalte sind im Kunden-PDF verboten:

- Coverage / Messabdeckung
- Test / getestet / Testumfang
- Prüfverfahren
- Toolnamen
- Evidence Grade
- Measurement Class
- Confidence
- `not_assessed`
- `SOURCE_NEEDED`
- interne Metric IDs
- Audit-Pipeline
- Validatorstatus
- QA-Status
- Fixture-/Simulation-Sprache
- technische Provenienz
- interne Contract-Versionen

### Ausnahme

Ein technischer Begriff darf erscheinen, wenn er selbst für die unternehmerische Entscheidung wichtig und allgemein verständlich ist, z. B.:

- Ladezeit
- Google-Position
- Barrierefreiheit

---

# 8. Presentation Story Architecture

Standardaufbau:

## Seite 1 — Cover

- Unternehmen
- URL
- Pixelkiez
- Gesamtwert, sofern fachlich zulässig
- ein kurzer Gesamtbefund

Keine Methodik.

## Seite 2 — Unternehmerisches Gesamtbild

Visual:

**horizontale Balken für die Business-Dimensionen**

Beispiel:

```text
Auffindbarkeit          42 / 100
Angebotsklarheit        78 / 100
Anfrageweg              61 / 100
Vertrauen               73 / 100
Technische Qualität     55 / 100
KI-Verständlichkeit     39 / 100

```

Keine Coverage-Zahlen.

## Seiten 3–6 — Vier wichtigste Business-Hebel

Jede Seite:

1. kurze Headline;
2. wichtigste Zahl oder Visual;
3. maximal 1–2 kurze Problemsätze;
4. „Warum das geschäftlich relevant ist“;
5. konkrete Maßnahme.

## Seite 7 — Potenzialbild / Vergleich

Nur wenn valide Vergleichsdaten verfügbar sind.

## Seite 8 — Priorisierte Maßnahmen

Visual:

Impact/Effort oder gestufte Roadmap.

## Seite 9 — Nächster sinnvoller Schritt

Keine technische Schlussseite.

---

# 9. Visualisierungssystem

Neue Reference:

`references/business-visualization-system.md`

Neue/erweiterte Logik:

`scripts/visual_story_planner.py`

## Grundregel

> Wenn Information sinnvoll quantitativ dargestellt werden kann, darf sie nicht ausschließlich als Fließtext erscheinen.

## Visual Eligibility

### `BIG_NUMBER`

Für einen einzelnen wichtigen Wert.

Beispiele:

- `4,1 s`
- `Position 18`
- `2 von 5`
- `63 / 100`

### `BULLET_BAR`

Für Wert gegen legitime Zielmarke.

Beispiele:

- Performance;
- Kategorie-/Business-Score.

### `HORIZONTAL_BAR`

Für mehrere vergleichbare Werte.

Beispiele:

- Business-Dimensionen;
- Kategorien;
- Wettbewerber.

### `RANKING_VISUAL`

Für Suchpositionen.

Beispiel:

```text
„Baumpflege Potsdam“        Position 18
„Baumfällung Potsdam“       Position 31
„Baumpflege Berlin“         nicht in Top 50

```

### `BENCHMARK_BAR`

Nur wenn echte Vergleichsdaten vorliegen.

```text
Unternehmen                 42
Wettbewerber A              61
Wettbewerber B              74
Wettbewerber C              57

```

### `STATUS_MATRIX`

Für binäre oder kategoriale Fakten.

Beispiele:

- Referenzen vorhanden;
- Ansprechpartner sichtbar;
- Leistungen eindeutig;
- strukturierte Firmendaten konsistent.

### `EVIDENCE_COMPARE`

Für widersprüchliche Angaben oder konkrete Seitenunterschiede.

### `PRIORITY_MATRIX`

Für Maßnahmen nach Business-Wirkung × Aufwand.

---

# 10. Kategoriebezogene Default-Visuals

| Business-BereichDefaultAlternative |                        |                  |
| ---------------------------------- | ---------------------- | ---------------- |
| Gesamtbild                         | horizontale Score Bars | Bullet Bars      |
| Auffindbarkeit                     | Ranking Visual         | Benchmark Bars   |
| Angebotsklarheit                   | Status Matrix          | Evidence Compare |
| Anfrageweg                         | Status/Friction Matrix | Journey Diagram  |
| Vertrauen                          | Status Matrix          | Evidence Compare |
| Performance                        | Bullet Bars            | Big Numbers      |
| Barrierefreiheit                   | Severity/Status Bars   | Status Matrix    |
| KI-Verständlichkeit                | Subscore Bars          | Status Matrix    |
| Top 4 Hebel                        | Hero Number + Chart    | Evidence Visual  |
| Roadmap                            | Impact/Effort Matrix   | Prioritätsstufen |

Der Agent darf einen anderen Visual-Typ wählen, wenn der Default für die konkreten Daten ungeeignet ist, muss dies aber im internen Render Model begründen.

---

# 11. Search Ranking Architecture

Neue strukturierte Records:

```text
query
market
location
observed_position
landing_page
observed_at
source
confidence_internal

```

## Kundenprojektion

Nur:

```text
Suchanfrage
Position
gefundene Zielseite
Business-Bedeutung

```

Keine technische SERP-Methodik.

## Regel

Nicht:

> „Google Ranking: schlecht“

Sondern:

> `„Baumpflege Potsdam“ – Position 18`

und kurze Interpretation:

> „Für diese wichtige Leistung erscheinen Wettbewerber deutlich früher.“

---

# 12. Competitor Benchmark Architecture

Benchmark nur bei vergleichbarer Datenbasis.

Ein Record benötigt:

```text
benchmark_dimension
subject
comparison_entities[]
values[]
market
observation_date
source_refs[]

```

## Hard Gate

Kein Benchmark Chart bei:

- unterschiedlichen Messmethoden;
- fehlender Vergleichsgruppe;
- unbekanntem Markt;
- vermuteten Wettbewerbern;
- nicht vergleichbaren Werten.

## Kundenform

> „Im Vergleich mit vier regionalen Anbietern liegt die Website bei der Auffindbarkeit zurück.“

Nicht:

> „Unser Benchmark-Test zeigt bei 67 % Coverage …“

---

# 13. Pixelkiez Brand Rendering Contract

Neue Reference:

`references/pixelkiez-brand-rendering-contract.md`

Canonical Tokens:

```text
font_family_primary
font_family_fallback
font_weights
font_size_cover
font_size_h1
font_size_h2
font_size_body
font_size_chart_label
font_size_caption
line_height
brand_colors
background_colors
chart_palette
spacing_scale
corner_radius
stroke_width
logo_rules

```

## Harte Regeln

- keine Fontgröße unter definiertem Minimum;
- kein automatisches Font Shrinking;
- keine lokale abweichende Font Definition im Renderer;
- Charts verwenden dieselbe Typografie;
- ausschließlich Brand Palette;
- konsistente Achsen, Labels, Karten und Abstände;
- ausreichender Kontrast;
- keine überladenen Legenden.

### Font Gate

Die konkrete Pixelkiez-Schrift wird aus dem bestehenden Brand-Asset/Template übernommen.

Wenn keine lizenzierte bzw. verfügbare Brand Font festgestellt werden kann:

`MISSING_BRAND_FONT`

und kein behaupteter Brand-PASS.

---

# 14. Neue zentrale Renderer-Architektur

```text
Canonical Analysis
        │
        ├── analysis_report.json
        │
        ├── analysis_report.md
        │
        ▼
Business Interpretation Layer
        │
        ▼
Business Lever Selector
        │
        ▼
Visualization Eligibility
        │
        ▼
Visual Story Planner
        │
        ▼
Pixelkiez Brand Render Model
        │
        ▼
PDF Renderer
        │
        ▼
Rendered PDF QA

```

Der Renderer darf keine fachlichen Entscheidungen treffen.

Er rendert ausschließlich ein bereits semantisch freigegebenes Model.

---

# 15. Implementation phases

## Phase 0 — Baseline und Brand Discovery

- installierten Skill snapshotten;
- bestehende Brand Assets inventarisieren;
- Fonts, Farben, Logo und Layouttokens bestimmen;
- bestehende PDF-Regression rendern;
- aktuelle Schriftgrößen und Visual-Dichte dokumentieren.

Exit:

Brand Source Map vorhanden.

---

## Phase 1 — Full Analysis Output Contract

Implementieren:

- `analysis_report.json`;
- `analysis_report.md`;
- Vollständigkeitsvalidator;
- Digest-Bindung zur kanonischen Analyse.

Exit:

jede Metrik erscheint in JSON und Markdown.

---

## Phase 2 — Business Interpretation Layer

Implementieren:

`scripts/business_value.py`

Tests:

- technische Aussage → Business-Aussage;
- keine Umsatzversprechen;
- keine generischen Agenturtexte;
- keine interne Terminologie.

Exit:

alle kundenfähigen Findings besitzen eine Business-Interpretation.

---

## Phase 3 — Customer Language Firewall

Implementieren:

`scripts/validate_customer_business_language.py`

Negativfälle:

- `Coverage`
- `Messabdeckung`
- `Testumfang`
- `E5`
- `not_assessed`
- `SOURCE_NEEDED`
- Metric IDs
- Toolnamen
- Validator
- QA

müssen Kundenmodell/PDF blockieren.

---

## Phase 4 — Visual Intelligence Layer

Implementieren:

- Visual Eligibility;
- Chart Routing;
- Ranking Visual;
- Benchmark Visual;
- Status Matrix;
- Priority Matrix;
- Big Number Cards.

Exit:

jede relevante Zahl besitzt einen expliziten Darstellungsentscheid.

---

## Phase 5 — Brand Rendering System

Zentrale Brand Tokens implementieren.

Alle bestehenden PDF-Komponenten auf dieselben Tokens migrieren.

Kein Styling mehr direkt in einzelnen Komponenten.

Exit:

Brand-Validator PASS.

---

## Phase 6 — PDF Story neu strukturieren

Implementieren:

- Gesamtbild;
- vier Hebel;
- Ranking/Benchmark bei belastbaren Daten;
- Roadmap;
- Next Step.

Technische Boundary-Seiten aus Kunden-PDF entfernen.

Exit:

keine interne Analysesprache sichtbar.

---

## Phase 7 — Internal Advisor Report

Markdown Renderer implementieren.

Für jede Metrik:

```text
Was wurde festgestellt?
Wert
Einordnung
Business-Bedeutung
Empfohlene Maßnahme
Priorität
Evidenz

```

Interner Bericht bleibt technisch detailliert.

---

## Phase 8 — Search & Benchmark Support

Ranking-Datenmodell implementieren.

Externe Capability erst nach Source-/Capability-Gate anbinden.

Ohne valide externe Quelle:

- keine erfundenen Rankings;
- keine erfundenen Branchenbenchmarks.

---

## Phase 9 — Rendered PDF Business QA

Semantic Review prüft:

1. Ist das eine konkrete Aussage über dieses Unternehmen?
2. Versteht ein Geschäftsführer sie ohne Fachwissen?
3. Ist klar, warum sie geschäftlich relevant ist?
4. Wird eine vorhandene Zahl sichtbar dargestellt?
5. Ist die Maßnahme konkret?
6. Ist die Visualisierung die beste Form?
7. Ist die Seite scanbar?
8. Gibt es unnötige Fachsprache?
9. Ist das Design Pixelkiez-konsistent?
10. Würde die Seite ohne Kundenname immer noch eindeutig zu diesem Kunden passen?

FAIL → neue Story erzeugen, nicht QA einfach freigeben.

---

# 16. Tasks

## TASK-001 — Brand Canon bestimmen

Objective: eine einzige Designquelle schaffen.

Create:

- `references/pixelkiez-brand-rendering-contract.md`

Modify:

- PDF renderer
- chart renderer

Test first:
Brand Regression mit falscher Font/Farbe/Fontgröße.

Acceptance:

Falsches Branding → FAIL.

---

## TASK-002 — Vollständiges Analyse-JSON stabilisieren

Objective: jede Metrik dauerhaft verfügbar machen.

Create/Modify:

- Analysis schema
- analysis exporter

Acceptance:

`metrics_in_canonical == metrics_in_analysis_report`.

---

## TASK-003 — Markdown-Bericht erzeugen

Create:

`scripts/render_analysis_markdown.py`

Test:

bewusst eine Metric entfernen → FAIL.

Acceptance:

JSON und MD vollständig.

---

## TASK-004 — Business Value Mapper bauen

Create:

`scripts/business_value.py`

Countertests:

- technische Fachsprache;
- unbelegte Umsatzwirkung;
- generische Aussagen.

Acceptance:

nur evidence-bound Business-Aussagen.

---

## TASK-005 — Customer Language Firewall bauen

Create:

`scripts/validate_customer_business_language.py`

Acceptance:

interne Audit-Sprache kann Customer Model nicht passieren.

---

## TASK-006 — Visual Eligibility Engine bauen

Create:

`scripts/visual_eligibility.py`

Für jede kundenrelevante Information:

```text
BIG_NUMBER
BULLET_BAR
HORIZONTAL_BAR
RANKING
BENCHMARK
STATUS_MATRIX
EVIDENCE_COMPARE
PRIORITY_MATRIX
SHORT_TEXT

```

Acceptance:

kein numerischer Hauptbefund bleibt ohne Visual Decision.

---

## TASK-007 — Chart Library vereinheitlichen

Create/extend:

- Brand chart primitives
- axes
- labels
- cards
- legends
- number tiles

Acceptance:

keine individuellen Farben/Fonts außerhalb Brand Tokens.

---

## TASK-008 — Business-Lever Selector härten

Maximal vier Hebel.

Ranking:

1. Business-Relevanz;
2. Evidenzstärke;
3. Handlungsfähigkeit;
4. Dringlichkeit;
5. unterschiedliche Business-Dimensionen.

Acceptance:

keine vier rein technischen Minor Findings verdrängen einen geschäftlich relevanten Befund.

---

## TASK-009 — Kunden-PDF neu rendern

Acceptance:

- vier Hebel;
- mehrere relevante Visuals;
- kein technischer Appendix;
- keine Test-/Coverage-Sprache;
- Pixelkiez Brand;
- Mindestschriftgröße erfüllt.

---

## TASK-010 — Ranking Contract implementieren

Create:

Ranking record/schema + renderer.

Acceptance:

jede Aussage enthält konkrete Query + beobachtete Position.

---

## TASK-011 — Benchmark Contract implementieren

Create:

Benchmark schema + comparability gate.

Acceptance:

inkompatible Vergleichswerte → kein Chart.

---

## TASK-012 — Full Report Completeness Gate

Create:

`scripts/validate_analysis_report_completeness.py`

Checks:

- JSON vorhanden;
- MD vorhanden;
- Metric parity;
- Finding parity;
- Recommendation parity;
- Digest parity.

---

## TASK-013 — Brand QA

Create:

`scripts/validate_pdf_brand.py`

Checks:

- Font Family;
- Mindestgrößen;
- Brand Palette;
- Chart Typography;
- Seitenkonsistenz.

---

## TASK-014 — Business Semantic QA

Extend:

Rendered-PDF Semantic QA.

Acceptance:

jede Lever-Seite beantwortet:

```text
Was ist los?
Was bedeutet das fürs Geschäft?
Welche Zahl/Beleg zeigt es?
Was sollte ich tun?

```

---

## TASK-015 — Realistische Branchenregression

Mindestens unterschiedliche Website-Typen verwenden:

- lokaler Dienstleister;
- B2B-Beratung;
- Gastronomie oder lokales Geschäft.

Ziel:

kein Template-Overfitting.

---

## TASK-016 — Existing Architecture Regression

Erneut validieren:

- Truth Discipline;
- v1.3;
- Batch CSV;
- provider-neutraler Packet;
- Voice Consumer;
- PDF;
- Full Report;
- Release Gate.

---

## TASK-017 — Final Freeze und Packaging

Erst nach Abschluss aller Non-Report-Dateien:

- finaler Tree Digest;
- Release Hook;
- Enterprise Evaluator;
- Validation;
- Pipeline Ledger;
- `PACKAGE_AUTHORIZED`;
- `skill.zip`.

---

# 17. Validation strategy

## Layer A — Evidence

Keine Business-Aussage ohne kanonischen Befund.

## Layer B — Completeness

Alle Metriken in JSON + Markdown.

## Layer C — Business Semantics

Keine interne Audit-/Testsprache in Customer Output.

## Layer D — Visual Intelligence

Zahlendaten werden sinnvoll visualisiert.

## Layer E — Brand

Font, Größen, Farben und Komponenten konsistent.

## Layer F — Rendered Customer Review

Jede finale Seite visuell und semantisch geprüft.

## Layer G — Existing Pipeline

Truth/v1.3/Voice unverändert grün.

## Layer H — Provenance

Alle Release-Artefakte auf demselben Snapshot.

---

# 18. Zentrale Negativtests

Der Release muss scheitern bei:

- PDF ohne ausreichende Visualisierung numerischer Hauptbefunde;
- Font unter Mindestgröße;
- falscher Brand Font;
- unzulässiger Farbe;
- `Coverage` im Kunden-PDF;
- `Testumfang` im Kunden-PDF;
- `E6` im Kunden-PDF;
- technischer Metric ID im Kunden-PDF;
- fehlendem `analysis_report.md`;
- fehlendem `analysis_report.json`;
- Metric nur im JSON, aber nicht im Markdown;
- unbelegtem Ranking;
- erfundenem Branchenbenchmark;
- generischem Business-Hebel;
- unbelegter Umsatz-/Conversionwirkung;
- mehr als vier Haupthebeln;
- Chart ohne Datenbasis;
- Textverkleinerung zum Verhindern eines Overflows.

---

# 19. Positive Release Scenarios

## Szenario A — Zahlenreiche Website

Erwartung:

- viele Charts;
- Big Numbers;
- Performance-/Ranking-/Score-Visuals;
- sehr wenig Fließtext.

## Szenario B — qualitative Website

Erwartung:

- Statusmatrizen;
- Evidence Comparisons;
- kurze Problemformulierungen;
- keine erfundenen Zahlen.

## Szenario C — Benchmark verfügbar

Erwartung:

- Wettbewerbsvergleich;
- klare Position des Unternehmens;
- intern dokumentierte Vergleichsgrundlage;
- außen ausschließlich unternehmerischer Vergleich.

## Szenario D — Benchmark nicht verfügbar

Erwartung:

- kein Fake-Benchmark;
- Kunden-PDF bleibt trotzdem vollständig;
- interner Bericht markiert die fehlende Datengrundlage.

---

# 20. Rollback and safety

- bestehende v1.3-Contracts nicht verändern;
- alte technische Analyse nicht zugunsten schönerer Präsentation entfernen;
- `analysis_report.md` nie als zweite manuelle Wahrheit führen;
- Charts niemals mit synthetischen Vergleichswerten füllen;
- Brand-Assets nicht ersetzen, bevor ihre Rolle geklärt ist;
- keine Zahlen aus Layout-/Darstellungsgründen runden oder verändern, außer eine dokumentierte Display-Rundung existiert;
- technische Details aus dem Kunden-PDF entfernen, aber nicht aus dem internen Report löschen.

Rollback:

Presentation-/Business-Layer kann auf vorherigen Renderer zurückgestellt werden, während Canonical Analysis und v1.3 unverändert bleiben.

---

# 21. Execution handoff

## Start with

`TASK-001 Brand Canon` und parallel nur Discovery für `TASK-002`.

Danach WIP = 1 Architekturphase:

```text
Canonical Analysis
→ Full Reports
→ Business Interpretation
→ Visual Intelligence
→ Brand Rendering
→ PDF Story
→ QA
→ Freeze

```

## Stop and investigate if

- Brand Font nicht eindeutig bestimmbar ist;
- eine bestehende Metric beim Full-Report-Export verloren geht;
- ein Chart Daten benötigt, die nicht gemessen wurden;
- Ranking ohne konkrete Query entstehen würde;
- eine Business-Aussage nur mit unbelegter Wirkung begründet werden kann;
- das Customer-PDF technische Audit-Sprache benötigt, um verständlich zu sein;
- nach `DRAFT_FROZEN` eine Non-Report-Datei geändert wird.

## Expected final artifacts

```text
analysis_report.json
analysis_report.md
client-report-model.json
pixelkiez-website-analysis.pdf
pixelkiez_elevenlabs_batch.csv
website-audit-packet.json

brand-validation.json
business-semantic-qa.json
visual-qa.json
analysis-completeness-report.json
release-gate-report.json
enterprise-skill-evaluation.xml
build-events.jsonl
skill.zip

```

---

# 22. Options considered

## Option A — Alles in ein einziges Kunden-PDF

Abgelehnt.

Grund: Vollständige technische Analyse und Managementkommunikation verfolgen gegensätzliche Informationsziele.

## Option B — PDF + technischer JSON-Bericht

Besser, aber unzureichend für Beratung.

Ein JSON ist für Agenten ideal, für menschliche Beratung jedoch unnötig schwer lesbar.

## Option C — PDF + JSON + Markdown

**Gewählt.**

- PDF = Unternehmerentscheidung
- Markdown = Beratung
- JSON = maschinenlesbare Wahrheit

Das ist die kleinste robuste Trennung.

---

# 23. Plausibility and truth self-check

- **Goal length:** unter 3999 Zeichen.
- **Unsupported claims removed or labeled:** ja.
- **Brand Font:** MISSING bis zur Prüfung des kanonischen Pixelkiez Brand Assets.
- **Ranking Provider:** SOURCE\_NEEDED; kein Provider wurde erfunden.
- **Benchmark Provider:** SOURCE\_NEEDED; keine Branchenwerte werden vorausgesetzt.
- **Strongest counterargument:** Zu viele feste Visualisierungsvorgaben könnten zu mechanischen Präsentationen führen. Deshalb sind die Diagrammtypen Default-Regeln mit datenabhängigem Fallback, nicht starre Seitentemplates.
- **Failure-mode chain:** Wenn Business-Semantik direkt aus technischen Metric-Namen erzeugt wird, entsteht Fachsprache; daraus entsteht eine zwar korrekte, aber für Unternehmer wertlose Präsentation. Mitigation: eigener Business-Interpretation-Layer plus Customer-Language-Firewall vor dem Rendering.
- **Failure-mode chain:** Wenn Visualisierung vor Datenvalidierung erfolgt, entstehen dekorative oder irreführende Charts. Mitigation: Visual Eligibility darf nur kanonisch belegte Daten akzeptieren.
- **Failure-mode chain:** Wenn die Kundenpräsentation zur vollständigen Analyse gemacht wird, wächst Textmenge, Schrift wird kleiner und Managementrelevanz sinkt. Mitigation: vollständige Evidenz ausschließlich in JSON/Markdown; PDF auf vier Business-Hebel begrenzen.
- **Bias risks:** Chart-Bias („alles muss ein Diagramm sein“), Benchmark-Bias, Redesign-Bias und Score-Bias. Die Architektur erlaubt SHORT\_TEXT und Statusvisuals, verbietet unbelegte Benchmarks und koppelt Empfehlungen an konkrete Befunde.
- **Final readiness:** **ready-for-execution**.