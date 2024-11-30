# mathematik_kurs_verwaltung.py - Teil 2/4

# Testdatenbank initialisieren
def initialisiere_testergebnisse():
    cursor.execute('''
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
        gesamt_prozent REAL,
        FOREIGN KEY (teilnehmer_id) REFERENCES teilnehmer (id)
    )
    ''')
    verbindung.commit()

initialisiere_testergebnisse()

# Testeingabe und Berechnung
def fuege_testergebnis_hinzu(teilnehmer_id, test_datum, ergebnisse):
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

# Testverwaltung in Streamlit
st.header("Testverwaltung")

teilnehmer_df = hole_teilnehmer()
if not teilnehmer_df.empty:
    # Teilnehmerauswahl für Testeingabe
    teilnehmer_df['auswahl'] = teilnehmer_df.apply(lambda reihe: f"{reihe['name']} (ID: {reihe['id']})", axis=1)
    ausgewaehlte_option = st.selectbox("Teilnehmer auswählen", teilnehmer_df['auswahl'])
    teilnehmer_id = int(ausgewaehlte_option.split("ID: ")[1].strip(')'))
    name = teilnehmer_df[teilnehmer_df['id'] == teilnehmer_id]['name'].values[0]

    st.subheader(f"Testergebnis für {name} hinzufügen")

    test_datum = st.date_input("Testdatum", date.today())

    # Kategorien-Initialisierung
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
            # Prozentberechnungen
            gesamt_erreicht = sum([ergebnisse[k]['erreicht'] for k in kategorien])
            gesamt_prozent = (gesamt_erreicht / total_max_punkte) * 100 if total_max_punkte > 0 else 0
            ergebnisse['gesamt_prozent'] = gesamt_prozent

            fuege_testergebnis_hinzu(teilnehmer_id, test_datum.strftime('%Y-%m-%d'), ergebnisse)
            st.success(f"Testergebnis für {name} erfolgreich hinzugefügt.")

else:
    st.warning("Keine Teilnehmer vorhanden. Bitte zuerst Teilnehmer hinzufügen.")
