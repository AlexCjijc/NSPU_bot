import telebot
from telebot import types
import datetime
import sqlite3
import time
import threading
import requests
import re
from contextlib import closing

import parcing_schedule
import api_data

bot = telebot.TeleBot('')
index_news = 0
lock = threading.Lock()
conn = sqlite3.connect('user_data.db', check_same_thread=False)
c = conn.cursor()
# Создание таблицы для хранения данных пользователей
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             user_id INTEGER,
             username TEXT,
             user_id_group TEXT,
             msg_today TEXT,
             msg_tomorrow TEXT,
             filter_on TEXT)''')



# Создание таблицы для хранения сообщении для каждой группы
c.execute('''CREATE TABLE IF NOT EXISTS notifications 
             (user_id_group TEXT,
             notification TEXT)''')

DAYS_OF_WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресение"]
DAYS_OF_WEEK_REDACTED = ["понедельник", "вторник", "среду", "четверг", "пятницу", "субботу", "воскресенье"]

MESSAGE_INFO = '''
🤖Что этот бот умеет?🤖
            
▫️Отображать актуальное расписание. Также этот бот умеет фильтровать расписание по дате или неделям, которые указаны в расписании пар, если же пара еще не началась или уже закончилась, то бот не будет выводить эти пары. НО будет выводить в "Полное расписание" расписание без фильтрации. ФИЛЬТРАЦИЮ МОЖНО ОТКЛЮЧИТЬ В НАСТРОЙКАХ! Также присутствует поиск "По дате", отображает расписание по дате от пользователя с фильтрацией. Полностью поддерживается расписание заочников.

▫️Оповещение пользователей. Бот каждый день присылает расписание на завтра c 20:00 по Новосибирскому времени и на сегодня c 07:00 по Новосибирскому времени. ОПОВЕЩЕНИЕ МОЖНО ОТКЛЮЧИТЬ В НАСТРОЙКАХ.

▫️Бот присылает актуальное сообщение группе. Если же бот видит то что сообщение группе обновилось, то бот пришлет уведомление с актуальной информацией.

▫️Вкладка "Новости". В этой вкладке можно посмотреть 5 последних новостей.

▫️Вкладка "Корпусы". В этой вкладке бот по вашему выбору пришлет локацию каждого корпуса.


👨‍🎓Об авторе👨‍🎓
Бота создал студент НГПУ🏫 - Чижиков Алексей Дмитриевич

📩По всем вопросам или ошибкам писать сюда: 
            '''


def get_user_url(user_id):
    with closing(conn.cursor()) as cursor:
        cursor.execute("SELECT user_id_group FROM users WHERE user_id = ?", (user_id,))
        url = cursor.fetchone()
    return url[0] if url else None


def send_keyboard(chat_id, message_text, buttons):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if buttons[-1] != '⬅️Назад в меню':
        btns = [types.KeyboardButton(text) for text in buttons]
        markup.add(*btns)
    else:
        btnBack = buttons[-1]
        buttons.pop()
        btns = [types.KeyboardButton(text) for text in buttons]
        markup.add(*btns)
        markup.row(btnBack)
    bot.send_message(chat_id, message_text, reply_markup=markup)


def find_groups(group_name):
    response = requests.get("https://schedule.nspu.ru/api/groups/", verify=False)
    groups_json = response.json()
    matching_groups = [group for group in groups_json["groups"] if group_name.lower() in group["name"].lower()]
    return matching_groups

@bot.message_handler(commands = ['start'])
def mainStart(message):
    user_id = message.from_user.id
    username = message.chat.username
    with closing(conn.cursor()) as c:
        with lock:
            c.execute("DELETE FROM users WHERE user_id=?", (user_id,))
            conn.commit()
    # buttons = ['🧑‍🎓Группы', '👨‍🏫Преподавателя']
    bot.reply_to(message, f'👋 Приветсвую вас, {message.from_user.first_name}!\nЯ бот для расписания НГПУ!\n\n'
                                      f'🔍Для поиска напишите свой номер группы: ')


@bot.message_handler(func=lambda message: True)
def on_click(message):
    url = get_user_url(message.from_user.id)
    with closing(conn.cursor()) as cursor:
        cursor.execute("SELECT filter_on FROM users WHERE user_id = ?", (message.from_user.id,))
        filter_on = cursor.fetchone()
    if (url == None or url == '') and message.text not in '‍👨‍🏫Преподавателя':
        try:
            group_name = message.text
            matching_groups = find_groups(group_name)
            if not matching_groups:
                bot.reply_to(message, "🔍Для поиска напишите свой номер группы: ")
            else:
                markup = telebot.types.InlineKeyboardMarkup()
                for group in matching_groups[:20]:  # Показываем первые 20 результатов
                    markup.add(telebot.types.InlineKeyboardButton(text=group['name'], callback_data=str(group['id'])))
                bot.reply_to(message, "🧑‍🎓Результаты поиска, выберите свою группу:", reply_markup=markup)
        except Exception as e:
            bot.reply_to(message, f'Ошибка❗️ \n{e}')
    else:
        url = get_user_url(message.from_user.id)
        if message.text == '🧑‍🎓Группы':
            on_click(message)

        if message.text == '🗓Расписание':
            buttons = ['📆На сегодня', '📆На завтра', '📆По дате','🗓Полное расписание', '⬅️Назад в меню']
            send_keyboard(message.chat.id,
                          '➡️Вкладка расписание⬅️\nВам доступно следующее:\n\n▫️ 📆На сегодня\n▫️ 📆На завтра\n▫️ 📆По дате\n▫️ 🗓Полное расписание\n',
                          buttons)
        if message.text == '📆На сегодня':
            try:
                date = datetime.datetime.now()
                if int(url) > 0:
                    table = api_data.get_table(url, date, filter_on[0])
                    # print(filter_on[0])
                    bot.reply_to(message, f'🗓<b>Расписание на {DAYS_OF_WEEK_REDACTED[date.weekday()]}</b>🗓 \n{table}',
                                 parse_mode='html')
                elif int(url) < 0:
                    table = api_data.get_table_zaochik_date(url, date)
                    bot.reply_to(message, f'🗓<b>Расписание на {DAYS_OF_WEEK_REDACTED[date.weekday()]}</b>🗓 \n{table}',
                                 parse_mode='html')
            except Exception as e:
                bot.reply_to(message, f'Ошибка❗️ \n{e}')
        if message.text == '📆На завтра':
            try:
                today = datetime.datetime.now()
                tomorrow = today + datetime.timedelta(days=1)
                if int(url) > 0:
                    table = api_data.get_table(url, tomorrow, filter_on[0])
                    bot.reply_to(message, f'🗓<b>Расписание на {DAYS_OF_WEEK_REDACTED[tomorrow.weekday()]}</b>🗓 \n{table}',
                                 parse_mode='html')
                elif int(url) < 0:
                    table = api_data.get_table_zaochik_date(url, tomorrow)
                    bot.reply_to(message, f'🗓<b>Расписание на {DAYS_OF_WEEK_REDACTED[tomorrow.weekday()]}</b>🗓 \n{table}',
                                 parse_mode='html')
            except Exception as e:
                bot.reply_to(message, f'Ошибка❗️ \n{e}')
        if message.text == '📆По дате':
            bot.send_message(message.chat.id, f'📆Введите дату формата ДД.ММ.ГГГГ\nНапример 19.08.2024')
        if re.match(r'\d{2}\.\d{2}\.\d{4}' , message.text):
            try:
                if int(url) > 0:
                    date = datetime.datetime.strptime(message.text, '%d.%m.%Y') + datetime.timedelta(minutes=1)
                    table = api_data.get_table(url, date, filter_on[0]) if api_data.get_table(url, date, filter_on[0])  else "Нет занятий!"
                    bot.reply_to(message, f'🗓<b>Расписание на {DAYS_OF_WEEK_REDACTED[date.weekday()]}, {message.text}</b>🗓 \n{table}',
                                 parse_mode='html')
                elif int(url) < 0:
                    date = datetime.datetime.strptime(message.text, '%d.%m.%Y') + datetime.timedelta(minutes=1)
                    table = api_data.get_table_zaochik_date(url, date) if api_data.get_table_zaochik_date(url, date) else "Нет занятий!"
                    bot.reply_to(message,
                                 f'🗓<b>Расписание на {DAYS_OF_WEEK_REDACTED[date.weekday()]}, {message.text}</b>🗓 \n{table}',
                                 parse_mode='html')
            except Exception as e:
                bot.reply_to(message, f'Ошибка❗️ \n{e}')
        if message.text == '🗓Полное расписание':
            try:
                tableOnWeek = api_data.get_week_schedule(url)
                for day_index in range(len(tableOnWeek)):  # Предполагая, что учебные занятия проводятся с понедельника по субботу
                    bot.reply_to(message, f'\n{tableOnWeek[day_index]}', parse_mode='html')
                    time.sleep(0.1)
            except Exception as e:
                bot.reply_to(message, f'Ошибка❗️ \n{e}')

        if message.text == '📩Сообщение':
            try:
                with closing(conn.cursor()) as c:
                    with lock:
                        c.execute("SELECT notification FROM notifications WHERE user_id_group=?", (url,))
                        notification = c.fetchone()
                bot.reply_to(message, notification)
            except Exception as e:
                bot.reply_to(message, f'Ошибка❗️ \n{e}')

        if message.text == '⬅️Назад в меню':
            buttons = ['🗓Расписание', '📰Новости', '🏫Корпусы', '📩Сообщение', '🧾О боте', '⚙️Настройки']
            send_keyboard(message.chat.id,
                          '➡️Главное меню⬅️\nВам доступно следующее:\n\n▫️ 🗓Расписание\n▫️ 📰Новости\n▫️ 🏫Корпуса\n▫️ 📩Сообщение\n▫️ 🧾О боте\n▫️ ⚙️Настройки\n',
                          buttons)

            global index_news
        if message.text == '📰Новости':
            try:
                buttons = ['Следующая➡️', '⬅️Назад в меню']
                send_keyboard(message.chat.id,
                              '➡️Новости⬅️',
                              buttons)
                index_news = 0
                bot.send_message(message.chat.id, parcing_schedule.news_parcer(0))
            except Exception as e:
                bot.reply_to(message, f'Ошибка❗️ \n{e}')
        if message.text == 'Следующая➡️':
            try:
                index_news += 1
                buttons = ['⬅️Предыдущая', 'Следующая➡️', '⬅️Назад в меню']
                send_keyboard(message.chat.id, parcing_schedule.news_parcer(index_news), buttons)
                if index_news > 4:
                    index_news = 5
                    buttons = ['⬅️Предыдущая', '⬅️Назад в меню']
                    send_keyboard(message.chat.id,
                                  f'Дальше новостей нет!\n'
                                  f'Больше новостей тут⬇️\n'
                                  f'https://nspu.ru/news/', buttons)
            except Exception as e:
                bot.reply_to(message, f'Ошибка❗️ \n{e}')
        if message.text == '⬅️Предыдущая':
            try:
                index_news -= 1
                buttons = ['⬅️Предыдущая', 'Следующая➡️', '⬅️Назад в меню']
                send_keyboard(message.chat.id, parcing_schedule.news_parcer(index_news), buttons)
                if index_news == 0:
                    index_news = 0
                    buttons = ['Следующая➡️', '⬅️Назад в меню']
                    send_keyboard(message.chat.id,
                                  f'Дальше новостей нет!\n'
                                  f'Больше новостей тут⬇️\n'
                                  f'https://nspu.ru/news/', buttons)

            except Exception as e:
                bot.reply_to(message, f'Ошибка❗️ \n{e}')

        if message.text == '⚙️Настройки':
            try:
                with closing(conn.cursor()) as c:
                    with lock:
                        c.execute("SELECT filter_on FROM users WHERE user_id = ?", (message.from_user.id,))
                        row = c.fetchone()
                        filter_on = row[0]
                        conn.commit()
                        buttons = ['🗓Изменить расписание', '📌Настройки оповещения','⛔OFF фильтрацию' if filter_on == 'true' else '✅ON фильтрацию', '⬅️Назад в меню']
                        send_keyboard(message.chat.id,
                                      '➡️Настройки⬅️\nВам доступно следующее:\n\n▫️🗓Изменить расписание\n▫️📌Настройки оповещения\n▫️🔬Настройки фильтрации расписания',
                                      buttons)
            except Exception as e:
                bot.reply_to(message, f'Ошибка❗️ \n{e}')

        if message.text == '✅ON фильтрацию':
            try:
                with closing(conn.cursor()) as c:
                    with lock:
                        c.execute("UPDATE users SET filter_on = ? WHERE user_id = ?", ('true', message.from_user.id))
                        conn.commit()
                buttons = ['⚙️Настройки', '⬅️Назад в меню']
                send_keyboard(message.chat.id,
                              'Ваши настройки обновлены❗️',
                              buttons)
            except Exception as e:
                bot.reply_to(message, f'Ошибка❗️ \n{e}')

        if message.text == '⛔OFF фильтрацию':
            try:
                with closing(conn.cursor()) as c:
                    with lock:
                        c.execute("UPDATE users SET filter_on = ? WHERE user_id = ?", ('false', message.from_user.id))
                        conn.commit()

                buttons = ['⚙️Настройки', '⬅️Назад в меню']
                send_keyboard(message.chat.id,
                              'Ваши настройки обновлены❗️',
                              buttons)
            except Exception as e:
                bot.reply_to(message, f'Ошибка❗️ \n{e}')

        if message.text == '🗓Изменить расписание':
            mainStart(message)
        if message.text == '📌Настройки оповещения':
            try:
                with closing(conn.cursor()) as c:
                    with lock:
                        c.execute("SELECT msg_today, msg_tomorrow FROM users WHERE user_id = ?", (message.from_user.id,))
                        row = c.fetchone()
                        msg_today = row[0]
                        msg_tomorrow = row[1]
                        conn.commit()
                    buttons = ['⛔️Отключить на сегодня' if msg_today == 'true' else '✅Включить на сегодня',
                    '⛔️Отключить на завтра' if msg_tomorrow == 'true' else '✅Включить на завтра', '⬅️Назад в меню']
                    send_keyboard(message.chat.id,
                                  '➡️Настройки оповещения⬅️\nВам доступно следующее:\n\n▫️✅Включить или ⛔️отключить оповещения расписания',
                                  buttons)
            except Exception as e:
                bot.reply_to(message, f'Ошибка❗️ \n{e}')

        if message.text == '⛔️Отключить на сегодня':
            try:
                with closing(conn.cursor()) as c:
                    with lock:
                        c.execute("UPDATE users SET msg_today = ? WHERE user_id = ?", ('false', message.from_user.id))
                        conn.commit()

                buttons = ['📌Настройки оповещения', '⬅️Назад в меню']
                send_keyboard(message.chat.id,
                              'Ваши настройки обновлены❗️',
                              buttons)
            except Exception as e:
                bot.reply_to(message, f'Ошибка❗️ \n{e}')

        if message.text == '✅Включить на сегодня':
            try:
                with closing(conn.cursor()) as c:
                    with lock:
                        c.execute("UPDATE users SET msg_today = ? WHERE user_id = ?", ('true', message.from_user.id))
                        conn.commit()
                buttons = ['📌Настройки оповещения', '⬅️Назад в меню']
                send_keyboard(message.chat.id,
                              'Ваши настройки обновлены❗️',
                              buttons)
            except Exception as e:
                bot.reply_to(message, f'Ошибка❗️ \n{e}')

        if message.text == '⛔️Отключить на завтра':
            try:
                with closing(conn.cursor()) as c:
                    with lock:
                        c.execute("UPDATE users SET msg_tomorrow = ? WHERE user_id = ?", ('false', message.from_user.id))
                        conn.commit()

                buttons = ['📌Настройки оповещения', '⬅️Назад в меню']
                send_keyboard(message.chat.id,
                              'Ваши настройки обновлены❗️',
                              buttons)
            except Exception as e:
                bot.reply_to(message, f'Ошибка❗️ \n{e}')

        if message.text == '✅Включить на завтра':
            try:
                with closing(conn.cursor()) as c:
                    with lock:
                        c.execute("UPDATE users SET msg_tomorrow = ? WHERE user_id = ?", ('true', message.from_user.id))
                        conn.commit()
                buttons = ['📌Настройки оповещения', '⬅️Назад в меню']
                send_keyboard(message.chat.id,
                              'Ваши настройки обновлены❗️',
                              buttons)
            except Exception as e:
                bot.reply_to(message, f'Ошибка❗️ \n{e}')

        if message.text == 'Кто твой создатель?': #пасхалка :)
            video_path = 'logo.mp4'
            video = open(video_path, 'rb')
            bot.send_video(message.chat.id, video,  caption='Чижиков Studio🐦\n\nСпасибо, что выбрали наc❤️')
            video.close()
        if ("бот" in message.text or "Бот" in message.text) and not "🧾О боте" in message.text : #пасхалка :)
            bot.send_message(message.chat.id, f'Я не бот😢\nУ меня тоже есть чувства\n\nДержи цветочек🌺')

        if message.text == '🏫Корпусы':
            buttons = ['Главный корпус НГПУ', 'ИФМИП', 'ИМИСК', 'ИОДО', '⬅️Назад в меню']
            send_keyboard(message.chat.id,
                          '➡️Корпусы⬅️\n\nВыберите корпус, чтобы посмотреть его местоположение🗺️',
                          buttons)
        if message.text in ['Главный корпус НГПУ', 'ИФМИП', 'ИМИСК', 'ИОДО']:
            locations = {
                'Главный корпус НГПУ': (55.000557, 83.016700),
                'ИФМИП': (55.000171, 83.021450),
                'ИМИСК': (54.999580, 83.018794),
                'ИОДО': (54.998198, 83.014693)
            }
            location_name, (latitude, longitude) = message.text, locations[message.text]
            bot.send_message(message.chat.id, f"{location_name}: ")
            bot.send_location(message.chat.id, latitude, longitude)

        if message.text == '🧾О боте' or message.text == '/help':
            bot.send_message(message.chat.id, MESSAGE_INFO)



@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        username = call.message.chat.username
        user_id = call.from_user.id
        bot.edit_message_text(f"🧑‍🎓Группа выбрана!\n\n"
                              f"Расписание успешно загружено!\n"
                              f"Приятного пользования 😊", call.message.chat.id,
                              call.message.message_id)
        with closing(conn.cursor()) as c:
            with lock:
                c.execute("DELETE FROM users WHERE user_id=?", (user_id,))
                c.execute("INSERT INTO users (user_id, username, msg_today, msg_tomorrow, filter_on) VALUES (?, ?, ?, ?,?)", (user_id, username, "true", "true", "true"))
                conn.commit()
        with closing(conn.cursor()) as c:
            c.execute("UPDATE users SET user_id_group = ? WHERE user_id = ?", (call.data, user_id))
            conn.commit()

        message = api_data.notification(call.data)

        # Проверка наличия записи с группой в базе данных
        with closing(conn.cursor()) as c:
            c.execute("SELECT COUNT(*) FROM notifications WHERE user_id_group = ?", (call.data,))
            result = c.fetchone()
            if result[0] == 0:
                # Вставка новой записи в базу данных

                c.execute(
                    "INSERT INTO notifications (user_id_group, notification) VALUES (?, ?)",
                    (call.data, message))
                conn.commit()
        buttons = ['🗓Расписание', '📰Новости', '🏫Корпусы', '📩Сообщение', '🧾О боте', '⚙️Настройки']
        send_keyboard(call.message.chat.id,
                      '➡️Главное меню⬅️\nВам доступно следующее:\n\n▫️ 🗓Расписание\n▫️ 📰Новости\n▫️ 🏫Корпуса\n▫️ 📩Сообщение\n▫️ 🧾О боте\n▫️ ⚙️Настройки\n',
                      buttons)
    except Exception as e:
        bot.reply_to(call.message.chat.id, f'Ошибка❗️ \n{e}')


if __name__ == "__main__":
    bot.infinity_polling()