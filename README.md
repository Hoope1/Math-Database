# Math-Database
Streamlit-based application designed to manage participant data and test results for mathematics courses. This tool is ideal for instructors looking for an easy-to-use and interactive platform to handle class records.
# Math Course Management System

A powerful **Streamlit-based application** designed to manage participant data and test results for mathematics courses. This tool is ideal for instructors looking for an easy-to-use and interactive platform to handle class records.

---

## **Features**

### **Participant Management**
- Add, edit, and manage participant information.
- Store details such as name, social security number (SV-number), job aspirations, and entry/exit dates.
- Automatically track participant status as active or inactive based on exit dates.

### **Test Management**
- Add test results for participants across six categories:
  - Text problems
  - Spatial awareness
  - Equations
  - Fractions
  - Arithmetic
  - Number systems
- Automatic validation of scores:
  - The sum of maximum points must always equal 100.
  - Calculates percentages for each category and overall scores.

### **Interactive Table**
- View all participants and their latest test results in a clear, sortable table.
- Includes a status column (active/inactive) and options to edit participant data.

### **Data Persistence**
- Stores data in a **SQLite database** for efficient and reliable storage.
- Offers CSV import/export functionality for data backup and portability.

---

## **Installation**

1. Clone the repository:
   ```bash
   git clone https://github.com/USERNAME/math-course-management.git
   ```

2. Navigate to the project directory:
   ```bash
   cd math-course-management
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   streamlit run main.py
   ```

---

## **Requirements**
- Python 3.8 or higher
- Streamlit
- Pandas
- SQLite3

---

## **Usage**
- Open the application in your web browser via the provided local Streamlit link.
- Manage participants and their test data interactively.
- Export data to CSV or import existing records.

---

## **Contributing**
If you'd like to contribute to this project, please fork the repository and submit a pull request with your changes.

---

## **License**
This project is licensed under the MIT License.
