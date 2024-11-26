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
            FOREIGN KEY(participant_id) REFERENCES participants(id)
        )
    """)

    connection.commit()
    return connection

# Teilnehmer hinzufügen
def add_participant(connection, name, sv_number, job, entry_date, exit_date, status):
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO participants (name, sv_number, job, entry_date, exit_date, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, sv_number, job, entry_date, exit_date, status))
    connection.commit()

# Testergebnisse hinzufügen
def add_test(connection, participant_id, category, reached_points, max_points):
    percentage = (reached_points / max_points) * 100 if max_points > 0 else 0
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO tests (participant_id, category, reached_points, max_points, percentage)
        VALUES (?, ?, ?, ?, ?)
    """, (participant_id, category, reached_points, max_points, percentage))
    connection.commit()

# Teilnehmer laden
def load_participants(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM participants")
    return cursor.fetchall()

# Tests laden
def load_tests(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM tests")
    return cursor.fetchall()

# CSV-Export für Teilnehmer und Tests
def export_to_csv(connection):
    participants = pd.read_sql_query("SELECT * FROM participants", connection)
    tests = pd.read_sql_query("SELECT * FROM tests", connection)

    participants.to_csv("participants.csv", index=False)
    tests.to_csv("tests.csv", index=False)

# CSV-Import für Teilnehmer und Tests
def import_from_csv(connection):
    participants = pd.read_csv("participants.csv")
    tests = pd.read_csv("tests.csv")

    participants.to_sql("participants", connection, if_exists="replace", index=False)
    tests.to_sql("tests", connection, if_exists="replace", index=False)

# Streamlit GUI
def main():
    connection = setup_database()
    st.title("Mathematik-Kurs Teilnehmerverwaltung")

    # Teilnehmer hinzufügen
    with st.form("add_participant"):
        st.subheader("Teilnehmer hinzufügen")
        name = st.text_input("Name")
        sv_number = st.text_input("SV-Nummer (XXXXDDMMYY)")
        job = st.text_input("Berufswunsch (Großbuchstaben)")
        entry_date = st.date_input("Eintrittsdatum", value=datetime.today())
        exit_date = st.date_input("Austrittsdatum", value=datetime.today())
        status = "Aktiv" if exit_date > datetime.today().date() else "Inaktiv"
        submitted = st.form_submit_button("Hinzufügen")

        if submitted and name and sv_number and job:
            add_participant(connection, name, sv_number, job, entry_date.strftime("%d.%m.%Y"), exit_date.strftime("%d.%m.%Y"), status)
            st.success("Teilnehmer hinzugefügt!")

    # Testergebnisse hinzufügen
    st.subheader("Testergebnisse hinzufügen")
    participants = load_participants(connection)
    participant_options = {f"{p[1]} ({p[0]})": p[0] for p in participants}
    selected_participant = st.selectbox("Teilnehmer auswählen", ["Teilnehmer auswählen"] + list(participant_options.keys()))

    if selected_participant != "Teilnehmer auswählen":
        participant_id = participant_options[selected_participant]
        categories = ["Textaufgaben", "Raumvorstellung", "Gleichungen", "Brüche", "Grundrechenarten", "Zahlenraum"]
        total_reached = 0
        total_max = 0

        with st.form("add_test"):
            test_data = {}
            for category in categories:
                reached = st.number_input(f"{category} erreichte Punkte", min_value=0, step=1, key=f"{category}_reached")
                max_points = st.number_input(f"{category} max. Punkte", min_value=0, step=1, key=f"{category}_max")
                test_data[category] = (reached, max_points)
                total_reached += reached
                total_max += max_points

            submitted_test = st.form_submit_button("Testergebnis hinzufügen")

            if submitted_test:
                if total_max == 100:
                    for category, (reached, max_points) in test_data.items():
                        add_test(connection, participant_id, category, reached, max_points)
                    st.success(f"Testergebnisse für {selected_participant} hinzugefügt!")
                else:
                    st.error("Die maximalen Punkte müssen insgesamt 100 ergeben!")

    # Tabelle anzeigen
    st.subheader("Teilnehmerübersicht")
    participants_df = pd.read_sql_query("SELECT * FROM participants", connection)
    st.dataframe(participants_df)

    st.subheader("Testübersicht")
    tests_df = pd.read_sql_query("SELECT * FROM tests", connection)
    st.dataframe(tests_df)

    # Export/Import
    if st.button("Exportieren nach CSV"):
        export_to_csv(connection)
        st.success("Daten exportiert!")

    if st.button("Importieren von CSV"):
        import_from_csv(connection)
        st.success("Daten importiert!")

if __name__ == "__main__":
    main()
