import datetime
import json
import requests
import time
import urllib
import re
import dbhelper
from dbhelper import DBHelper, date_format
import src

UPDATE_ID_TUPLE_INDEX = 2
TOKEN = src.TOKEN
URL = "https://api.telegram.org/bot{}/".format(TOKEN)
admins = {src.admin: True}
states = {"הכנסה": False, "הוצאה": False, "חיפוש": False, "גיבוי": False, "איפוס": False, "עדכונים": False,
          "היסטוריית פעולות": False}
update_states = {'משתמש א': False, 'משתמש ב': False, 'קופה': False, 'קופה$': False}
users = [src.user]
# pattern for the input text for income/outcome
input_pattern = re.compile(r'\d+\$?\s\w+\s\w+')
digits_pattern = re.compile(r'\d')
date_pattern = re.compile(r'\d[0123]')
date_formats = ["%d-%m-%Y", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%y", "%d.%m.%y", "%d/%m/%y"]
db = DBHelper()

# Requests handlers


def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content


def get_json_from_url(url):
    content = get_url(url)
    js = json.loads(content)
    return js


def get_updates(offset=None):
    url = URL + "getUpdates?timeout=100"
    if offset:
        url += "&offset={}".format(offset)
    js = get_json_from_url(url)
    return js


def get_last_update_id(updates):
    update_ids = []
    for update in updates["result"]:
        update_ids.append(int(update["update_id"]))
    return max(update_ids)


def get_last_chat_id_text_update_id(updates):
    updates_count = len(updates["result"])
    last_update = updates_count - 1
    text = updates["result"][last_update]["message"]["text"]
    chat_id = updates["result"][last_update]["message"]["chat"]["id"]
    update_id = updates["result"][last_update]["update_id"]
    return text, chat_id, update_id


def handle_updates(updates):
    for update in updates["result"]:
        text = update["message"]["text"]
        chat = update["message"]["chat"]["id"]
        # items = db.get_items(chat)
        if str(chat) in admins.keys():
            handle_admin_updates(updates, chat, text, admins[str(chat)])
        else:
            handle_user_updates(updates, chat, text)


def send_message(text, chat_id, reply_markup=None):
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
    if reply_markup:
        url += "&reply_markup={}".format(reply_markup)
    get_url(url)


# Keyboards


def build_keyboard(items):
    keyboard = [[item] for item in items]
    reply_markup = {"keyboard": keyboard, "one_time_keyboard": True}
    return json.dumps(reply_markup)


def build_admin_keyboard():
    items = ['הכנסה', 'הוצאה', 'חיפוש', 'גיבוי', 'איפוס', 'עדכונים', 'היסטוריית פעולות']
    keyboard = [[item] for item in items]
    reply_markup = {"keyboard": keyboard, "one_time_keyboard": True}
    return json.dumps(reply_markup)


def build_user_keyboard():
    items = ['משתמש א', 'משתמש ב']
    keyboard = [[item] for item in items]
    reply_markup = {"keyboard": keyboard, "one_time_keyboard": True}
    return json.dumps(reply_markup)


def build_reset_keyboard():
    items = ['full reset', 'half reset']
    keyboard = [[item] for item in items]
    reply_markup = {"keyboard": keyboard, "one_time_keyboard": True}
    return json.dumps(reply_markup)


def build_updates_keyboard():
    items = ['משתמש א', 'משתמש ב', 'קופה', 'קופה$']
    keyboard = [[item] for item in items]
    reply_markup = {"keyboard": keyboard, "one_time_keyboard": True}
    return json.dumps(reply_markup)


# Parsers


def text_to_dict(text):
    words = str.split(text, " ")
    words_dict = {
        "sum": words[0],
        "description": words[1],
        "name": words[2],
    }
    return words_dict


def parse_tuple_to_dict(result):
    result = {
        "type": result[4],
        "amount": result[0],
        "name": result[1],
        "description": result[2],
        "date": result[3]
    }
    result_str = str(result)
    chars_to_replace = ['{', '}', "'"]
    for char in chars_to_replace:
        result_str = result_str.replace(char, '')
    return result_str

# States handlers


def set_states(chat, text):
    if text == 'הכנסה':
        update_states_dict(states, 'הכנסה')
        send_message("enter income and details", chat)
    elif text == 'הוצאה':
        update_states_dict(states, 'הוצאה')
        send_message("enter outcome", chat)
    elif text == 'חיפוש':
        update_states_dict(states, 'חיפוש')
        send_message("search mode", chat)
    elif text == 'גיבוי':
        update_states_dict(states, 'גיבוי')
        send_message("backup mode", chat)
    elif text == 'איפוס':
        update_states_dict(states, 'איפוס')
        keyboard = build_reset_keyboard()
        send_message("reset mode", chat, keyboard)
    elif text == 'עדכונים':
        update_states_dict(states, 'עדכונים')
        keyboard = build_updates_keyboard()
        send_message("update mode", chat, keyboard)
    elif text == 'היסטוריית פעולות':
        update_states_dict(states, 'היסטוריית פעולות')
        send_message("history mode press any key", chat)


def handle_state_request(state, chat, text):
    if state == "הכנסה":
        handle_income_outcome_input(text, chat, state)
    elif state == "הוצאה":
        handle_income_outcome_input(text, chat, state)
    elif state == "חיפוש":
        handle_search(text, chat)
    elif state == "גיבוי":
        handle_backup(text, chat)
    elif state == "איפוס":
        handle_reset(text, chat)
    elif state == "עדכונים":
        if text == 'קופה':
            update_states_dict(update_states, 'קופה')
            send_message('enter new amount for the shekel bank', chat)
        elif text == 'קופה$':
            update_states_dict(update_states, 'קופה$')
            send_message('enter new amount for the dollar bank', chat)
        elif text == 'משתמש א':
            update_states_dict(update_states, 'משתמש א')
            send_message('enter new amount for user a bank', chat)
        elif text == 'משתמש ב':
            update_states_dict(update_states, 'משתמש ב')
            send_message('enter new amount for user b bank', chat)
        elif re.fullmatch(r'^[0-9]+$', text):
            update_state = get_current_state(update_states)
            if update_state == 'קופה':
                handle_update_sum_at(dbhelper.SHEKEL_HISTORY_TABLE_NAME, text, chat)
            elif update_state == 'קופה$':
                handle_update_sum_at(dbhelper.DOLLAR_HISTORY_TABLE_NAME, text, chat)
            elif update_state == 'משתמש א':
                handle_update_sum_at(dbhelper.USER_A_TABLE_NAME, text, chat)
            elif update_state == 'משתמש ב':
                handle_update_sum_at(dbhelper.USER_B_TABLE_NAME, text, chat)
            else:
                send_message('invalid input', chat)
        else:
            send_message('invalid input', chat)
    elif state == "היסטוריית פעולות":
        send_message('total history', chat)
        handle_history(chat)
        states['היסטוריית פעולות'] = False
        send_message('end of history :)', chat)


def handle_updates_state(text, chat):
    if text == 'קופה ':
        send_message('enter new money amount', chat)
    elif text == 'קופה$':
        send_message('enter new dollar amount', chat)
    elif text == 'משתמש ב':
        send_message('enter new user b amount', chat)
    elif text == 'משתמש א':
        send_message('enter new user a amount', chat)
    else:
        send_message('invalid input', chat)


def update_states_dict(dictionary , true_state):
    for state in dictionary:
        dictionary[state] = False
    dictionary[true_state] = True


def get_current_state(dictionary):
    for state in dictionary:
        if dictionary[state]:
            return state


# Button handlers


def handle_income_outcome_input(text, chat, state):
    if input_pattern.fullmatch(text) is not None:
        data = text_to_dict(text)
        data["date"] = str(datetime.datetime.now())
        if '$' in text:
            data["sum"] = data["sum"].replace('$', '')
            db.insert_col_data(data["sum"], data["description"], data["name"], data["date"], state, True)
            db.get_items()
        else:
            db.insert_col_data(data["sum"], data["description"], data["name"], data["date"], state, False)
            db.get_items()
    else:
        send_message("invalid input", chat)


def handle_backup(text, chat):
    result = db.sum_tables_until_date(text)
    for key in result.keys():
        send_message('the sum at the ' + key + ' bank until ' + text + ' is: ' + str(result[key]), chat)


def handle_reset(text, chat):
    pass


def handle_search(text, chat):
    results = []
    if re.match("\d{1,2}[.,/,\,-]\d{1,2}[.,/,\,-]\d{2,4}", text):
        for date in yield_valid_dates(text):
            results = (db.search_dates(datetime.datetime.strftime(date, dbhelper.date_format)))
    else:
        results = db.search_names(text)
        results = results + db.search_description(text )
        results = results + db.search_sums(text)
    for result in results:
        res = parse_tuple_to_dict(result)
        send_message(res, chat)


def yield_valid_dates(text):
    for match in re.finditer(r"\d{1,2}[.,/,\,-]\d{1,2}[.,/,\,-]\d{2,4}", text):
        try:
            for date_format in date_formats:
                try:
                    date = datetime.datetime.strptime(match.group(0), date_format)
                    yield date
                except ValueError:
                    pass
        except ValueError as error:
            print(error)


def handle_update_sum_at(table_name, text, chat):
    if table_name == dbhelper.SHEKEL_HISTORY_TABLE_NAME:
        db.update_sum_at('shekel', text)
    if table_name == dbhelper.DOLLAR_HISTORY_TABLE_NAME:
        db.update_sum_at('dollar', text)
    if table_name == dbhelper.USER_A_TABLE_NAME:
        db.update_sum_at('usera', text)
    if table_name == dbhelper.USER_B_TABLE_NAME:
        db.update_sum_at('userb', text)
    db.add_item_to_table(text, table_name + ' updated sum to: ' + text, str(chat), str(datetime.datetime.now()),
                         'עדכון', table_name)


def handle_history(chat):
    items_dict = db.get_items()
    for key in items_dict.keys():
        send_message(key, chat)
        for item in items_dict[key]:
            send_message(str(item), chat)

# Users type handlers


def handle_admin_updates(updates, chat, text, is_first_visit):
    keyboard = build_admin_keyboard()
    if is_first_visit:
        send_message("hey admin", chat, keyboard)
        admins[str(chat)] = False
    if text in states.keys():
        set_states(chat, text)
    else:
        state = get_current_state(states)
        handle_state_request(state, chat, text)


def handle_user_updates(updates, chat, text):
    keyboard = build_user_keyboard()
    send_message("hi user", chat, keyboard)


def main():
    db.setup()
    items = db.get_items()
    for key in items:
        print(key)
        for item in items[key]:
            print(item)
    last_update_id = None
    while True:
        updates = get_updates(last_update_id)
        if len(updates["result"]) > 0:
            last_update_id = get_last_update_id(updates) + 1
            handle_updates(updates)
        time.sleep(0.5)


if __name__ == '__main__':
    main()
