# prognose.py
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pycaret.regression import setup, compare_models, predict_model, save_model, load_model
import matplotlib.pyplot as plt

# Datenbankverbindung
verbindung = sqlite3.connect('data/mathematik_kurs.db', check_same_thread=False)

# Modell speichern/laden
def lade_modell():
    """Lädt das gespeicherte Modell oder erstellt ein neues Modell, wenn keines vorhanden ist."""
    try:
        modell = load_model('bestes_prognose_modell')
        return modell
    except FileNotFoundError:
        st.warning("Kein gespeichertes Modell gefunden. Trainiere neues Modell...")
        return trainiere_modell()

def trainiere_modell():
    """Trainiert ein neues Modell basierend auf vorhandenen Testergebnissen."""
    testergebnisse_df = pd.read_sql_query('SELECT * FROM testergebnisse', verbindung)
    if testergebnisse_df.empty:
        st.error("Nicht genügend Daten zum Trainieren des Modells.")
        return None

    # Nur relevante Spalten für das Modell verwenden
    daten = testergebnisse_df[[
        'textaufgaben_erreicht', 'raumvorstellung_erreicht', 'gleichungen_erreicht',
        'brueche_erreicht', 'grundrechenarten_erreicht', 'zahlenraum_erreicht', 'gesamt_prozent'
    ]]

    # PyCaret-Setup und Modellvergleich
    setup(data=daten, target='gesamt_prozent', silent=True, session_id=123)
    bestes_modell = compare_models()
    save_model(bestes_modell, 'bestes_prognose_modell')
    st.success("Modelltraining abgeschlossen und Modell gespeichert.")
    return bestes_modell

def generiere_prognosen(modell, daten):
    """Erstellt Vorhersagen für einen gegebenen Datensatz."""
    vorhersagen = predict_model(modell, data=daten)
    return vorhersagen

def erstelle_prognosedaten(teilnehmer_id):
    """Bereitet die Daten für Prognosen vor."""
    # Letzte Testergebnisse des Teilnehmers abrufen
    testergebnisse_df = pd.read_sql_query(f'''
    SELECT textaufgaben_erreicht, raumvorstellung_erreicht, gleichungen_erreicht,
           brueche_erreicht, grundrechenarten_erreicht, zahlenraum_erreicht
    FROM testergebnisse WHERE teilnehmer_id = {teilnehmer_id}
    ORDER BY test_datum DESC LIMIT 1
    ''', verbindung)

    if testergebnisse_df.empty:
        st.error("Keine Testdaten für diesen Teilnehmer vorhanden.")
        return None

    # Daten für 60-Tage-Prognose vorbereiten
    daten = pd.concat([testergebnisse_df] * 61, ignore_index=True)
    daten['Tage'] = range(-30, 31)
    return daten

def zeichne_prognosediagramm(vorhersagen):
    """Erstellt ein Liniendiagramm der Prognosen."""
    plt.figure(figsize=(10, 6))
    plt.plot(vorhersagen['Tage'], vorhersagen['gesamt_prozent'], label="Gesamtfortschritt", color='black')

    # Kategoriedaten zeichnen
    kategorien = ['textaufgaben_erreicht', 'raumvorstellung_erreicht', 'gleichungen_erreicht',
                  'brueche_erreicht', 'grundrechenarten_erreicht', 'zahlenraum_erreicht']
    farben = ['red', 'blue', 'green', 'orange', 'purple', 'brown']
    for kategorie, farbe in zip(kategorien, farben):
        plt.plot(vorhersagen['Tage'], vorhersagen[kategorie], label=kategorie.capitalize(), linestyle='dashed', color=farbe)

    plt.axvline(0, color='gray', linestyle='--', label='Heute')
    plt.title("60-Tage-Prognose")
    plt.xlabel("Tage (von -30 bis +30)")
    plt.ylabel("Prozentwert")
    plt.legend()
    plt.grid(True)
    st.pyplot(plt)

# Prognosesystem
def prognosesystem():
    st.header("Prognose-System")

    # Teilnehmerdaten abrufen
    teilnehmer_df = pd.read_sql_query('SELECT id, name FROM teilnehmer', verbindung)
    if teilnehmer_df.empty:
        st.warning("Keine Teilnehmer vorhanden. Bitte zuerst Teilnehmer hinzufügen.")
        return

    # Teilnehmer auswählen
    teilnehmer_df['Auswahl'] = teilnehmer_df.apply(lambda x: f"{x['name']} (ID: {x['id']})", axis=1)
    ausgewaehlter = st.selectbox("Teilnehmer auswählen", teilnehmer_df['Auswahl'])
    teilnehmer_id = int(ausgewaehlter.split("ID: ")[1].strip(')'))
    name = teilnehmer_df[teilnehmer_df['id'] == teilnehmer_id]['name'].values[0]
    st.subheader(f"Prognose für {name}")

    # Modell laden und Prognose erstellen
    modell = lade_modell()
    if modell is None:
        return

    prognosedaten = erstelle_prognosedaten(teilnehmer_id)
    if prognosedaten is None:
        return

    vorhersagen = generiere_prognosen(modell, prognosedaten)
    vorhersagen['Tage'] = prognosedaten['Tage']

    # Prognosediagramm zeichnen
    zeichne_prognosediagramm(vorhersagen)
