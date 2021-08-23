from datetime import datetime
import json
import requests
import time
import urllib
import re
from dbhelper import DBHelper

UPDATE_ID_TUPLE_INDEX = 2
TOKEN = "1932158682:AAGI6P5W5lZhYaX5EvdY-6tyLisHrJa-E5k"
URL = "https://api.telegram.org/bot{}/".format(TOKEN)
admins = {"820613555": True}
states = {"הכנסה": False, "הוצאה": False, "חיפוש": False, "גיבוי": False, "איפוס": False, "עדכונים": False,
          "היסטוריית פעולות": False}
users = [1979257669]
# pattern for the input text for income/outcome
input_pattern = re.compile(r'\d+\$?\s\w+\s\w+')
digits_pattern = re.compile(r'\d')
date_pattern = re.compile(r'\d[0123]')
db = DBHelper()


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


def set_states(chat, text):
    if text == 'הכנסה':
        for state in states:
            states[state] = False
        states["הכנסה"] = True
        send_message("enter income and details", chat)
    elif text == 'הוצאה':
        for state in states:
            states[state] = False
        states["הוצאה"] = True
        send_message("enter outcome", chat)
    elif text == 'חיפוש':
        for state in states:
            states[state] = False
        states["חיפוש"] = True
        send_message("search mode", chat)
    elif text == 'גיבוי':
        for state in states:
            states[state] = False
        states["גיבוי"] = True
        send_message("backup mode", chat)
    elif text == 'איפוס':
        for state in states:
            states[state] = False
        states["איפוס"] = True
        send_message("reset mode", chat)
    elif text == 'עדכונים':
        for state in states:
            states[state] = False
        states["עדכונים"] = True
        send_message("update mode", chat)
    elif text == 'היסטוריית פעולות':
        for state in states:
            states[state] = False
        states["היסטוריית פעולות"] = True
        send_message("history mode", chat)
        db.get_items()


def text_to_dict(text):
    words = str.split(text, " ")
    words_dict = {
        "sum": words[0],
        "description": words[1],
        "name": words[2],
    }
    return words_dict


def handle_income_outcome_input(text, chat, state):
    if input_pattern.fullmatch(text) is not None:
        data = text_to_dict(text)
        data["date"] = str(datetime.now())
        if '$' in text:
            data["sum"] = data["sum"].replace('$', '')
            db.insert_col_data(data["sum"], data["description"], data["name"], data["date"], state, True)
            db.get_items()
        else:
            db.insert_col_data(data["sum"], data["description"], data["name"], data["date"], state, False)
            db.get_items()
    else:
        send_message("invalid input", chat)


def handle_state_request(state, chat, text):
    if state == "הכנסה":
        handle_income_outcome_input(text, chat, state)
    elif state == "הוצאה":
        handle_income_outcome_input(text, chat, state)
    elif state == "חיפוש":
        for date in yield_valid_dates(text):
            print(date)
    elif state == "גיבוי":
        pass
    elif state == "איפוס":
        pass
    elif state == "עדכונים":
        pass
    elif state == "היסטורית פעולות":
        pass


def yield_valid_dates(text):
    for match in re.finditer(r"\d{1,2}-\d{1,2}-\d{4}", text):
        try:
            datetime.datetime.strptime(match.group(0), "%m-%d-%Y")
            yield match.group(0)
        except ValueError:
            pass


def get_current_state():
    for state in states:
        if states[state]:
            return state


def handle_admin_updates(updates, chat, text, is_first_visit):
    keyboard = build_admin_keyboard()
    if is_first_visit:
        send_message("hey admin", chat, keyboard)
        admins[str(chat)] = False
    if text in states.keys():
        set_states(chat, text)
    else:
        state = get_current_state()
        handle_state_request(state, chat, text)


def handle_user_updates(updates, chat, text):
    keyboard = build_user_keyboard()
    send_message("hi user", chat, keyboard)


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


def build_keyboard(items):
    keyboard = [[item] for item in items]
    reply_markup = {"keyboard": keyboard, "one_time_keyboard": True}
    return json.dumps(reply_markup)


def main():
    db.setup()
    last_update_id = None
    while True:
        updates = get_updates(last_update_id)
        if len(updates["result"]) > 0:
            last_update_id = get_last_update_id(updates) + 1
            handle_updates(updates)
        time.sleep(0.5)


if __name__ == '__main__':
    main()
