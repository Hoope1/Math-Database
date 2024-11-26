import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime

# Datenbank einrichten
def setup_database():
    connection = sqlite3.connect("participants.db")
    cursor = connection.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            sv_number TEXT,
            job TEXT,
            entry_date TEXT,
            exit_date TEXT,
            status TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id INTEGER,
            category TEXT,
            reached_points INTEGER,
            max_points INTEGER,
            percentage REAL,
            test_date TEXT,
            FOREIGN KEY(participant_id) REFERENCES participants(id)
        )
    """)

    connection.commit()
    return connection

# Teilnehmer hinzufügen oder aktualisieren
def add_or_update_participant(connection, participant_id, name, sv_number, job, entry_date, exit_date):
    cursor = connection.cursor()
    status = "Aktiv" if exit_date > datetime.today().strftime("%Y-%m-%d") else "Inaktiv"
    if participant_id:
        cursor.execute("""
            UPDATE participants
            SET name = ?, sv_number = ?, job = ?, entry_date = ?, exit_date = ?, status = ?
            WHERE id = ?
        """, (name, sv_number, job, entry_date, exit_date, status, participant_id))
    else:
        cursor.execute("""
            INSERT INTO participants (name, sv_number, job, entry_date, exit_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, sv_number, job, entry_date, exit_date, status))
    connection.commit()

# Testergebnisse hinzufügen oder aktualisieren
def add_or_update_test(connection, test_id, participant_id, category, reached_points, max_points, test_date):
    percentage = (reached_points / max_points) * 100 if max_points > 0 else 0
    cursor = connection.cursor()
    if test_id:
        cursor.execute("""
            UPDATE tests
            SET category = ?, reached_points = ?, max_points = ?, percentage = ?, test_date = ?
            WHERE id = ?
        """, (category, reached_points, max_points, percentage, test_date, test_id))
    else:
        cursor.execute("""
            INSERT INTO tests (participant_id, category, reached_points, max_points, percentage, test_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (participant_id, category, reached_points, max_points, percentage, test_date))
    connection.commit()

# Teilnehmer und Tests laden
def load_participants(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM participants")
    return cursor.fetchall()

def load_tests(connection, participant_id=None):
    cursor = connection.cursor()
    if participant_id:
        cursor.execute("SELECT id, participant_id, category, reached_points, max_points, percentage, test_date FROM tests WHERE participant_id = ?", (participant_id,))
    else:
        cursor.execute("SELECT id, participant_id, category, reached_points, max_points, percentage, test_date FROM tests")
    return cursor.fetchall()

# Streamlit GUI
def main():
    connection = setup_database()
    st.title("Mathematik-Kurs Teilnehmerverwaltung")

    # Teilnehmerübersicht und Bearbeitung
    st.subheader("Teilnehmerübersicht")
    participants = load_participants(connection)
    participants_df = pd.DataFrame(participants, columns=["ID", "Name", "SV-Nummer", "Berufswunsch", "Eintrittsdatum", "Austrittsdatum", "Status"])
    participants_df = participants_df.drop(columns=["ID", "SV-Nummer"])
    st.dataframe(participants_df)

    # Filter für aktive/inaktive Teilnehmer
    show_inactive = st.checkbox("Inaktive Teilnehmer anzeigen")
    if not show_inactive:
        participants = [p for p in participants if p[6] == "Aktiv"]

    # Teilnehmer hinzufügen/bearbeiten
    st.subheader("Teilnehmer hinzufügen oder bearbeiten")
    with st.form("participant_form"):
        selected_participant = st.selectbox("Teilnehmer auswählen", ["Neuer Teilnehmer"] + [p[1] for p in participants])

        if selected_participant != "Neuer Teilnehmer":
            participant_data = next(p for p in participants if p[1] == selected_participant)
            participant_id = participant_data[0]
            name = st.text_input("Name", value=participant_data[1])
            sv_number = st.text_input("SV-Nummer", value=participant_data[2])
            job = st.text_input("Berufswunsch", value=participant_data[3])
            entry_date = st.date_input("Eintrittsdatum", value=datetime.strptime(participant_data[4], "%Y-%m-%d"))
            exit_date = st.date_input("Austrittsdatum", value=datetime.strptime(participant_data[5], "%Y-%m-%d"))
        else:
            participant_id = None
            name = st.text_input("Name")
            sv_number = st.text_input("SV-Nummer")
            job = st.text_input("Berufswunsch")
            entry_date = st.date_input("Eintrittsdatum", value=datetime.today())
            exit_date = st.date_input("Austrittsdatum", value=datetime.today())

        submitted = st.form_submit_button("Speichern")

        if submitted:
            add_or_update_participant(connection, participant_id, name, sv_number, job, entry_date.strftime("%Y-%m-%d"), exit_date.strftime("%Y-%m-%d"))
            st.success("Teilnehmer gespeichert!")

    # Testergebnisse hinzufügen/bearbeiten
    st.subheader("Testergebnisse hinzufügen oder bearbeiten")
    selected_participant = st.selectbox("Teilnehmer für Testergebnisse", ["Teilnehmer auswählen"] + [p[1] for p in participants])

    if selected_participant != "Teilnehmer auswählen":
        participant_id = next(p[0] for p in participants if p[1] == selected_participant)
        tests = load_tests(connection, participant_id)

        if tests:
            tests_df = pd.DataFrame(tests, columns=["ID", "Teilnehmer-ID", "Kategorie", "Erreichte Punkte", "Maximale Punkte", "Prozent", "Datum"])
            st.dataframe(tests_df.drop(columns=["ID", "Teilnehmer-ID"]))

        with st.form("test_form"):
            category = st.selectbox("Kategorie", ["Textaufgaben", "Raumvorstellung", "Gleichungen", "Brüche", "Grundrechenarten", "Zahlenraum"])
            reached_points = st.number_input("Erreichte Punkte", min_value=0, step=1)
            max_points = st.number_input("Maximale Punkte", min_value=0, step=1)
            test_date = st.date_input("Testdatum", value=datetime.today())

            submitted_test = st.form_submit_button("Speichern")

            if submitted_test:
                add_or_update_test(connection, None, participant_id, category, reached_points, max_points, test_date.strftime("%Y-%m-%d"))
                st.success("Testergebnis gespeichert!")

if __name__ == "__main__":
    main()
