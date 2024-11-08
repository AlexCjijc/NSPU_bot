import schedule
import time
import telebot
import datetime
import sqlite3
import threading
from contextlib import closing

import api_data

TOKEN = '6882377792:AAGTgaCQhGUC8yZ4Z3TkiCq1VowW_XrjHxQ'
# основоной API к НГПУ Расписание
# 6882377792:AAGTgaCQhGUC8yZ4Z3TkiCq1VowW_XrjHxQ
# для теста API к тестовому боту
# 6937274132:AAGA9f8Q0oZ5TFN5ksKoPpxLPJ_pELFL8N8


bot = telebot.TeleBot(TOKEN)

lock = threading.Lock()
conn = sqlite3.connect('user_data.db', check_same_thread=False)

# DAYS_OF_WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресение"]
DAYS_OF_WEEK_REDACTED = ["понедельник", "вторник", "среду", "четверг", "пятницу", "субботу", "воскресенье"]

def get_users_data():
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, user_id_group FROM users")
    users_data = cursor.fetchall()
    cursor.close()
    return users_data


def zaochick_notification(url, date_print):
    table = api_data.get_table_zaochik_date(url, date_print)
    return table

def send_schedule_notification_with_retry(user_id, message, max_retries=3):
    for retry in range(max_retries):
        try:
            bot.send_message(user_id, message, parse_mode='html')
            with open('message_alert.txt', 'a') as file:
                file.write(f"Сообщение успешно отправлено пользователю {user_id}\n")
            break  # Если сообщение успешно отправлено, выходим из цикла
        except Exception as e:
            if retry < max_retries - 1:
                with open('message_alert.txt', 'a') as file:
                    file.write(f"XXX - Ошибка при отправке сообщения пользователю {user_id}. Повторная попытка ({retry + 1}/{max_retries}): {e}\n")
            else:
                with open('message_alert.txt', 'a') as file:
                    file.write(f"XXX - Ошибка при отправке сообщения пользователю {user_id}, все попытки исчерпаны: {e}\n")

def get_user_urls_with_lock():
    with lock:
        with closing(conn.cursor()) as cursor:
            cursor.execute("SELECT user_id, user_id_group, msg_today, msg_tomorrow, filter_on FROM users")
            return cursor.fetchall()

def process_schedule_notifications(date_offset):
    timestamp = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")  # Получаем текущую дату и время
    with open('message_alert.txt', 'a') as file:
        file.write(f"\n\n\nВРЕМЯ: {timestamp}\n")  # Записываем дату и время в файл
    base_date = datetime.datetime.now()
    target_date = base_date + datetime.timedelta(days=date_offset)
    user_urls = get_user_urls_with_lock()
    for user_id, url, mes_today, mes_tomorrow, filter_on in user_urls:
        if not url or (date_offset == 0 and mes_today == 'false') or (date_offset == 1 and mes_tomorrow == 'false'):
            continue
        try:
            if int(url) > 0:
                table = api_data.get_table(url, target_date, filter_on)
                message = f'📌Оповещение расписания📌\n' \
                          f'<b>🗓Расписание на {DAYS_OF_WEEK_REDACTED[target_date.weekday()]}🗓</b> \n{table}'
                send_schedule_notification_with_retry(user_id, message)
            elif int(url) < 0:
                table = zaochick_notification(url, target_date)
                if table:
                    message = f'📌Оповещение расписания📌\n' \
                              f'<b>🗓Расписание на {DAYS_OF_WEEK_REDACTED[target_date.weekday()]}🗓</b> \n{table}'
                    send_schedule_notification_with_retry(user_id, message)
        except Exception as e:
            with open('message_alert.txt', 'a') as file:
                file.write(f"XXX - Ошибка при обработке URL {url} пользователя {user_id}: {e}\n")
        time.sleep(1)

def table_today():
    process_schedule_notifications(0)

def table_tomorrow():
    process_schedule_notifications(1)


def notification():
    timestamp = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")  # Получаем текущую дату и время
    with open('message_message.txt', 'a') as file:
        file.write(f"\n\n\nВРЕМЯ: {timestamp}\n")  # Записываем дату и время в файл
    current_hour = time.localtime().tm_hour
    if current_hour != 7 and current_hour != 20:
        users_data = get_users_data()
        with lock, closing(conn.cursor()) as cursor:
            cursor.execute("SELECT user_id, user_id_group FROM users")
            users = cursor.fetchall()

            cursor.execute("SELECT user_id_group, notification FROM notifications")
            notifications = {user_id_group: old_notification for user_id_group, old_notification in cursor.fetchall()}

        for user_id, url in users_data:
            if not url:
                continue
            try:
                new_notification = api_data.notification(url)
                if url in notifications and new_notification != notifications[url]:
                    bot.send_message(user_id, f'📩<b>Уведомление</b>📩\n\n{new_notification}', parse_mode='html')
                    update_user_notification(url, new_notification)
                    with open('message_message.txt', 'a') as file:
                        file.write(f"Сообщение успешно отправлено пользователю {user_id}\n")
            except Exception as e:
                with open('message_message.txt', 'a') as file:
                    file.write(f"XXX - Ошибка при отправке сообщения пользователю {user_id}: {e}\n")
            time.sleep(0.1)
        pass


def update_user_notification(user_id_group, new_notification):
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET notification = ? WHERE user_id_group = ?", (new_notification, user_id_group))
    conn.commit()
    cursor.close()



schedule.every().monday.at("20:00").do(table_tomorrow)
schedule.every().tuesday.at("20:00").do(table_tomorrow)
schedule.every().wednesday.at("20:00").do(table_tomorrow)
schedule.every().thursday.at("20:00").do(table_tomorrow)
schedule.every().friday.at("20:00").do(table_tomorrow)
# -- в субботу не нужно присылать расписание на завтра, тк воскресенье
schedule.every().sunday.at("20:00").do(table_tomorrow)
# schedule.every().day.at("21:00").do(table_tomorrow)


schedule.every().monday.at("07:00").do(table_today)
schedule.every().tuesday.at("07:00").do(table_today)
schedule.every().wednesday.at("07:00").do(table_today)
schedule.every().thursday.at("07:00").do(table_today)
schedule.every().friday.at("07:00").do(table_today)
schedule.every().saturday.at("07:00").do(table_today)
# schedule.every().day.at("07:00").do(table_today)

schedule.every().hour.at(":00").do(notification)

# table_tomorrow()
# table_today()
notification()



#для теста
# table_today()
# table_tomorrow()
# notification()
# schedule.every(5).minutes.do(notification)


while True:
    schedule.run_pending()
    time.sleep(1)

