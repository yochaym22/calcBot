import sqlite3
import dateutil.parser

OUTCOME = 'הוצאה'
DOLLAR_HISTORY_TABLE_NAME = "DOLLARHISTORY"
SHEKEL_HISTORY_TABLE_NAME = "SHEKELHISTORY"
USER_A_TABLE_NAME = "USERA"
USER_B_TABLE_NAME = "USERB"
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
                            (name text PRIMARY KEY,
                             sum INT NOT NULL)''')
        try:
            self.conn.execute(''' INSERT INTO BANK (name, sum) VALUES ('shekel',0)''')
            self.conn.execute(''' INSERT INTO BANK (name, sum) VALUES ('dollar',0)''')
            self.conn.execute(''' INSERT INTO BANK (name, sum) VALUES ('usera',0)''')
            self.conn.execute(''' INSERT INTO BANK (name, sum) VALUES ('userb',0)''')
        except:
            print('tables exist')

        self.conn.commit()

    def insert_col_data(self, item_sum, description, name, date, data_type, is_dollar):
        date = dateutil.parser.parse(date)
        if is_dollar:
            self.add_item_to_table(item_sum, description, name, date, data_type, DOLLAR_HISTORY_TABLE_NAME)
            if data_type == OUTCOME:
                item_sum = '-' + item_sum
            self.update_bank_count_at('dollar', item_sum)
        else:
            self.add_item_to_table(item_sum, description, name, str(date), data_type, SHEKEL_HISTORY_TABLE_NAME)
            self.add_item_to_table(str(int(item_sum) / 2), description, name, str(date), data_type, USER_A_TABLE_NAME)
            self.add_item_to_table(str(int(item_sum) / 2), description, name, str(date), data_type, USER_B_TABLE_NAME)
            if data_type == OUTCOME:
                item_sum = '-' + item_sum
            else:
                self.update_bank_count_at('usera', str(int(item_sum) / 2))
                self.update_bank_count_at('userb', str(int(item_sum) / 2))
            self.update_bank_count_at('shekel', item_sum)

    def add_item_to_table(self, item_sum, description, name, date, type, table_name):
        stmt = f"INSERT INTO {table_name} (sum, description, name, date, type) VALUES (?, ?, ?, ?, ?)"
        args = (item_sum, description, name, date, type)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def delete_item_from_table_by_name_and_date(self, name, date, table_name):
        stmt = f"DELETE FROM {table_name} WHERE name = (?) AND date = (?)"
        args = (name, date)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def update_bank_count_at(self, table_name, amount):
        stmt = 'SELECT sum from BANK where name = ?'
        args = [table_name]
        current_amount = self.conn.cursor()
        current_amount.execute(stmt, args)
        current_amount = current_amount.fetchone()
        new_sum = current_amount[0] + int(float(amount))
        stmt = f"UPDATE BANK set sum = (?) WHERE name = ?"
        args = [new_sum, table_name]
        self.conn.execute(stmt, args)
        self.conn.commit()

    def update_sum_at(self, table_name, amount):
        stmt = 'UPDATE BANK set sum = ? where name = ?'
        args = [amount, table_name]
        self.conn.execute(stmt, args)
        self.conn.commit()

    def get_items(self):
        items = {
            "shekel": self.get_items_from_table(SHEKEL_HISTORY_TABLE_NAME),
            "dollar": self.get_items_from_table(DOLLAR_HISTORY_TABLE_NAME),
        }
        return items

    def get_items_from_table(self, table_name):
        stmt = f"SELECT * FROM {table_name}"
        curr = self.conn.cursor()
        curr.execute(stmt)
        rows = curr.fetchall()
        return rows

    def search_dates(self, text):
        rows = self.execute_date_search_query(SHEKEL_HISTORY_TABLE_NAME, text)
        rows = rows + self.execute_date_search_query(DOLLAR_HISTORY_TABLE_NAME, text)
        return rows

    def search_description(self, text):
        rows = self.execute_description_search_query(SHEKEL_HISTORY_TABLE_NAME, text)
        rows = rows + self.execute_description_search_query(DOLLAR_HISTORY_TABLE_NAME, text)
        return rows

    def search_names(self, text):
        rows = self.execute_name_search_query(SHEKEL_HISTORY_TABLE_NAME, text)
        rows = rows + self.execute_name_search_query(DOLLAR_HISTORY_TABLE_NAME, text)
        return rows

    def search_sums(self, text):
        rows = self.execute_sum_search_query(SHEKEL_HISTORY_TABLE_NAME, text)
        rows = rows + self.execute_sum_search_query(DOLLAR_HISTORY_TABLE_NAME, text)
        return rows

    def execute_date_search_query(self, table_name, args):
        stmt = f"SELECT * from {table_name} where date like ?"
        return self.execute_search_query(stmt, [args + '%'])

    def execute_name_search_query(self, table_name, args):
        stmt = f"SELECT * from {table_name} where name like ?"
        return self.execute_search_query(stmt, [args + '%'])

    def execute_description_search_query(self, table_name, args):
        stmt = f"SELECT * from {table_name} where description like ?"
        return self.execute_search_query(stmt, [args + '%'])

    def execute_sum_search_query(self, table_name, args):
        stmt = f"SELECT * from {table_name} where sum = ?"
        return self.execute_search_query(stmt, [args])

    def sum_tables_until_date(self, args):
        stmt = "SELECT * from SHEKELHISTORY where date < (?)"
        stmt2 = "SELECT * from DOLLARHISTORY where date < (?)"
        results = {"shekel": self.execute_search_query(stmt, args),
                   "dollar": self.execute_search_query(stmt2, args)}
        sum_dict = {"shekel": 0,
                    "dollar": 0}
        for key in results.keys():
            for item in results[key]:
                sum_dict[key] += item[0]

        return sum_dict

    def execute_search_query(self, stmt, args):
        cur = self.conn.cursor()
        cur.execute(stmt, [args])
        rows = cur.fetchall()
        return rows
