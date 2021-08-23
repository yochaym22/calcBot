import sqlite3
import dateutil.parser

INCOME = 'הכנסה'
DOLLAR_HISTORY_TABLE_NAME = "DOLLARHISTORY"
SHEKEL_HISTORY_TABLE_NAME = "SHEKELHISTORY"
date_format = "%Y-%m-%d"


class DBHelper:
    def __init__(self, dbname="calc.sqlite"):
        self.dbname = dbname
        self.conn = sqlite3.connect(dbname)

    def setup(self):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS USERA 
                            (sum INT NOT NULL,
                                 description text NOT NULL,
                                 name text NOT NULL,
                                 date text NOT NULL,
                                 type text NOT NULL);''')

        self.conn.execute('''CREATE TABLE IF NOT EXISTS USERB 
                                    (sum INT NOT NULL,
                                         description text NOT NULL,
                                         name text NOT NULL,
                                         date text NOT NULL,
                                         type text NOT NULL);''')

        self.conn.execute('''CREATE TABLE IF NOT EXISTS SHEKELHISTORY 
                                    (sum INT NOT NULL,
                                         description text NOT NULL,
                                         name text NOT NULL,
                                         date text NOT NULL,
                                         type text NOT NULL);''')

        self.conn.execute(''' CREATE TABLE IF NOT EXISTS DOLLARHISTORY
                                            (sum INT NOT NULL,
                                             description text NOT NULL,
                                             name text NOT NULL,
                                             date text NOT NULL,
                                             type text NOT NULL);''')

        self.conn.execute(''' CREATE TABLE IF NOT EXISTS BANK 
                            (id INTEGER PRIMARY KEY,
                             sum INT NOT NULL)''')
        try:
            # setting up shekel bank with id 0
            self.conn.execute(''' INSERT INTO BANK (id, sum) VALUES (0,0)''')
            # setting up dollar bank  with id 1
            self.conn.execute(''' INSERT INTO BANK (id, sum) VALUES (1,0)''')
        except:
            pass

        self.conn.commit()

    def insert_col_data(self, item_sum, description, name, date, data_type, is_dollar):
        date = dateutil.parser.parse(date)
        if is_dollar:
            self.add_dollar(item_sum, description, name, date, data_type)
            self.update_total_count(item_sum, data_type, DOLLAR_HISTORY_TABLE_NAME)
        else:
            self.add_shekel(item_sum, description, name, str(date), data_type)
            stmt_user_a = "INSERT INTO USERA (sum, description, name, date, type) VALUES (?, ?, ?, ?, ?)"
            stmt_user_b = "INSERT INTO USERB (sum, description, name, date, type) VALUES (?, ?, ?, ?, ?)"
            args_user = (str(int(item_sum) / 2), description, name, date, data_type)
            self.conn.execute(stmt_user_a, args_user)
            self.conn.execute(stmt_user_b, args_user)
            self.update_total_count(item_sum, data_type, SHEKEL_HISTORY_TABLE_NAME)
        self.conn.commit()

    def add_dollar(self, item_sum, description, name, date, type):
        stmt = "INSERT INTO DOLLARHISTORY (sum, description, name, date, type) VALUES (?, ?, ?, ?, ?)"
        args = (item_sum, description, name, date, type)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def add_shekel(self, item_sum, description, name, date, type):
        stmt = "INSERT INTO SHEKELHISTORY (sum, description, name, date, type) VALUES (?, ?, ?, ?, ?)"
        args = (item_sum, description, name, date, type)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def delete_shekel_bank_item(self, name, date):
        stmt = "DELETE FROM SHEKELHISTORY WHERE name = (?) AND date = (?)"
        args = (name, date)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def delete_dollar_bank_item(self, name, date):
        stmt = "DELETE FROM DOLLARHISTORY WHERE name = (?) AND date = (?)"
        args = (name, date)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def update_total_count(self, amount, data_type, table):
        if table == SHEKEL_HISTORY_TABLE_NAME:
            current_amount = self.conn.cursor()
            current_amount.execute("SELECT sum from BANK WHERE id = 0")
            current_amount = current_amount.fetchone()
            if data_type == INCOME:
                new_sum = current_amount[0] + int(amount)
            else:
                new_sum = current_amount[0] - int(amount)
            stmt = "UPDATE BANK set sum = (?) WHERE id = 0"
            args = [str(new_sum)]
            self.conn.execute(stmt, args)
        else:
            current_amount = self.conn.cursor()
            current_amount.execute("SELECT sum from BANK WHERE id = 1")
            current_amount = current_amount.fetchone()
            if data_type == INCOME:
                new_sum = current_amount[0] + int(amount)
            else:
                new_sum = current_amount[0] - int(amount)
            stmt = "UPDATE BANK set sum = (?) WHERE id = 1"
            args = [str(new_sum)]
            self.conn.execute(stmt, args)

    def get_items(self):
        items = {
            "shekel": self.get_shekel_items(),
            "dollar": self.get_dollar_items()
        }
        return items

    def get_shekel_items(self):
        stmt = "SELECT * FROM SHEKELHISTORY"
        curr = self.conn.cursor()
        curr.execute(stmt)
        rows = curr.fetchall()
        return rows

    def get_dollar_items(self):
        stmt = "SELECT * FROM DOLLARHISTORY"
        curr = self.conn.cursor()
        curr.execute(stmt)
        rows = curr.fetchall()
        return rows

    def search_dates(self, text):
        rows = self.execute_date_search_query('SHEKELHISTORY', text)
        rows = rows + self.execute_date_search_query('DOLLARHISTORY', text)
        return rows

    def search_description(self, text):
        rows = self.execute_description_search_query('SHEKELHISTORY', text)
        rows = rows + self.execute_description_search_query('DOLLARHISTORY', text)
        return rows

    def search_names(self, text):
        rows = self.execute_name_search_query('SHEKELHISTORY', text)
        rows = rows + self.execute_name_search_query('DOLLARHISTORY', text)
        return rows

    def search_sums(self, text):
        rows = self.execute_sum_search_query('SHEKELHISTORY', text)
        rows = rows + self.execute_sum_search_query('DOLLARHISTORY', text)
        return rows

    def execute_date_search_query(self, table_name, args):
        stmt = f"SELECT * from {table_name} where date like ?"
        return self.execute_search_query(stmt, [args+'%'])

    def execute_name_search_query(self, table_name, args):
        stmt = f"SELECT * from {table_name} where name like ?"
        return self.execute_search_query(stmt, [args+'%'])

    def execute_description_search_query(self, table_name, args):
        stmt = f"SELECT * from {table_name} where description like ?"
        return self.execute_search_query(stmt, [args + '%'])

    def execute_sum_search_query(self, table_name, args):
        stmt = f"SELECT * from {table_name} where sum = ?"
        return self.execute_search_query(stmt, [args])

    def execute_search_query(self, stmt, args):
        cur = self.conn.cursor()
        cur.execute(stmt, args)
        rows = cur.fetchall()
        return rows
