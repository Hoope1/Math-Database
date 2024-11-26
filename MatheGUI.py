import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import re

# Initialize the database connection
conn = sqlite3.connect('teilnehmer.db', check_same_thread=False)
c = conn.cursor()

# Create tables if they don't exist
def init_db():
    c.execute('''
        CREATE TABLE IF NOT EXISTS teilnehmer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sv_nummer TEXT NOT NULL UNIQUE,
            berufswunsch TEXT NOT NULL,
            eintrittsdatum TEXT NOT NULL,
            austrittsdatum TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS testergebnisse (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teilnehmer_id INTEGER NOT NULL,
            test_datum TEXT NOT NULL,
            textaufgaben_erreicht INTEGER,
            textaufgaben_max INTEGER,
            raumvorstellung_erreicht INTEGER,
            raumvorstellung_max INTEGER,
            gleichungen_erreicht INTEGER,
            gleichungen_max INTEGER,
            brueche_erreicht INTEGER,
            brueche_max INTEGER,
            grundrechenarten_erreicht INTEGER,
            grundrechenarten_max INTEGER,
            zahlenraum_erreicht INTEGER,
            zahlenraum_max INTEGER,
            FOREIGN KEY (teilnehmer_id) REFERENCES teilnehmer (id)
        )
    ''')
    conn.commit()

init_db()

# Helper functions
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
    return datetime.strptime(austrittsdatum, '%Y-%m-%d').date() > date.today()

# Database operations
def add_teilnehmer(name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum):
    c.execute('''
        INSERT INTO teilnehmer (name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum))
    conn.commit()

def update_teilnehmer(teilnehmer_id, name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum):
    c.execute('''
        UPDATE teilnehmer
        SET name = ?, sv_nummer = ?, berufswunsch = ?, eintrittsdatum = ?, austrittsdatum = ?
        WHERE id = ?
    ''', (name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum, teilnehmer_id))
    conn.commit()

def get_teilnehmer():
    c.execute('SELECT * FROM teilnehmer')
    rows = c.fetchall()
    columns = [desc[0] for desc in c.description]
    return pd.DataFrame(rows, columns=columns)

def get_teilnehmer_by_id(teilnehmer_id):
    c.execute('SELECT * FROM teilnehmer WHERE id = ?', (teilnehmer_id,))
    return c.fetchone()

def add_testergebnis(teilnehmer_id, test_datum, ergebnisse):
    c.execute('''
        INSERT INTO testergebnisse (
            teilnehmer_id, test_datum,
            textaufgaben_erreicht, textaufgaben_max,
            raumvorstellung_erreicht, raumvorstellung_max,
            gleichungen_erreicht, gleichungen_max,
            brueche_erreicht, brueche_max,
            grundrechenarten_erreicht, grundrechenarten_max,
            zahlenraum_erreicht, zahlenraum_max
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        teilnehmer_id, test_datum,
        ergebnisse['Textaufgaben']['erreicht'], ergebnisse['Textaufgaben']['max'],
        ergebnisse['Raumvorstellung']['erreicht'], ergebnisse['Raumvorstellung']['max'],
        ergebnisse['Gleichungen']['erreicht'], ergebnisse['Gleichungen']['max'],
        ergebnisse['Brüche']['erreicht'], ergebnisse['Brüche']['max'],
        ergebnisse['Grundrechenarten']['erreicht'], ergebnisse['Grundrechenarten']['max'],
        ergebnisse['Zahlenraum']['erreicht'], ergebnisse['Zahlenraum']['max']
    ))
    conn.commit()

def get_latest_testergebnis(teilnehmer_id):
    c.execute('''
        SELECT * FROM testergebnisse
        WHERE teilnehmer_id = ?
        ORDER BY test_datum DESC
        LIMIT 1
    ''', (teilnehmer_id,))
    return c.fetchone()

# Streamlit app layout
st.title("Mathematik-Kurs Teilnehmerverwaltung")

# Tabs for different sections
tabs = st.tabs(["Teilnehmer hinzufügen/bearbeiten", "Testergebnisse hinzufügen", "Teilnehmerliste"])

# Teilnehmer hinzufügen/bearbeiten
with tabs[0]:
    st.header("Teilnehmer hinzufügen oder bearbeiten")
    # Fetch existing participants for editing
    teilnehmer_df = get_teilnehmer()
    teilnehmer_options = ["Neuen Teilnehmer hinzufügen"] + teilnehmer_df['name'].tolist()
    selected_teilnehmer = st.selectbox("Teilnehmer auswählen", teilnehmer_options)

    if selected_teilnehmer == "Neuen Teilnehmer hinzufügen":
        name = st.text_input("Name")
        sv_nummer = st.text_input("SV-Nummer (XXXXDDMMYY)")
        berufswunsch = st.text_input("Berufswunsch (Großbuchstaben)")
        eintrittsdatum = st.date_input("Eintrittsdatum", date.today())
        austrittsdatum = st.date_input("Austrittsdatum", date.today())

        if st.button("Hinzufügen"):
            if not re.match(r'^\d{10}$', sv_nummer):
                st.error("SV-Nummer muss aus genau 10 Ziffern bestehen.")
            elif not berufswunsch.isupper():
                st.error("Berufswunsch muss in Großbuchstaben eingegeben werden.")
            else:
                add_teilnehmer(
                    name, sv_nummer, berufswunsch,
                    eintrittsdatum.strftime('%Y-%m-%d'),
                    austrittsdatum.strftime('%Y-%m-%d')
                )
                st.success("Teilnehmer erfolgreich hinzugefügt.")
    else:
        teilnehmer_row = teilnehmer_df[teilnehmer_df['name'] == selected_teilnehmer].iloc[0]
        teilnehmer_id = teilnehmer_row['id']
        name = st.text_input("Name", teilnehmer_row['name'])
        sv_nummer = st.text_input("SV-Nummer (XXXXDDMMYY)", teilnehmer_row['sv_nummer'])
        berufswunsch = st.text_input("Berufswunsch (Großbuchstaben)", teilnehmer_row['berufswunsch'])
        eintrittsdatum = st.date_input("Eintrittsdatum", datetime.strptime(teilnehmer_row['eintrittsdatum'], '%Y-%m-%d'))
        austrittsdatum = st.date_input("Austrittsdatum", datetime.strptime(teilnehmer_row['austrittsdatum'], '%Y-%m-%d'))

        if st.button("Aktualisieren"):
            if not re.match(r'^\d{10}$', sv_nummer):
                st.error("SV-Nummer muss aus genau 10 Ziffern bestehen.")
            elif not berufswunsch.isupper():
                st.error("Berufswunsch muss in Großbuchstaben eingegeben werden.")
            else:
                update_teilnehmer(
                    teilnehmer_id, name, sv_nummer, berufswunsch,
                    eintrittsdatum.strftime('%Y-%m-%d'),
                    austrittsdatum.strftime('%Y-%m-%d')
                )
                st.success("Teilnehmerdaten erfolgreich aktualisiert.")

# Testergebnisse hinzufügen
with tabs[1]:
    st.header("Testergebnisse hinzufügen")
    # Fetch participants for selection
    teilnehmer_df = get_teilnehmer()
    teilnehmer_list = teilnehmer_df[['id', 'name']].values.tolist()
    teilnehmer_dict = {name: id for id, name in teilnehmer_list}
    selected_name = st.selectbox("Teilnehmer auswählen", [name for name in teilnehmer_dict.keys()])
    teilnehmer_id = teilnehmer_dict[selected_name]

    test_datum = st.date_input("Testdatum", date.today())

    kategorien = ["Textaufgaben", "Raumvorstellung", "Gleichungen", "Brüche", "Grundrechenarten", "Zahlenraum"]
    ergebnisse = {}

    st.subheader("Punkte eingeben")
    for kategorie in kategorien:
        st.markdown(f"**{kategorie}**")
        erreicht = st.number_input(f"{kategorie} erreichte Punkte", min_value=0, value=0, key=f"{kategorie}_erreicht")
        max_punkte = st.number_input(f"{kategorie} maximale Punkte", min_value=1, value=1, key=f"{kategorie}_max")
        ergebnisse[kategorie] = {'erreicht': erreicht, 'max': max_punkte}

    if st.button("Testergebnis hinzufügen"):
        add_testergebnis(teilnehmer_id, test_datum.strftime('%Y-%m-%d'), ergebnisse)
        st.success("Testergebnis erfolgreich hinzugefügt.")

# Teilnehmerliste anzeigen
with tabs[2]:
    st.header("Teilnehmerliste")
    show_inactive = st.checkbox("Inaktive Teilnehmer einblenden", value=True)

    # Fetch participants and their latest test results
    teilnehmer_df = get_teilnehmer()
    if not teilnehmer_df.empty:
        teilnehmer_df['alter'] = teilnehmer_df['sv_nummer'].apply(berechne_alter)
        teilnehmer_df['status'] = teilnehmer_df['austrittsdatum'].apply(lambda x: 'Aktiv' if ist_aktiv(x) else 'Inaktiv')
        if not show_inactive:
            teilnehmer_df = teilnehmer_df[teilnehmer_df['status'] == 'Aktiv']

        # Get latest test results
        testergebnisse_list = []
        for idx, row in teilnehmer_df.iterrows():
            latest_result = get_latest_testergebnis(row['id'])
            if latest_result:
                total_erreicht = sum([
                    latest_result[3], latest_result[5], latest_result[7],
                    latest_result[9], latest_result[11], latest_result[13]
                ])
                total_max = sum([
                    latest_result[4], latest_result[6], latest_result[8],
                    latest_result[10], latest_result[12], latest_result[14]
                ])
                gesamt_prozent = (total_erreicht / total_max) * 100 if total_max > 0 else 0
                testergebnisse_list.append({
                    'id': row['id'],
                    'Letztes Testdatum': latest_result[2],
                    'Gesamtprozent': f"{gesamt_prozent:.2f}%"
                })
            else:
                testergebnisse_list.append({
                    'id': row['id'],
                    'Letztes Testdatum': 'Keine Ergebnisse',
                    'Gesamtprozent': ''
                })

        testergebnisse_df = pd.DataFrame(testergebnisse_list)
        merged_df = pd.merge(teilnehmer_df, testergebnisse_df, on='id', how='left')

        # Display DataFrame
        display_df = merged_df[[
            'name', 'alter', 'berufswunsch', 'eintrittsdatum', 'austrittsdatum',
            'status', 'Letztes Testdatum', 'Gesamtprozent'
        ]]
        display_df.columns = [
            'Name', 'Alter', 'Berufswunsch', 'Eintrittsdatum', 'Austrittsdatum',
            'Status', 'Letzte Testergebnisse', 'Gesamtprozent'
        ]

        st.dataframe(display_df)
    else:
        st.write("Keine Teilnehmer vorhanden.")
