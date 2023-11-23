# -*- coding: utf8 -*-

import base64
import datetime
import itertools
import json
import os
import re
import time
import requests
import sqlite3

import httpx
import ujson
from yclients import YClientsAPI



from wappi_collab import *
# Создадим индексную базу из разделенных фрагментов текста

system="Очень подробно и детально ответь на вопрос пользователя, опираясь точно на документ с информацией для ответа клиенту. Не придумывай ничего от себя. Не ссылайся на сами отрывки документ с информацией для ответа, клиент о них ничего не должен знать. Ответ дай не более 5 предложений. Не упоминай в ответе дату, имя, услугу на которую можно записаться."


# этот ключ генерируем на странице https://wappi.pro/api-documentation Работа с webhook (уведомлениями) Get - генерируем этот ключ он же равен токену для него
token_id = "f5972db8-1d87-486f-b3f3-608206570c5c"
headers = {"api-key": "f5972db8-1d87-486f-b3f3-608206570c5c"}


def table_exists(conn, table_name):
    cursor = conn.cursor()
    cursor.execute('''SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?''', (table_name,))

    # If count is 1, then table exists
    return cursor.fetchone()[0] == 1


def create_table_inc_messages(conn):
    with conn:
        c = conn.cursor()

        c.execute('''CREATE TABLE IncomingMessages
                     (id INTEGER PRIMARY KEY,
                      phone_number varchar(20) NOT NULL,
                      time_incoming INTEGER NOT NULL,
                      sender_name varchar(100) NOT NULL,
                      question TEXT NOT NULL,
                      answer TEXT NOT NULL,
                      time_answer REAL NOT NULL)''')
        conn.commit()


def create_table_chat_history(conn):
    with conn:
        c = conn.cursor()

        c.execute('''CREATE TABLE ChatHistory (
                      id INT AUTO_INCREMENT,
                      question TEXT,
                      answer TEXT,
                      name TEXT,
                      phone_number INT,
                      date DATETIME,
                      service TEXT,
                      seance_date TEXT,
                      seances TEXT,
                      is_service_extracted BOOL DEFAULT false,
                      is_seances_sended BOOL DEFAULT false,
                      is_seances_extracted BOOL DEFAULT false,
                      PRIMARY KEY (id)
                    );''')
        conn.commit()


def database_insert_inc_mess(phone_number, time_incoming, sender_name, question, answer, time_answer):
    # conn = sqlite3.connect('/content/drive/MyDrive/wappi_neuro.db')  # You can create a new database by changing the name within the quotes
    conn = sqlite3.connect('wappi_neuro.db')  # You can create a new database by changing the name within the quotes
    if table_exists(conn, 'IncomingMessages') is False:
        create_table_inc_messages(conn)
    cursor = conn.cursor()
    sqlite_insert_query = f"""INSERT INTO IncomingMessages
                                  (phone_number, time_incoming, sender_name, question, answer, time_answer) 
                                   VALUES ("{phone_number}","{time_incoming}","{sender_name}","{question}","{answer}","{time_answer}")"""

    count = cursor.execute(sqlite_insert_query)
    conn.commit()
    print("Record inserted successfully into SqliteDb_developers table ", cursor.rowcount)
    cursor.close()


def database_insert_chat_history(question, ans, name_from_topic, phone_number,
                                 date, service_from_topic, seance_date,
                                 seances, is_service_extracted="FALSE",
                                 is_seances_sended="FALSE", is_seances_extracted="FALSE"):
    conn = sqlite3.connect('wappi_neuro.db')  # You can create a new database by changing the name within the quotes
    if table_exists(conn, 'ChatHistory') is False:
        create_table_chat_history(conn)
    cursor = conn.cursor()
    sqlite_insert_query = f"""INSERT INTO ChatHistory
                                      (question, answer, name, phone_number, date, service, seance_date, seances,
                                      is_service_extracted, is_seances_sended, is_seances_extracted)
                                       VALUES ("{question}","{ans}","{name_from_topic}","{phone_number}","{date}",
                                       "{service_from_topic}", "{seance_date}","{seances}","{is_service_extracted}",
                                       "{is_seances_sended}","{is_seances_extracted}")"""

    count = cursor.execute(sqlite_insert_query)
    conn.commit()
    print("Record inserted successfully into ChatHistory table ", cursor.rowcount)
    cursor.close()


def check_chat_history_record(name_from_topic, phone_number):
    conn = sqlite3.connect('wappi_neuro.db')  # You can create a new database by changing the name within the quotes
    if table_exists(conn, 'ChatHistory') is False:
        create_table_chat_history(conn)
    cursor = conn.cursor()
    query = f"""SELECT * FROM ChatHistory WHERE name = "{name_from_topic}" AND phone_number = "{phone_number}" """
    cursor.execute(query)
    record = cursor.fetchone()
    cursor.close()
    if record:
        return True
    else:
        return False


def update_chat_history_service(question, answer, service_from_topic, phone_number, bool_val):
    conn = sqlite3.connect('wappi_neuro.db')
    cursor = conn.cursor()
    update_query = f"""
        UPDATE ChatHistory
        SET question = "{question}",
            answer = "{answer}",
            service = "{service_from_topic}",
            is_service_extracted = "{bool_val}"
        WHERE phone_number = "{phone_number}"
    """

    # Пример значений для обновления

    # Выполнение обновления
    cursor.execute(update_query)
    conn.commit()

    # Закрытие соединения с базой данных
    cursor.close()
    conn.close()


def update_chat_history_seance_date(question, answer, seance_date, phone_number, bool_val):
    conn = sqlite3.connect('wappi_neuro.db')
    cursor = conn.cursor()
    update_query = f"""
            UPDATE ChatHistory
            SET question = "{question}",
                answer = "{answer}",
                seance_date = "{seance_date}",
                is_seances_sended = "{bool_val}"
            WHERE phone_number = "{phone_number}"
        """



    # Выполнение обновления
    cursor.execute(update_query)
    conn.commit()

    # Закрытие соединения с базой данных
    cursor.close()
    conn.close()

def update_chat_history_seance_extracted(question, answer, seance_date, phone_number, bool_val):
    conn = sqlite3.connect('wappi_neuro.db')
    cursor = conn.cursor()
    update_query = f"""
                UPDATE ChatHistory
                SET question = "{question}",
                    answer = "{answer}",
                    seance_date = "{seance_date}",
                    is_seances_extracted = "{bool_val}"
                WHERE phone_number = "{phone_number}"
            """

    # Выполнение обновления
    cursor.execute(update_query)
    conn.commit()

    # Закрытие соединения с базой данных
    cursor.close()
    conn.close()

def get_seances(phone_number):
    conn = sqlite3.connect('wappi_neuro.db')
    cursor = conn.cursor()
    query = f"""SELECT seances FROM ChatHistory WHERE phone_number = "{phone_number}" """
    cursor.execute(query)
    seances = cursor.fetchone()
    cursor.close()
    if seances is None:
        return 'Нет свободных сеансов'
    return seances[0]

def get_serv_date_sean_db(phone_number):
    conn = sqlite3.connect('wappi_neuro.db')
    cursor = conn.cursor()
    query = f"""SELECT service, seance_date, seances FROM ChatHistory WHERE phone_number = "{phone_number}" """
    cursor.execute(query)
    service = ""
    seance_date = ""
    seances = ""
    res = cursor.fetchone()
    if type(res) is tuple:
        service, seance_date, seances = res
    cursor.close()

    return service, seance_date, seances

def delete_record_chat_history(phone_number):
    conn = sqlite3.connect('wappi_neuro.db')
    cursor = conn.cursor()
    update_query = f"""
            DELETE FROM ChatHistory
            WHERE is_seances_extracted = 'TRUE' AND phone_number = {phone_number};
        """

    # Выполнение обновления
    cursor.execute(update_query)
    conn.commit()

    # Закрытие соединения с базой данных
    cursor.close()
    conn.close()

def get_bool_values(phone_number):
    conn = sqlite3.connect('wappi_neuro.db')
    if table_exists(conn, 'ChatHistory') is False:
        create_table_chat_history(conn)
    cursor = conn.cursor()
    #Определяем есть ли у нас определена услуга, отправлены ли сенасы (время) пользователю, и получены ли от пользователя время сеансов - определяем по телефону
    query = f"""SELECT is_service_extracted , is_seances_sended , is_seances_extracted  FROM ChatHistory WHERE phone_number = "{phone_number}" """
    cursor.execute(query)
    is_service_extracted = False
    is_seances_sended = False
    is_seances_extracted = False
    res = cursor.fetchone()
    if type(res) is tuple:
        is_service_extracted, is_seances_sended, is_seances_extracted = res
    cursor.close()

    return is_service_extracted, is_seances_sended, is_seances_extracted

def get_message_info(data, ans, question):
    phone_number = data['from'][:-5]
    time_incoming = data['time']
    sender_name = data['senderName']
    answer = ans.replace('{', '').replace('}', '')
    time_answer = time.time()
    database_insert_inc_mess(phone_number, time_incoming, sender_name, question, answer, time_answer)


def speech_to_text(topic_base64):
    ba_topic = base64.b64decode(topic_base64)
    os.environ["OPENAI_API_KEY"] = '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'

    try:
        file = open('temp.mp3', 'wb')
        file.write(ba_topic)
        file.close()
    except:
        print('Something went wrong!')

    headers = {
        'Authorization': 'Bearer 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',
        # requests won't add a boundary if this header is set when you pass files=
        # 'Content-Type': 'multipart/form-data',
    }

    files = {
        'file': open('temp.mp3', 'rb'),
        'model': (None, 'whisper-1'),
    }

    response = requests.post('https://api.openai.com/v1/audio/transcriptions', headers=headers, files=files)
    if response.status_code != 200:
        return ""
    transcription = json.loads(response.text)['text']
    return transcription


#функция получения свободных сеансов для сотрудника 1
def get_book_staff_seances(token, form_id, company_id, staff_id) -> dict:
    """ Return all available days for specific staff and service"""
    url = "https://n{}.yclients.com/api/v1/book_staff_seances/{}/{}".format(form_id, company_id, staff_id)
    headers = {
        "Accept": "application/vnd.yclients.v2+json",
        'Authorization': "Bearer {}".format(token),
        'Cache-Control': "no-cache"
    }
    querystring = {}
    response = httpx.request("GET", url, headers=headers, params=querystring)
    return ujson.loads(response.text)


#на вход дата - на выходе даты и время сеансов свободных
def get_free_times(date):
    #токен берем в Интеграции -> Аккаунт разработчика -> Настройки акааунта -> Токен партнера
    TOKEN = "2njgd5hw486pafadsfjr"
    # в самом yclient в url - 153828 https://yclients.com/appstore/153828/applications/overview/
    CID = 153828
    #форма id - Онлайн-запись где ссылка https://n146532.yclients.com/ - только само число
    FID = 146532


    api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
    #получаем своборднее время для сотрудника на заданную дату, если их нет - отдаем на ближайшие даты
    time_slots = api.get_available_times(staff_id=396083, day=date)
    if not time_slots['data']:
        time_slots = get_book_staff_seances(TOKEN, FID, CID, 396083)
        seance_date = time_slots['data']['seance_date']
        seances = time_slots['data']['seances']
    else:
        seance_date = date
        seances = time_slots['data']
    list_with_seances = [el['time'] for el in seances]
    seances = '\n'.join(list_with_seances)
    return seance_date, seances

#функция создания записи
def create_book(name, phone_number, service_id, date_time, staff_id):
    TOKEN = "2njgd5hw486pafadsfjr"
    CID = 153828
    FID = 146532

    api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
    booked, message = api.book(booking_id=0,
                               fullname=name,
                               phone=phone_number,
                                service_id = service_id,
                                date_time = date_time,
                                staff_id=staff_id,
                               email=''
                               )
    print(booked, message)

#получение стоимости по названию услуги и id услуги, staff_name - имя сотрудника, staff_id - это id сотрудника, он у нас 396083
def get_cost_serv_id_staff_name_id(service_name):
    if service_name in ['ЛПГ-массаж', 'LPG-массаж']:
        service_name = 'ЛПГ массаж'
    TOKEN = "2njgd5hw486pafadsfjr"
    CID = 153828
    FID = 146532
    api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
    services = api.get_services(staff_id=396083) # id Сотрудника 1
    for service in services['data']['services']:
        if service['title'] == service_name:
            service_id = service['id']
            price = service['price_min']
    all_staff = api.get_staff()
    for staff in all_staff['data']:
        if staff['id'] == 396083:
            staff_name = staff['name']
            staff_id = staff['id']
    return price, service_id, staff_name, staff_id

# проверка - является ли ответ chatgpt в формате json
def is_json(myjson):
    try:
        json.loads(myjson)
    except ValueError as e:
        return False
    return True


def send_message(text, recipient):
    json_body = {
        "body": text,
        "recipient": recipient[:-5]
    }
    url = f'https://wappi.pro/api/sync/message/send?profile_id=e10f170a-f36a'
    # это берем с личного кабинета в wappi
    headers = {
        "Authorization": 'c6605acba50c709da32d7d11606684e98793863b',
        "accept": "application/json"
    }
    send_response = requests.post(url, headers=headers, json=json_body)
    print()

def delete_webhook(token_id, req_id, headers):
    requests.delete(f'https://webhook.site/token/{token_id}/request/{req_id}', headers=headers)

def iterate_over_requests(data):
    for request in data['data']:
        if request['user_agent'] == 'WappiWH':
            content = json.loads(request['content'])
            content_data = content['messages'][0]
            # является ли сообщение файлом - картинка, голос и т.п.
            if content_data['chatId'] != '79262684110-1588248175@g.us':
                topic_text = ''
                chat_id, topic = content_data['chatId'], content_data['body']
                if 'mimetype' in content_data:
                    if content_data['mimetype'] == 'audio/ogg; codecs=opus':
                        send_message('Подождите, аудиосообщение обрабатывается', chat_id)
                        topic_text = speech_to_text(topic)
                        if topic_text == '':
                            send_message('Слова в аудиосообщении не распознаны, отправьте заново', chat_id)
                    else:
                        send_message('Только текстовые или аудио сообщения', chat_id)
                        delete_webhook(token_id, request['uuid'], headers)
                        break
                else:
                    send_message('Подождите, сообщение обрабатывается', chat_id)
                question = topic if topic_text == '' else topic_text

                ans=answer_index(system, question, db_2, temp=0, verbose=0)
                # ans = 'Ответ topic_text == '

                if is_json(ans):
                    gpt_answer = json.loads(ans)
                    ans = gpt_answer['answer']

                    is_service_extracted, is_seances_sended, is_seances_extracted = get_bool_values(
                        content_data['from'][:-5])

                    try:
                        if 'TRUE' in [is_service_extracted, is_seances_sended, is_seances_extracted]:
                            pass
                        else:
                            send_message(ans, chat_id)
                    except Exception as e:
                        print(e)

                    name_from_topic = content_data['senderName']
                    phone_number = content_data['from'][:-5]
                    # if check_chat_history_record(name_from_topic, phone_number):

                    service_from_topic = gpt_answer['service']
                    date = gpt_answer['date']

                    #определние даты и времени
                    # проверка на то, входят ли слова из массива в дату пользователя
                    if any(ele in str(question).lower() for ele in ['сегодня', 'завтра', 'послезавтра']) and date == "": 
                        date = question
                    if any(ele in str(date).lower() for ele in ['сегодня', 'завтра', 'послезавтра']):
                        if 'сегодня' in date.lower():
                            date = datetime.datetime.today().strftime('%Y-%m-%d')
                        elif 'завтра' in date.lower() :
                            date = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                        elif 'послезавтра'  in date.lower():
                            date = (datetime.date.today() + datetime.timedelta(days=2)).strftime('%Y-%m-%d')

                    #если есть ли записи в диалоге - новая попытка записи на услугу
                    if not check_chat_history_record(name_from_topic, phone_number):
                        database_insert_chat_history(question, ans, name_from_topic, phone_number, date, service_from_topic, '', '')

                    #смотрим на каком этапе мы в общении с клиентом - есть ли услуга, выбрал ли дату и время
                    service_db, date_db, seances_db = get_serv_date_sean_db(phone_number)
                    date_hours = ""
                    if date_db != "":
                        time_re = re.compile(r'^(([01]\d|2[0-3]):([0-5]\d)|24:00)$')
                        seance_date, seances = get_free_times(date_db)
                        m = re.search(r'(([01]\d|2[0-3]):([0-5]\d)|24:00)$', question)
                        if m:
                            date_hours = m.group(1)
                            if date_hours in seances:
                                date_hours = date_hours
                            else:
                                send_message("Неверное время, выберите корректное", chat_id)
                                date = date_db
                                date_db = ""

                    if service_from_topic == "" and service_db == "":
                        send_message("Отправьте название процедуры, на которую хотите записаться", chat_id)

                    elif (service_db != "" or service_from_topic != "") and (date_db == "" and date == ""):
                        update_chat_history_service(question, ans, service_from_topic, phone_number, "TRUE")
                        send_message("Отправьте дату, на которую хотите записаться, мы пришлем свободные слоты", chat_id)
                    elif (date_db == "" and date != "") and service_db != "":
                        seance_date = date_db if date_db != "" else date
                        seance_date, seances = get_free_times(seance_date)
                        update_chat_history_seance_date(question, ans, seance_date, phone_number, "TRUE")
                        send_message("Выберите время, на которое хотите записаться и отправьте его сообщением\n" + seances, chat_id)
                    elif (seances_db != "" or date_hours != "") and date_db != "" and service_db != "":
                        seance_date = str(date_db) + " " + str(date_hours) # Переделать, чтобы дата приходила корректной
                        update_chat_history_seance_extracted(question, ans, seance_date, phone_number, "TRUE")
                        converted_date = datetime.datetime.strptime(seance_date, "%Y-%m-%d %H:%M").isoformat() # необходимо привести время записи к формату ISO8601
                        #Определяем стоимость, услугу, сотрудника
                        cost, service_id, staff_name, staff_id = get_cost_serv_id_staff_name_id(service_db)
                        #создаем запись в yclient
                        create_book(name_from_topic, phone_number, service_id, converted_date, staff_id )
                        send_message(f"Вы записались на {seance_date} к {staff_name}. Стоимость {cost}.", chat_id)


                        delete_record_chat_history(phone_number)




                try:
                    get_message_info(content_data, ans, question)
                except Exception as db_e:
                    print(db_e)
                    pass

        delete_webhook(token_id, request['uuid'], headers)


while True:

    try:
        r = requests.get('https://webhook.site/token/' + token_id + '/requests?sorting=newest', headers=headers)
        while r.status_code != 200:
            time.sleep(10)
            r = requests.get('https://webhook.site/token/' + token_id + '/requests?sorting=newest', headers=headers)
        data = r.json()
        if not data['data']:
            time.sleep(1)
        iterate_over_requests(data)

    except Exception as e:
        print(e)
        time.sleep(5)
