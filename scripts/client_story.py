#!/usr/bin/env python3
"""Deterministic customer-story selection and chart planning for Pixelkiez reports."""
from __future__ import annotations

import copy
import re
from typing import Any

from strategic_relevance import evaluate_finding
from branch_priority import preferred_order

REAL_CHARTS = {f"V{i:02d}" for i in range(1, 12)}
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "positive": 4}
CONFIDENCE_DE = {"HIGH": "hoch", "MEDIUM": "mittel", "LOW": "niedrig"}


def _keep_case(replacement: str):
    """Replacement callable that keeps a sentence-initial capital letter."""
    def sub(match: re.Match) -> str:
        return replacement[:1].upper() + replacement[1:] if match.group(0)[:1].isupper() else replacement
    return sub

CLIENT_REPLACEMENTS = [
    (re.compile(r"Die drei wichtigsten Suchintentionen auf eigene, klar verlinkte Leistungsseiten abbilden\.?", re.I), "Die drei wichtigsten Suchanfragen mit klar verlinkten Leistungsseiten abdecken."),
    (re.compile(r"LCP-Element,?\s*Bildauslieferung und kritische Ressourcen prüfen und danach erneut messen\.?", re.I), "Mobile Hauptdarstellung durch optimierte Bilder und Ressourcen beschleunigen."),
    (re.compile(r"größtes sichtbares Seitenelement,?\s*Bildauslieferung und kritische Ressourcen prüfen und danach erneut messen\.?", re.I), "Mobile Hauptdarstellung durch optimierte Bilder und Ressourcen beschleunigen."),
    # Method, synthetic origin and sample scope survive simplification (evidence-bound claims patch).
    # "Testmessung" is customer-safe; "Labortest"/"Labormessung" are guardrail-forbidden provider/test terms.
    (re.compile(r"Lighthouse/PageSpeed-Labortest", re.I), "technische Testmessung der Ladezeit"),
    (re.compile(r"\bim\s+mobilen\s+Labortest\b", re.I), _keep_case("in der mobilen Testmessung")),
    (re.compile(r"\bim\s+Labortest\b", re.I), _keep_case("in der Testmessung")),
    (re.compile(r"\bLabortest(?:s)?\b", re.I), "Testmessung"),
    (re.compile(r"\bdie\s+mobile\s+Labormessung\b", re.I), _keep_case("die mobile Testmessung")),
    (re.compile(r"\bLabormessung(?:en)?\b", re.I), "Testmessung"),
    (re.compile(r"synthetische\s+Testreihe", re.I), "Beispieldaten"),
    (re.compile(r"synthetisches?\s+Testfeld", re.I), "Beispieldaten"),
    (re.compile(r"Synthetic fixture", re.I), "Beispieldaten"),
    (re.compile(r"synthetisch(?:e|en|er|es)?\s+(?:Fixture|Daten|Messung)", re.I), "Beispieldaten"),
    (re.compile(r"\bTestläufe?\b", re.I), "Messwerte"),
    (re.compile(r"\bTestreihen?\b", re.I), "Messwerte"),
    (re.compile(r"\bMessreihe(?:n)?\b", re.I), "Messwerte"),
    (re.compile(r"\bdokumentierte\s+Datenbasis\b", re.I), "vorliegende Werte"),
    (re.compile(r"\bim\s+geprüften\s+Umfang\b", re.I), "in der Stichprobe"),
    (re.compile(r"\bBelegstärke\b", re.I), "Belastbarkeit der Werte"),
    (re.compile(r"Testläufen", re.I), "Messungen"),
    (re.compile(r"Testlauf", re.I), "Messung"),
    (re.compile(r"Testreihe", re.I), "Messreihe"),
    (re.compile(r"\bTests?\b", re.I), "Prüfung"),
    (re.compile(r"\bFixture\b", re.I), "Analyse"),
    (re.compile(r"Belegte Projektbeispiele, Zertifikate und Qualifikationsnachweise und freigegebene Kundenstimmen", re.I), "Belegte Projektbeispiele, Zertifikate, Qualifikationsnachweise und freigegebene Kundenstimmen"),
    (re.compile(r"\bEntitätsklarheit\b", re.I), "Eindeutige Unternehmensdarstellung"),
    (re.compile(r"Leistung, Zielgruppe & Standort explizit", re.I), "Leistung, Zielgruppe und Standort"),
    (re.compile(r"Datenschutz- & Consent-Oberfläche", re.I), "Datenschutz und Einwilligungen"),
    (re.compile(r"Impressum & rechtliche Oberfläche", re.I), "Impressum und rechtliche Angaben"),
    (re.compile(r"\bThematische Tiefe\b", re.I), "Inhaltliche Tiefe"),
    (re.compile(r"Nach den Korrekturen Audit mit Performance-, Mobile-, Accessibility- und privaten Such-/Nutzungsdaten erweitern\.?", re.I), "Nach den Korrekturen Ladezeit, mobile Bedienung, Barrierefreiheit sowie private Such- und Nutzungsdaten prüfen."),
    (re.compile(r"Zertifikats-/Qualifikationsnachweise", re.I), "Zertifikate und Qualifikationsnachweise"),
    (re.compile(r"\bWeb\b", re.I), "Website"),
    (re.compile(r"Besucherdaten/CRM", re.I), "Besucher- und Kundendaten"),
    (re.compile(r"datiertes öffentliches Suchtest", re.I), "datierter öffentlicher Suchtest"),
    (re.compile(r"Local Auffindbarkeit", re.I), "Lokale Auffindbarkeit"),
    (re.compile(r"Nach den Korrekturen Audit mit Ladegeschwindigkeit-, Mobile-, Barrierefreiheit- und privaten Such-/Nutzungsdaten erweitern\.?", re.I), "Nach den Korrekturen Ladezeit, mobile Bedienung, Barrierefreiheit sowie private Such- und Nutzungsdaten prüfen."),
    (re.compile(r"direkter CrUX/PSI/Lighthouse-Messrunner", re.I), "direkte reale und technische Ladezeit-Messung"),
    (re.compile(r"vollständiger Roh-HTML-/Header-Inspektor", re.I), "vollständige Prüfung technischer Seitendaten"),
    (re.compile(r"Search Console/Analytics/CRM", re.I), "Google-Daten zu Suchanfragen sowie Besucher- und Kundendaten"),
    (re.compile(r"interaktiver Accessibility-/Viewport-Runner", re.I), "interaktive Prüfung mobiler Bedienung und Barrierefreiheit"),
    (re.compile(r"Repository-/Deployment-Zugriff", re.I), "Zugriff auf Entwicklung und Hosting"),
    (re.compile(r"öffentlicher Browser-/Webabruf", re.I), "öffentlicher Website-Abruf"),
    (re.compile(r"lokale Pixelkiez Scoring-/Validierungs-/PDF-Werkzeuge", re.I), "lokale Pixelkiez Prüf- und Berichtswerkzeuge"),
    (re.compile(r"Raw-HTML Canonical/Robots-Meta/JSON-LD", re.I), "technische Angaben zur Hauptadresse, Indexierung und Seitenstruktur"),
    (re.compile(r"CrUX/Felddaten", re.I), "reale Lade- und Nutzungsdaten"),
    (re.compile(r"Assetgrößen und Response-Header", re.I), "Größe wichtiger Seitendateien und Serverantworten"),
    (re.compile(r"pixelgenaue Mobile-/Desktop-Viewportprüfung", re.I), "pixelgenaue Prüfung auf Mobilgeräten und Desktop"),
    (re.compile(r"Tastatur/Fokus/Kontrast/automatisierter WCAG-Snapshot", re.I), "vollständige Prüfung von Tastaturbedienung, Fokus, Kontrast und Barrierefreiheit"),
    (re.compile(r"Repository, Backend und Deployment", re.I), "Entwicklungs-, System- und Hostingzugriff"),
    (re.compile(r"technischer Ladezeit-Test/Ladezeit-Test-Labortest", re.I), "technischer Ladezeit-Test"),
    (re.compile(r"reale Nutzungsdaten/reale Nutzerdaten", re.I), "reale Lade- und Nutzungsdaten"),
    (re.compile(r"Besucherdaten/CRM", re.I), "Besucher- und Kundendaten"),
    (re.compile(r"vollständiger Roh-HTML-/Serverangaben-Inspektor", re.I), "vollständige Prüfung technischer Seitendaten"),
    (re.compile(r"interaktiver Barrierefreiheit-/Viewport-Runner", re.I), "interaktive Prüfung mobiler Bedienung und Barrierefreiheit"),
    (re.compile(r"Entwicklungszugriff-/Hosting-Zugriff", re.I), "Zugriff auf Entwicklung und Hosting"),
    (re.compile(r"technische Seitendaten eindeutige Hauptadressen/Robots-Meta/strukturierte Daten", re.I), "technische Angaben zur Hauptadresse, Indexierung und Seitenstruktur"),
    (re.compile(r"Gesetzes-/ODR-Verweise", re.I), "Gesetzes- und Streitbeilegungsverweise"),
    (re.compile(r"Ladegeschwindigkeit-, Mobile-, Barrierefreiheit- und privaten Such-/Nutzungsdaten", re.I), "Ladezeit, mobile Bedienung, Barrierefreiheit sowie private Such- und Nutzungsdaten"),
    (re.compile(r"\bSEO\b", re.I), "Auffindbarkeit"),
    (re.compile(r"\bContent\b", re.I), "Inhalte"),
    (re.compile(r"technischer Ladezeit-Test/PageSpeed-Labortest", re.I), "technischer Ladezeit-Test"),
    (re.compile(r"\bPageSpeed\b", re.I), "Ladezeit-Test"),
    (re.compile(r"direkter CrUX/PSI/technischer Ladezeit-Test-Messrunner", re.I), "direkte reale und technische Ladezeit-Messung"),
    (re.compile(r"CrUX/reale Nutzerdaten", re.I), "reale Lade- und Nutzungsdaten"),
    (re.compile(r"\bCrUX\b", re.I), "reale Nutzungsdaten"),
    (re.compile(r"\bPSI\b", re.I), "Ladezeit-Test"),
    (re.compile(r"\bauthoritative\b", re.I), "verbindliche"),
    (re.compile(r"Raw-HTML eindeutige Hauptadressen/Robots-Meta/strukturierte Daten", re.I), "technische Angaben zur Hauptadresse, Indexierung und Seitenstruktur"),
    (re.compile(r"Raw-HTML-JSON-LD", re.I), "strukturierte Seitendaten"),
    (re.compile(r"\bRaw-HTML\b", re.I), "technische Seitendaten"),
    (re.compile(r"\bLocal SEO\b", re.I), "Lokale Auffindbarkeit"),
    (re.compile(r"\bAnalytics\b", re.I), "Besucherdaten"),
    (re.compile(r"\bWCAG(?:-Prüfung|-Konformität)?\b", re.I), "Barrierefreiheits-Prüfung"),
    (re.compile(r"\bDeployment\b", re.I), "Hosting"),
    (re.compile(r"\bRepository(?:-Zugriff)?\b", re.I), "Entwicklungszugriff"),
    (re.compile(r"\bSearch Console\b", re.I), "Google-Daten zu Suchanfragen"),
    (re.compile(r"Analytics/CRM", re.I), "Besucher-, Anfrage- und Kundendaten"),
    (re.compile(r"reale Lade- und Reaktionswerte reale Nutzerdaten", re.I), "reale Lade- und Reaktionswerte aus Nutzerdaten"),
    (re.compile(r"\bCanonicals?\b", re.I), "eindeutige Hauptadressen"),
    (re.compile(r"robots\.txt", re.I), "Suchmaschinen-Steuerdatei"),
    (re.compile(r"sitemap\.xml", re.I), "Seitenübersicht für Suchmaschinen"),
    (re.compile(r"\bLCP-Element\b", re.I), "größtes sichtbares Seitenelement"),
    (re.compile(r"\bLCP\b", re.I), "Ladezeit des wichtigsten sichtbaren Inhalts"),
    (re.compile(r"\bINP\b", re.I), "Reaktionszeit"),
    (re.compile(r"\bCLS\b", re.I), "Layout-Stabilität"),
    (re.compile(r"\bTTFB\b", re.I), "Server-Antwortzeit"),
    (re.compile(r"\bCTA\b", re.I), "Hauptaktion"),
    (re.compile(r"\bLandingpages?\b", re.I), "Leistungsseiten"),
    (re.compile(r"FAQ- und Belege-Strukturen", re.I), "Fragen und Antworten mit passenden Belegen"),
    (re.compile(r"Die (?:oeffentliche|\u00f6ffentliche) Basis ist fachlich klar genug f(?:ue|\u00fc)r gezielte Modernisierung\.?", re.I), "Die Website hat eine brauchbare Basis f\u00fcr gezielte Verbesserungen."),
    (re.compile(r"Why/Whom/How/What/Pricing macht die Angebotsseite gut beantwortbar\.?", re.I), "Die Angebotsseite beantwortet Zweck, Zielgruppe, Vorgehen und Preis klar."),
    (re.compile(r"\bPublic-Surface-Stichprobe\b", re.I), "Stichprobe der \u00f6ffentlich sichtbaren Seiten"),
    (re.compile(r"\bBackendzugriff\b", re.I), "Zugriff auf interne Systeme"),
    (re.compile(r"Search Console Index- und Query-Daten", re.I), "Search-Console-Daten zu Auffindbarkeit und Suchanfragen"),
    (re.compile(r"Analytics-/Conversion-Daten", re.I), "Besucher- und Anfrage-Daten"),
    (re.compile(r"\bFelddaten\b", re.I), "reale Nutzerdaten"),
    (re.compile(r"\bRankinganteile\b", re.I), "dauerhaften Platzierungen"),
    (re.compile(r"Zweck, Zielgruppe, Vorgehen und Preis macht", re.I), "Zweck, Zielgruppe, Vorgehen und Preis machen"),
    (re.compile(r"Im\s+Brand-\s*(?:/|und)\s*Non-Brand-Suchsample", re.I), "In Suchtests mit und ohne Firmennamen"),
    (re.compile(r"Indexierung\s+pruefen\s+und\s+fuer\s+Kernintents\s+klar benannte Leistungsseiten.*?erstellen", re.I), "Pr\u00fcfen, ob wichtige Seiten auffindbar sind, und Kernleistungen klar benennen"),
    (re.compile(r"Performance,\s*Header,\s*Mobile-UX\s+und\s+Accessibility\s+mit echten Messwerkzeugen\s+pruefen", re.I), "Ladezeit, mobile Bedienbarkeit und Barrierefreiheit messen"),
    (re.compile(r"Auffindbarkeit\s+technisch\s+verifizieren", re.I), "Auffindbarkeit genauer pr\u00fcfen"),
    (re.compile(r"\bDiscovery-Call\b", re.I), "Beratungsgespr\u00e4ch"),
    (re.compile(r"Indexierung\s+pruefen\s+und\s+fuer\s+wichtige Suchanfragen\s+klar benannte Leistungsseiten.*?erstellen", re.I), "Pr\u00fcfen, ob wichtige Seiten auffindbar sind, und Kernleistungen klar benennen"),
    (re.compile(r"Indexierung\s+pruefen\s+und\s+klare Intent-Seiten fuer Kernleistungen aufbauen", re.I), "Kernleistungen auf klar benannten Seiten f\u00fcr wichtige Suchanfragen erkl\u00e4ren"),
    (re.compile(r"Zwei bis drei belegte Cases/Proof Points", re.I), "Zwei bis drei belegte Fallbeispiele"),
    (re.compile(r"Indexierung\s+pruefen\s+und\s+fuer\s+wichtige Suchanfragen\s+klar benannte Leistungsseiten\s+mit\s+eindeutigen(?:\s+Seitentitel(?:n)?\s+und\s+Haupt(?:ue|\u00fc)berschriften)?\s*erstellen", re.I), "Pr\u00fcfen, ob wichtige Seiten auffindbar sind, und Kernleistungen klar benennen"),
    (re.compile(r"Indexierung\s+pruefen\s+und\s+klare Seiten f\u00fcr wichtige Suchanfragen fuer Kernleistungen aufbauen", re.I), "Kernleistungen auf klar benannten Seiten f\u00fcr wichtige Suchanfragen erkl\u00e4ren"),
    (re.compile(r"Zwei bis drei belegte Fallbeispiele/Belege", re.I), "Zwei bis drei belegte Fallbeispiele"),
    (re.compile(r"\bFakten auf allen Seiten gleich\b", re.I), "Einheitliche Fakten"),
    (re.compile(r"\bAktualit\u00e4t sichtbarer Inhalte?\b", re.I), "Aktuelle Inhalte"),
    (re.compile(r"\bTitles?, Metas? \& (?:Ue|\u00dc)berschriften\b", re.I), "Titel und \u00dcberschriften"),
    (re.compile(r"\bAntwortbarkeit \& FAQ-Struktur\b", re.I), "Antworten auf Kundenfragen"),
    (re.compile(r"\bBild-SEO\b", re.I), "Bilder f\u00fcr die Suche"),
    (re.compile(r"\bSynchronisieren\b", re.I), "angleichen"),
    (re.compile(r"\bsynchronisieren\b", re.I), "angleichen"),
    (re.compile(r"\boeffentlichen\b", re.I), "\u00f6ffentlichen"),
    (re.compile(r"\boeffentliche\b", re.I), "\u00f6ffentliche"),
    (re.compile(r"\boeffentlich\b", re.I), "\u00f6ffentlich"),
    (re.compile(r"\bPraesenz\b", re.I), "Pr\u00e4senz"),
    (re.compile(r"\bkoennen\b", re.I), "k\u00f6nnen"),
    (re.compile(r"\bAktualitaet\b", re.I), "Aktualit\u00e4t"),
    (re.compile(r"\bIdentitaet\b", re.I), "Identit\u00e4t"),
    (re.compile(r"\bfuer\b", re.I), "f\u00fcr"),
    (re.compile(r"\bpruefen\b", re.I), "pr\u00fcfen"),
    (re.compile(r"\bgeprueft(?:e|en|er|es)?\b", re.I), lambda m: m.group(0).replace("geprueft", "gepr\u00fcft")),
    (re.compile(r"\bergaenzen\b", re.I), "erg\u00e4nzen"),
    (re.compile(r"\beinpregsam\b", re.I), "einpr\u00e4gsam"),
    (re.compile(r"\beinpraegsam\b", re.I), "einpr\u00e4gsam"),
    (re.compile(r"\bHauptueberschriften\b", re.I), "Haupt\u00fcberschriften"),
    (re.compile(r"\bUeberschriften\b", re.I), "\u00dcberschriften"),
    (re.compile(r"\berklaeren\b", re.I), "erkl\u00e4ren"),
    (re.compile(r"\bspaeter\b", re.I), "sp\u00e4ter"),
    (re.compile(r"\bspaet\b", re.I), "sp\u00e4t"),
    (re.compile(r"\bmuessen\b", re.I), "m\u00fcssen"),
    (re.compile(r"\baeltere\b"), "\u00e4ltere"),
    (re.compile(r"\bAeltere\b"), "\u00c4ltere"),
    (re.compile(r"\bNon-Brand-Sichtbarkeit\b", re.I), "Treffer ohne Firmennamen"),
    (re.compile(r"\bBrand-Sichtbarkeit\b", re.I), "Treffer beim Firmennamen"),
    (re.compile(r"Konsistente Unternehmens-\s*&\s*Leistungsdaten", re.I), "Einheitliche Firmendaten"),
    (re.compile(r"Faktenkonsistenz \u00fcber Seiten(?: hinweg)?", re.I), "Einheitliche Fakten"),
    (re.compile(r"Referenzen, Belege \& Proof Points", re.I), "Referenzen und Fallbelege"),
    (re.compile(r"Zuordnung von Claims zu Belegen", re.I), "Belege f\u00fcr Nutzenversprechen"),
    (re.compile(r"Das\s+(?:oeffentliche|\u00f6ffentliche)\s+Suchsample\s+zeigt", re.I), "Die \u00f6ffentlichen Suchtests zeigen"),
    (re.compile(r"\bBrand-Sichtbarkeit\b", re.I), "Sichtbarkeit beim Firmennamen"),
    (re.compile(r"Why/Whom/How/What/Pricing", re.I), "Zweck, Zielgruppe, Vorgehen und Preis"),
    (re.compile(r"\bPerformance\b", re.I), "Ladegeschwindigkeit"),
    (re.compile(r"\bMobile-UX\b", re.I), "mobile Bedienbarkeit"),
    (re.compile(r"\bAccessibility\b", re.I), "Barrierefreiheit"),
    (re.compile(r"\bSecurity-Header\b", re.I), "Sicherheitsangaben"),
    (re.compile(r"\bHeader\b", re.I), "Serverangaben"),
    (re.compile(r"Brand-\s*(?:/|und)\s*Non-Brand-Suchsample", re.I), "Suchtests mit und ohne Firmennamen"),
    (re.compile(r"Brand-\s*(?:/|und)\s*Non-Brand-Suchtests?", re.I), "Suchtests mit und ohne Firmennamen"),
    (re.compile(r"\bSuchsample\b", re.I), "Suchtest"),
    (re.compile(r"\bKernsample\b", re.I), "gepr\u00fcften Seiten"),
    (re.compile(r"\bClaims?\b", re.I), "Nutzenversprechen"),
    (re.compile(r"\bCases?\b", re.I), "Fallbeispiele"),
    (re.compile(r"\bFirst-Party-Domain\b", re.I), "eigene Website"),
    (re.compile(r"\bFirst-Party-Treffer\b", re.I), "Treffer der eigenen Website"),
    (re.compile(r"\bFirst-Party\b", re.I), "eigene Website"),
    (re.compile(r"Brand-/Non-Brand-Suchsample", re.I), "Suchtests mit und ohne Firmennamen"),
    (re.compile(r"\bBrand-Suchsample\b", re.I), "Suchtest mit Firmennamen"),
    (re.compile(r"\bNon-Brand-Auffindbarkeit\b", re.I), "Auffindbarkeit ohne Firmennamen"),
    (re.compile(r"\bNon-Brand-Sichtbarkeit\b", re.I), "Sichtbarkeit ohne Firmennamen"),
    (re.compile(r"\bNon-Brand-Suchen\b", re.I), "Suchanfragen ohne Firmennamen"),
    (re.compile(r"\bNon-Brand-Intentionen\b", re.I), "Suchanfragen ohne Firmennamen"),
    (re.compile(r"\bNon-Brand-(?:Intents?|Suchproben?|Suchintents?)\b", re.I), "Suchanfragen ohne Firmennamen"),
    (re.compile(r"\bKernintents?\b", re.I), "wichtige Suchanfragen"),
    (re.compile(r"\bIntent-Seiten\b", re.I), "Seiten f\u00fcr wichtige Suchanfragen"),
    (re.compile(r"\bStammdaten synchronisieren\b", re.I), "Firmendaten \u00fcberall angleichen"),
    (re.compile(r"\bStammdaten\b", re.I), "Firmendaten"),
    (re.compile(r"\bProof Points?\b", re.I), "Belege"),
    (re.compile(r"\bProof\b", re.I), "Belege"),
    (re.compile(r"Nutzerf\u00fchrung\s*&\s*Conversion", re.I), "Nutzerf\u00fchrung & Anfragen"),
    (re.compile(r"\bConversion\b", re.I), "Anfragen oder Abschl\u00fcsse"),
    (re.compile(r"\bTitles?\s*(?:und|&)\s*H1\b", re.I), "Seitentitel und Haupt\u00fcberschriften"),
    (re.compile(r"\bRaw DOM\b", re.I), "Seitenquelltext"),
    (re.compile(r"\bJSON-LD\b", re.I), "strukturierte Daten"),
    (re.compile(r"\bSERP\b", re.I), "Suchergebnis"),
    (re.compile(r"\bCore Web Vitals\b", re.I), "reale Lade- und Reaktionswerte"),
    (re.compile(r"\bLighthouse\b", re.I), "technischer Ladezeit-Test"),
    (re.compile(r"Assets,? Caching,? Kompression,? Security-Header", re.I), "Seitendateien, Zwischenspeicherung und Sicherheitsangaben"),
    (re.compile(r"Canonical,? noindex und hreflang", re.I), "Indexierungs- und Sprachsignale"),
    (re.compile(r"\bCoverage\b", re.I), "Messabdeckung"),
    (re.compile(r"\bConfidence\b", re.I), "Sicherheit"),
]

CLIENT_FINAL_REPLACEMENTS = [
    (re.compile(r"Auffindbarkeit & Auffindbarkeit", re.I), "Auffindbarkeit in Suchmaschinen"),
    (re.compile(r"\bstrukturierte Daten\b", re.I), "maschinenlesbare Firmenangaben"),
    (re.compile(r"Besucherdaten/CRM", re.I), "Besucher- und Kundendaten"),
    (re.compile(r"datiertes öffentliches Suchtest", re.I), "datierter öffentlicher Suchtest"),
    (re.compile(r"Local Auffindbarkeit", re.I), "Lokale Auffindbarkeit"),
]


CLIENT_JARGON = re.compile(
    r"\b(?:First-Party(?:-Treffer|-Domain)?|Non-Brand(?:-Intents?|[- ]Suchproben?|[- ]Suchintents?)|"
    r"Proof(?: Points?)?|Conversion|Kernintents?|Raw DOM|JSON-LD|Coverage|Confidence)\b",
    re.I,
)


def clip(text: object, limit: int) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= limit:
        return value
    cut = value[: max(0, limit - 1)].rstrip()
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(".,;:") + "\u2026"


def clientize(text: object, limit: int) -> str:
    value = " ".join(str(text or "").split())
    for pattern, replacement in CLIENT_REPLACEMENTS:
        value = pattern.sub(replacement, value)
    for pattern, replacement in CLIENT_FINAL_REPLACEMENTS:
        value = pattern.sub(replacement, value)
    return clip(value, limit)


def confidence_de(value: object) -> str:
    return CONFIDENCE_DE.get(str(value).upper(), str(value).lower() if value else "niedrig")


def select_client_levers(
    report: dict[str, Any], max_levers: int = 4, *,
    branch_weights: dict[str, int] | None = None,
    branch_roles: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    findings = [
        f for f in report.get("findings", [])
        if isinstance(f, dict)
        and f.get("severity") != "positive"
        and evaluate_finding(report, f)["eligible"]
    ]
    findings.sort(key=lambda f: (SEVERITY_RANK.get(str(f.get("severity")), 9), -int(f.get("confidence", 0)), str(f.get("id", ""))))
    # Approved industry priorities reorder only existing evidence-admitted findings
    # within the same severity band. No profile => legacy byte-for-byte order.
    if branch_weights is not None:
        findings = preferred_order(findings, branch_weights, branch_roles or {})
    selected: list[dict[str, Any]] = []
    seen_categories: set[str] = set()

    # Mandatory customer risks are selected before ordinary website optimization findings.
    # Legal claim certainty remains separate in customer_risk.claim_state; this is only
    # a customer-visibility and prioritization decision.
    priority_rank = {"MANDATORY_CRITICAL": 0, "MANDATORY_HIGH": 1}
    mandatory = [
        f for f in findings
        if isinstance(f.get("customer_risk"), dict)
        and f["customer_risk"].get("priority") in priority_rank
    ]
    mandatory.sort(key=lambda f: (
        priority_rank.get(str(f.get("customer_risk", {}).get("priority")), 9),
        0 if f.get("customer_risk", {}).get("group") == "PROVIDER_IDENTITY" else 1,
        SEVERITY_RANK.get(str(f.get("severity")), 9),
        -int(f.get("confidence", 0)),
        str(f.get("id", "")),
    ))
    for f in mandatory:
        if len(selected) >= max_levers:
            break
        selected.append(f)
        seen_categories.add(str(f.get("category", "")))

    # Other critical/high findings outrank category diversity, but can no longer hide
    # a mandatory provider-identification risk.
    for f in findings:
        if f in selected or len(selected) >= max_levers:
            continue
        if f.get("severity") in {"critical", "high"}:
            selected.append(f)
            seen_categories.add(str(f.get("category", "")))

    # Then add medium/low findings with category diversity where possible.
    for f in findings:
        if f in selected or len(selected) >= max_levers:
            continue
        cat = str(f.get("category", ""))
        if cat not in seen_categories:
            selected.append(f)
            seen_categories.add(cat)

    # Fill remaining slots only from findings that passed the Strategic Relevance Gate.
    for f in findings:
        if f not in selected and len(selected) < max_levers:
            selected.append(f)
    return selected[:max_levers]

def _next_viz_id(values: list[dict[str, Any]]) -> str:
    nums: list[int] = []
    for item in values:
        match = re.fullmatch(r"VIZ-(\d+)", str(item.get("id", ""))) if isinstance(item, dict) else None
        if match:
            nums.append(int(match.group(1)))
    return f"VIZ-{max([899, *nums]) + 1:03d}"


def _clientize_visualization(value: dict[str, Any]) -> dict[str, Any]:
    item = copy.deepcopy(value)
    item["title"] = clientize(item.get("title"), 120)
    item["metric_label"] = clientize(item.get("metric_label"), 80)
    item["current_value_label"] = clientize(item.get("current_value_label"), 40)
    item["does_not_prove"] = clientize(item.get("does_not_prove"), 220)
    data = item.get("data")
    if isinstance(data, dict):
        for key in ("groups",):
            if isinstance(data.get(key), list):
                data[key] = [clientize(x, 28) for x in data[key]]
        for key in ("series", "rows", "parts", "points", "axes", "classes", "tiles", "nets"):
            rows = data.get(key)
            if not isinstance(rows, list):
                continue
            clean_rows: list[Any] = []
            for row in rows:
                if not isinstance(row, dict):
                    clean_rows.append(row)
                    continue
                copy_row = dict(row)
                for field, limit in (("label", 36), ("name", 32), ("metric", 48), ("does_not_prove", 90)):
                    if field in copy_row:
                        copy_row[field] = clientize(copy_row[field], limit)
                clean_rows.append(copy_row)
            data[key] = clean_rows
        if "radius_legend" in data:
            data["radius_legend"] = clientize(data.get("radius_legend"), 60)
    return item


def _metric_gap_rows(
    report: dict[str, Any],
    registry: dict[str, Any],
    preferred_categories: set[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    defs = {m.get("id"): m for m in registry.get("metrics", []) if isinstance(m, dict)}
    candidates: list[tuple[int, int, str, str, float]] = []
    for metric in report.get("metrics", []):
        if not isinstance(metric, dict):
            continue
        score = metric.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            continue
        if metric.get("measurement_class") not in {"measured", "observed"}:
            continue
        if metric.get("evidence_grade") in {"E7", "E8"}:
            continue
        if float(score) >= 100:
            continue
        mid = str(metric.get("id", ""))
        mdef = defs.get(mid, {})
        cat = str(mdef.get("category", ""))
        preferred = 0 if cat in preferred_categories else 1
        severity_order = 0 if float(score) <= 50 else 1
        label = clientize(mdef.get("label_de", mid), 34)
        candidates.append((preferred, severity_order, mid, label, round(100.0 - float(score), 1)))
    candidates.sort(key=lambda x: (x[0], x[1], -x[4], x[3]))
    picked: list[tuple[int, int, str, str, float]] = []
    per_gap: dict[float, int] = {}
    for candidate in candidates:
        gap = candidate[4]
        if per_gap.get(gap, 0) >= 2:
            continue
        picked.append(candidate)
        per_gap[gap] = per_gap.get(gap, 0) + 1
        if len(picked) == 6:
            break
    if len(picked) < 4:
        for candidate in candidates:
            if candidate not in picked:
                picked.append(candidate)
                if len(picked) == 6:
                    break
    if len(picked) < 4:
        return [], []
    picked.sort(key=lambda x: (-x[4], x[3]))
    return ([{"label": label, "value": gap} for _, _, _, label, gap in picked], [mid for _, _, mid, _, _ in picked])


def _build_metric_gap_chart(
    report: dict[str, Any],
    registry: dict[str, Any],
    selected_categories: set[str],
    values: list[dict[str, Any]],
) -> dict[str, Any] | None:
    rows, metric_refs = _metric_gap_rows(report, registry, selected_categories)
    if not rows:
        return None
    score = report.get("score_summary", {}) if isinstance(report.get("score_summary"), dict) else {}
    audit_date = str(report.get("meta", {}).get("audit_date", ""))
    top = rows[0]
    return {
        "id": _next_viz_id(values),
        "template_id": "V04",
        "category": "overall",
        "metric_refs": metric_refs,
        "finding_ref": None,
        "title": clientize(f"Die gr\u00f6\u00dfte Bewertungsl\u00fccke betrifft: {top['label']}.", 120),
        "metric_label": "Gr\u00f6\u00dfte Bewertungsl\u00fccken · Pixelkiez Bewertungsmodell",
        "current_value_label": f"{str(top['value']).replace('.', ',')} Punkte",
        "evidence": {
            "grade": "BUSINESS_DERIVED",
            "mode": "DERIVED",
            "scope": "SITE",
            "population": f"{len(rows)} bewertete Messpunkte aus priorisierten Bereichen",
            "tool": "Pixelkiez scoring policy",
            "version": str(score.get("policy_version", "2.0.0")),
            "date": audit_date,
        },
        "threshold": None,
        "does_not_prove": "Die Bewertungsl\u00fccke ist kein Umsatz-, Ranking- oder Anfragepotenzial. Sie zeigt nur den Abstand im Pixelkiez Bewertungsmodell.",
        "data": {"rows": rows},
    }


def _build_category_score_chart(
    report: dict[str, Any],
    category: dict[str, Any],
    values: list[dict[str, Any]],
) -> dict[str, Any]:
    score_summary = report.get("score_summary", {}) if isinstance(report.get("score_summary"), dict) else {}
    score_value = float(category["score"])
    coverage = int(category.get("coverage", 0))
    label = clientize(category.get("label", category.get("category", "Bereich")), 42)
    gap = round(100.0 - score_value, 1)
    if score_value < 60:
        verdict = "klarer Verbesserungshebel"
    elif score_value < 75:
        verdict = "gezielte Verbesserungen sind sinnvoll"
    elif score_value < 90:
        verdict = "stark mit wenigen L\u00fccken"
    else:
        verdict = "sehr stark im gepr\u00fcften Umfang"
    return {
        "id": _next_viz_id(values),
        "template_id": "V07",
        "category": str(category.get("category", "overall")),
        "metric_refs": [f"CATEGORY:{category.get('category', 'unknown')}"] ,
        "finding_ref": None,
        "title": clientize(f"{label}: {round(score_value)} von 100 - {verdict}.", 120),
        "metric_label": f"{label} · Pixelkiez Bereichswert",
        "current_value_label": f"{round(score_value)} / 100",
        "evidence": {
            "grade": "BUSINESS_DERIVED",
            "mode": "DERIVED",
            "scope": "SITE",
            "population": f"Pixelkiez Bereichswert für {label}",
            "tool": "Pixelkiez scoring policy",
            "version": str(score_summary.get("policy_version", "2.0.0")),
            "date": str(report.get("meta", {}).get("audit_date", "")),
        },
        "threshold": None,
        "does_not_prove": "Der Bereichswert ist keine Umsatz-, Ranking- oder Anfrageprognose. Er ist eine Orientierung im Pixelkiez Bewertungsmodell.",
        "data": {
            "value": score_value,
            "scale": {"min": 0, "max": 100, "source": f"Pixelkiez scoring policy {score_summary.get('policy_version', '2.0.0')}"},
            "tiles": [
                {"value": f"{str(gap).replace('.', ',')}", "label": "Abstand bis 100"},
            ],
        },
    }


def _build_overall_score_chart(report: dict[str, Any], values: list[dict[str, Any]]) -> dict[str, Any] | None:
    score = report.get("score_summary", {}) if isinstance(report.get("score_summary"), dict) else {}
    overall = score.get("score")
    if not isinstance(overall, (int, float)) or isinstance(overall, bool):
        return None
    urgent = sum(
        1 for f in report.get("findings", [])
        if isinstance(f, dict) and f.get("severity") in {"critical", "high"}
    )
    return {
        "id": _next_viz_id(values),
        "template_id": "V07",
        "category": "overall",
        "metric_refs": ["SCORE-SUMMARY"],
        "finding_ref": None,
        "title": clientize(f"{round(float(overall))} von 100: {score.get('interpretation', 'Orientierung im gepr\u00fcften Umfang')}.", 120),
        "metric_label": "Pixelkiez Score · Orientierung im gepr\u00fcften Umfang",
        "current_value_label": f"{round(float(overall))} / 100",
        "evidence": {
            "grade": "BUSINESS_DERIVED",
            "mode": "DERIVED",
            "scope": "SITE",
            "population": "Pixelkiez Gesamtwert der belastbar bewertbaren Bereiche",
            "tool": "Pixelkiez scoring policy",
            "version": str(score.get("policy_version", "2.0.0")),
            "date": str(report.get("meta", {}).get("audit_date", "")),
        },
        "threshold": None,
        "does_not_prove": "Der Pixelkiez Score ist keine universelle Website-Qualit\u00e4t und keine Prognose f\u00fcr Umsatz, Ranking oder Anfragen.",
        "data": {
            "value": float(overall),
            "scale": {"min": 0, "max": 100, "source": f"Pixelkiez scoring policy {score.get('policy_version', '2.0.0')}"},
            "tiles": [
                {"value": str(urgent), "label": "hohe oder kritische Priorit\u00e4ten"},
            ],
        },
    }


def plan_visual_story(
    report: dict[str, Any],
    categories: list[dict[str, Any]],
    selected_levers: list[dict[str, Any]],
    registry: dict[str, Any],
    max_charts: int = 3,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected_ids = {str(f.get("id", "")) for f in selected_levers}
    direct = [
        _clientize_visualization(v)
        for v in report.get("visualizations", [])
        if isinstance(v, dict) and v.get("template_id") in REAL_CHARTS
    ]
    direct.sort(key=lambda v: (0 if v.get("finding_ref") in selected_ids else 1, str(v.get("id", ""))))
    values = direct[:max_charts]
    selected_categories = {str(f.get("category", "")) for f in selected_levers}

    metric_gap_possible = bool(_metric_gap_rows(report, registry, selected_categories)[0])
    scored_categories = [
        c for c in categories
        if isinstance(c.get("score"), (int, float)) and not isinstance(c.get("score"), bool)
    ]
    scored_categories.sort(key=lambda c: (0 if c.get("category") in selected_categories else 1, float(c.get("score", 100)), -int(c.get("coverage", 0))))
    overall_score_available = isinstance(report.get("score_summary", {}).get("score"), (int, float)) and not isinstance(report.get("score_summary", {}).get("score"), bool)

    candidate_count = len(direct)
    candidate_count += 1 if metric_gap_possible else 0
    candidate_count += min(2, len(scored_categories))
    candidate_count += 1 if overall_score_available else 0

    if len(values) < 2 and metric_gap_possible:
        gap_chart = _build_metric_gap_chart(report, registry, selected_categories, values)
        if gap_chart:
            values.append(gap_chart)
    used_categories: set[str] = set()
    for chart in values:
        if str(chart.get("category", "")) not in {"", "overall"}:
            used_categories.add(str(chart.get("category")))
    for category in scored_categories:
        if len(values) >= 2:
            break
        cid = str(category.get("category", ""))
        if cid in used_categories:
            continue
        values.append(_build_category_score_chart(report, category, values))
        used_categories.add(cid)
    if len(values) < 2 and overall_score_available:
        overall = _build_overall_score_chart(report, values)
        if overall:
            values.append(overall)
    for category in scored_categories:
        if len(values) >= 2:
            break
        cid = str(category.get("category", ""))
        if cid in used_categories:
            continue
        values.append(_build_category_score_chart(report, category, values))
        used_categories.add(cid)

    values = values[:max_charts]
    status = "PASS" if len(values) >= 2 else "INSUFFICIENT_QUANTITATIVE_EVIDENCE"
    plan = {
        "mode": "marketing_summary",
        "selected_lever_ids": [str(f.get("id", "")) for f in selected_levers],
        "max_levers": 4,
        "real_chart_count": len(values),
        "target_real_charts": "2-3",
        "quantitative_opportunities": candidate_count,
        "visual_story_status": status,
        "technical_appendix_rendered": False,
        "max_customer_pages": 12,
    }
    return values, plan


def visible_text(data: dict[str, Any]) -> str:
    parts: list[str] = []
    cover = data.get("cover", {})
    executive = data.get("executive", {})
    recommendation = data.get("recommendation", {})
    parts.extend([
        cover.get("title", ""), cover.get("verdict", ""), executive.get("takeaway", ""),
        recommendation.get("route", ""), recommendation.get("reason", ""), recommendation.get("next_step", ""),
    ])
    parts.extend(executive.get("strengths", []))
    parts.extend(executive.get("priorities", []))
    for cat in data.get("categories", []):
        if isinstance(cat, dict):
            parts.extend([cat.get("label", ""), cat.get("summary", "")])
    for finding in data.get("findings", []):
        if isinstance(finding, dict):
            parts.extend([finding.get("headline", ""), finding.get("observation", ""), finding.get("impact", ""), finding.get("action", "")])
    for bucket in data.get("roadmap", {}).values():
        if isinstance(bucket, list):
            for item in bucket:
                if isinstance(item, dict):
                    parts.append(item.get("action", ""))
    for viz in data.get("visualizations", []):
        if isinstance(viz, dict):
            parts.extend([viz.get("title", ""), viz.get("metric_label", "")])
    closing = data.get("closing", {})
    if isinstance(closing, dict):
        parts.extend([closing.get("eyebrow", ""), closing.get("title", ""), closing.get("summary", ""), closing.get("cta", ""), closing.get("next_step", "")])
        parts.extend(closing.get("actions", []))
        for item in closing.get("measurement_highlights", []):
            if isinstance(item, dict):
                parts.extend([item.get("label", ""), item.get("value", ""), item.get("context", "")])
    return " ".join(str(x) for x in parts if x)


def validate_story_model(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    values = [v for v in data.get("visualizations", []) if isinstance(v, dict)]
    real = [v for v in values if v.get("template_id") in REAL_CHARTS]
    story = data.get("client_story", {}) if isinstance(data.get("client_story"), dict) else {}
    canonical = story.get("visualization_plan_is_canonical") is True
    if not canonical and len(real) < 2:
        errors.append(f"client model requires at least two semantic chart candidates when no canonical visualization plan is bound; found {len(real)}")
    if len(real) > 3:
        errors.append(f"client model may contain at most three legacy semantic chart candidates; found {len(real)}")
    if story.get("semantic_candidate_chart_count") != len(real):
        errors.append("client_story.semantic_candidate_chart_count must match model visualizations")
    if canonical:
        if not 4 <= int(story.get("real_chart_count", 0)) <= 7:
            errors.append("canonical visualization plan must contain 4-7 rendered visuals")
        if story.get("target_real_charts") != "4-7" or not str(story.get("visualization_plan_source") or "").strip():
            errors.append("canonical visualization-plan binding is incomplete")
    else:
        if story.get("real_chart_count") != len(real) or story.get("target_real_charts") != "2-3":
            errors.append("legacy semantic candidate count/target drift")
    if any(v.get("template_id") == "V12" for v in values):
        errors.append("V12 evidence tables are internal trace material and must not appear in the default customer PDF model")
    if len(data.get("findings", [])) > 4:
        errors.append("customer report may contain at most four prioritized lever findings")
    if story.get("visual_story_status") != "PASS":
        errors.append("client_story.visual_story_status must be PASS before customer PDF completion")
    if story.get("technical_appendix_rendered") is not False:
        errors.append("technical appendix must not be rendered in the customer PDF")
    if story.get("max_customer_pages") != 12:
        errors.append("client_story.max_customer_pages must be 12")
    finding_ids = {str(f.get("id", "")) for f in data.get("findings", []) if isinstance(f, dict)}
    selected_ids = {str(x) for x in story.get("selected_lever_ids", [])}
    if finding_ids != selected_ids:
        errors.append("client_story selected_lever_ids must match the customer-facing findings exactly")
    jargon = CLIENT_JARGON.search(visible_text(data))
    if jargon:
        errors.append(f"untranslated customer jargon remains visible: {jargon.group(0)}")
    for viz in real:
        ev = viz.get("evidence", {}) if isinstance(viz.get("evidence"), dict) else {}
        if ev.get("mode") == "DERIVED":
            limit = str(viz.get("does_not_prove", "")).lower()
            if not any(word in limit for word in ("umsatz", "ranking", "anfragen", "erfolg")):
                errors.append(f"{viz.get('id')}: derived chart must reject business-outcome interpretation")
    return errors
