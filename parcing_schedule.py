import bs4
import requests
import io
import pandas as pd
import datetime
import re


def get_weekday(date):
    weekday = datetime.datetime.weekday(date)
    str_weekday = ''
    match weekday:
        case 0:
            str_weekday = 'понедельник'
        case 1:
            str_weekday = 'вторник'
        case 2:
            str_weekday = 'среду'
        case 3:
            str_weekday = 'четверг'
        case 4:
            str_weekday = 'пятницу'
        case 5:
            str_weekday = 'субботу'
        case 6:
            str_weekday = 'воскресенье'
    return str_weekday


def get_url(url_print):
    source = requests.get(url_print)  # чтение кода страницы
    soup = bs4.BeautifulSoup(source.content, 'lxml')  # преобразование кода в BeautifulSoup для структуризации кода

    table = soup.select('.rasp_table')  # выбор таблицы с расписанием
    if "https://schedule.nspu.ru/group_shedule" in url_print:
        table = table[1]
    else:
        table = table[0]

    data = pd.read_html(io.StringIO(str(table)))  # преобразование таблицы в dataframe
    data = data[0]
    return data

def where_room(url_print):
    source = requests.get(url_print)  # чтение кода страницы
    ROOMS = ''
    output = ''
    if not "https://schedule.nspu.ru/room_shedule" in url_print:
        soup = bs4.BeautifulSoup(source.content, 'lxml')  # преобразование кода в BeautifulSoup для структуризации кода
    # если что ОТКЛЮЧИТЬ, парсинг кабинетов и корпусов с расписания
        table = soup.select('.rasp_table')  # выбор таблицы с расписанием
        if "https://schedule.nspu.ru/group_shedule" in url_print:
            table = table[1]
        else:
            table = table[0]
        a = soup.find_all('a', table)
        url_room = re.findall(r'<a href="room_shedule(.*?)">', str(a))
        rooms=[]
        url_room = list(set(url_room))
        for i in range(len(url_room)):
            source_room = requests.get('https://schedule.nspu.ru/room_shedule'+url_room[i])
            soup_room = bs4.BeautifulSoup(source_room.text, 'html.parser')
            r = soup_room.find('h2').text.strip()
            rooms.append(str(r))
        cleaned_elements = [element.replace('\r', '') for element in rooms]
        output = '\n\n➡️а. '.join(cleaned_elements)
        if output:
            ROOMS = f'➡️a. ' + output
        else:
            ROOMS = f'Ничего не нашел😔'
    else:
        source = requests.get(url_print)
        soup_room = bs4.BeautifulSoup(source.text, 'html.parser')
        r = soup_room.find('h2').text.strip()
        cleaned_elements = r.replace('\r', '')
        ROOMS = f'❗️Вы и так смотрите расписание аудитории❗️\n\n ➡️a. ' + cleaned_elements
    return ROOMS


# Функция для извлечения всех дат начала из строки предмета
def extract_start_dates(subject):
    dates = re.findall(r'(\d{2}\.\d{2})', subject) # добавить "с" если что перед датой в маске поиска
    return [datetime.datetime.strptime(date+f'.{datetime.date.today().year}', '%d.%m.%Y') for date in dates]


# Функция для фильтрации предметов, которые уже начались
def filter_subjects(schedule_text, current_date):
    lines = schedule_text.strip().split('\n')
    filtered_lines = []

    for line in lines:
        subjects = line.split(';')
        valid_subjects = []

        for subject in subjects:
            # Получаем все даты начала для каждого предмета
            start_dates = extract_start_dates(subject)

            # Если хотя бы одна дата начинается раньше или равна текущей дате, предмет начался
            if any(start_date <= current_date for start_date in start_dates):
                valid_subjects.append(subject)

        # Добавляем отфильтрованный список предметов в общий список строк
        filtered_lines.append('; '.join(valid_subjects))

    return '\n'.join(filtered_lines)


def contains_date(text):
    pattern = r'\b(?!(?:до|по)\s+)\d{2}\.\d{2}\b'
    matches = re.findall(r'\b(?!(?:до|по)\s+)\d{2}\.\d{2}\b', text)
    return matches


def get_table(data, date_print):

    try:
        table = pd.DataFrame()

        date = date_print
        nums = int(datetime.datetime.utcnow().isocalendar()[1])
        weekday = datetime.datetime.weekday(date)
        boolweek = True if (nums % 2) != 0 else False # True - числитель неделя False - знаменатель

        nan_rows = (data[data[0].isna()].index).tolist() #определение пустых строк для разделения на дни недели

        data[2] = data[2].str.replace('&nbsp', '')
        data[3] = data[3].str.replace('&nbsp', '')

        # weekday = 1
        # boolweek = False
        match weekday:
            case 0:
                # print("Понедельник")
                mon = data.loc[nan_rows[0] + 1: nan_rows[1] - 1]
                del mon[0]
                del mon[3 if boolweek == True else 2]
                mon = mon.loc[mon[2 if boolweek == True else 3].str.len().gt(0)]
                table = str(mon.to_csv(sep='\t', index=False, header=False))
            case 1:
                # print("Вторник")
                tue = data.loc[nan_rows[1] + 1: nan_rows[2] - 1]
                del tue[0]
                del tue[3 if boolweek == True else 2]
                tue = tue.loc[tue[2 if boolweek == True else 3].str.len().gt(0)]
                table = str(tue.to_csv(sep='\t', index=False, header = False))
            case 2:
                # print("Среда")
                wed = data.loc[nan_rows[2] + 1: nan_rows[3] - 1]
                del wed[0]
                del wed[3 if boolweek == True else 2]
                wed = wed.loc[wed[2 if boolweek == True else 3].str.len().gt(0)]
                table = str(wed.to_csv(sep='\t', index=False, header = False))
            case 3:
                # print("Четверг")
                thu = data.loc[nan_rows[3] + 1: nan_rows[4] - 1]
                del thu[0]
                del thu[3 if boolweek == True else 2]
                thu = thu.loc[thu[2 if boolweek == True else 3].str.len().gt(0)]
                table = str(thu.to_csv(sep='\t', index=False, header = False))
            case 4:
                # print("Пятница")
                fri = data.loc[nan_rows[4] + 1: nan_rows[5] - 1]
                del fri[0]
                del fri[3 if boolweek == True else 2]
                fri = fri.loc[fri[2 if boolweek == True else 3].str.len().gt(0)]
                table = str(fri.to_csv(sep='\t', index=False, header = False))
            case 5:
                # print("Суббота")
                sat = data.loc[nan_rows[5] + 1: nan_rows[6] - 1]
                del sat[0]
                del sat[3 if boolweek == True else 2]
                sat = sat.loc[sat[2 if boolweek == True else 3].str.len().gt(0)]
                table = str(sat.to_csv(sep='\t', index=False, header = False))
            case 6:
                table = "Выходной день!"

        is_date = False
        lines = table.split('\n')
        for line in lines:
            if line:
                if contains_date(line):
                    is_date = True
                else:
                    is_date = False
                    break

        filtered_schedule = filter_subjects(table, date_print) if is_date else table
        schedule_text = filtered_schedule
        schedule_text = re.sub(r'(\d{2}:\d{2})-(\d{2}:\d{2})', r'\n🕐\1-\2🕐', schedule_text)
        schedule_text = re.sub(r'(8:30)-(\d{2}:\d{2})', r'\n🕐\1-\2🕐', schedule_text)

        schedule_text = re.sub(r'(\d{2}:\d{2}.+?),\s', r'\1,\n👨‍🏫', schedule_text)
        schedule_text = re.sub(r'(;.+?),\s', r'\1,\n👨‍🏫', schedule_text)

        schedule_text = re.sub(r'((8:30)-(\d{2}:\d{2})🕐)\s', r'\1\n📚', schedule_text)
        schedule_text = re.sub(r'((\d{2}:\d{2})-(\d{2}:\d{2})🕐)\s', r'\1\n📚', schedule_text)

        schedule_text = re.sub(r'а\. (\d+)', r'\n🚪а. \1', schedule_text)

        # schedule_text = re.sub(r'(а\. \d+)\s', r'\1,\n📅', schedule_text) #если одиночная дата
        schedule_text = re.sub(r'📅, ', r'📅', schedule_text)
        schedule_text = re.sub(r'с ([\d.]+ г\.)', r'\n📅с \1', schedule_text)

        schedule_text = re.sub(r'; ', r'\n📚', schedule_text)

        if schedule_text == '' or schedule_text is None or schedule_text == '\n' or schedule_text == '\n\n':
            schedule_text = 'Нет занятий'

        return schedule_text
    except Exception as e:
        schedule_text = 'Некорректное расписание❗️ \nТакой тип расписания не поддерживается😔'
        return schedule_text


def get_tableOnWeek(data, weekday):
    try:
        table = pd.DataFrame()
        nums = int(datetime.datetime.utcnow().isocalendar()[1])

        boolweek = True if (nums % 2) != 0 else False # True - числитель неделя False - знаменатель

        nan_rows = (data[data[0].isna()].index).tolist() #определение пустых строк для разделения на дни недели

        data[2] = data[2].str.replace('&nbsp', '')
        data[3] = data[3].str.replace('&nbsp', '')

        # weekday = 1
        # boolweek = False
        match weekday:
            case 0:
                # print("Понедельник")
                mon = data.loc[nan_rows[0] + 1: nan_rows[1] - 1]
                del mon[0]
                del mon[3 if boolweek == True else 2]
                mon = mon.loc[mon[2 if boolweek == True else 3].str.len().gt(0)]
                table = str(mon.to_csv(sep='\t', index=False, header=False))
            case 1:
                # print("Вторник")
                tue = data.loc[nan_rows[1] + 1: nan_rows[2] - 1]
                del tue[0]
                del tue[3 if boolweek == True else 2]
                tue = tue.loc[tue[2 if boolweek == True else 3].str.len().gt(0)]
                table = str(tue.to_csv(sep='\t', index=False, header=False))
            case 2:
                # print("Среда")
                wed = data.loc[nan_rows[2] + 1: nan_rows[3] - 1]
                del wed[0]
                del wed[3 if boolweek == True else 2]
                wed = wed.loc[wed[2 if boolweek == True else 3].str.len().gt(0)]
                table = str(wed.to_csv(sep='\t', index=False, header=False))
            case 3:
                # print("Четверг")
                thu = data.loc[nan_rows[3] + 1: nan_rows[4] - 1]
                del thu[0]
                del thu[3 if boolweek == True else 2]
                thu = thu.loc[thu[2 if boolweek == True else 3].str.len().gt(0)]
                table = str(thu.to_csv(sep='\t', index=False, header=False))
            case 4:
                # print("Пятница")
                fri = data.loc[nan_rows[4] + 1: nan_rows[5] - 1]
                del fri[0]
                del fri[3 if boolweek == True else 2]
                fri = fri.loc[fri[2 if boolweek == True else 3].str.len().gt(0)]
                table = str(fri.to_csv(sep='\t', index=False, header=False))
            case 5:
                # print("Суббота")
                sat = data.loc[nan_rows[5] + 1: nan_rows[6] - 1]
                del sat[0]
                del sat[3 if boolweek == True else 2]
                sat = sat.loc[sat[2 if boolweek == True else 3].str.len().gt(0)]
                table = str(sat.to_csv(sep='\t', index=False, header=False))
            case 6:
                table = "Выходной день!"

        schedule_text = table
        schedule_text = re.sub(r'(\d{2}:\d{2})-(\d{2}:\d{2})', r'🕐\1-\2🕐', schedule_text)
        schedule_text = re.sub(r'(8:30)-(\d{2}:\d{2})', r'🕐\1-\2🕐', schedule_text)

        schedule_text = re.sub(r'((8:30)-(\d{2}:\d{2})🕐)\s', r'\1\n📚', schedule_text)
        schedule_text = re.sub(r'((\d{2}:\d{2})-(\d{2}:\d{2})🕐)\s', r'\1\n📚', schedule_text)
        schedule_text = re.sub(r'; ', r'\n📚', schedule_text)

        if schedule_text == '':
            schedule_text = 'Нет занятий\n'
        return schedule_text

    except Exception as e:
        schedule_text = 'Некорректное расписание❗️ \nТакой тип расписания не поддерживается😔'
        return schedule_text


def notification(url_print):
    source = requests.get(url_print)  # чтение кода страницы
    soup = bs4.BeautifulSoup(source.content, 'lxml')  # преобразование кода в BeautifulSoup для структуризации кода

    table = soup.select('.rasp_table')  # выбор таблицы с расписанием
    if "https://schedule.nspu.ru/group_shedule" in url_print:
        table = table[0]
    else:
        data = "Уведомлении нет!"
        return data

    data = pd.read_html(io.StringIO(str(table)))  # преобразование таблицы в dataframe
    data = data[0]
    del data[0]
    if data.empty == True:
        data = "Уведомлении нет!"
    else:
        data = str(data.to_csv(sep='\t', index=False, header=False))

    data = re.sub( r"!+(?=[^!]*$)", r'!\n', data)
    data = re.sub(r"(!)", r'!\n', data)

    data = re.sub(r"_+(?=[^!]*$)", r'\n', data)

    data = re.sub(r'(с \d{2}\.\d{2}\.\d{4} по \d{2}\.\d{2}\.\d{4})', r'\1\n', data)
    data = re.sub(r'(с \d{2}\.\d{2}\.\d{2} по \d{2}\.\d{2}\.\d{2})', r'\1\n', data)
    data = re.sub(r'(с \d{2}\.\d{2}\.\d{4} г. по \d{2}\.\d{2}\.\d{4} г.)', r'\1\n', data)

    data = re.sub(r'(семестр)', r'\1\n', data)

    data = re.sub(r'(\b\w{3,}\.)', r'\1\n', data)
    return data

def news_parcer(i):
    url_= 'https://nspu.ru/news/'
    source = requests.get(url_)  # чтение кода страницы
    soup = bs4.BeautifulSoup(source.text, 'html.parser')  # преобразование кода в BeautifulSoup для структуризации кода
    news = soup.find_all('div', class_ = 'col-md-4 pt-3 pb-2 pcs-news-main-page-item')
    contain = news[i]('div', class_='row')
    date = contain[1].text.strip()
    title = contain[2].text.strip()
    mainText = contain[3].text.strip()
    url_news = 'https://nspu.ru' + (re.search(r'<a href="(.*?)">', str(contain[2]))).group(1)
    return (f'🗓Дата размещения: {date}\n\n'
              f'📰{title}\n\n'
              f'{mainText}\n\n'
              f'Читать далее: {url_news}')


# today = datetime.datetime.now()
# tomorrow = today + datetime.timedelta(days=-3)
# print(get_table(get_url('https://schedule.nspu.ru/group_shedule.php?id=2592'),tomorrow ))
#
# print(get_tableOnWeek(get_url('https://schedule.nspu.ru/zgroup_shedule.php?id=2063'), 3))

# print(where_room('https://schedule.nspu.ru/group_shedule.php?id=2163'))

# print(get_weekday())
# print(get_tableOnWeek(get_url('https://schedule.nspu.ru/group_shedule.php?id=2482'), 2))
# print(str(get_url('https://schedule.nspu.ru/group_shedule.php?id=2163').to_csv(sep='\t', index=False, header=False))
# )
# print(notification('https://schedule.nspu.ru/zgroup_shedule.php?id=2063'))

# https://schedule.nspu.ru/group_shedule.php?id=1792 не выводит время во вторник второй парой why?

