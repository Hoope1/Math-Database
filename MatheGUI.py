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
        .titel { font-size: 14px !important; font-weight: bold; }
        .überschrift { font-size: 12px !important; }
        .unterüberschrift { font-size: 10px !important; }
        .absatz { font-size: 9px !important; }
        .hinweis { font-size: 8px !important; color: gray; }
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
    # Teilnehmer-Tabelle
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
    # Testergebnisse-Tabelle
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
    """Berechnet das Alter basierend auf der SV-Nummer."""
    jahr = int(sv_nummer[8:10])
    jahr += 2000 if jahr <= int(datetime.now().year) % 100 else 1900
    monat = int(sv_nummer[6:8])
    tag = int(sv_nummer[4:6])
    geburtsdatum = date(jahr, monat, tag)
    heute = date.today()
    alter = heute.year - geburtsdatum.year - ((heute.month, heute.day) < (geburtsdatum.month, geburtsdatum.day))
    return alter

def ist_aktiv(austrittsdatum):
    """Prüft, ob ein Teilnehmer noch aktiv ist."""
    return datetime.strptime(austrittsdatum, '%Y-%m-%d').date() >= date.today()

# Datenbankoperationen
def fuege_teilnehmer_hinzu(name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum):
    """Fügt einen neuen Teilnehmer zur Datenbank hinzu."""
    cursor.execute('''
        INSERT INTO teilnehmer (name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum))
    verbindung.commit()

def aktualisiere_teilnehmer(teilnehmer_id, name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum):
    """Aktualisiert die Daten eines bestehenden Teilnehmers."""
    cursor.execute('''
        UPDATE teilnehmer
        SET name = ?, sv_nummer = ?, berufswunsch = ?, eintrittsdatum = ?, austrittsdatum = ?
        WHERE id = ?
    ''', (name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum, teilnehmer_id))
    verbindung.commit()

def hole_teilnehmer():
    """Holt alle Teilnehmer aus der Datenbank."""
    cursor.execute('SELECT * FROM teilnehmer')
    zeilen = cursor.fetchall()
    spalten = [beschreibung[0] for beschreibung in cursor.description]
    return pd.DataFrame(zeilen, columns=spalten)

def hole_teilnehmer_nach_id(teilnehmer_id):
    """Holt einen Teilnehmer nach ID."""
    cursor.execute('SELECT * FROM teilnehmer WHERE id = ?', (teilnehmer_id,))
    return cursor.fetchone()

def fuege_testergebnis_hinzu(teilnehmer_id, test_datum, ergebnisse):
    """Fügt ein Testergebnis für einen Teilnehmer hinzu."""
    cursor.execute('''
        INSERT INTO testergebnisse (
            teilnehmer_id, test_datum,
            textaufgaben_erreicht, textaufgaben_max, textaufgaben_prozent,
            raumvorstellung_erreicht, raumvorstellung_max, raumvorstellung_prozent,
            gleichungen_erreicht, gleichungen_max, gleichungen_prozent,
            brueche_erreicht, brueche_max, brueche_prozent,
            grundrechenarten_erreicht, grundrechenarten_max, grundrechenarten_prozent,
            zahlenraum_erreicht, zahlenraum_max, zahlenraum_prozent,
            gesamt_prozent,
            normalisierte_kategorien
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
        ergebnisse['gesamt_prozent'],
        ergebnisse['normalisierte_kategorien']
    ))
    verbindung.commit()

def hole_testergebnisse(teilnehmer_id):
    """Holt alle Testergebnisse eines Teilnehmers."""
    cursor.execute('''
        SELECT * FROM testergebnisse
        WHERE teilnehmer_id = ?
    ''', (teilnehmer_id,))
    zeilen = cursor.fetchall()
    spalten = [beschreibung[0] for beschreibung in cursor.description]
    return pd.DataFrame(zeilen, columns=spalten)

def hole_alle_testergebnisse():
    """Holt alle Testergebnisse aus der Datenbank."""
    cursor.execute('SELECT * FROM testergebnisse')
    zeilen = cursor.fetchall()
    spalten = [beschreibung[0] for beschreibung in cursor.description]
    return pd.DataFrame(zeilen, columns=spalten)
    # Streamlit App Layout
st.title("Mathematik-Kurs Teilnehmerverwaltung")

# Teilnehmerübersicht im oberen Teil
st.header("Teilnehmerübersicht")

def markiere_inaktive(zeile):
    """Markiert inaktive Teilnehmer grau."""
    if zeile['Status'] == 'Inaktiv':
        return ['color: grey'] * len(zeile)
    else:
        return [''] * len(zeile)

def lade_teilnehmer():
    """Lädt alle Teilnehmer aus der Datenbank."""
    teilnehmer_df = hole_teilnehmer()
    if not teilnehmer_df.empty:
        teilnehmer_df['Alter'] = teilnehmer_df['sv_nummer'].apply(berechne_alter)
        teilnehmer_df['Status'] = teilnehmer_df['austrittsdatum'].apply(lambda x: 'Aktiv' if ist_aktiv(x) else 'Inaktiv')
        anzeige_df = teilnehmer_df[['name', 'Alter', 'berufswunsch', 'eintrittsdatum', 'austrittsdatum', 'Status']]
        anzeige_df.columns = ['Name', 'Alter', 'Berufswunsch', 'Eintrittsdatum', 'Austrittsdatum', 'Status']
        return anzeige_df
    else:
        return pd.DataFrame()

# Teilnehmerübersicht anzeigen
anzeige_df = lade_teilnehmer()
if not anzeige_df.empty:
    # Ein- und Ausblenden von inaktiven Teilnehmern
    zeige_inaktive = st.checkbox("Inaktive Teilnehmer anzeigen", value=False)
    if not zeige_inaktive:
        anzeige_df = anzeige_df[anzeige_df['Status'] == 'Aktiv']
    
    # Sortier- und Filterfunktionen
    st.dataframe(anzeige_df.style.apply(markiere_inaktive, axis=1), use_container_width=True)
else:
    st.write("Keine Teilnehmer vorhanden.")

# Tabs für verschiedene Bereiche
tabs = st.tabs(["Teilnehmerverwaltung", "Testverwaltung", "Prognose-System", "Berichtswesen"])

# Teilnehmerverwaltung
with tabs[0]:
    st.header("Teilnehmerverwaltung")
    # Teilnehmerliste aktualisieren
    teilnehmer_df = hole_teilnehmer()
    teilnehmer_optionen = ["Neuen Teilnehmer hinzufügen"] + teilnehmer_df['name'].tolist()
    ausgewaehlter_teilnehmer = st.selectbox("Teilnehmer auswählen", teilnehmer_optionen, key='teilnehmer_auswahl')
    
    if ausgewaehlter_teilnehmer == "Neuen Teilnehmer hinzufügen":
        st.subheader("Neuen Teilnehmer hinzufügen")
        name = st.text_input("Name", key='name_neu')
        sv_nummer = st.text_input("SV-Nummer (XXXXDDMMYY)", key='sv_nummer_neu')
        berufswunsch = st.text_input("Berufswunsch (GROSSBUCHSTABEN)", key='berufswunsch_neu')
        eintrittsdatum = st.date_input("Eintrittsdatum", date.today(), key='eintritt_neu')
        austrittsdatum = st.date_input("Austrittsdatum", date.today(), key='austritt_neu')

        if st.button("Teilnehmer hinzufügen"):
            if not re.match(r'^\d{10}$', sv_nummer):
                st.error("SV-Nummer muss aus genau 10 Ziffern bestehen.")
            elif not berufswunsch.isupper():
                st.error("Berufswunsch muss in GROSSBUCHSTABEN eingegeben werden.")
            else:
                fuege_teilnehmer_hinzu(
                    name, sv_nummer, berufswunsch,
                    eintrittsdatum.strftime('%Y-%m-%d'),
                    austrittsdatum.strftime('%Y-%m-%d')
                )
                st.success("Teilnehmer erfolgreich hinzugefügt.")
    else:
        st.subheader("Teilnehmer bearbeiten")
        teilnehmer_reihe = teilnehmer_df[teilnehmer_df['name'] == ausgewaehlter_teilnehmer].iloc[0]
        teilnehmer_id = teilnehmer_reihe['id']
        name = st.text_input("Name", teilnehmer_reihe['name'], key='name_bearbeiten')
        sv_nummer = st.text_input("SV-Nummer (XXXXDDMMYY)", teilnehmer_reihe['sv_nummer'], key='sv_nummer_bearbeiten')
        berufswunsch = st.text_input("Berufswunsch (GROSSBUCHSTABEN)", teilnehmer_reihe['berufswunsch'], key='berufswunsch_bearbeiten')
        eintrittsdatum = st.date_input("Eintrittsdatum", datetime.strptime(teilnehmer_reihe['eintrittsdatum'], '%Y-%m-%d'), key='eintritt_bearbeiten')
        austrittsdatum = st.date_input("Austrittsdatum", datetime.strptime(teilnehmer_reihe['austrittsdatum'], '%Y-%m-%d'), key='austritt_bearbeiten')

        if st.button("Teilnehmerdaten aktualisieren"):
            if not re.match(r'^\d{10}$', sv_nummer):
                st.error("SV-Nummer muss aus genau 10 Ziffern bestehen.")
            elif not berufswunsch.isupper():
                st.error("Berufswunsch muss in GROSSBUCHSTABEN eingegeben werden.")
            else:
                aktualisiere_teilnehmer(
                    teilnehmer_id, name, sv_nummer, berufswunsch,
                    eintrittsdatum.strftime('%Y-%m-%d'),
                    austrittsdatum.strftime('%Y-%m-%d')
                )
                st.success("Teilnehmerdaten erfolgreich aktualisiert.")

# Testverwaltung
with tabs[1]:
    st.header("Testverwaltung")
    # Teilnehmerliste aktualisieren
    teilnehmer_df = hole_teilnehmer()
    if not teilnehmer_df.empty:
        teilnehmer_df['auswahl'] = teilnehmer_df.apply(lambda reihe: f"{reihe['name']} (ID: {reihe['id']})", axis=1)
        ausgewaehlte_option = st.selectbox("Teilnehmer auswählen", teilnehmer_df['auswahl'], key='testverwaltung_teilnehmer')
        teilnehmer_id = int(ausgewaehlte_option.split("ID: ")[1].strip(')'))
        name = teilnehmer_df[teilnehmer_df['id'] == teilnehmer_id]['name'].values[0]
        
        st.subheader(f"Testergebnis für {name} hinzufügen")
        
        test_datum = st.date_input("Testdatum", date.today(), key='test_datum')
        
        kategorien = ["Textaufgaben", "Raumvorstellung", "Gleichungen", "Brüche", "Grundrechenarten", "Zahlenraum"]
        ergebnisse = {}
        
        total_max_punkte = 0
        st.markdown("<div class='unterüberschrift'>Punkteingabe für die Kategorien:</div>", unsafe_allow_html=True)
        for kategorie in kategorien:
            st.markdown(f"<div class='absatz'><strong>{kategorie}</strong></div>", unsafe_allow_html=True)
            erreicht = st.number_input(f"{kategorie} - Erreichte Punkte", min_value=0, value=0, key=f"{kategorie}_erreicht")
            max_punkte = st.number_input(f"{kategorie} - Maximale Punkte", min_value=1, value=1, key=f"{kategorie}_max")
            total_max_punkte += max_punkte
            ergebnisse[kategorie] = {'erreicht': erreicht, 'max': max_punkte}
        
        if total_max_punkte != 100:
            st.error("Die Summe der maximalen Punkte aller Kategorien muss genau 100 sein.")
        else:
            if st.button("Testergebnis hinzufügen"):
                # Prozentwerte berechnen
                gesamt_erreicht = 0
                normalisierte_kategorien = {}
                for kategorie in kategorien:
                    erreicht = ergebnisse[kategorie]['erreicht']
                    max_punkte = ergebnisse[kategorie]['max']
                    prozent = (erreicht / max_punkte) * 100 if max_punkte > 0 else 0
                    ergebnisse[kategorie]['prozent'] = prozent
                    gesamt_erreicht += erreicht
                    # Normalisierung der Kategoriewerte (Beispiel: Skalierung zwischen 0 und 1)
                    normalisierte_kategorien[kategorie] = prozent / 100
                    
                ergebnisse['gesamt_prozent'] = (gesamt_erreicht / total_max_punkte) * 100 if total_max_punkte > 0 else 0
                ergebnisse['normalisierte_kategorien'] = str(normalisierte_kategorien)
                
                fuege_testergebnis_hinzu(teilnehmer_id, test_datum.strftime('%Y-%m-%d'), ergebnisse)
                st.success("Testergebnis erfolgreich hinzugefügt.")
                
                # Modell automatisch aktualisieren
                trainiere_modell()
    else:
        st.warning("Es sind keine Teilnehmer vorhanden. Bitte fügen Sie zuerst Teilnehmer hinzu.")

# Modelltraining mit PyCaret
def trainiere_modell():
    """Trainiert das Prognosemodell mit PyCaret und ermöglicht inkrementelles Lernen."""
    tests_df = hole_alle_testergebnisse()
    if tests_df.empty:
        st.write("Nicht genügend Daten zum Trainieren des Modells.")
        return None
    # Nur relevante Spalten verwenden
    daten = tests_df[[
        'textaufgaben_prozent',
        'raumvorstellung_prozent',
        'gleichungen_prozent',
        'brueche_prozent',
        'grundrechenarten_prozent',
        'zahlenraum_prozent',
        'gesamt_prozent'
    ]]
    reg = setup(data=daten, target='gesamt_prozent', silent=True, session_id=123)
    bestes_modell = compare_models()
    save_model(bestes_modell, 'bestes_prognose_modell')
    return bestes_modell

def lade_modell():
    """Lädt das trainierte Prognosemodell."""
    try:
        modell = load_model('bestes_prognose_modell')
    except:
        modell = trainiere_modell()
    return modell

# Prognose-System
with tabs[2]:
    st.header("Prognose-System")
    # Teilnehmerliste aktualisieren
    teilnehmer_df = hole_teilnehmer()
    if not teilnehmer_df.empty:
        teilnehmer_df['auswahl'] = teilnehmer_df.apply(lambda reihe: f"{reihe['name']} (ID: {reihe['id']})", axis=1)
        ausgewaehlte_option = st.selectbox("Teilnehmer auswählen", teilnehmer_df['auswahl'], key='prognose_teilnehmer')
        teilnehmer_id = int(ausgewaehlte_option.split("ID: ")[1].strip(')'))
        name = teilnehmer_df[teilnehmer_df['id'] == teilnehmer_id]['name'].values[0]

        st.subheader(f"Prognose für {name}")

        if st.button("Prognosediagramm anzeigen"):
            testergebnisse = hole_testergebnisse(teilnehmer_id)
            if testergebnisse.empty:
                st.warning("Keine Testergebnisse für diesen Teilnehmer.")
            else:
                # Modell laden
                modell = lade_modell()
                # Prognose erstellen
                daten = testergebnisse.copy()
                daten['test_datum'] = pd.to_datetime(daten['test_datum'])
                daten.sort_values('test_datum', inplace=True)

                # Merkmale für Prognose
                merkmale = [
                    'textaufgaben_prozent',
                    'raumvorstellung_prozent',
                    'gleichungen_prozent',
                    'brueche_prozent',
                    'grundrechenarten_prozent',
                    'zahlenraum_prozent'
                ]

                # Prognose für die nächsten 30 Tage
                zukunft_tage = pd.date_range(start=date.today(), periods=31)
                zukunft_daten = pd.DataFrame({
                    'Tag': (zukunft_tage - date.today()).days,
                    'textaufgaben_prozent': daten['textaufgaben_prozent'].iloc[-1],
                    'raumvorstellung_prozent': daten['raumvorstellung_prozent'].iloc[-1],
                    'gleichungen_prozent': daten['gleichungen_prozent'].iloc[-1],
                    'brueche_prozent': daten['brueche_prozent'].iloc[-1],
                    'grundrechenarten_prozent': daten['grundrechenarten_prozent'].iloc[-1],
                    'zahlenraum_prozent': daten['zahlenraum_prozent'].iloc[-1]
                })

                prognose = predict_model(modell, data=zukunft_daten[merkmale])
                zukunft_daten['prognose_gesamt_prozent'] = prognose['Label']

                # Historische Daten der letzten 30 Tage
                daten['Tag'] = (daten['test_datum'] - pd.Timestamp(date.today())).dt.days
                vergangenheit_daten = daten[daten['Tag'] >= -30]

                # Zusammenführen von Vergangenheit und Zukunft
                gesamtdaten = pd.concat([vergangenheit_daten, zukunft_daten], ignore_index=True)

                # Daten für Altair vorbereiten
                df_melted = pd.melt(
                    gesamtdaten,
                    id_vars=['Tag'],
                    value_vars=[
                        'gesamt_prozent',
                        'prognose_gesamt_prozent',
                        'textaufgaben_prozent',
                        'raumvorstellung_prozent',
                        'gleichungen_prozent',
                        'brueche_prozent',
                        'grundrechenarten_prozent',
                        'zahlenraum_prozent'
                    ],
                    var_name='Kategorie',
                    value_name='Prozent'
                )

                # Kategorienamen anpassen
                kategorie_mapping = {
                    'gesamt_prozent': 'Gesamtfortschritt',
                    'prognose_gesamt_prozent': 'Prognose Gesamtfortschritt',
                    'textaufgaben_prozent': 'Textaufgaben',
                    'raumvorstellung_prozent': 'Raumvorstellung',
                    'gleichungen_prozent': 'Gleichungen',
                    'brueche_prozent': 'Brüche',
                    'grundrechenarten_prozent': 'Grundrechenarten',
                    'zahlenraum_prozent': 'Zahlenraum'
                }
                df_melted['Kategorie'] = df_melted['Kategorie'].map(kategorie_mapping)

                # Interaktive Elementauswahl
                kategorien_optionen = [
                    'Gesamtfortschritt',
                    'Prognose Gesamtfortschritt',
                    'Textaufgaben',
                    'Raumvorstellung',
                    'Gleichungen',
                    'Brüche',
                    'Grundrechenarten',
                    'Zahlenraum'
                ]
                ausgewaehlte_kategorien = st.multiselect(
                    "Kategorien auswählen",
                    kategorien_optionen,
                    default=['Gesamtfortschritt', 'Prognose Gesamtfortschritt']
                )

                # Farben und Linienstile definieren
                farben = {
                    'Gesamtfortschritt': 'black',
                    'Prognose Gesamtfortschritt': 'black',
                    'Textaufgaben': 'red',
                    'Raumvorstellung': 'blue',
                    'Gleichungen': 'green',
                    'Brüche': 'purple',
                    'Grundrechenarten': 'orange',
                    'Zahlenraum': 'brown'
                }
                linienstile = {
                    'Gesamtfortschritt': [],
                    'Prognose Gesamtfortschritt': [5, 5],
                    'Textaufgaben': [5, 5],
                    'Raumvorstellung': [5, 5],
                    'Gleichungen': [5, 5],
                    'Brüche': [5, 5],
                    'Grundrechenarten': [5, 5],
                    'Zahlenraum': [5, 5]
                }

                # Daten filtern
                df_melted = df_melted[df_melted['Kategorie'].isin(ausgewaehlte_kategorien)]

                # Diagramm erstellen
                linien = []
                for kategorie in ausgewaehlte_kategorien:
                    daten_kategorie = df_melted[df_melted['Kategorie'] == kategorie]
                    linie = alt.Chart(daten_kategorie).mark_line(
                        color=farben[kategorie],
                        strokeDash=linienstile[kategorie]
                    ).encode(
                        x=alt.X('Tag', scale=alt.Scale(domain=[-30, 30]), title='Tage'),
                        y=alt.Y('Prozent', scale=alt.Scale(domain=[0, 100]), title='Prozent'),
                        tooltip=['Tag', 'Prozent']
                    )
                    linien.append(linie)

                chart = alt.layer(*linien).properties(
                    width=700,
                    height=400,
                    title='Prognose über 60 Tage (-30 bis +30 Tage)'
                )
                st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("Es sind keine Teilnehmer vorhanden.")

# Berichtswesen
with tabs[3]:
    st.header("Berichtswesen")
    teilnehmer_df = hole_teilnehmer()
    if not teilnehmer_df.empty:
        teilnehmer_df['auswahl'] = teilnehmer_df.apply(lambda reihe: f"{reihe['name']} (ID: {reihe['id']})", axis=1)
        ausgewaehlte_option = st.selectbox("Teilnehmer auswählen", teilnehmer_df['auswahl'], key='bericht_teilnehmer')
        teilnehmer_id = int(ausgewaehlte_option.split("ID: ")[1].strip(')'))
        name = teilnehmer_df[teilnehmer_df['id'] == teilnehmer_id]['name'].values[0]

        st.subheader(f"Bericht für {name} erstellen")

        if st.button("Bericht generieren"):
            # Teilnehmerdaten abrufen
            teilnehmer = hole_teilnehmer_nach_id(teilnehmer_id)
            testergebnisse = hole_testergebnisse(teilnehmer_id)
            if testergebnisse.empty:
                st.warning("Keine Testergebnisse für diesen Teilnehmer.")
            else:
                # Durchschnitt der letzten zwei Tests berechnen
                letzte_zwei = testergebnisse.sort_values(by='test_datum', ascending=False).head(2)
                mittelwert = letzte_zwei['gesamt_prozent'].mean()

                # Prognosediagramm erstellen und als Bild speichern
                def speichere_prognose_diagramm(teilnehmer_id):
                    # Prognosedaten vorbereiten (gleiche Logik wie im Prognose-System)
                    testergebnisse = hole_testergebnisse(teilnehmer_id)
                    if testergebnisse.empty:
                        return None
                    modell = lade_modell()
                    daten = testergebnisse.copy()
                    daten['test_datum'] = pd.to_datetime(daten['test_datum'])
                    daten.sort_values('test_datum', inplace=True)

                    # Merkmale für Prognose
                    merkmale = [
                        'textaufgaben_prozent',
                        'raumvorstellung_prozent',
                        'gleichungen_prozent',
                        'brueche_prozent',
                        'grundrechenarten_prozent',
                        'zahlenraum_prozent'
                    ]

                    # Prognose für die nächsten 30 Tage
                    zukunft_tage = pd.date_range(start=date.today(), periods=31)
                    zukunft_daten = pd.DataFrame({
                        'Tag': (zukunft_tage - date.today()).days,
                        'textaufgaben_prozent': daten['textaufgaben_prozent'].iloc[-1],
                        'raumvorstellung_prozent': daten['raumvorstellung_prozent'].iloc[-1],
                        'gleichungen_prozent': daten['gleichungen_prozent'].iloc[-1],
                        'brueche_prozent': daten['brueche_prozent'].iloc[-1],
                        'grundrechenarten_prozent': daten['grundrechenarten_prozent'].iloc[-1],
                        'zahlenraum_prozent': daten['zahlenraum_prozent'].iloc[-1]
                    })

                    prognose = predict_model(modell, data=zukunft_daten[merkmale])
                    zukunft_daten['prognose_gesamt_prozent'] = prognose['Label']

                    # Historische Daten der letzten 30 Tage
                    daten['Tag'] = (daten['test_datum'] - pd.Timestamp(date.today())).dt.days
                    vergangenheit_daten = daten[daten['Tag'] >= -30]

                    # Zusammenführen von Vergangenheit und Zukunft
                    gesamtdaten = pd.concat([vergangenheit_daten, zukunft_daten], ignore_index=True)

                    # Daten für Altair vorbereiten
                    df_melted = pd.melt(
                        gesamtdaten,
                        id_vars=['Tag'],
                        value_vars=[
                            'gesamt_prozent',
                            'prognose_gesamt_prozent'
                        ],
                        var_name='Kategorie',
                        value_name='Prozent'
                    )

                    # Diagramm erstellen
                    chart = alt.Chart(df_melted).mark_line().encode(
                        x=alt.X('Tag', scale=alt.Scale(domain=[-30, 30]), title='Tage'),
                        y=alt.Y('Prozent', scale=alt.Scale(domain=[0, 100]), title='Prozent'),
                        color=alt.Color('Kategorie', legend=alt.Legend(title="Kategorie")),
                        strokeDash=alt.condition(
                            alt.datum.Kategorie == 'prognose_gesamt_prozent',
                            alt.value([5, 5]),
                            alt.value([])
                        )
                    ).properties(
                        width=600,
                        height=300,
                        title='Prognose über 60 Tage (-30 bis +30 Tage)'
                    )

                    # Chart als PNG speichern
                    buffer = BytesIO()
                    chart.save(buffer, format='png')
                    buffer.seek(0)
                    return buffer

                diagramm_buffer = speichere_prognose_diagramm(teilnehmer_id)

                # PDF-Bericht erstellen
                def erstelle_pdf(teilnehmer, testergebnisse, mittelwert, diagramm_buffer):
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

                    pdf.cell(0, 10, "", ln=True)  # Leerzeile
                    pdf.set_font("Arial", 'B', 14)
                    pdf.cell(0, 10, "Testergebnisse:", ln=True)

                    pdf.set_font("Arial", '', 10)
                    # Testergebnisse als Tabelle hinzufügen
                    for index, reihe in testergebnisse.iterrows():
                        pdf.cell(0, 10, f"Testdatum: {reihe['test_datum']}", ln=True)
                        pdf.cell(0, 10, f"Gesamtprozent: {reihe['gesamt_prozent']:.2f}%", ln=True)
                        pdf.cell(0, 10, "", ln=True)  # Leerzeile zwischen Tests

                    # Diagramm hinzufügen, wenn vorhanden
                    if diagramm_buffer:
                        pdf.add_page()
                        pdf.image(diagramm_buffer, x=10, y=10, w=pdf.w - 20)
                    else:
                        pdf.cell(0, 10, "Kein Prognosediagramm verfügbar.", ln=True)

                    pdf_file = f"{teilnehmer[1]}-Bericht.pdf"
                    pdf.output(pdf_file)
                    return pdf_file

                pdf_file = erstelle_pdf(teilnehmer, testergebnisse, mittelwert, diagramm_buffer)

                # Excel-Bericht erstellen
                def erstelle_excel(teilnehmer, testergebnisse, mittelwert):
                    datei_name = f"{teilnehmer[1]}-Bericht.xlsx"
                    with pd.ExcelWriter(datei_name) as writer:
                        testergebnisse.to_excel(writer, sheet_name='Testergebnisse', index=False)
                        # Durchschnitt der letzten zwei Tests hinzufügen
                        df_mittelwert = pd.DataFrame({'Durchschnitt der letzten zwei Tests': [mittelwert]})
                        df_mittelwert.to_excel(writer, sheet_name='Durchschnitt', index=False)
                    return datei_name

                excel_file = erstelle_excel(teilnehmer, testergebnisse, mittelwert)

                # Dateien zum Download anbieten
                with open(pdf_file, "rb") as f:
                    pdf_bytes = f.read()
                    b64_pdf = base64.b64encode(pdf_bytes).decode()
                    href = f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="{pdf_file}">📄 PDF-Bericht herunterladen</a>'
                    st.markdown(href, unsafe_allow_html=True)

                with open(excel_file, "rb") as f:
                    excel_bytes = f.read()
                    b64_excel = base64.b64encode(excel_bytes).decode()
                    href = f'<a href="data:application/octet-stream;base64,{b64_excel}" download="{excel_file}">📊 Excel-Bericht herunterladen</a>'
                    st.markdown(href, unsafe_allow_html=True)

                # Temporäre Dateien entfernen
                os.remove(pdf_file)
                os.remove(excel_file)
    else:
        st.warning("Es sind keine Teilnehmer vorhanden.")

# Anpassung der Caching-Dekoratoren (Optimierung O8)
# Entfernen von Caching bei Datenbankabfragen, um Dateninkonsistenzen zu vermeiden
# Alle Funktionen mit @st.cache_data wurden angepasst oder der Dekorator wurde entfernt

# Debugging: Anzeigen aller Teilnehmer und Testergebnisse
if st.checkbox("Datenbankinhalt anzeigen (nur für Debugging)"):
    st.subheader("Teilnehmer")
    st.write(hole_teilnehmer())
    st.subheader("Testergebnisse")
    testergebnisse_df = hole_alle_testergebnisse()
    st.write(testergebnisse_df)

# Requirements.txt erstellen (Optimierung O7)
def erstelle_requirements():
    requirements = """
    streamlit==1.25.0  # Für die Web-App
    pandas==2.1.1      # Für Datenverarbeitung
    sqlite3            # Für Datenbank
    altair==5.1.1      # Für Visualisierung
    pycaret==3.0.5     # Für AutoML und Prognosemodellierung
    fpdf==1.7.2        # Für PDF-Generierung
    openpyxl==3.1.2    # Für Excel-Verarbeitung
    scikit-learn==1.3.0  # Für maschinelles Lernen
    """
    with open('requirements.txt', 'w') as f:
        f.write(requirements.strip())

erstelle_requirements()
