# Fire Journey

Fire Journey is a personal finance application designed to help users track their income, expenses, investments, and loans. It includes features such as a FIRE (Financial Independence, Retire Early) calculator, portfolio management, and net worth tracking. It was made by Maksimilian Stajer (682271) for the Fin-tech course.

## Features

- **User Login:** Secure login for each user.
- **Income and Expense Tracking:** Record and predict expenses and income.
- **Portfolio Management:** Track stock investments, add and remove holdings, and view performance.
- **Net Worth Calculation:** Track your net worth over time.
- **Assets and Loans Management:** Track assets and manage loan details.
- **FIRE Calculator:** Calculate the number of years to reach financial independence based on various inputs.

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/StayerM/FinTech-682271
    cd FinTech-682271
    ```

2. Create and activate a virtual environment:
    ```sh
    python3 -m venv venv
    source venv/bin/activate
    ```

3. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

4. Run the application:
    ```sh
    python main.py
    ```

## Dependencies

- Python 3.6+
- PyQt5
- scikit-learn
- matplotlib
- seaborn
- pandas
- yfinance
- SQLite3 (built-in with Python)

## Usage

1. On startup, the application will prompt the user to log in.
2. After logging in, users can navigate through the tabs to manage their finances.
3. The **Income and Expenses** tab allows users to add and view records, predict future expenses, and visualize weekly income and expenses.
4. The **Portfolio** tab lets users manage their stock holdings, view all records, and track portfolio performance.
5. The **Net Worth** tab shows the user's current net worth and provides a graphical history.
6. The **Assets and Loans** tab allows users to manage their assets and loans.
7. The **FIRE Calculator** tab helps users calculate their retirement timeline based on their financial data.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Commit your changes (`git commit -am 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Create a new Pull Request.

## Acknowledgements

Special thanks to the open-source community for providing the tools and libraries that made this project possible.

## Contact

For questions or feedback, please contact [max.stajer@gmail.com](mailto:max.stajer@gmail.com).

