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

# Datenbankverbindung initialisieren
conn = sqlite3.connect('teilnehmer.db', check_same_thread=False)
c = conn.cursor()

# Tabellen erstellen, falls sie nicht existieren
def init_db():
    # Teilnehmer-Tabelle
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
    # Testergebnisse-Tabelle
    c.execute('''
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
            FOREIGN KEY (teilnehmer_id) REFERENCES teilnehmer (id)
        )
    ''')
    conn.commit()

init_db()

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
    return datetime.strptime(austrittsdatum, '%Y-%m-%d').date() > date.today()

# Datenbankoperationen
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
            textaufgaben_erreicht, textaufgaben_max, textaufgaben_prozent,
            raumvorstellung_erreicht, raumvorstellung_max, raumvorstellung_prozent,
            gleichungen_erreicht, gleichungen_max, gleichungen_prozent,
            brueche_erreicht, brueche_max, brueche_prozent,
            grundrechenarten_erreicht, grundrechenarten_max, grundrechenarten_prozent,
            zahlenraum_erreicht, zahlenraum_max, zahlenraum_prozent,
            gesamt_prozent
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        teilnehmer_id, test_datum,
        ergebnisse['Textaufgaben']['erreicht'], ergebnisse['Textaufgaben']['max'], ergebnisse['Textaufgaben']['prozent'],
        ergebnisse['Raumvorstellung']['erreicht'], ergebnisse['Raumvorstellung']['max'], ergebnisse['Raumvorstellung']['prozent'],
        ergebnisse['Gleichungen']['erreicht'], ergebnisse['Gleichungen']['max'], ergebnisse['Gleichungen']['prozent'],
        ergebnisse['Brüche']['erreicht'], ergebnisse['Brüche']['max'], ergebnisse['Brüche']['prozent'],
        ergebnisse['Grundrechenarten']['erreicht'], ergebnisse['Grundrechenarten']['max'], ergebnisse['Grundrechenarten']['prozent'],
        ergebnisse['Zahlenraum']['erreicht'], ergebnisse['Zahlenraum']['max'], ergebnisse['Zahlenraum']['prozent'],
        ergebnisse['gesamt_prozent']
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

def get_testergebnisse(teilnehmer_id):
    c.execute('''
        SELECT * FROM testergebnisse
        WHERE teilnehmer_id = ?
    ''', (teilnehmer_id,))
    rows = c.fetchall()
    columns = [desc[0] for desc in c.description]
    return pd.DataFrame(rows, columns=columns)

def get_all_testergebnisse():
    c.execute('SELECT * FROM testergebnisse')
    rows = c.fetchall()
    columns = [desc[0] for desc in c.description]
    return pd.DataFrame(rows, columns=columns)

# Streamlit App Layout
st.title("Mathematik-Kurs Teilnehmerverwaltung")

# Teilnehmerübersicht im oberen Teil
st.header("Teilnehmerübersicht")
teilnehmer_df = get_teilnehmer()
if not teilnehmer_df.empty:
    teilnehmer_df['Alter'] = teilnehmer_df['sv_nummer'].apply(berechne_alter)
    teilnehmer_df['Status'] = teilnehmer_df['austrittsdatum'].apply(lambda x: 'Aktiv' if ist_aktiv(x) else 'Inaktiv')
    display_df = teilnehmer_df[['name', 'Alter', 'berufswunsch', 'eintrittsdatum', 'austrittsdatum', 'Status']]
    display_df.columns = ['Name', 'Alter', 'Berufswunsch', 'Eintrittsdatum', 'Austrittsdatum', 'Status']

    # Ein- und Ausblenden von inaktiven Teilnehmern
    show_inactive = st.checkbox("Inaktive Teilnehmer anzeigen", value=False)
    if not show_inactive:
        display_df = display_df[display_df['Status'] == 'Aktiv']

    # Ausgrauen von inaktiven Teilnehmern
    def highlight_inactive(row):
        if row['Status'] == 'Inaktiv':
            return ['color: grey'] * len(row)
        else:
            return [''] * len(row)

    st.dataframe(display_df.style.apply(highlight_inactive, axis=1))
else:
    st.write("Keine Teilnehmer vorhanden.")

# Tabs für verschiedene Bereiche
tabs = st.tabs(["Teilnehmer hinzufügen/bearbeiten", "Testergebnisse hinzufügen", "Prognosediagramm", "Bericht erstellen"])

# Teilnehmer hinzufügen/bearbeiten
with tabs[0]:
    st.header("Teilnehmer hinzufügen oder bearbeiten")
    # Teilnehmerliste aktualisieren
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
    # Teilnehmerliste aktualisieren
    teilnehmer_df = get_teilnehmer()
    if not teilnehmer_df.empty:
        teilnehmer_list = teilnehmer_df[['id', 'name']].values.tolist()
        teilnehmer_dict = {name: id for id, name in teilnehmer_list}
        selected_name = st.selectbox("Teilnehmer auswählen", [name for name in teilnehmer_dict.keys()])
        teilnehmer_id = teilnehmer_dict[selected_name]

        test_datum = st.date_input("Testdatum", date.today())

        kategorien = ["Textaufgaben", "Raumvorstellung", "Gleichungen", "Brüche", "Grundrechenarten", "Zahlenraum"]
        ergebnisse = {}

        st.subheader("Punkte eingeben")
        total_max_punkte = 0
        for kategorie in kategorien:
            st.markdown(f"**{kategorie}**")
            erreicht = st.number_input(f"{kategorie} erreichte Punkte", min_value=0, value=0, key=f"{kategorie}_erreicht")
            max_punkte = st.number_input(f"{kategorie} maximale Punkte", min_value=1, value=1, key=f"{kategorie}_max")
            total_max_punkte += max_punkte
            ergebnisse[kategorie] = {'erreicht': erreicht, 'max': max_punkte}

        if total_max_punkte != 100:
            st.error("Die Summe der maximalen Punkte aller Kategorien muss genau 100 sein.")
        else:
            if st.button("Testergebnis hinzufügen"):
                # Prozentwerte berechnen
                gesamt_erreicht = 0
                for kategorie in kategorien:
                    erreicht = ergebnisse[kategorie]['erreicht']
                    max_punkte = ergebnisse[kategorie]['max']
                    prozent = (erreicht / max_punkte) * 100 if max_punkte > 0 else 0
                    ergebnisse[kategorie]['prozent'] = prozent
                    gesamt_erreicht += erreicht
                gesamt_prozent = (gesamt_erreicht / total_max_punkte) * 100 if total_max_punkte > 0 else 0
                ergebnisse['gesamt_prozent'] = gesamt_prozent

                add_testergebnis(teilnehmer_id, test_datum.strftime('%Y-%m-%d'), ergebnisse)
                st.success("Testergebnis erfolgreich hinzugefügt.")
    else:
        st.warning("Es sind keine Teilnehmer vorhanden. Bitte fügen Sie zuerst Teilnehmer hinzu.")

# Prognosediagramm
with tabs[2]:
    st.header("Prognosediagramm")
    teilnehmer_df = get_teilnehmer()
    if not teilnehmer_df.empty:
        selected_name = st.selectbox("Teilnehmer auswählen", teilnehmer_df['name'].tolist())
        teilnehmer_id = teilnehmer_df[teilnehmer_df['name'] == selected_name]['id'].values[0]
        if st.button("Prognosediagramm anzeigen"):
            def prognose_diagramm(teilnehmer_id):
                testdaten = get_testergebnisse(teilnehmer_id)
                if testdaten.empty:
                    st.write("Keine Testergebnisse für diesen Teilnehmer.")
                    return

                # Datum in Tage relativ zu heute umrechnen
                testdaten['Tag'] = (pd.to_datetime(testdaten['test_datum']) - pd.Timestamp.today()).dt.days
                # Filtern auf Zeitraum von -30 bis +30 Tagen
                testdaten = testdaten[(testdaten['Tag'] >= -30) & (testdaten['Tag'] <= 30)]

                # Daten für Altair vorbereiten
                df_melted = testdaten.melt(id_vars=['Tag'], value_vars=[
                    'gesamt_prozent',
                    'textaufgaben_prozent',
                    'raumvorstellung_prozent',
                    'gleichungen_prozent',
                    'brueche_prozent',
                    'grundrechenarten_prozent',
                    'zahlenraum_prozent'
                ], var_name='Kategorie', value_name='Prozent')

                # Linienstil definieren
                linienstil = alt.condition(
                    alt.FieldEqualPredicate(field='Kategorie', equal='gesamt_prozent'),
                    alt.value('solid'),
                    alt.value('dashed')
                )

                # Farben definieren
                farben = {
                    'gesamt_prozent': 'black',
                    'textaufgaben_prozent': 'red',
                    'raumvorstellung_prozent': 'green',
                    'gleichungen_prozent': 'blue',
                    'brueche_prozent': 'orange',
                    'grundrechenarten_prozent': 'purple',
                    'zahlenraum_prozent': 'brown'
                }

                # Diagramm erstellen
                chart = alt.Chart(df_melted).mark_line().encode(
                    x=alt.X('Tag', scale=alt.Scale(domain=[-30, 30]), title='Tage'),
                    y=alt.Y('Prozent', scale=alt.Scale(domain=[0, 100]), title='Prozent'),
                    color=alt.Color('Kategorie', scale=alt.Scale(domain=list(farben.keys()), range=list(farben.values()))),
                    strokeDash=linienstil
                )

                st.altair_chart(chart, use_container_width=True)

            prognose_diagramm(teilnehmer_id)
    else:
        st.warning("Es sind keine Teilnehmer vorhanden.")

# Bericht erstellen
with tabs[3]:
    st.header("Bericht erstellen")
    teilnehmer_df = get_teilnehmer()
    if not teilnehmer_df.empty:
        selected_name = st.selectbox("Teilnehmer auswählen", teilnehmer_df['name'].tolist())
        teilnehmer_id = teilnehmer_df[teilnehmer_df['name'] == selected_name]['id'].values[0]

        if st.button("Bericht generieren"):
            # Daten abrufen
            teilnehmer = get_teilnehmer_by_id(teilnehmer_id)
            testergebnisse = get_testergebnisse(teilnehmer_id)
            if testergebnisse.empty:
                st.warning("Keine Testergebnisse für diesen Teilnehmer.")
            else:
                # Mittelwert der letzten beiden Tests
                letzte_zwei = testergebnisse.sort_values(by='test_datum', ascending=False).head(2)
                mittelwert = letzte_zwei['gesamt_prozent'].mean()

                # Prognosediagramm erstellen und als Bild speichern
                def save_prognose_diagramm(teilnehmer_id):
                    testdaten = get_testergebnisse(teilnehmer_id)
                    testdaten['Tag'] = (pd.to_datetime(testdaten['test_datum']) - pd.Timestamp.today()).dt.days
                    testdaten = testdaten[(testdaten['Tag'] >= -30) & (testdaten['Tag'] <= 30)]
                    df_melted = testdaten.melt(id_vars=['Tag'], value_vars=[
                        'gesamt_prozent',
                        'textaufgaben_prozent',
                        'raumvorstellung_prozent',
                        'gleichungen_prozent',
                        'brueche_prozent',
                        'grundrechenarten_prozent',
                        'zahlenraum_prozent'
                    ], var_name='Kategorie', value_name='Prozent')
                    linienstil = alt.condition(
                        alt.FieldEqualPredicate(field='Kategorie', equal='gesamt_prozent'),
                        alt.value('solid'),
                        alt.value('dashed')
                    )
                    farben = {
                        'gesamt_prozent': 'black',
                        'textaufgaben_prozent': 'red',
                        'raumvorstellung_prozent': 'green',
                        'gleichungen_prozent': 'blue',
                        'brueche_prozent': 'orange',
                        'grundrechenarten_prozent': 'purple',
                        'zahlenraum_prozent': 'brown'
                    }
                    chart = alt.Chart(df_melted).mark_line().encode(
                        x=alt.X('Tag', scale=alt.Scale(domain=[-30, 30]), title='Tage'),
                        y=alt.Y('Prozent', scale=alt.Scale(domain=[0, 100]), title='Prozent'),
                        color=alt.Color('Kategorie', scale=alt.Scale(domain=list(farben.keys()), range=list(farben.values()))),
                        strokeDash=linienstil
                    )
                    chart_path = f"{teilnehmer[1]}_prognose_diagramm.png"
                    chart.save(chart_path)
                    return chart_path

                diagramm_path = save_prognose_diagramm(teilnehmer_id)

                # PDF-Bericht erstellen
                def create_pdf(teilnehmer, testergebnisse, mittelwert, diagramm_path):
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
                    pdf.cell(0, 10, f"Mittelwert der letzten zwei Tests: {mittelwert:.2f}%", ln=True)

                    pdf.cell(0, 10, "", ln=True)  # Leerzeile
                    pdf.set_font("Arial", 'B', 14)
                    pdf.cell(0, 10, "Testergebnisse:", ln=True)

                    pdf.set_font("Arial", '', 10)
                    # Testergebnisse als Tabelle hinzufügen
                    for index, row in testergebnisse.iterrows():
                        pdf.cell(0, 10, f"Testdatum: {row['test_datum']}", ln=True)
                        pdf.cell(0, 10, f"Gesamtprozent: {row['gesamt_prozent']:.2f}%", ln=True)
                        pdf.cell(0, 10, "", ln=True)  # Leerzeile zwischen Tests

                    # Diagramm hinzufügen
                    pdf.add_page()
                    pdf.image(diagramm_path, x=10, y=10, w=pdf.w - 20)

                    pdf_file = f"{teilnehmer[1]}-Bericht.pdf"
                    pdf.output(pdf_file)
                    return pdf_file

                pdf_file = create_pdf(teilnehmer, testergebnisse, mittelwert, diagramm_path)

                # Excel-Bericht erstellen
                def create_excel(teilnehmer, testergebnisse):
                    file_name = f"{teilnehmer[1]}-Bericht.xlsx"
                    with pd.ExcelWriter(file_name) as writer:
                        testergebnisse.to_excel(writer, index=False)
                    return file_name

                excel_file = create_excel(teilnehmer, testergebnisse)

                # Dateien zum Download anbieten
                with open(pdf_file, "rb") as f:
                    pdf_bytes = f.read()
                    b64_pdf = base64.b64encode(pdf_bytes).decode()
                    href = f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="{pdf_file}">PDF-Bericht herunterladen</a>'
                    st.markdown(href, unsafe_allow_html=True)

                with open(excel_file, "rb") as f:
                    excel_bytes = f.read()
                    b64_excel = base64.b64encode(excel_bytes).decode()
                    href = f'<a href="data:application/octet-stream;base64,{b64_excel}" download="{excel_file}">Excel-Bericht herunterladen</a>'
                    st.markdown(href, unsafe_allow_html=True)

                # Temporäre Dateien entfernen
                os.remove(diagramm_path)
                os.remove(pdf_file)
                os.remove(excel_file)
    else:
        st.warning("Es sind keine Teilnehmer vorhanden.")

# Modelltraining mit PyCaret (optional, kann beim Start der App ausgeführt werden)
def train_model():
    tests_df = get_all_testergebnisse()
    if tests_df.empty:
        st.write("Nicht genügend Daten zum Trainieren des Modells.")
        return None
    # Nur relevante Spalten verwenden
    data = tests_df[[
        'textaufgaben_prozent',
        'raumvorstellung_prozent',
        'gleichungen_prozent',
        'brueche_prozent',
        'grundrechenarten_prozent',
        'zahlenraum_prozent',
        'gesamt_prozent'
    ]]
    reg = setup(data=data, target='gesamt_prozent', silent=True, session_id=123)
    best_model = compare_models()
    save_model(best_model, 'best_prognose_model')
    st.success("Modell erfolgreich trainiert.")

# Optional: Modell beim Start der App trainieren
# train_model()
