import sqlite3
import random
from faker import Faker
from datetime import date as dt, timedelta
import yfinance as yf

fake = Faker()

# Connect to the SQLite database
conn = sqlite3.connect('finance.db')
c = conn.cursor()

# Ensure the user "Maks" exists and retrieve their user_id
c.execute("SELECT user_id FROM users WHERE name = ?", ('Maks',))
user = c.fetchone()
if not user:
    c.execute("INSERT INTO users (name) VALUES (?)", ('Maks',))
    conn.commit()
    user_id = c.lastrowid
else:
    user_id = user[0]

# Define the categories and types
categories = ["Groceries", "Utilities", "Rent", "Entertainment", "Transport", "Healthcare", "Paycheck", "Investments", "Other"]
types = ["Income", "Expense"]

# Generate and insert fake data into the records table
for _ in range(100):  # Generate 100 records
    fake_date = fake.date_between(start_date=dt(2024, 5, 1), end_date=dt(2024, 7, 1))
    category = random.choice(categories)
    type = random.choice(types)
    amount = round(random.uniform(10, 1000), 2)  # Random amount between 10 and 1000
    c.execute('INSERT INTO records (user_id, date, category, type, amount) VALUES (?, ?, ?, ?, ?)', 
              (user_id, fake_date, category, type, amount))

# Generate and insert fake data into the net_worth_history table
start_date = dt(2023, 1, 1)
end_date = dt(2024, 6, 30)
current_date = start_date
net_worth = 50000  # Starting net worth

while current_date <= end_date:
    net_worth += random.uniform(-2000, 5000)  # Randomly fluctuate net worth
    net_worth = max(0, net_worth)  # Ensure net worth doesn't go negative
    c.execute('INSERT INTO net_worth_history (user_id, date, net_worth) VALUES (?, ?, ?)',
              (user_id, current_date.strftime('%Y-%m-%d'), net_worth))
    current_date += timedelta(days=30)  # Increment date by one month

# Commit the changes and close the connection
conn.commit()
conn.close()
