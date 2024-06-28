import sys
import datetime
import sqlite3

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QComboBox, QPushButton, QVBoxLayout,
    QMessageBox, QDialog, QTableWidget, QTableWidgetItem, QDateEdit, QTabWidget,
    QCheckBox, QFormLayout
)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QDoubleValidator, QIntValidator, QIcon
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import seaborn as sns
import pandas as pd
import matplotlib.colors as mcolors
import colorsys
import yfinance as yf  # type: ignore

pd.set_option('future.no_silent_downcasting', True)

# User login dialog
class UserLoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Login")
        self.layout = QVBoxLayout()

        self.name_label = QLabel("Enter your name:")  # Label for user to enter name
        self.name_input = QLineEdit()  # Input field for user name
        self.layout.addWidget(self.name_label)
        self.layout.addWidget(self.name_input)

        self.login_button = QPushButton("Login")  # Login button
        self.login_button.clicked.connect(self.login)  # Connect login button to login method
        self.layout.addWidget(self.login_button)

        self.setLayout(self.layout)

    def login(self):
        name = self.name_input.text()
        if not name:
            QMessageBox.warning(self, "Error", "Name cannot be empty")  # Show warning if name is empty
            return
        self.accept()  # Accept the dialog if name is not empty


# Main Finance Application
class FinanceApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fire Journey")
        # Set the window icon
        self.setWindowIcon(QIcon('applogo.png'))  # Replace 'path_to_icon/icon.png' with the path to your icon file
        # Set the initial window size
        self.resize(1200, 800)

        self.conn = sqlite3.connect('finance.db')  # Connect to SQLite database
        self.c = self.conn.cursor()
        self.create_tables()  # Create necessary tables

        self.user_id = None
        self.user_name = None
        self.login_user()  # Show login dialog

        self.main_layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)
        self.setLayout(self.main_layout)

        self.figure_net_worth = plt.figure()
        self.canvas_net_worth = FigureCanvas(self.figure_net_worth)

        self.current_portfolio_value = 0.0  # Initialize the portfolio value variable

        self.setup_tabs()  # Setup tabs for the application
        self.update_all()  # Call update_all on startup

    def create_tables(self):
        # SQL queries to create necessary tables if they don't exist
        tables = {
            'users': '''CREATE TABLE IF NOT EXISTS users
                        (user_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)''',
            'records': '''CREATE TABLE IF NOT EXISTS records
                        (record_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date TEXT NOT NULL, category TEXT, type TEXT, amount REAL, linked_loan INTEGER,
                        FOREIGN KEY(user_id) REFERENCES users(user_id), FOREIGN KEY(linked_loan) REFERENCES loans(id))''',
            'recurring_records': '''CREATE TABLE IF NOT EXISTS recurring_records
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date TEXT NOT NULL, category TEXT, type TEXT, amount REAL, frequency TEXT, linked_loan INTEGER,
                        FOREIGN KEY(user_id) REFERENCES users(user_id), FOREIGN KEY(linked_loan) REFERENCES loans(id))''',
            'portfolio': '''CREATE TABLE IF NOT EXISTS portfolio
                        (portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, symbol TEXT NOT NULL, purchase_price REAL, quantity REAL, company_name TEXT, purchase_date TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(user_id))''',
            'assets': '''CREATE TABLE IF NOT EXISTS assets
                        (asset_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT NOT NULL, purchase_price REAL, year_of_purchase INTEGER,
                        FOREIGN KEY(user_id) REFERENCES users(user_id))''',
            'loans': '''CREATE TABLE IF NOT EXISTS loans
                        (loan_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT NOT NULL, principal REAL, initial_principal REAL, interest_rate REAL, signing_date TEXT, interest REAL, last_calculated_date TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(user_id))''',
            'net_worth_history': '''CREATE TABLE IF NOT EXISTS net_worth_history
                        (user_id INTEGER, date TEXT PRIMARY KEY, net_worth REAL,
                        FOREIGN KEY(user_id) REFERENCES users(user_id))''',
            'loan_repayment': '''CREATE TABLE IF NOT EXISTS loan_repayment
                                (loan_id INTEGER PRIMARY KEY, repaid_principal REAL,
                                FOREIGN KEY(loan_id) REFERENCES loans(loan_id))'''
        }

        for table, query in tables.items():
            self.c.execute(query)

        self.conn.commit()

    def login_user(self):
        dialog = UserLoginDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.user_name = dialog.name_input.text()
            self.c.execute("SELECT user_id FROM users WHERE name = ?", (self.user_name,))
            user = self.c.fetchone()
            if user:
                self.user_id = user[0]  # Set user_id if user exists
            else:
                self.c.execute("INSERT INTO users (name) VALUES (?)", (self.user_name,))
                self.conn.commit()
                self.user_id = self.c.lastrowid  # Set user_id for new user
        else:
            sys.exit(0)  # Exit the application if login is not accepted

    def setup_tabs(self):
        # Setup all the tabs for the application
        self.setup_graph_tab()
        self.setup_portfolio_tab()
        self.setup_assets_loans_tab()
        self.setup_net_worth_tab()
        self.setup_fire_tab()

    def update_all(self):
        # Update all relevant data in the application
        self.update_recurring_records()
        self.show_graph()
        self.update_portfolio()
        self.update_assets_table()
        self.update_net_worth()
        self.update_loans_table()

    # Tab setup methods
    def setup_graph_tab(self):
        self.graph_tab = QWidget()
        graph_layout = QVBoxLayout()

        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        graph_layout.addWidget(self.canvas)

        self.add_entry_button = QPushButton("Add Entry")
        self.add_entry_button.clicked.connect(self.show_form)
        graph_layout.addWidget(self.add_entry_button)

        self.view_records_button = QPushButton("View Records")
        self.view_records_button.clicked.connect(self.show_records)
        graph_layout.addWidget(self.view_records_button)

        self.view_recurring_records_button = QPushButton("View Recurring Records")
        self.view_recurring_records_button.clicked.connect(self.show_recurring_records)
        graph_layout.addWidget(self.view_recurring_records_button)

        self.predict_expenses_button = QPushButton("Predict Expenses")
        self.predict_expenses_button.clicked.connect(self.show_predict_expenses)
        graph_layout.addWidget(self.predict_expenses_button)

        self.graph_tab.setLayout(graph_layout)
        self.tab_widget.addTab(self.graph_tab, "Income and Expenses")

    def setup_portfolio_tab(self):
        self.portfolio_tab = QWidget()
        portfolio_layout = QVBoxLayout()

        self.portfolio_table = QTableWidget()
        self.portfolio_table.setColumnCount(6)
        self.portfolio_table.setHorizontalHeaderLabels(["Symbol", "Company Name", "Purchase Price", "Quantity", "Current Price", "Total P&L"])
        self.portfolio_table.horizontalHeader().setStretchLastSection(True)
        self.portfolio_table.setAlternatingRowColors(True)
        self.portfolio_table.setStyleSheet("alternate-background-color: #f0f0f0;")
        self.portfolio_table.horizontalHeader().setStyleSheet("font-weight: bold; font-size: 14px;")
        self.portfolio_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Make table read-only
        portfolio_layout.addWidget(self.portfolio_table)

        self.add_stock_button = QPushButton("Add Stock")
        self.add_stock_button.clicked.connect(self.add_stock)
        portfolio_layout.addWidget(self.add_stock_button)

        self.update_portfolio_button = QPushButton("Update Portfolio")
        self.update_portfolio_button.clicked.connect(self.update_portfolio)
        portfolio_layout.addWidget(self.update_portfolio_button)

        self.view_all_stocks_button = QPushButton("View All Records")
        self.view_all_stocks_button.clicked.connect(self.show_all_stocks)
        portfolio_layout.addWidget(self.view_all_stocks_button)

        self.remove_stock_button = QPushButton("Remove Holding")
        self.remove_stock_button.clicked.connect(self.remove_stock)
        portfolio_layout.addWidget(self.remove_stock_button)

        self.portfolio_tab.setLayout(portfolio_layout)
        self.tab_widget.addTab(self.portfolio_tab, "Portfolio")

    def setup_net_worth_tab(self):
        self.net_worth_tab = QWidget()
        net_worth_layout = QVBoxLayout()

        # Large "Net Worth" label at the top
        self.net_worth_title_label = QLabel("Net Worth")
        self.net_worth_title_label.setAlignment(Qt.AlignCenter)
        self.net_worth_title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        net_worth_layout.addWidget(self.net_worth_title_label)

        # Current net worth label
        self.net_worth_label = QLabel("$0.00")
        self.net_worth_label.setAlignment(Qt.AlignCenter)
        self.net_worth_label.setStyleSheet("font-size: 20px; color: green;")
        net_worth_layout.addWidget(self.net_worth_label)

        self.update_net_worth_button = QPushButton("Update Net Worth")
        self.update_net_worth_button.clicked.connect(self.update_net_worth)
        net_worth_layout.addWidget(self.update_net_worth_button)

        # Add the net worth graph canvas to the layout
        net_worth_layout.addWidget(self.canvas_net_worth)

        self.net_worth_tab.setLayout(net_worth_layout)
        self.tab_widget.addTab(self.net_worth_tab, "Net Worth")

    def setup_fire_tab(self):
        self.fire_tab = QWidget()
        fire_layout = QVBoxLayout()

        form_layout = QFormLayout()

        portfolio_value, annual_income = self.get_default_values()

        self.portfolio_value_input = QLineEdit()
        self.portfolio_value_input.setValidator(QDoubleValidator(0, 1e9, 2))
        self.portfolio_value_input.setText(str(portfolio_value))  # Set default portfolio value
        form_layout.addRow("Portfolio Value:", self.portfolio_value_input)

        self.annual_income_input = QLineEdit()
        self.annual_income_input.setValidator(QDoubleValidator(0, 1e9, 2))
        self.annual_income_input.setText(str(annual_income))  # Set default annual income
        form_layout.addRow("Annual Income:", self.annual_income_input)

        self.savings_rate_input = QLineEdit()
        self.savings_rate_input.setValidator(QDoubleValidator(0, 100, 2))
        self.savings_rate_input.setText("40")  # Set default savings rate
        form_layout.addRow("Savings Rate (%):", self.savings_rate_input)

        self.income_growth_input = QLineEdit()
        self.income_growth_input.setValidator(QDoubleValidator(0, 100, 2))
        self.income_growth_input.setText("2")  # Set default income growth rate
        form_layout.addRow("Income Growth Rate (%):", self.income_growth_input)

        self.income_growth_duration_input = QLineEdit()
        self.income_growth_duration_input.setValidator(QIntValidator(0, 100))
        self.income_growth_duration_input.setText("20")  # Set default income growth duration
        form_layout.addRow("Income Growth Duration (years):", self.income_growth_duration_input)

        self.annual_expenses_input = QLineEdit()
        self.annual_expenses_input.setValidator(QDoubleValidator(0, 1e9, 2))
        initial_savings_rate = float(self.savings_rate_input.text().strip()) / 100
        initial_annual_expenses = annual_income * (1 - initial_savings_rate)
        self.annual_expenses_input.setText(f"{initial_annual_expenses:.2f}")
        form_layout.addRow("Annual Expenses:", self.annual_expenses_input)

        self.withdrawal_rate_input = QLineEdit()
        self.withdrawal_rate_input.setValidator(QDoubleValidator(0, 100, 2))
        self.withdrawal_rate_input.setText("4.0")  # Set default withdrawal rate
        form_layout.addRow("Withdrawal Rate (%):", self.withdrawal_rate_input)

        self.annual_roi_input = QLineEdit()
        self.annual_roi_input.setValidator(QDoubleValidator(0, 100, 2))
        self.annual_roi_input.setText("5.0")  # Set default annual ROI
        form_layout.addRow("Annual ROI (%):", self.annual_roi_input)

        self.include_loan_expenses_checkbox = QCheckBox()
        self.include_loan_expenses_checkbox.setToolTip("If checked, annual loan expenses will be deducted from the annual income until the loan is repaid.")
        form_layout.addRow("Include Loan Expenses:", self.include_loan_expenses_checkbox)

        self.calculate_button = QPushButton("Calculate")
        self.calculate_button.clicked.connect(self.calculate_fire)
        form_layout.addRow(self.calculate_button)

        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignCenter)  # Center the text horizontally
        fire_layout.addWidget(self.result_label)

        fire_layout.addLayout(form_layout)

        self.figure_fire = plt.figure()
        self.canvas_fire = FigureCanvas(self.figure_fire)
        fire_layout.addWidget(self.canvas_fire)

        self.fire_tab.setLayout(fire_layout)
        self.tab_widget.addTab(self.fire_tab, "FIRE Calculator")

        self.savings_rate_input.textChanged.connect(self.update_annual_expenses)
        self.annual_expenses_input.textChanged.connect(self.update_savings_rate)

    def setup_assets_loans_tab(self):
        self.assets_loans_tab = QWidget()
        assets_loans_layout = QVBoxLayout()

        self.setup_assets_table(assets_loans_layout)
        self.setup_loans_table(assets_loans_layout)

        self.assets_loans_tab.setLayout(assets_loans_layout)
        self.tab_widget.addTab(self.assets_loans_tab, "Assets and Loans")

    def setup_assets_table(self, layout):
        self.assets_table = QTableWidget()
        self.assets_table.setColumnCount(3)
        self.assets_table.setHorizontalHeaderLabels(["Name", "Purchase Price", "Year of Purchase"])
        self.assets_table.horizontalHeader().setStretchLastSection(True)
        self.assets_table.setAlternatingRowColors(True)
        self.assets_table.setStyleSheet("alternate-background-color: #f0f0f0;")
        self.assets_table.horizontalHeader().setStyleSheet("font-weight: bold; font-size: 14px;")
        self.assets_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Make table read-only
        layout.addWidget(self.assets_table)

        self.add_asset_button = QPushButton("Add Asset")
        self.add_asset_button.clicked.connect(self.add_asset)
        layout.addWidget(self.add_asset_button)

        self.remove_asset_button = QPushButton("Remove Asset")
        self.remove_asset_button.clicked.connect(self.remove_asset)
        layout.addWidget(self.remove_asset_button)

    def setup_loans_table(self, layout):
        self.loans_table = QTableWidget()
        self.loans_table.setColumnCount(7)
        self.loans_table.setHorizontalHeaderLabels(["Name", "Amount", "Interest Rate", "Signing Date", "Current Interest", "Principal to Repay", "Next Repayment Date"])
        self.loans_table.horizontalHeader().setStretchLastSection(True)
        self.loans_table.setAlternatingRowColors(True)
        self.loans_table.setStyleSheet("alternate-background-color: #f0f0f0;")
        self.loans_table.horizontalHeader().setStyleSheet("font-weight: bold; font-size: 14px;")
        self.loans_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Make table read-only
        layout.addWidget(self.loans_table)

        self.add_loan_button = QPushButton("Add Loan")
        self.add_loan_button.clicked.connect(self.add_loan)
        layout.addWidget(self.add_loan_button)

        self.remove_loan_button = QPushButton("Remove Loan")
        self.remove_loan_button.clicked.connect(self.remove_loan)
        layout.addWidget(self.remove_loan_button)

    # Asset and loan addition methods
    def add_asset(self):
        self.open_dialog("Add Asset", self.save_asset,
                         ["Asset Name", "Purchase Price", "Year of Purchase"],
                         [QLineEdit(), QLineEdit(), QLineEdit()],
                         [None, QDoubleValidator(0.99, 99.99, 2), QIntValidator(1900, datetime.datetime.now().year)]
                         )

    def add_loan(self):
        self.open_dialog("Add Loan", self.save_loan,
                         ["Loan Name", "Amount", "Interest Rate (%)", "Signing Date (YYYY-MM-DD)"],
                         [QLineEdit(), QLineEdit(), QLineEdit(), QDateEdit()],
                         [None, QDoubleValidator(0.99, 999999.99, 2), QDoubleValidator(0.0, 100.0, 2)]
                         )

    def open_dialog(self, title, save_func, labels, inputs, validators=None):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout()

        for i, label in enumerate(labels):
            layout.addWidget(QLabel(label))
            if isinstance(inputs[i], QDateEdit):
                inputs[i].setCalendarPopup(True)
                inputs[i].setDisplayFormat("yyyy-MM-dd")
                inputs[i].setDate(QDate.currentDate())
            elif isinstance(inputs[i], QComboBox):
                if inputs[i].count() == 0:  # Add items only if the list is empty
                    if i == 1:  # Category
                        inputs[i].addItems(
                            ["Groceries", "Utilities", "Rent", "Entertainment", "Transport", "Healthcare", "Paycheck", "Investments", "Other"])
                    elif i == 2:  # Type
                        inputs[i].addItems(["Income", "Expense"])
                    elif i == 4:  # Frequency
                        inputs[i].addItems(["None", "Daily", "Weekly", "Monthly", "Annual"])
            elif validators and i < len(validators) and validators[i] is not None:
                inputs[i].setValidator(validators[i])
            layout.addWidget(inputs[i])

        add_button = QPushButton("Add")
        add_button.clicked.connect(lambda: save_func(dialog, inputs))
        layout.addWidget(add_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def save_asset(self, dialog, inputs):
        try:
            name, purchase_price, year_of_purchase = [inp.text().strip() for inp in inputs]
            if not name or not purchase_price or not year_of_purchase:
                raise ValueError("All fields must be filled.")
            self.c.execute('INSERT INTO assets (user_id, name, purchase_price, year_of_purchase) VALUES (?, ?, ?, ?)',
                           (self.user_id, name, float(purchase_price), int(year_of_purchase)))
            self.conn.commit()
            QMessageBox.information(self, "Success", "Asset added successfully")
            dialog.close()
            self.update_all()  # Update all relevant data
        except ValueError as ve:
            QMessageBox.critical(self, "Input Error", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def save_loan(self, dialog, inputs):
        try:
            name, principal, interest_rate, signing_date = [inp.text().strip() for inp in inputs[:3]] + [inputs[3].text().strip()]

            if not name or not principal or not interest_rate or not signing_date:
                raise ValueError("All fields must be filled.")

            initial_principal = float(principal)

            # Ensure interest is set to 0.0
            interest = 0.0
            last_calculated_date = signing_date

            self.c.execute('''
                INSERT INTO loans (user_id, name, principal, initial_principal, interest_rate, signing_date, last_calculated_date, interest)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (self.user_id, name, initial_principal, initial_principal, float(interest_rate), signing_date, last_calculated_date, interest))

            self.conn.commit()
            QMessageBox.information(self, "Success", "Loan added successfully")
            dialog.close()
            self.update_all()  # Update all relevant data


        except ValueError as ve:
            QMessageBox.critical(self, "Input Error", str(ve))
            print(f"ValueError: {ve}")  # Debug print statement for ValueError
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            print(f"Exception: {e}")  # Debug print statement for any other exceptions

    def remove_asset(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Remove Asset")
        dialog.resize(800, 600)
        layout = QVBoxLayout()

        self.c.execute('SELECT asset_id, name, purchase_price, year_of_purchase FROM assets WHERE user_id = ?', (self.user_id,))
        assets = self.c.fetchall()

        self.remove_asset_table = QTableWidget()
        self.remove_asset_table.setColumnCount(4)
        self.remove_asset_table.setHorizontalHeaderLabels(["Select", "Name", "Purchase Price", "Year of Purchase"])
        self.remove_asset_table.setRowCount(len(assets))
        self.remove_asset_table.horizontalHeader().setStretchLastSection(True)
        self.remove_asset_table.setAlternatingRowColors(True)
        self.remove_asset_table.setStyleSheet("alternate-background-color: #f0f0f0;")
        self.remove_asset_table.horizontalHeader().setStyleSheet("font-weight: bold; font-size: 14px;")

        for row, asset in enumerate(assets):
            asset_id, name, purchase_price, year_of_purchase = asset
            checkbox = QCheckBox()
            checkbox.setStyleSheet("margin:auto;")  # Center the checkbox
            checkbox.setProperty('asset_id', asset_id)
            self.remove_asset_table.setCellWidget(row, 0, checkbox)

            items = [name, f"{purchase_price:.2f}", str(year_of_purchase)]
            for col, item in enumerate(items, start=1):
                cell_item = QTableWidgetItem(item)
                cell_item.setTextAlignment(Qt.AlignCenter)
                self.remove_asset_table.setItem(row, col, cell_item)

        layout.addWidget(self.remove_asset_table)

        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(lambda: self.confirm_remove_asset(dialog))
        layout.addWidget(remove_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def confirm_remove_asset(self, dialog):
        try:
            for row in range(self.remove_asset_table.rowCount()):
                checkbox = self.remove_asset_table.cellWidget(row, 0)
                if checkbox.isChecked():
                    asset_id = checkbox.property('asset_id')
                    self.c.execute('DELETE FROM assets WHERE asset_id = ?', (asset_id,))
            self.conn.commit()
            QMessageBox.information(self, "Success", "Selected assets removed")
            dialog.close()
            self.update_all()  # Update all relevant data
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def remove_loan(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Remove Loan")
        dialog.resize(800, 600)
        layout = QVBoxLayout()

        self.c.execute('SELECT loan_id, name, principal, interest_rate, signing_date, interest FROM loans WHERE user_id = ?', (self.user_id,))
        loans = self.c.fetchall()

        self.remove_loan_table = QTableWidget()
        self.remove_loan_table.setColumnCount(7)
        self.remove_loan_table.setHorizontalHeaderLabels(["Select", "Name", "Principal", "Interest Rate", "Signing Date", "Current Interest", "Next Repayment Date"])
        self.remove_loan_table.setRowCount(len(loans))
        self.remove_loan_table.horizontalHeader().setStretchLastSection(True)
        self.remove_loan_table.setAlternatingRowColors(True)
        self.remove_loan_table.setStyleSheet("alternate-background-color: #f0f0f0;")
        self.remove_loan_table.horizontalHeader().setStyleSheet("font-weight: bold; font-size: 14px;")

        for row, loan in enumerate(loans):
            loan_id, name, principal, interest_rate, signing_date, interest = loan
            checkbox = QCheckBox()
            checkbox.setStyleSheet("margin:auto;")  # Center the checkbox
            checkbox.setProperty('loan_id', loan_id)
            self.remove_loan_table.setCellWidget(row, 0, checkbox)

            items = [name, f"{principal:.2f}", f"{interest_rate:.2f}%", signing_date, f"{interest:.2f}", "No Linked Expense"]
            for col, item in enumerate(items, start=1):
                cell_item = QTableWidgetItem(item)
                cell_item.setTextAlignment(Qt.AlignCenter)
                self.remove_loan_table.setItem(row, col, cell_item)

        layout.addWidget(self.remove_loan_table)

        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(lambda: self.confirm_remove_loan(dialog))
        layout.addWidget(remove_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def confirm_remove_loan(self, dialog):
        try:
            for row in range(self.remove_loan_table.rowCount()):
                checkbox = self.remove_loan_table.cellWidget(row, 0)
                if checkbox.isChecked():
                    loan_id = checkbox.property('loan_id')
                    print(f"Removing loan with ID: {loan_id}")  # Debug print
                    if loan_id:
                        # Remove linked recurring records
                        self.c.execute('DELETE FROM recurring_records WHERE linked_loan = ?', (loan_id,))
                        # Remove associated records in the main records table
                        self.c.execute('DELETE FROM records WHERE linked_loan = ?', (loan_id,))
                        # Reset principal and interest
                        self.c.execute('UPDATE loans SET principal = 0, interest = 0 WHERE loan_id = ?', (loan_id,))
                        self.c.execute('DELETE FROM loans WHERE loan_id = ?', (loan_id,))
                        self.c.execute('DELETE FROM loan_repayment WHERE loan_id = ?', (loan_id,))
            self.conn.commit()
            QMessageBox.information(self, "Success", "Selected loans removed")
            dialog.close()
            self.update_all()  # Update all relevant data
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # Update methods
    def update_loans_table(self):
        # Explicitly selecting the columns
        self.c.execute('SELECT loan_id, name, principal, initial_principal, interest_rate, signing_date, last_calculated_date, interest FROM loans WHERE user_id = ?', (self.user_id,))
        loans = self.c.fetchall()
        self.loans_table.setRowCount(len(loans))
        today = datetime.datetime.today().date()

        for row, loan in enumerate(loans):
            loan_id, name, principal, initial_principal, interest_rate, signing_date, last_calculated_date, interest = loan

            try:
                signing_date = datetime.datetime.strptime(signing_date, '%Y-%m-%d').date()
                last_calculated_date = datetime.datetime.strptime(last_calculated_date, '%Y-%m-%d').date()
            except ValueError as ve:
                print(f"Date conversion error: {ve}")

            days_elapsed = (today - last_calculated_date).days
            accumulated_interest = (initial_principal * interest_rate / 100) * (days_elapsed / 365)  # Simple interest calculation
            try:
                current_interest = max(0, float(interest) + accumulated_interest)  # Ensure interest is not negative
            except ValueError as ve:
                print(f"Interest conversion error: {ve}")

            self.c.execute('SELECT repaid_principal FROM loan_repayment WHERE loan_id = ?', (loan_id,))
            repaid_principal_data = self.c.fetchone()
            repaid_principal = repaid_principal_data[0] if repaid_principal_data else 0.0

            principal_to_repay = max(0, principal - repaid_principal)  # Ensure principal to repay is not negative
            self.c.execute('SELECT date FROM recurring_records WHERE linked_loan = ? AND user_id = ? ORDER BY date LIMIT 1', (loan_id, self.user_id))
            next_repayment_date = self.c.fetchone()
            if next_repayment_date:
                next_repayment_date = next_repayment_date[0]
            else:
                next_repayment_date = "No Linked Expense"

            if principal_to_repay == 0:
                principal_to_repay_str = "Loan Repaid"
            else:
                principal_to_repay_str = f"{principal_to_repay:.2f}"

            items = [name, f"{initial_principal:.2f}", f"{interest_rate:.2f}%", signing_date.strftime('%Y-%m-%d'), f"{current_interest:.2f}", principal_to_repay_str, next_repayment_date]
            for col, item in enumerate(items):
                cell_item = QTableWidgetItem(item)
                cell_item.setTextAlignment(Qt.AlignCenter)
                self.loans_table.setItem(row, col, cell_item)

            # Update last_calculated_date in the database to today after interest calculation
            self.c.execute('UPDATE loans SET last_calculated_date = ?, interest = ? WHERE user_id = ? AND loan_id = ?', (today.strftime('%Y-%m-%d'), current_interest, self.user_id, loan_id))

        self.conn.commit()

    def update_assets_table(self):
        self.c.execute('SELECT name, purchase_price, year_of_purchase FROM assets WHERE user_id = ?', (self.user_id,))
        assets = self.c.fetchall()
        self.assets_table.setRowCount(len(assets))
        for row, asset in enumerate(assets):
            name, purchase_price, year_of_purchase = asset
            items = [name, f"{purchase_price:.2f}", f"{year_of_purchase}"]
            for col, item in enumerate(items):
                cell_item = QTableWidgetItem(item)
                cell_item.setTextAlignment(Qt.AlignCenter)
                self.assets_table.setItem(row, col, cell_item)

    def update_recurring_records(self):
        self.c.execute('SELECT id, date, category, type, amount, frequency, linked_loan FROM recurring_records WHERE user_id = ?', (self.user_id,))
        recurring_records = self.c.fetchall()

        for record in recurring_records:
            record_id, date, category, record_type, amount, frequency, linked_loan = record
            next_due_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
            end_date = datetime.datetime.today().date()

            while next_due_date <= end_date:
                if linked_loan:
                    self.c.execute('SELECT loan_id, principal, initial_principal, interest, interest_rate, last_calculated_date FROM loans WHERE user_id = ? AND loan_id = ?', (self.user_id, linked_loan))
                    loan = self.c.fetchone()
                    if loan:
                        loan_id, principal, initial_principal, current_interest, annual_interest_rate, last_calculated_date = loan
                        last_calculated_date = datetime.datetime.strptime(last_calculated_date, '%Y-%m-%d').date()

                        # Calculate interest for the period
                        days_elapsed = (next_due_date - last_calculated_date).days
                        daily_interest_rate = annual_interest_rate / 365 / 100
                        new_interest = principal * daily_interest_rate * days_elapsed
                        current_interest += new_interest

                        # Ensure the amount is positive
                        amount = abs(float(amount))

                        # Apply the payment to the interest first, then principal
                        if amount <= current_interest:
                            current_interest -= amount
                        else:
                            remaining_payment = amount - current_interest
                            current_interest = 0
                            principal = max(0, principal - remaining_payment)

                        # Update loan information in the database
                        self.c.execute('UPDATE loans SET principal = ?, interest = ?, last_calculated_date = ? WHERE user_id = ? AND loan_id = ?',
                                       (principal, current_interest, next_due_date.strftime('%Y-%m-%d'), self.user_id, loan_id))

                    else:
                        # Loan not found, break out of the loop
                        break

                # Insert the record
                self.c.execute('INSERT OR IGNORE INTO records (user_id, date, category, type, amount, linked_loan) VALUES (?, ?, ?, ?, ?, ?)',
                               (self.user_id, next_due_date.strftime('%Y-%m-%d'), category, record_type, float(amount), linked_loan))
                next_due_date = self.calculate_next_due_date(next_due_date, frequency)

            # Update the next due date of the recurring record
            self.c.execute('UPDATE recurring_records SET date = ? WHERE id = ?', (next_due_date.strftime('%Y-%m-%d'), record_id))

        # Commit the changes to the database
        self.conn.commit()

    def calculate_next_due_date(self, current_date, frequency):
        if frequency == 'Daily':
            return current_date + datetime.timedelta(days=1)
        elif frequency == 'Weekly':
            return current_date + datetime.timedelta(weeks=1)
        elif frequency == 'Monthly':
            return current_date + datetime.timedelta(days=30)
        elif frequency == 'Annual':
            return current_date + datetime.timedelta(days=365)
        else:
            return current_date

    # Graph and prediction methods
    def show_predict_expenses(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Predict Expenses")
        dialog.resize(400, 300)
        layout = QVBoxLayout()

        prediction_periods = ["Next Day", "Next Week", "Next Month"]
        self.period_combobox = QComboBox()
        self.period_combobox.addItems(prediction_periods)
        layout.addWidget(self.period_combobox)

        self.predict_button = QPushButton("Predict")
        self.predict_button.clicked.connect(self.predict_expenses)
        layout.addWidget(self.predict_button)

        self.result_label = QLabel("")
        layout.addWidget(self.result_label)

        dialog.setLayout(layout)
        dialog.exec_()

    def predict_expenses(self):
        period = self.period_combobox.currentText()

        if period == "Next Day":
            days = 1
        elif period == "Next Week":
            days = 7
        elif period == "Next Month":
            days = 30

        # Fetching past expense records, excluding Income and Investments
        self.c.execute('''
            SELECT date, amount FROM records 
            WHERE user_id = ? AND type = "Expense" AND category != "Investments"
        ''', (self.user_id,))
        records = self.c.fetchall()
        df = pd.DataFrame(records, columns=['date', 'amount'])
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df = df.resample('D').sum().fillna(0)

        # Preparing the data for the model
        df['days'] = (df.index - df.index.min()).days
        X = df[['days']]
        y = df['amount']

        # Training the model
        model = LinearRegression()
        model.fit(X, y)

        # Predicting expenses
        last_day = df['days'].max()
        future_days = pd.DataFrame({'days': range(last_day + 1, last_day + days + 1)})
        predictions = model.predict(future_days)

        # Displaying the result
        total_expenses = predictions.sum()
        self.result_label.setText(f"Predicted expenses for {period}:\n${total_expenses:.2f}")
        self.result_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.result_label.setAlignment(Qt.AlignCenter)

    def show_graph(self):
        self.tab_widget.setCurrentWidget(self.graph_tab)

        # Fetch regular records from the past 7 days
        self.c.execute('''
            SELECT strftime("%w", date) as weekday, sum(amount), type 
            FROM records 
            WHERE user_id = ? AND date >= date('now', 'weekday 0', '-7 days') AND date < date('now', 'weekday 0')
            GROUP BY weekday, type
        ''', (self.user_id,))
        data = self.c.fetchall()

        # Fetch recurring records that fall within the past 7 days
        today = datetime.datetime.today().date()
        last_week = today - datetime.timedelta(days=7)

        self.c.execute('''
            SELECT id, date, category, type, amount, frequency, linked_loan 
            FROM recurring_records 
            WHERE user_id = ? AND category != "Investments"
        ''', (self.user_id,))
        recurring_records = self.c.fetchall()

        recurring_data = []
        for record in recurring_records:
            record_id, date, category, record_type, amount, frequency, linked_loan = record
            next_due_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
            while next_due_date <= today:
                if next_due_date >= last_week:
                    weekday = next_due_date.weekday()
                    recurring_data.append((str(weekday), amount, record_type))
                next_due_date = self.calculate_next_due_date(next_due_date, frequency)

        # Combine regular and recurring data
        combined_data = data + recurring_data

        # Create dataframe for visualization
        df = pd.DataFrame(combined_data, columns=['weekday', 'amount', 'type'])
        all_days = pd.DataFrame({'weekday': [str(i) for i in range(7)] * 2, 'amount': [0] * 14, 'type': ['Expense'] * 7 + ['Income'] * 7})
        df = all_days.merge(df, on=['weekday', 'type'], how='left').fillna(0).infer_objects(copy=False)
        df = df.drop('amount_x', axis=1).rename(columns={'amount_y': 'amount'}).infer_objects(copy=False)

        self.figure.clear()
        self.figure.set_size_inches(12, 8)
        ax = self.figure.add_subplot(111)

        def lighten_color(color, amount=0.5):
            try:
                c = mcolors.cnames[color]
            except:
                c = color
            c = colorsys.rgb_to_hls(*mcolors.to_rgb(c))
            return colorsys.hls_to_rgb(c[0], 1 - amount * (1 - c[1]), c[2])

        colors = {'Expense': lighten_color('darkred', 0.5), 'Income': lighten_color('darkgreen', 0.5)}
        sns.barplot(x='weekday', y='amount', hue='type', data=df, palette=colors, edgecolor=".2", ax=ax)

        ax.set_title('Weekly Income and Expenses')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)

        plt.rcParams['font.sans-serif'] = ['Arial']

        for p in ax.patches:
            if p.get_height() > 0:
                ax.text(p.get_x() + p.get_width() / 2., p.get_height(), '%d' % int(p.get_height()),
                        fontsize=12, color='black', ha='center', va='bottom')

        ax.set_yticks([])
        ax.set_ylabel('')
        ax.set_xticks(range(7))
        ax.set_xticklabels(['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'])
        ax.legend()

        self.canvas.draw()

    # Stock portfolio methods
    def add_stock(self):
        self.open_dialog("Add Stock", self.save_stock,
                         ["Stock Symbol", "Purchase Price", "Quantity", "Purchase Date (YYYY-MM-DD)"],
                         [QLineEdit(), QLineEdit(), QLineEdit(), QDateEdit()],
                         [None, QDoubleValidator(0.99, 99.99, 2), QDoubleValidator(0.99, 99.99, 2)]
                         )

    def remove_stock(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Remove Stock")
        dialog.resize(800, 600)  # Adjust the size of the dialog window
        layout = QVBoxLayout()

        self.c.execute('SELECT portfolio_id, UPPER(symbol), company_name, purchase_price, quantity, purchase_date FROM portfolio WHERE user_id = ?', (self.user_id,))
        stocks = self.c.fetchall()

        self.remove_stock_table = QTableWidget()
        self.remove_stock_table.setColumnCount(6)
        self.remove_stock_table.setHorizontalHeaderLabels(["Select", "Symbol", "Company Name", "Purchase Price", "Quantity", "Purchase Date"])
        self.remove_stock_table.setRowCount(len(stocks))
        self.remove_stock_table.horizontalHeader().setStretchLastSection(True)
        self.remove_stock_table.setAlternatingRowColors(True)
        self.remove_stock_table.setStyleSheet("alternate-background-color: #f0f0f0;")
        self.remove_stock_table.horizontalHeader().setStyleSheet("font-weight: bold; font-size: 14px;")

        for row, stock in enumerate(stocks):
            portfolio_id, symbol, company_name, purchase_price, quantity, purchase_date = stock
            checkbox = QCheckBox()
            checkbox.setStyleSheet("margin:auto;")  # Center the checkbox
            checkbox.setProperty('stock_id', portfolio_id)
            self.remove_stock_table.setCellWidget(row, 0, checkbox)

            items = [symbol, company_name, f"{purchase_price:.2f}", f"{quantity:.2f}", purchase_date]
            for col, item in enumerate(items, start=1):
                cell_item = QTableWidgetItem(item)
                cell_item.setTextAlignment(Qt.AlignCenter)
                self.remove_stock_table.setItem(row, col, cell_item)

        layout.addWidget(self.remove_stock_table)

        self.add_to_records_checkbox = QCheckBox("Add to records")
        layout.addWidget(self.add_to_records_checkbox)

        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(lambda: self.confirm_remove_stock(dialog))
        layout.addWidget(remove_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def confirm_remove_stock(self, dialog):
        try:
            total_pl = 0
            for row in range(self.remove_stock_table.rowCount()):
                checkbox = self.remove_stock_table.cellWidget(row, 0)
                if checkbox.isChecked():
                    stock_id = checkbox.property('stock_id')
                    symbol = self.remove_stock_table.item(row, 1).text()
                    purchase_price = float(self.remove_stock_table.item(row, 3).text())
                    quantity = float(self.remove_stock_table.item(row, 4).text())
                    current_price = self.get_stock_info(symbol)[1]
                    pl = (current_price - purchase_price) * quantity
                    total_pl += pl
                    self.c.execute('DELETE FROM portfolio WHERE portfolio_id = ?', (stock_id,))
                    if self.add_to_records_checkbox.isChecked():
                        category = "Investments"
                        record_type = "Income" if pl >= 0 else "Expense"
                        self.c.execute('INSERT INTO records (user_id, date, category, type, amount) VALUES (?, ?, ?, ?, ?)',
                                       (self.user_id, datetime.datetime.now().date(), category, record_type, abs(pl)))
            self.conn.commit()
            QMessageBox.information(self, "Success", "Selected stocks removed")
            dialog.close()
            self.update_all()  # Update all relevant data
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def save_stock(self, dialog, inputs):
        try:
            symbol, purchase_price, quantity, purchase_date = [inp.text().strip() for inp in inputs]
            if not symbol or not purchase_price or not quantity or not purchase_date:
                raise ValueError("All fields must be filled.")
            symbol = symbol.upper()  # Convert the ticker symbol to uppercase
            company_name, current_price = self.get_stock_info(symbol)
            purchase_date_obj = datetime.datetime.strptime(purchase_date, '%Y-%m-%d').date()
            self.c.execute('INSERT INTO portfolio (user_id, symbol, purchase_price, quantity, company_name, purchase_date) VALUES (?, ?, ?, ?, ?, ?)',
                           (self.user_id, symbol, float(purchase_price), float(quantity), company_name, purchase_date_obj))
            self.conn.commit()
            QMessageBox.information(self, "Success", "Stock added successfully")
            dialog.close()
            self.update_all()  # Update all relevant data
        except ValueError as ve:
            QMessageBox.critical(self, "Error", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def get_stock_info(self, symbol):
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            company_name = info.get('shortName', None)
            current_price = info.get('regularMarketPrice', info.get('currentPrice', None))

            if not company_name or not current_price:
                raise ValueError(f"Invalid ticker: {symbol}")

            return company_name, current_price
        except Exception as e:
            raise ValueError(f"Error fetching data for symbol {symbol}: {str(e)}")

    def show_all_stocks(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("All Stock Records")
        dialog.resize(800, 600)
        layout = QVBoxLayout()

        all_stocks_table = QTableWidget()
        all_stocks_table.setColumnCount(6)
        all_stocks_table.setHorizontalHeaderLabels(["Symbol", "Company Name", "Purchase Price", "Quantity", "Purchase Date", "Total P&L"])
        all_stocks_table.horizontalHeader().setStretchLastSection(True)
        all_stocks_table.setAlternatingRowColors(True)
        all_stocks_table.setStyleSheet("alternate-background-color: #f0f0f0;")
        all_stocks_table.horizontalHeader().setStyleSheet("font-weight: bold; font-size: 14px;")
        all_stocks_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.c.execute('SELECT symbol, company_name, purchase_price, quantity, purchase_date FROM portfolio WHERE user_id = ?', (self.user_id,))
        stocks = self.c.fetchall()
        all_stocks_table.setRowCount(len(stocks))

        for row, stock in enumerate(stocks):
            symbol, company_name, purchase_price, quantity, purchase_date = stock
            current_price = self.get_stock_info(symbol)[1]
            total_pl = (current_price - purchase_price) * quantity
            items = [symbol, company_name, f"{purchase_price:.2f}", f"{quantity:.2f}", purchase_date, f"{total_pl:.2f}"]
            for col, item in enumerate(items):
                cell_item = QTableWidgetItem(item)
                cell_item.setTextAlignment(Qt.AlignCenter)
                all_stocks_table.setItem(row, col, cell_item)

        all_stocks_table.resizeColumnsToContents()
        layout.addWidget(all_stocks_table)
        dialog.setLayout(layout)
        dialog.exec_()

    def update_portfolio(self):
        self.c.execute('SELECT UPPER(symbol), company_name, AVG(purchase_price) as avg_price, SUM(quantity) as total_quantity FROM portfolio WHERE user_id = ? GROUP BY UPPER(symbol), company_name', (self.user_id,))
        combined_stocks = self.c.fetchall()
        self.portfolio_table.setRowCount(len(combined_stocks))

        current_value = 0
        total_purchase_value = 0
        daily_change = 0
        yearly_change = 0
        total_change = 0

        for row, stock in enumerate(combined_stocks):
            symbol, company_name, avg_price, total_quantity = stock
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                current_price = self.get_stock_info(symbol)[1]
                opening_price = info.get('regularMarketOpen', 0)
                one_year_ago_price = ticker.history(start=datetime.datetime.now() - datetime.timedelta(days=365), end=datetime.datetime.now())['Close'].iloc[0]
                total_pl = (current_price - avg_price) * total_quantity
                current_value += current_price * total_quantity
                total_purchase_value += avg_price * total_quantity
                daily_change += (current_price - opening_price) * total_quantity
                yearly_change += (current_price - one_year_ago_price) * total_quantity
                total_change += total_pl

                items = [symbol, company_name, f"{avg_price:.2f}", f"{total_quantity:.2f}", f"{current_price:.2f}", f"{total_pl:.2f}"]
                for col, item in enumerate(items):
                    cell_item = QTableWidgetItem(item)
                    cell_item.setTextAlignment(Qt.AlignCenter)
                    self.portfolio_table.setItem(row, col, cell_item)
            except ValueError as e:
                QMessageBox.warning(self, "Warning", str(e))
                self.c.execute('DELETE FROM portfolio WHERE user_id = ? AND symbol = ?', (self.user_id, symbol))
                self.conn.commit()
                self.portfolio_table.removeRow(row)

        self.current_portfolio_value = current_value  # Update the portfolio value variable

        daily_change_percent = (daily_change / (current_value - daily_change)) * 100 if current_value - daily_change != 0 else 0
        yearly_change_percent = (yearly_change / (current_value - yearly_change)) * 100 if current_value - yearly_change != 0 else 0
        total_change_percent = (total_change / total_purchase_value) * 100 if total_purchase_value != 0 else 0

        # Create labels for the statistics
        statistics = [
            f"Current Value: <span style='color: black;'>${current_value:.2f}</span>",
            f"Daily Change: <span style='color: {'green' if daily_change >= 0 else 'red'};'>{daily_change_percent:.2f}% (${daily_change:.2f})</span>",
            f"Yearly Change: <span style='color: {'green' if yearly_change >= 0 else 'red'};'>{yearly_change_percent:.2f}% (${yearly_change:.2f})</span>",
            f"Total Change: <span style='color: {'green' if total_change >= 0 else 'red'};'>{total_change_percent:.2f}% (${total_change:.2f})</span>"
        ]

        # Clear existing statistics labels
        for i in reversed(range(self.portfolio_tab.layout().count())):
            widget = self.portfolio_tab.layout().itemAt(i).widget()
            if isinstance(widget, QLabel) and widget.objectName().startswith("stat_label"):
                self.portfolio_tab.layout().removeWidget(widget)
                widget.deleteLater()

        # Display the statistics below the portfolio table
        for stat in statistics:
            label = QLabel(stat)
            label.setObjectName("stat_label")
            label.setStyleSheet("font-size: 18px;")
            label.setAlignment(Qt.AlignCenter)
            self.portfolio_tab.layout().insertWidget(self.portfolio_tab.layout().count() - 5, label)  # Insert above the buttons

    # Net worth methods
    def update_net_worth(self):
        try:
            # Fetch total income
            self.c.execute('SELECT SUM(amount) FROM records WHERE user_id = ? AND type="Income"', (self.user_id,))
            total_income = self.c.fetchone()[0] or 0

            # Fetch total expenses excluding those linked to loans
            self.c.execute('SELECT SUM(amount) FROM records WHERE user_id = ? AND type="Expense" AND linked_loan IS NULL', (self.user_id,))
            total_expenses = self.c.fetchone()[0] or 0

            # Fetch total value of portfolio (current value)
            self.c.execute('SELECT symbol, SUM(quantity) FROM portfolio WHERE user_id = ? GROUP BY symbol', (self.user_id,))
            portfolio = self.c.fetchall()
            total_portfolio_value = 0
            for stock in portfolio:
                symbol, total_quantity = stock
                current_price = self.get_stock_info(symbol)[1]
                total_portfolio_value += current_price * total_quantity

            # Fetch total value of assets   
            self.c.execute('SELECT SUM(purchase_price) FROM assets WHERE user_id = ?', (self.user_id,))
            total_assets_value = self.c.fetchone()[0] or 0

            # Fetch total liabilities (principal to be repaid plus current interest)
            self.c.execute('SELECT SUM(principal + interest) FROM loans WHERE user_id = ?', (self.user_id,))
            total_liabilities = self.c.fetchone()[0] or 0

            # Calculate net worth
            net_worth = total_income - total_expenses + total_portfolio_value + total_assets_value - total_liabilities

            # Update net worth label style based on value
            if net_worth < 0:
                self.net_worth_label.setStyleSheet("font-size: 20px; color: red;")
            else:
                self.net_worth_label.setStyleSheet("font-size: 20px; color: green;")
            self.net_worth_label.setText(f"${net_worth:,.2f}")

            # Update net worth history table
            today = datetime.datetime.now().date()
            self.c.execute('INSERT OR REPLACE INTO net_worth_history (user_id, date, net_worth) VALUES (?, ?, ?)', (self.user_id, today, net_worth))
            self.conn.commit()

            # Update net worth graph
            self.c.execute('SELECT date, net_worth FROM net_worth_history WHERE user_id = ? ORDER BY date', (self.user_id,))
            records = self.c.fetchall()
            dates = [datetime.datetime.strptime(record[0], '%Y-%m-%d') for record in records]
            net_worths = [record[1] for record in records]

            self.figure_net_worth.clear()
            ax_net_worth = self.figure_net_worth.add_subplot(111)
            ax_net_worth.plot(dates, net_worths, color='blue', marker='o', markersize=4)
            ax_net_worth.set_title('Net Worth Over Time')
            ax_net_worth.set_xlabel('Date')
            ax_net_worth.set_ylabel('Net Worth')
            self.canvas_net_worth.draw()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # Record methods
    def show_form(self):
        inputs = [QDateEdit(), QComboBox(), QComboBox(), QLineEdit(), QCheckBox(), QComboBox(), QComboBox()]
        inputs[1].addItems(["Groceries", "Utilities", "Rent", "Entertainment", "Transport", "Healthcare", "Paycheck", "Investments", "Other", "Loan"])
        inputs[2].addItems(["Income", "Expense"])
        inputs[4].setText("Recurring Record")
        inputs[6].addItems(["Daily", "Weekly", "Monthly", "Annual"])  # Recurrence frequency

        # Set validator for amount input field to allow only numbers
        inputs[3].setValidator(QDoubleValidator(0.0, 1e9, 2))

        # Load loans into the combobox
        self.load_loans_into_combobox(inputs[5])
        inputs[5].setEnabled(False)  # Initially disabled
        inputs[6].setEnabled(False)  # Initially disabled

        inputs[1].currentTextChanged.connect(lambda: self.toggle_loan_combobox(inputs))
        inputs[2].currentTextChanged.connect(lambda: self.toggle_loan_combobox(inputs))
        inputs[4].stateChanged.connect(lambda: self.toggle_loan_combobox(inputs))

        self.open_dialog("Add Record", self.add_record,
                         ["Date (YYYY-MM-DD)", "Category", "Type", "Amount", "", "Link to Loan", "Recurrence Frequency"], inputs)

    def toggle_loan_combobox(self, inputs):
        category = inputs[1].currentText()
        record_type = inputs[2].currentText()
        is_recurring = inputs[4].isChecked()

        if category == "Loan" and record_type == "Expense" and is_recurring:
            inputs[5].setEnabled(True)
            inputs[6].setEnabled(True)
        elif is_recurring:
            inputs[6].setEnabled(True)
        else:
            inputs[5].setEnabled(False)
            inputs[6].setEnabled(False)

    def load_loans_into_combobox(self, loan_combobox):
        self.c.execute('SELECT loan_id, name FROM loans WHERE user_id = ?', (self.user_id,))
        loans = self.c.fetchall()
        for loan in loans:
            loan_combobox.addItem(loan[1], loan[0])

    def add_record(self, dialog, inputs):
        try:
            date = inputs[0].text().strip()
            category = inputs[1].currentText().strip()
            record_type = inputs[2].currentText().strip()
            amount = inputs[3].text().strip()
            if not date or not category or not record_type or not amount:
                raise ValueError("All fields must be filled.")
            amount = float(amount)
            is_recurring = inputs[4].isChecked()
            loan_id = inputs[5].currentData() if inputs[5].isEnabled() else None
            frequency = inputs[6].currentText() if inputs[6].isEnabled() else None

            date_obj = datetime.datetime.strptime(date, '%Y-%m-%d').date()

            if is_recurring:
                if loan_id:
                    self.c.execute('INSERT INTO recurring_records (user_id, date, category, type, amount, frequency, linked_loan) VALUES (?, ?, ?, ?, ?, ?, ?)',
                                   (self.user_id, date, category, record_type, amount, frequency, loan_id))
                else:
                    self.c.execute('INSERT INTO recurring_records (user_id, date, category, type, amount, frequency) VALUES (?, ?, ?, ?, ?, ?)',
                                   (self.user_id, date, category, record_type, amount, frequency))
            else:
                if loan_id:
                    self.c.execute('INSERT INTO records (user_id, date, category, type, amount, linked_loan) VALUES (?, ?, ?, ?, ?, ?)',
                                   (self.user_id, date, category, record_type, amount, loan_id))
                else:
                    self.c.execute('INSERT INTO records (user_id, date, category, type, amount) VALUES (?, ?, ?, ?, ?)',
                                   (self.user_id, date, category, record_type, amount))

            self.conn.commit()
            QMessageBox.information(self, "Success", "Record added successfully")
            dialog.close()
            self.update_all()  # Update all relevant data
        except ValueError as ve:
            QMessageBox.critical(self, "Input Error", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            print(f"Error: {str(e)}")

    def show_records(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Records")
        dialog.resize(800, 600)  # Adjust the size of the dialog window
        layout = QVBoxLayout()

        self.records_table = QTableWidget()
        self.records_table.setColumnCount(5)
        self.records_table.setHorizontalHeaderLabels(["Select", "Date", "Category", "Type", "Amount"])
        self.records_table.horizontalHeader().setStretchLastSection(True)
        self.records_table.setAlternatingRowColors(True)
        self.records_table.setStyleSheet("alternate-background-color: #f0f0f0;")
        self.records_table.horizontalHeader().setStyleSheet("font-weight: bold; font-size: 14px;")
        self.records_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Make table read-only

        # Fetch only non-recurring records
        self.c.execute('''
            SELECT rowid, date, category, type, amount 
            FROM records 
            WHERE user_id = ? 
            AND rowid NOT IN (SELECT rowid FROM records WHERE user_id = ? AND linked_loan IS NOT NULL)
            ORDER BY date DESC
        ''', (self.user_id, self.user_id))
        records = self.c.fetchall()

        self.records_table.setRowCount(len(records))

        for row, record in enumerate(records):
            checkbox = QCheckBox()
            checkbox.setStyleSheet("margin:auto;")  # Center the checkbox
            checkbox.stateChanged.connect(self.toggle_remove_button)
            checkbox.setProperty('record_id', record[0])
            self.records_table.setCellWidget(row, 0, checkbox)

            for col, value in enumerate(record[1:], start=1):
                cell_item = QTableWidgetItem(str(value))
                cell_item.setTextAlignment(Qt.AlignCenter)
                self.records_table.setItem(row, col, cell_item)

        # Resize columns to fit the contents
        self.records_table.resizeColumnsToContents()

        self.remove_record_button = QPushButton("Remove Record")
        self.remove_record_button.setEnabled(False)
        self.remove_record_button.clicked.connect(lambda: self.remove_selected_records(dialog))
        layout.addWidget(self.records_table)
        layout.addWidget(self.remove_record_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def show_recurring_records(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Recurring Records")
        dialog.resize(800, 600)  # Adjust the size of the dialog window
        layout = QVBoxLayout()

        self.recurring_records_table = QTableWidget()
        self.recurring_records_table.setColumnCount(6)
        self.recurring_records_table.setHorizontalHeaderLabels(["Select", "Date", "Category", "Type", "Amount", "Frequency"])
        self.recurring_records_table.horizontalHeader().setStretchLastSection(True)
        self.recurring_records_table.setAlternatingRowColors(True)
        self.recurring_records_table.setStyleSheet("alternate-background-color: #f0f0f0;")
        self.recurring_records_table.horizontalHeader().setStyleSheet("font-weight: bold; font-size: 14px;")
        self.recurring_records_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Make table read-only

        # Fetch recurring records
        self.c.execute('''
            SELECT id, date, category, type, amount, frequency FROM recurring_records 
            WHERE user_id = ?
            ORDER BY date DESC
        ''', (self.user_id,))
        records = self.c.fetchall()

        self.recurring_records_table.setRowCount(len(records))

        for row, record in enumerate(records):
            checkbox = QCheckBox()
            checkbox.setStyleSheet("margin:auto;")  # Center the checkbox
            checkbox.stateChanged.connect(self.toggle_remove_button_recurring)
            checkbox.setProperty('record_id', record[0])
            self.recurring_records_table.setCellWidget(row, 0, checkbox)

            for col, value in enumerate(record[1:], start=1):
                cell_item = QTableWidgetItem(str(value))
                cell_item.setTextAlignment(Qt.AlignCenter)
                self.recurring_records_table.setItem(row, col, cell_item)

        # Resize columns to fit the contents
        self.recurring_records_table.resizeColumnsToContents()

        self.remove_recurring_record_button = QPushButton("Remove Recurring Record")
        self.remove_recurring_record_button.setEnabled(False)
        self.remove_recurring_record_button.clicked.connect(lambda: self.remove_selected_recurring_records(dialog))
        layout.addWidget(self.recurring_records_table)
        layout.addWidget(self.remove_recurring_record_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def toggle_remove_button_recurring(self):
        any_checked = any(self.recurring_records_table.cellWidget(row, 0).isChecked() for row in range(self.recurring_records_table.rowCount()))
        self.remove_recurring_record_button.setEnabled(any_checked)

    def remove_selected_recurring_records(self, dialog):
        try:
            for row in range(self.recurring_records_table.rowCount()):
                checkbox = self.recurring_records_table.cellWidget(row, 0)
                if checkbox.isChecked():
                    record_id = checkbox.property('record_id')
                    print(f"Removing recurring record with ID: {record_id}")  # Debug print

                    if record_id:
                        # Get the linked loan before deleting the recurring record
                        self.c.execute('SELECT linked_loan FROM recurring_records WHERE id = ?', (record_id,))
                        linked_loan = self.c.fetchone()

                        if linked_loan:
                            linked_loan = linked_loan[0]
                            print(f"Linked loan ID: {linked_loan}")  # Debug print
                            if linked_loan:
                                # Reset the loan to its initial state
                                self.c.execute('SELECT initial_principal FROM loans WHERE loan_id = ?', (linked_loan,))
                                initial_principal = self.c.fetchone()[0]
                                self.c.execute('UPDATE loans SET principal = ?, interest = 0 WHERE loan_id = ?', (initial_principal, linked_loan))
                                self.c.execute('DELETE FROM loan_repayment WHERE loan_id = ?', (linked_loan,))

                            # Delete associated records in the main records table
                            self.c.execute('DELETE FROM records WHERE linked_loan = ?', (linked_loan,))

                        # Delete the recurring record
                        self.c.execute('DELETE FROM recurring_records WHERE id = ?', (record_id,))

            self.conn.commit()
            QMessageBox.information(self, "Success", "Selected recurring records removed and loans reset to initial state")
            dialog.close()
            self.update_all()  # Update all relevant data
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def toggle_remove_button(self):
        any_checked = any(self.records_table.cellWidget(row, 0).isChecked() for row in range(self.records_table.rowCount()))
        self.remove_record_button.setEnabled(any_checked)

    def remove_selected_records(self, dialog):
        try:
            for row in range(self.records_table.rowCount()):
                checkbox = self.records_table.cellWidget(row, 0)
                if checkbox.isChecked():
                    record_id = checkbox.property('record_id')
                    self.c.execute('DELETE FROM records WHERE rowid = ?', (record_id,))
            self.conn.commit()
            QMessageBox.information(self, "Success", "Selected records removed")
            dialog.close()
            self.update_all()  # Update all relevant data
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # FIRE calculation methods
    def calculate_fire(self):
        try:
            portfolio_value = self.portfolio_value_input.text().strip()
            annual_income = self.annual_income_input.text().strip()
            savings_rate = self.savings_rate_input.text().strip()
            income_growth_rate = self.income_growth_input.text().strip()
            income_growth_duration = self.income_growth_duration_input.text().strip()
            annual_expenses = self.annual_expenses_input.text().strip()
            withdrawal_rate = self.withdrawal_rate_input.text().strip()
            annual_roi = self.annual_roi_input.text().strip()

            if not portfolio_value or not annual_income or not savings_rate or not income_growth_rate or not income_growth_duration or not annual_expenses or not withdrawal_rate or not annual_roi:
                QMessageBox.warning(self, "Input Error", "All fields must be filled.")
                return

            portfolio_value = float(portfolio_value)
            annual_income = float(annual_income)
            savings_rate = float(savings_rate) / 100
            income_growth_rate = float(income_growth_rate) / 100
            income_growth_duration = int(income_growth_duration)
            annual_expenses = float(annual_expenses)
            withdrawal_rate = float(withdrawal_rate) / 100
            annual_roi = float(annual_roi) / 100
            include_loan_expenses = self.include_loan_expenses_checkbox.isChecked()

            years_to_retirement, portfolio_values = self.calculate_years_to_retirement(
                portfolio_value, annual_income, savings_rate, income_growth_rate, income_growth_duration,
                annual_expenses, withdrawal_rate, annual_roi, include_loan_expenses
            )

            self.result_label.setText(f"You can retire in <b>{years_to_retirement}</b> years.")
            self.result_label.setStyleSheet("font-size: 24px; text-align: center;")
            self.plot_fire_growth(portfolio_values)

        except ValueError as ve:
            QMessageBox.critical(self, "Input Error", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def calculate_years_to_retirement(self, portfolio_value, annual_income, savings_rate, income_growth_rate,
                                    income_growth_duration, annual_expenses, withdrawal_rate, annual_roi,
                                    include_loan_expenses):
        years = 0
        portfolio_values = [portfolio_value]

        if include_loan_expenses:
            # Load loan data
            self.c.execute('SELECT loan_id, principal, interest, interest_rate FROM loans WHERE user_id = ?', (self.user_id,))
            loans = self.c.fetchall()
            loan_details = {loan[0]: {'principal': loan[1], 'interest': loan[2], 'interest_rate': loan[3]} for loan in loans}
        else:
            loan_details = {}

        while True:
            # Deduct loan repayments if included
            total_loan_expenses = 0
            if include_loan_expenses:
                for loan_id, details in loan_details.items():
                    principal = details['principal']
                    interest = details['interest']
                    interest_rate = details['interest_rate']

                    # Calculate the interest accumulated for the year
                    accumulated_interest = (principal * interest_rate / 100)
                    details['interest'] += accumulated_interest

                    # Get the recurring expense for this loan
                    self.c.execute('SELECT amount, frequency FROM recurring_records WHERE user_id = ? AND linked_loan = ?',
                                (self.user_id, loan_id))
                    recurring_record = self.c.fetchone()
                    if recurring_record:
                        amount, frequency = recurring_record
                        if frequency == 'Daily':
                            annual_expense = amount * 365
                        elif frequency == 'Weekly':
                            annual_expense = amount * 52
                        elif frequency == 'Monthly':
                            annual_expense = amount * 12
                        elif frequency == 'Annual':
                            annual_expense = amount

                        # Check if the loan can be repaid within this year
                        total_debt = principal + details['interest']
                        if annual_expense >= total_debt:
                            annual_expense = total_debt
                            details['principal'] = 0
                            details['interest'] = 0
                        else:
                            if annual_expense <= details['interest']:
                                details['interest'] -= annual_expense
                            else:
                                details['principal'] -= (annual_expense - details['interest'])
                                details['interest'] = 0

                        total_loan_expenses += annual_expense

            if years < income_growth_duration:
                annual_income *= (1 + income_growth_rate)

            annual_income -= total_loan_expenses
            annual_income = max(0, annual_income)  # Ensure income doesn't go below zero
            annual_savings = annual_income * savings_rate

            portfolio_value = (portfolio_value + annual_savings) * (1 + annual_roi)
            portfolio_values.append(portfolio_value)
            years += 1
            if portfolio_value * withdrawal_rate >= annual_expenses:
                break

        return years, portfolio_values

    def get_default_values(self):
        # Use the updated portfolio value
        portfolio_value = self.current_portfolio_value

        # Get annual income from recurring records with category "Paycheck"
        self.c.execute('''
            SELECT amount, frequency FROM recurring_records 
            WHERE user_id = ? AND category = "Paycheck"
        ''', (self.user_id,))
        recurring_income_records = self.c.fetchall()
        annual_income = 0
        for amount, frequency in recurring_income_records:
            if frequency == 'Daily':
                annual_income += amount * 365
            elif frequency == 'Weekly':
                annual_income += amount * 52
            elif frequency == 'Monthly':
                annual_income += amount * 12
            elif frequency == 'Annual':
                annual_income += amount

        return portfolio_value, annual_income

    def update_annual_expenses(self):
        try:
            annual_income = float(self.annual_income_input.text().strip())
            savings_rate = float(self.savings_rate_input.text().strip()) / 100
            annual_expenses = annual_income * (1 - savings_rate)
            self.annual_expenses_input.blockSignals(True)
            self.annual_expenses_input.setText(f"{annual_expenses:.2f}")
            self.annual_expenses_input.blockSignals(False)
        except ValueError:
            pass

    def update_savings_rate(self):
        try:
            annual_income = float(self.annual_income_input.text().strip())
            annual_expenses = float(self.annual_expenses_input.text().strip())
            savings_rate = (annual_income - annual_expenses) / annual_income * 100
            self.savings_rate_input.blockSignals(True)
            self.savings_rate_input.setText(f"{savings_rate:.2f}")
            self.savings_rate_input.blockSignals(False)
        except ValueError:
            pass

    def plot_fire_growth(self, portfolio_values):
        self.figure_fire.clear()
        ax = self.figure_fire.add_subplot(111)

        # Create a dataframe for better handling with seaborn
        data = pd.DataFrame({
            'Years': list(range(len(portfolio_values))),
            'Portfolio Value': portfolio_values
        })

        sns.barplot(x='Years', y='Portfolio Value', data=data, ax=ax, palette='viridis', hue='Years', legend=False)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)

        ax.set_yticks([])
        ax.set_ylabel('Portfolio Value')

        ax.set_title("FIRE Portfolio Growth")
        ax.set_xlabel("Years")

        # Adding values on top of the bars
        for p in ax.patches:
            if p.get_height() > 0:
                ax.text(p.get_x() + p.get_width() / 2., p.get_height(), '%d' % int(p.get_height()),
                        fontsize=12, color='black', ha='center', va='bottom')

        self.canvas_fire.draw()


# Main function to run the application
def main():
    app = QApplication(sys.argv)
    window = FinanceApp()
    window.show()
    window.raise_()
    window.activateWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
