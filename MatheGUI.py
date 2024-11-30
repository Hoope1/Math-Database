# mathematik_kurs_verwaltung.py - Teil 1/4
import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
import re

# CSS für Schriftgrößen
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

# Datenbank einrichten
verbindung = sqlite3.connect('mathematik_kurs.db', check_same_thread=False)
cursor = verbindung.cursor()

def initialisiere_datenbank():
    # Tabelle für Teilnehmer
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

initialisiere_datenbank()

# Hilfsfunktionen
def berechne_alter(sv_nummer):
    jahr = int(sv_nummer[8:10])
    jahr += 2000 if jahr <= int(datetime.now().year) % 100 else 1900
    monat = int(sv_nummer[6:8])
    tag = int(sv_nummer[4:6])
    geburtsdatum = date(jahr, monat, tag)
    heute = date.today()
    return heute.year - geburtsdatum.year - ((heute.month, heute.day) < (geburtsdatum.month, geburtsdatum.day))

def ist_aktiv(austrittsdatum):
    return datetime.strptime(austrittsdatum, '%Y-%m-%d').date() > date.today()

def fuege_teilnehmer_hinzu(name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum):
    cursor.execute('''
    INSERT INTO teilnehmer (name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum)
    VALUES (?, ?, ?, ?, ?)
    ''', (name, sv_nummer, berufswunsch, eintrittsdatum, austrittsdatum))
    verbindung.commit()

def hole_teilnehmer():
    cursor.execute('SELECT * FROM teilnehmer')
    zeilen = cursor.fetchall()
    spalten = [beschreibung[0] for beschreibung in cursor.description]
    return pd.DataFrame(zeilen, columns=spalten)

# Teilnehmerübersicht
st.title("Mathematik-Kurs Verwaltung")
st.header("Teilnehmerübersicht")

teilnehmer_df = hole_teilnehmer()
if not teilnehmer_df.empty:
    teilnehmer_df['Alter'] = teilnehmer_df['sv_nummer'].apply(berechne_alter)
    teilnehmer_df['Status'] = teilnehmer_df['austrittsdatum'].apply(lambda x: 'Aktiv' if ist_aktiv(x) else 'Inaktiv')

    if st.checkbox("Inaktive Teilnehmer anzeigen"):
        st.dataframe(teilnehmer_df)
    else:
        aktive_df = teilnehmer_df[teilnehmer_df['Status'] == 'Aktiv']
        st.dataframe(aktive_df)
else:
    st.write("Keine Teilnehmer gefunden.")

# Teilnehmer hinzufügen
st.header("Neuen Teilnehmer hinzufügen")
name = st.text_input("Name")
sv_nummer = st.text_input("SV-Nummer (XXXXDDMMYY)")
berufswunsch = st.text_input("Berufswunsch (Großbuchstaben)")
eintrittsdatum = st.date_input("Eintrittsdatum", date.today())
austrittsdatum = st.date_input("Austrittsdatum", date.today())

if st.button("Teilnehmer hinzufügen"):
    if not re.match(r'^\d{10}$', sv_nummer):
        st.error("Die SV-Nummer muss aus genau 10 Ziffern bestehen.")
    elif not berufswunsch.isupper():
        st.error("Berufswunsch muss in Großbuchstaben eingegeben werden.")
    else:
        fuege_teilnehmer_hinzu(name, sv_nummer, berufswunsch, eintrittsdatum.strftime('%Y-%m-%d'), austrittsdatum.strftime('%Y-%m-%d'))
        st.success("Teilnehmer erfolgreich hinzugefügt.")
