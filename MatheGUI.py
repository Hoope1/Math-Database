# app.py
import streamlit as st
from teilnehmer import teilnehmerverwaltung
from testverwaltung import testverwaltung  # Import aktualisiert
from prognose import prognosesystem
from bericht import berichtswesen

# Hauptlayout der Anwendung
st.sidebar.title("Navigation")
option = st.sidebar.radio(
    "Bereich auswählen",
    ["Teilnehmerverwaltung", "Testverwaltung", "Prognose-System", "Berichtswesen"]
)

# Navigation zwischen Modulen
if option == "Teilnehmerverwaltung":
    teilnehmerverwaltung()
elif option == "Testverwaltung":
    testverwaltung()
elif option == "Prognose-System":
    prognosesystem()
elif option == "Berichtswesen":
    berichtswesen()
