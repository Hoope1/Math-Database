import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import re
import altair as alt
from pycaret.regression import setup, compare_models, predict_model, save_model, load_model
from fpdf import FPDF
import base64
import os
from io import BytesIO

# CSS-Schriftgrößenhierarchie laden
def lade_css():
    st.markdown(
        """
        <style>
        .titel { font-size: 14px !important; font-weight: bold; color: #2e3b4e; }
        .überschrift { font-size: 12px !important; color: #4e5d6c; }
        .unterüberschrift { font-size: 10px !important; }
        .absatz { font-size: 9px !important; }
        .hinweis { font-size: 8px !important; color: gray; }
        .warnung { color: red; font-weight: bold; }
        .erfolg { color: green; font-weight: bold; }
        </style>
        """,
        unsafe_allow_html=True
    )

lade_css()

# Datenbankverbindung initialisieren
verbindung = sqlite3.connect('teilnehmer.db', check_same_thread=False)
cursor = verbindung.cursor()

# Tabellen erstellen, falls sie nicht existieren
def initialisiere_datenbank():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teilnehmer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sv_nummer TEXT NOT NULL UNIQUE,
            berufswunsch TEXT NOT NULL,
            eintrittsdatum TEXT NOT NULL,
            austrittsdatum TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS testergebnisse (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teilnehmer_id INTEGER NOT NULL,
            test_datum TEXT NOT NULL,
            textaufgaben_erreicht INTEGER,
            textaufgaben_max INTEGER,
            textaufgaben_prozent REAL,
            raumvorstellung_erreicht INTEGER,
            raumvorstellung_max INTEGER,
            raumvorstellung_prozent REAL,
            gleichungen_erreicht INTEGER,
            gleichungen_max INTEGER,
            gleichungen_prozent REAL,
            brueche_erreicht INTEGER,
            brueche_max INTEGER,
            brueche_prozent REAL,
            grundrechenarten_erreicht INTEGER,
            grundrechenarten_max INTEGER,
            grundrechenarten_prozent REAL,
            zahlenraum_erreicht INTEGER,
            zahlenraum_max INTEGER,
            zahlenraum_prozent REAL,
            gesamt_prozent REAL,
            normalisierte_kategorien TEXT,
            FOREIGN KEY (teilnehmer_id) REFERENCES teilnehmer (id)
        )
    ''')
    verbindung.commit()

initialisiere_datenbank()

# Hilfsfunktionen
def berechne_alter(sv_nummer):
    jahr = int(sv_nummer[8:10])
    jahr += 2000 if jahr <= int(datetime.now().year) % 100 else 1900
    monat = int(sv_nummer[6:8])
    tag = int(sv_nummer[4:6])
    geburtsdatum = date(jahr, monat, tag)
    heute = date.today()
    alter = heute.year - geburtsdatum.year - ((heute.month, heute.day) < (geburtsdatum.month, geburtsdatum.day))
    return alter

def ist_aktiv(austrittsdatum):
    return datetime.strptime(austrittsdatum, '%Y-%m-%d').date() >= date.today()

# Teilnehmer-Datenbankoperationen
def fuege_teilnehmer_hinzu(name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum):
    cursor.execute('''
        INSERT INTO teilnehmer (name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum))
    verbindung.commit()

def aktualisiere_teilnehmer(teilnehmer_id, name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum):
    cursor.execute('''
        UPDATE teilnehmer
        SET name = ?, sv_nummer = ?, berufswunsch = ?, eintrittsdatum = ?, austrittsdatum = ?
        WHERE id = ?
    ''', (name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum, teilnehmer_id))
    verbindung.commit()

def hole_teilnehmer():
    cursor.execute('SELECT * FROM teilnehmer')
    zeilen = cursor.fetchall()
    spalten = [beschreibung[0] for beschreibung in cursor.description]
    return pd.DataFrame(zeilen, columns=spalten)

def hole_teilnehmer_nach_id(teilnehmer_id):
    cursor.execute('SELECT * FROM teilnehmer WHERE id = ?', (teilnehmer_id,))
    return cursor.fetchone()

# Testergebnis-Datenbankoperationen
def fuege_testergebnis_hinzu(teilnehmer_id, test_datum, ergebnisse):
    cursor.execute('''
        INSERT INTO testergebnisse (
            teilnehmer_id, test_datum,
            textaufgaben_erreicht, textaufgaben_max, textaufgaben_prozent,
            raumvorstellung_erreicht, raumvorstellung_max, raumvorstellung_prozent,
            gleichungen_erreicht, gleichungen_max, gleichungen_prozent,
            brueche_erreicht, brueche_max, brueche_prozent,
            grundrechenarten_erreicht, grundrechenarten_max, grundrechenarten_prozent,
            zahlenraum_erreicht, zahlenraum_max, zahlenraum_prozent,
            gesamt_prozent, normalisierte_kategorien
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        teilnehmer_id, test_datum,
        ergebnisse['Textaufgaben']['erreicht'], ergebnisse['Textaufgaben']['max'], ergebnisse['Textaufgaben']['prozent'],
        ergebnisse['Raumvorstellung']['erreicht'], ergebnisse['Raumvorstellung']['max'], ergebnisse['Raumvorstellung']['prozent'],
        ergebnisse['Gleichungen']['erreicht'], ergebnisse['Gleichungen']['max'], ergebnisse['Gleichungen']['prozent'],
        ergebnisse['Brüche']['erreicht'], ergebnisse['Brüche']['max'], ergebnisse['Brüche']['prozent'],
        ergebnisse['Grundrechenarten']['erreicht'], ergebnisse['Grundrechenarten']['max'], ergebnisse['Grundrechenarten']['prozent'],
        ergebnisse['Zahlenraum']['erreicht'], ergebnisse['Zahlenraum']['max'], ergebnisse['Zahlenraum']['prozent'],
        ergebnisse['gesamt_prozent'], ergebnisse['normalisierte_kategorien']
    ))
    verbindung.commit()

def hole_testergebnisse(teilnehmer_id):
    cursor.execute('''
        SELECT * FROM testergebnisse
        WHERE teilnehmer_id = ?
    ''', (teilnehmer_id,))
    zeilen = cursor.fetchall()
    spalten = [beschreibung[0] for beschreibung in cursor.description]
    return pd.DataFrame(zeilen, columns=spalten)

def hole_alle_testergebnisse():
    cursor.execute('SELECT * FROM testergebnisse')
    zeilen = cursor.fetchall()
    spalten = [beschreibung[0] for beschreibung in cursor.description]
    return pd.DataFrame(zeilen, columns=spalten)
# Modelltraining und Prognose mit PyCaret
def trainiere_modell():
    """
    Trainiert ein Prognosemodell mit PyCaret und speichert es zur Wiederverwendung.
    """
    tests_df = hole_alle_testergebnisse()
    if tests_df.empty or len(tests_df) < 10:
        st.warning("Nicht genügend Daten für Modelltraining. Mindestens 10 Datensätze erforderlich.")
        return None

    daten = tests_df[[
        'textaufgaben_prozent',
        'raumvorstellung_prozent',
        'gleichungen_prozent',
        'brueche_prozent',
        'grundrechenarten_prozent',
        'zahlenraum_prozent',
        'gesamt_prozent'
    ]].dropna()
    reg = setup(data=daten, target='gesamt_prozent', silent=True, session_id=123)
    bestes_modell = compare_models()
    save_model(bestes_modell, 'bestes_prognose_modell')
    return bestes_modell

def lade_modell():
    """
    Lädt ein gespeichertes Modell. Wenn kein Modell existiert, wird ein neues trainiert.
    """
    try:
        modell = load_model('bestes_prognose_modell')
    except FileNotFoundError:
        st.warning("Kein gespeichertes Modell gefunden. Ein neues Modell wird trainiert.")
        modell = trainiere_modell()
    return modell

def erstelle_prognose(teilnehmer_id):
    """
    Erstellt eine Prognose basierend auf den letzten Testergebnissen eines Teilnehmers.
    """
    testergebnisse = hole_testergebnisse(teilnehmer_id)
    if testergebnisse.empty:
        st.warning("Keine Testergebnisse für diesen Teilnehmer verfügbar.")
        return None

    modell = lade_modell()
    if modell is None:
        st.error("Das Modell konnte nicht geladen werden.")
        return None

    daten = testergebnisse.copy()
    daten['test_datum'] = pd.to_datetime(daten['test_datum'])
    daten.sort_values('test_datum', inplace=True)

    merkmale = [
        'textaufgaben_prozent',
        'raumvorstellung_prozent',
        'gleichungen_prozent',
        'brueche_prozent',
        'grundrechenarten_prozent',
        'zahlenraum_prozent'
    ]

    zukunft_tage = pd.date_range(start=date.today(), periods=31)
    zukunft_daten = pd.DataFrame({'Tag': (zukunft_tage - date.today()).days})
    for merkmal in merkmale:
        letzter_wert = daten[merkmal].iloc[-1]
        zukunft_daten[merkmal] = letzter_wert

    try:
        prognose = predict_model(modell, data=zukunft_daten)
        zukunft_daten['prognose_gesamt_prozent'] = prognose['Label']
        return zukunft_daten
    except Exception as e:
        st.error(f"Fehler bei der Prognoseerstellung: {e}")
        return None

# Diagramm speichern
def speichere_prognose_diagramm(prognose_daten):
    """
    Speichert ein Prognosediagramm als PNG-Datei zur Einbettung in Berichte.
    """
    chart = alt.Chart(prognose_daten).mark_line().encode(
        x=alt.X('Tag', title='Tage'),
        y=alt.Y('prognose_gesamt_prozent', title='Gesamtprozent'),
        tooltip=['Tag', 'prognose_gesamt_prozent']
    ).properties(
        title="Prognose über 30 Tage"
    )
    buffer = BytesIO()
    chart.save(buffer, format='png')
    buffer.seek(0)
    return buffer

# PDF-Berichterstellung
def erstelle_pdf(teilnehmer, testergebnisse, mittelwert, diagramm_buffer=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Bericht für {teilnehmer[1]}", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Name: {teilnehmer[1]}", ln=True)
    pdf.cell(0, 10, f"SV-Nummer: {teilnehmer[2]}", ln=True)
    pdf.cell(0, 10, f"Berufswunsch: {teilnehmer[3]}", ln=True)
    pdf.cell(0, 10, f"Eintrittsdatum: {teilnehmer[4]}", ln=True)
    pdf.cell(0, 10, f"Austrittsdatum: {teilnehmer[5]}", ln=True)
    pdf.cell(0, 10, f"Durchschnitt der letzten zwei Tests: {mittelwert:.2f}%", ln=True)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Testergebnisse:", ln=True)
    pdf.set_font("Arial", '', 10)
    for index, reihe in testergebnisse.iterrows():
        pdf.cell(0, 10, f"Testdatum: {reihe['test_datum']}, Gesamtprozent: {reihe['gesamt_prozent']:.2f}%", ln=True)
    if diagramm_buffer:
        pdf.add_page()
        pdf.image(diagramm_buffer, x=10, y=20, w=pdf.w - 20)
    dateiname = f"{teilnehmer[1]}-Bericht.pdf"
    pdf.output(dateiname)
    return dateiname

# Excel-Berichterstellung
def erstelle_excel(teilnehmer, testergebnisse, mittelwert):
    dateiname = f"{teilnehmer[1]}-Bericht.xlsx"
    with pd.ExcelWriter(dateiname) as writer:
        testergebnisse.to_excel(writer, sheet_name='Testergebnisse', index=False)
        df_mittelwert = pd.DataFrame({'Durchschnitt der letzten zwei Tests': [mittelwert]})
        df_mittelwert.to_excel(writer, sheet_name='Zusammenfassung', index=False)
    return dateiname
