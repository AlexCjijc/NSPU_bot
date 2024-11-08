import requests
import datetime
import re
import json
from bs4 import BeautifulSoup
import sqlite3

WORDS = ['затем', 'потом', 'позже']
DAYS_OF_WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресение"]

connection =  sqlite3.connect('user_data.db', check_same_thread=False)
cursor = connection.cursor()

def get_academic_week(date):
    today = date.date()
    year = datetime.datetime.now().year
    a_year = year - 1 if datetime.datetime.now().month <= 6 else year
    academic_year_start = datetime.date(a_year, 9, 1)

    days_passed = (today - academic_year_start).days
    academic_week = days_passed // 7 + 1
    return academic_week


def filter_by_week(pair, date):
    week_str = pair['comment']
    week_str = re.sub(r'(с)(\d+)', r'\1 \2', week_str)
    week_str = re.sub(r'(по)(\d+)', r'\1 \2', week_str)
    week = get_academic_week(date)

    week_ranges = re.findall(r'с (\d+) ?(?:н\.|недели?) ?по (\d+) ?(?:н\.|неделю?)', week_str)

    if str(week) in week_str:
        for start_week, end_week in week_ranges:
            if week == start_week or end_week==week:
                return True
    if 'с' in week_str or 'по' in week_str:
        for start_week, end_week in week_ranges:
            if int(start_week) <= week <= int(end_week):
                return True
    else:
        weeks_matched = re.findall(r'\d+', week_str)
        for matched_week in weeks_matched:
            if '-' in matched_week:
                start, end = map(int, matched_week.split('-'))
                if start <= week <= end:
                    return True
            if int(matched_week) == int(week):
                return True
    return False


def filter_by_date(pair, date, filter_on='true'):
    try:  # попытка офильтрации по датам/неделям
        dates_str = pair['comment']
        dates = re.findall(r'(\d{2}\.\d{2})', dates_str)
        # Текущий год
        current_year = str(datetime.datetime.now().year)

        # Изолированные даты
        isolated_dates = re.findall(r'\b(\d{2}\.\d{2})\b', dates_str)
        isolated_dates_year = [f"{date_str}.{current_year}" for date_str in isolated_dates]

        # Даты с периодами
        period_dates = re.findall(r'с (\d{2}\.\d{2}) (?:до|по)\s+(\d{2}\.\d{2})', dates_str)
        if filter_on == 'false':
            return True

        # Проверка изолированных дат
        for date_str in isolated_dates_year:
            check_date = datetime.datetime.strptime(date_str, '%d.%m.%Y')
            if check_date.date() == date.date():
                # print('one date')
                return True
            if check_date.date() <= date.date() and any(word in dates_str for word in WORDS):
                return True


        # Проверка дат в периодах
        for start_str, end_str in period_dates:
            # print('period')
            start_date_str = f"{start_str}.{current_year}"
            end_date_str = f"{end_str}.{current_year}"
            start_date = datetime.datetime.strptime(start_date_str, '%d.%m.%Y')
            end_date = datetime.datetime.strptime(end_date_str, '%d.%m.%Y')
            # Включаем проверку на принадлежность диапазону [start_date, end_date]
            if start_date <= date <= end_date:
                return True

        if 'недел' in pair['comment'] or 'н.' in pair['comment'] or 'нед.' in pair['comment']:
            return filter_by_week(pair, date)

        elif 'с' in dates_str and 'н.' in dates_str and 'недел' not in dates_str:  # фильтрация расписвния тип "с 11.03.2024 г., 3 н. "
            dates = re.search(r'(\d{2}\.\d{2})', pair['comment']).group(0)
            start_date = datetime.datetime.strptime(dates + f'.{datetime.date.today().year}', '%d.%m.%Y')
            weeks_delta = re.findall(r'(\d+) н\.', pair['comment'])
            weeks_delta = int(max(weeks_delta))
            dates_for_end = max(re.findall(r'(\d{2}\.\d{2})', pair['comment']))
            start_date_for_end = datetime.datetime.strptime(dates_for_end + f'.{datetime.date.today().year}',
                                                            '%d.%m.%Y')
            end_date = start_date_for_end + datetime.timedelta(weeks=weeks_delta)
            if start_date <= date <= end_date:
                return True
        elif ('до' in dates_str or 'по' in dates_str) and 'недел' not in dates_str:  # для дат с ... по ... "09.02.24 по 16.02.24; с 29.03.24 по 14.06.24"
            start_dates = re.findall(r'с (\d{2}\.\d{2})', dates_str)
            end_dates = re.findall(r'(?:до|по)\s+(\d{2}\.\d{2})', dates_str)
            for start, end in zip(start_dates, end_dates):
                start_date = datetime.datetime.strptime(start + f'.{datetime.date.today().year}', '%d.%m.%Y')
                end_date = datetime.datetime.strptime(end + f'.{datetime.date.today().year}', '%d.%m.%Y')
                if start_date <= date <= end_date:
                    return True
        elif 'с' in dates_str and 'недел' not in dates_str and not ('до' in dates_str or 'по' in dates_str and 'н.' in dates_str):  # фильтрация расписвния тип "с 11.03"
            dates = re.search(r'(\d{2}\.\d{2})', pair['comment']).group(0)
            start_date = datetime.datetime.strptime(dates + f'.{datetime.date.today().year}', '%d.%m.%Y')
            if start_date <= date:
                return True
        elif dates:  # для одиночных дат " 29.03.24; 12.04.24; 26.04.24; 10.05.24 (24.05.24; 07.06.24 (п.з)). "
            for date_str in dates:
                check_date = datetime.datetime.strptime(date_str + f'.{datetime.date.today().year}', '%d.%m.%Y')
                if check_date.date() == date.date():
                    return True
        elif any(word in dates_str for word in WORDS):
            return True
        return False


    except Exception as e: # в случае ошибки фильтрации вернуть без изменении расписание
        print(f"Ошибка фильтрации: {e}")
        return True


def get_table_zaochik_date(id_group, date_print):
    response = requests.get('' + id_group, verify=False)
    try:
        # Удаление недопустимых символов из JSON
        cleaned_response = response.text.replace('\x00', '').replace('\x1f', '')
        cleaned_response = re.sub("^\s+|\n|\r|\s+$", '', cleaned_response)
        json_data = json.loads(cleaned_response, strict=False)
    except json.decoder.JSONDecodeError as e:
        cursor.execute("SELECT data FROM dataSchedule WHERE id_group = ?", (id_group,))
        response = cursor.fetchone()
        cleaned_response = response[0].replace('\x00', '').replace('\x1f', '')
        cleaned_response = re.sub("^\s+|\n|\r|\s+$", '', cleaned_response)
        json_data = json.loads(cleaned_response, strict=False)

    output = ""
    pairs_by_date = {}
    for pair in json_data['pairs']:
        date = pair['date']
        if date not in pairs_by_date:
            pairs_by_date[date] = []
        pairs_by_date[date].append(pair)

    for date, pairs in pairs_by_date.items():
        if date == date_print.strftime('%Y-%m-%d'):  # Сравнение даты с завтрашней датой
            pairs_details = "".join([
                f"🕐{p['call']}🕐\n"
                f"📚{p['predmet']}\n"
                f"👨‍🏫{p['prepod']}\n"
                f"🚪а.{p['room']}, {p['type']}\n"
                f"{p['comment']}\n"
                for p in pairs
            ])
            output = f"📅{date}\n{pairs_details}"
    return output


def get_table_zaochik(response, id_group):
    try:
        # Удаление недопустимых символов из JSON
        cleaned_response = response.text.replace('\x00', '').replace('\x1f', '')
        cleaned_response = re.sub("^\s+|\n|\r|\s+$", '', cleaned_response)
        json_data = json.loads(cleaned_response, strict=False)
    except json.decoder.JSONDecodeError as e:
        cursor.execute("SELECT data FROM dataSchedule WHERE id_group = ?", (id_group,))
        response = cursor.fetchone()
        cleaned_response = response[0].replace('\x00', '').replace('\x1f', '')
        cleaned_response = re.sub("^\s+|\n|\r|\s+$", '', cleaned_response)
        json_data = json.loads(cleaned_response, strict=False)
    schedule = []
    day_schedule= ''
    pairs_by_date = {}
    for pair in json_data['pairs']:
            date = pair['date']
            if date not in pairs_by_date:
                pairs_by_date[date] = []
            pairs_by_date[date].append(pair)

    for date, pairs in pairs_by_date.items():
        pairs_details = "".join([
            f"🕐{p['call']}🕐\n"
            f"📚{p['predmet']}\n"
            f"👨‍🏫{p['prepod']}\n"
            f"🚪а.{p['room']}, {p['type']}\n"
            f"{p['comment']}\n"
            for p in pairs
        ])
        output = f"📅{date}\n{pairs_details}"
        schedule.append(output)
    return schedule


def get_table(id_group, date_print, filter_on='true'):
    date = date_print
    weekday = date.isoweekday()
    nums = int(date.isocalendar()[1])
    chetweek = 1 if (nums % 2) != 0 else 2  # 1 - 26числитель неделя 2 - знаменатель

    if int(id_group) < 0:
        return f'\nЗаочное расписание смотрите в "🗓Полном расписании"'
    else:
        response = requests.get('' + id_group, verify=False)


    try:
        # Удаление недопустимых символов из JSON
        cleaned_response = response.text.replace('\x00', '').replace('\x1f', '')
        cleaned_response = re.sub("^\s+|\n|\r|\s+$", '', cleaned_response)
        json_data = json.loads(cleaned_response, strict=False)
    except json.decoder.JSONDecodeError as e:
        cursor.execute("SELECT data FROM dataSchedule WHERE id_group = ?", (id_group,))
        response = cursor.fetchone()
        cleaned_response = response[0].replace('\x00', '').replace('\x1f', '')
        cleaned_response = re.sub("^\s+|\n|\r|\s+$", '', cleaned_response)
        json_data = json.loads(cleaned_response, strict=False)


    table = ''
    pairs_by_time_room = {}  # Словарь для хранения пар, сгруппированных по комбинации времени и кабинета

    for pair in json_data['pairs']:
        if weekday == pair['day'] and chetweek == pair['chetnechet'] and filter_by_date(pair, date, filter_on):
            time_room = f"{pair['call']} - {pair['room']} - {pair['predmet']} - {pair['comment']}"
            if time_room not in pairs_by_time_room:
                pairs_by_time_room[time_room] = {
                    'call': set(),
                    'predmets': set(),
                    'prepod': set(),
                    'room': set(),
                    'comment': set(),
                    'type': pair['type']
                }
            pairs_by_time_room[time_room]['call'].add(pair['call'])
            pairs_by_time_room[time_room]['predmets'].add(pair['predmet'])
            pairs_by_time_room[time_room]['prepod'].add(pair['prepod'])
            pairs_by_time_room[time_room]['room'].add(pair['room'])
            pairs_by_time_room[time_room]['comment'].add(pair['comment'])

    for time_room, pair_info in pairs_by_time_room.items():
        call = ', '.join(pair_info['call'])
        predmets = ', '.join(pair_info['predmets'])
        prepods = ', '.join(pair_info['prepod'])
        room = ', '.join(pair_info['room'])
        comment = ', '.join(pair_info['comment'])
        output = (f"🕐{call}🕐\n"
                  f"📚{predmets}\n"
                  f"👨‍🏫{prepods}\n"
                  f"🚪а.{room}, {pair_info['type']}\n"
                  f"📅{comment}\n\n")
        table += output
    return table if table else "Выходной день!"


def get_week_schedule(id_group):
    date = datetime.datetime.now()
    nums = int(date.isocalendar()[1])

    if int(id_group) < 0:
        response = requests.get('' + id_group, verify=False)
        return get_table_zaochik(response, id_group)

    else:
        response = requests.get('' + id_group, verify=False)

    try:
        # Удаление недопустимых символов из JSON
        cleaned_response = response.text.replace('\x00', '').replace('\x1f', '')
        cleaned_response = re.sub("^\s+|\n|\r|\s+$", '', cleaned_response)
        json_data = json.loads(cleaned_response, strict=False)
    except json.decoder.JSONDecodeError as e:
        cursor.execute("SELECT data FROM dataSchedule WHERE id_group = ?", (id_group,))
        response = cursor.fetchone()
        cleaned_response = response[0].replace('\x00', '').replace('\x1f', '')
        cleaned_response = re.sub("^\s+|\n|\r|\s+$", '', cleaned_response)
        json_data = json.loads(cleaned_response, strict=False)

    weekly_schedule = []

    # Перебираем каждый день недели начиная с понедельника (от 1 до 6)
    for day_offset in range(6):
        chetweek = 1 if (nums % 2) != 0 else 2  # 1 - числитель, 2 - знаменатель
        day_schedule = {}

        for pair in json_data['pairs']:
            if (day_offset + 1) == pair['day'] and chetweek == pair['chetnechet']:
                key = (pair['call'], pair['room'], pair['comment'])
                if key not in day_schedule:
                    day_schedule[key] = {
                        "predmet": pair['predmet'],
                        "prepod": [pair['prepod']],
                        "type": pair['type'],
                        "comment": pair['comment']
                    }
                else:
                    if pair['prepod'] not in day_schedule[key]["prepod"]:
                        day_schedule[key]["prepod"].append(pair['prepod'])

        # Формируем расписание на день
        schedule_for_day = ''
        for (time, room, comment), info in day_schedule.items():
            schedule_for_day += (f"🕐{time}🕐\n"
                                 f"📚{info['predmet']}\n"
                                 f"{', '.join(info['prepod'])}, "
                                 f"а.{room}, {info['type']}, "
                                 f"{info['comment']}\n")

        if schedule_for_day:
            weekly_schedule.append(f"📅{DAYS_OF_WEEK[day_offset]}:\n{schedule_for_day}")
        else:
            weekly_schedule.append(f"📅{DAYS_OF_WEEK[day_offset]}:\nВыходной день!")

    return weekly_schedule


def notification(id_group):
    response = requests.get('' + id_group, verify=False)
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text()
    text = text.replace('\n', '\n\n')
    if text:
        return text
    else:
        return "Уведомлений нет😢"


# print(notification('2163'))
# today = datetime.datetime.now()
# tomorrow = today + datetime.timedelta(days=2)


# print(get_table_zaochik_date('-3178', tomorrow))

# print(get_table('2163', tomorrow))

# print(get_week_schedule('', tomorrow))

# group_name = input("Введите название группы для поиска: ")
# group_id = find_group_id_by_name(group_name)
# print(f"ID выбранной группы: {group_id}")

