# app.py
import streamlit as st
from teilnehmer_modul import teilnehmerverwaltung
from test_modul import testverwaltung
from prognose_modul import prognosesystem
from bericht_modul import berichtswesen

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
