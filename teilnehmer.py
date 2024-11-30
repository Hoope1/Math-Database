# teilnehmer.py
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime
import re

# Datenbankverbindung
verbindung = sqlite3.connect('data/mathematik_kurs.db', check_same_thread=False)
cursor = verbindung.cursor()

# Tabelle initialisieren
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
verbindung.commit()

# Hilfsfunktionen
def berechne_alter(sv_nummer):
    """Berechnet das Alter basierend auf der SV-Nummer."""
    jahr = int(sv_nummer[8:10]) + (2000 if int(sv_nummer[8:10]) <= int(datetime.now().year % 100) else 1900)
    geburtsdatum = date(jahr, int(sv_nummer[6:8]), int(sv_nummer[4:6]))
    return date.today().year - geburtsdatum.year - ((date.today().month, date.today().day) < (geburtsdatum.month, geburtsdatum.day))

def ist_aktiv(austrittsdatum):
    """Prüft, ob ein Teilnehmer aktiv ist (Austrittsdatum > heute)."""
    return datetime.strptime(austrittsdatum, '%Y-%m-%d').date() > date.today()

def aktualisiere_austrittsdatum(teilnehmer_id, neues_datum):
    """Aktualisiert das Austrittsdatum eines Teilnehmers."""
    cursor.execute('UPDATE teilnehmer SET austrittsdatum = ? WHERE id = ?', (neues_datum, teilnehmer_id))
    verbindung.commit()

def teilnehmer_hinzufuegen(name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum):
    """Fügt einen neuen Teilnehmer zur Datenbank hinzu."""
    cursor.execute('''
    INSERT INTO teilnehmer (name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum)
    VALUES (?, ?, ?, ?, ?)
    ''', (name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum))
    verbindung.commit()

# Teilnehmerverwaltung
def teilnehmerverwaltung():
    st.header("Teilnehmerverwaltung")

    # Teilnehmer anzeigen
    teilnehmer_df = pd.read_sql_query('SELECT * FROM teilnehmer', verbindung)
    if not teilnehmer_df.empty:
        teilnehmer_df['Alter'] = teilnehmer_df['sv_nummer'].apply(berechne_alter)
        teilnehmer_df['Status'] = teilnehmer_df['austrittsdatum'].apply(lambda x: 'Aktiv' if ist_aktiv(x) else 'Inaktiv')

        # Teilnehmer filtern und anzeigen
        if st.checkbox("Inaktive Teilnehmer anzeigen"):
            st.dataframe(teilnehmer_df)
        else:
            aktive_df = teilnehmer_df[teilnehmer_df['Status'] == 'Aktiv']
            st.dataframe(aktive_df)

        # Austrittsdatum aktualisieren
        st.subheader("Austrittsdatum aktualisieren")
        teilnehmer_df['Auswahl'] = teilnehmer_df.apply(lambda row: f"{row['name']} (ID: {row['id']})", axis=1)
        ausgewaehlter = st.selectbox("Teilnehmer auswählen", teilnehmer_df['Auswahl'])
        teilnehmer_id = int(ausgewaehlter.split("ID: ")[1].strip(')'))
        neues_datum = st.date_input("Neues Austrittsdatum", date.today())
        if st.button("Austrittsdatum aktualisieren"):
            aktualisiere_austrittsdatum(teilnehmer_id, neues_datum.strftime('%Y-%m-%d'))
            st.success("Austrittsdatum erfolgreich aktualisiert!")
    else:
        st.write("Keine Teilnehmer vorhanden.")

    # Teilnehmer hinzufügen
    st.subheader("Neuen Teilnehmer hinzufügen")
    name = st.text_input("Name")
    sv_nummer = st.text_input("SV-Nummer (XXXXDDMMYY)")
    berufswunsch = st.text_input("Berufswunsch (Großbuchstaben)")
    eintrittsdatum = st.date_input("Eintrittsdatum", date.today())
    austrittsdatum = st.date_input("Austrittsdatum", date.today())

    if st.button("Teilnehmer hinzufügen"):
        # Validierung der Eingaben
        if not re.match(r'^\d{10}$', sv_nummer):
            st.error("Die SV-Nummer muss aus genau 10 Ziffern bestehen.")
        elif not berufswunsch.isupper():
            st.error("Berufswunsch muss in Großbuchstaben eingegeben werden.")
        else:
            teilnehmer_hinzufuegen(name, sv_nummer, berufswunsch, eintrittsdatum.strftime('%Y-%m-%d'), austrittsdatum.strftime('%Y-%m-%d'))
            st.success("Teilnehmer erfolgreich hinzugefügt!")
