# tests.py
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# Datenbankverbindung
verbindung = sqlite3.connect('data/mathematik_kurs.db', check_same_thread=False)
cursor = verbindung.cursor()

# Tabelle für Testergebnisse initialisieren
cursor.execute('''
CREATE TABLE IF NOT EXISTS testergebnisse (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teilnehmer_id INTEGER NOT NULL,
    test_datum TEXT NOT NULL,
    textaufgaben_erreicht INTEGER NOT NULL,
    textaufgaben_max INTEGER NOT NULL,
    raumvorstellung_erreicht INTEGER NOT NULL,
    raumvorstellung_max INTEGER NOT NULL,
    gleichungen_erreicht INTEGER NOT NULL,
    gleichungen_max INTEGER NOT NULL,
    brueche_erreicht INTEGER NOT NULL,
    brueche_max INTEGER NOT NULL,
    grundrechenarten_erreicht INTEGER NOT NULL,
    grundrechenarten_max INTEGER NOT NULL,
    zahlenraum_erreicht INTEGER NOT NULL,
    zahlenraum_max INTEGER NOT NULL,
    gesamt_prozent REAL NOT NULL,
    FOREIGN KEY (teilnehmer_id) REFERENCES teilnehmer (id)
)
''')
verbindung.commit()

# Hilfsfunktionen
def berechne_prozent(erreichte_punkte, maximale_punkte):
    """Berechnet den Prozentwert einer Kategorie."""
    return (erreichte_punkte / maximale_punkte) * 100 if maximale_punkte > 0 else 0

def fuege_testergebnis_hinzu(teilnehmer_id, test_datum, ergebnisse):
    """Speichert ein Testergebnis in der Datenbank."""
    cursor.execute('''
    INSERT INTO testergebnisse (
        teilnehmer_id, test_datum,
        textaufgaben_erreicht, textaufgaben_max,
        raumvorstellung_erreicht, raumvorstellung_max,
        gleichungen_erreicht, gleichungen_max,
        brueche_erreicht, brueche_max,
        grundrechenarten_erreicht, grundrechenarten_max,
        zahlenraum_erreicht, zahlenraum_max,
        gesamt_prozent
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        teilnehmer_id, test_datum,
        ergebnisse['Textaufgaben']['erreicht'], ergebnisse['Textaufgaben']['max'],
        ergebnisse['Raumvorstellung']['erreicht'], ergebnisse['Raumvorstellung']['max'],
        ergebnisse['Gleichungen']['erreicht'], ergebnisse['Gleichungen']['max'],
        ergebnisse['Brüche']['erreicht'], ergebnisse['Brüche']['max'],
        ergebnisse['Grundrechenarten']['erreicht'], ergebnisse['Grundrechenarten']['max'],
        ergebnisse['Zahlenraum']['erreicht'], ergebnisse['Zahlenraum']['max'],
        ergebnisse['gesamt_prozent']
    ))
    verbindung.commit()

# Testverwaltung
def testverwaltung():
    st.header("Testverwaltung")

    # Teilnehmerdaten abrufen
    teilnehmer_df = pd.read_sql_query('SELECT id, name FROM teilnehmer', verbindung)
    if teilnehmer_df.empty:
        st.warning("Keine Teilnehmer vorhanden. Bitte zuerst Teilnehmer hinzufügen.")
        return

    # Teilnehmer auswählen
    teilnehmer_df['Auswahl'] = teilnehmer_df.apply(lambda x: f"{x['name']} (ID: {x['id']})", axis=1)
    ausgewaehlter = st.selectbox("Teilnehmer auswählen", teilnehmer_df['Auswahl'])
    teilnehmer_id = int(ausgewaehlter.split("ID: ")[1].strip(')'))
    st.subheader(f"Testergebnisse für {teilnehmer_df[teilnehmer_df['id'] == teilnehmer_id]['name'].values[0]}")

    # Testdaten eingeben
    test_datum = st.date_input("Testdatum", date.today())
    kategorien = ["Textaufgaben", "Raumvorstellung", "Gleichungen", "Brüche", "Grundrechenarten", "Zahlenraum"]
    ergebnisse = {}
    total_max_punkte = 0
    gesamt_erreichte_punkte = 0

    for kategorie in kategorien:
        st.markdown(f"### {kategorie}")
        erreicht = st.number_input(f"{kategorie} - Erreichte Punkte", min_value=0, value=0, key=f"{kategorie}_erreicht")
        max_punkte = st.number_input(f"{kategorie} - Maximale Punkte", min_value=1, value=1, key=f"{kategorie}_max")
        total_max_punkte += max_punkte
        gesamt_erreichte_punkte += erreicht
        ergebnisse[kategorie] = {'erreicht': erreicht, 'max': max_punkte}

    # Validierung der Punktesumme
    if total_max_punkte != 100:
        st.error("Die Summe der maximalen Punkte aller Kategorien muss genau 100 betragen.")
        return

    # Ergebnisse speichern
    if st.button("Testergebnis hinzufügen"):
        gesamt_prozent = berechne_prozent(gesamt_erreichte_punkte, total_max_punkte)
        ergebnisse['gesamt_prozent'] = gesamt_prozent
        fuege_testergebnis_hinzu(teilnehmer_id, test_datum.strftime('%Y-%m-%d'), ergebnisse)
        st.success("Testergebnis erfolgreich hinzugefügt!")

    # Vorhandene Testergebnisse anzeigen
    st.subheader("Vorhandene Testergebnisse")
    testergebnisse_df = pd.read_sql_query(f'SELECT * FROM testergebnisse WHERE teilnehmer_id = {teilnehmer_id}', verbindung)
    if not testergebnisse_df.empty:
        testergebnisse_df['Testdatum'] = pd.to_datetime(testergebnisse_df['test_datum']).dt.strftime('%d.%m.%Y')
        st.dataframe(testergebnisse_df[["Testdatum", "gesamt_prozent"]])
    else:
        st.info("Keine Testergebnisse vorhanden.")
