# -*- coding: utf-8 -*-
import datetime
import os


import base64
import json
import httpx
import ujson
from yclients import YClientsAPI

from settings import *
from db import *
from wappi_collab import *

# Создадим индексную базу из разделенных фрагментов текста

system = "Очень подробно и детально ответь на вопрос пользователя, опираясь точно на документ с информацией для ответа клиенту. Не придумывай ничего от себя. Не ссылайся на сами отрывки документ с информацией для ответа, клиент о них ничего не должен знать. Ответ дай не более 5 предложений. Не упоминай в ответе дату, имя, услугу на которую можно записаться."


def get_message_info(data, ans, question):
    phone_number = data['from'][:-5]
    time_incoming = data['time']
    sender_name = data['senderName']
    answer = ans.replace('{', '').replace('}', '')
    time_answer = time.time()
    insert_incoming_message(phone_number, time_incoming, sender_name, question, answer, time_answer)


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


# свободное время сотрудника
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


# свободное время сотрудника
def get_free_times(date, staff_id, serv_id):
    api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
    time_slots = api.get_available_times(staff_id=staff_id, day=date, service_id=serv_id)
    if not time_slots['data']:
        time_slots = get_book_staff_seances(TOKEN, FID, CID, staff_id)
        seance_date = time_slots['data']['seance_date']
        seances = time_slots['data']['seances']
    else:
        seance_date = date
        seances = time_slots['data']
    list_with_seances = [el['time'] for el in seances]
    seances = '\n'.join(list_with_seances)
    return seance_date, seances


# создание записи в yclients
def create_book(name, phone_number, service_id, date_time, staff_id):
    api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
    booked, message = api.book(booking_id=0,
                               fullname=name,
                               phone=phone_number,
                               service_id=service_id,
                               date_time=date_time,
                               staff_id=staff_id,
                               email=''
                               )
    print(booked, message)


# порлучение стоимости
def get_cost(service_name, staff_id):
    api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
    services = api.get_services(staff_id=staff_id)  # id Сотрудника 1
    for service in services['data']['services']:
        if service['title'] in service_name:
            price = service['price_min']
    return price


# id услуги по названию
def get_serv_id_by_name(name):
    api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
    for i in api.get_service_info()['data']:
        if i['title'] in name:
            serv_id = i['id']
    return serv_id


# id сотрудника по имени
def get_staff_id_by_name(name):
    api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
    for i in api.get_staff()['data']:
        if i['name'] in name:
            staff_id = i['id']
    return staff_id


# изьятие выбранной услуги из чата
def extract_service(message, bool_val, phone_number):
    if bool(bool_val['is_services_sent']) is True and bool(bool_val['is_service_extracted']) is False:
        api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
        response = api.get_service_info()
        service_list = [f"{str(i + 1)}. {val['title']}" for i, val in enumerate(response['data'])]
        service_name = ''
        for serv in service_list:

            num, service_name = serv.split('.')

            if message in num:
                update_table(['is_service_extracted', 'service'], ['TRUE', service_name],
                             phone_number)


# изьятие выбранной сотрудника из чата
def extract_specialists(message, bool_val, phone_number):
    if bool(bool_val['is_specialists_sent']) is True and bool(bool_val['is_specialists_extracted']) is False:
        serv_name = get_values_by_columns(['service'], phone_number)[0]['service']
        serv_id = get_serv_id_by_name(serv_name)
        api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
        response = api.get_staff(serv_id)
        staff_list = [f"{str(i + 1)}. {val['name']}" for i, val in enumerate(response['data'])]
        staff_name = ''
        for st in staff_list:
            num, staff_name = st.split('.')
            if message in num:
                update_table(['is_specialists_extracted', 'specialists'], ['TRUE', staff_name],
                             phone_number)
                break


# получение сотрудников по услуге
def get_specialists(phone_number):
    serv_name = get_values_by_columns(['service'], phone_number)[0]['service']

    api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
    serv_id = get_serv_id_by_name(serv_name)

    response = api.get_staff(service_id=serv_id)
    specialists_list = [f"{str(i + 1)}. {val['name']}" for i, val in enumerate(response['data'])]
    return specialists_list


# отправка всех сотрудников по услуге в чат
def send_specialist_list(bool_val, chat_id, phone_number):
    specialist_list_text = "Выберите сотрудника из списка, отправив его номер: \n"
    if bool(bool_val['is_service_extracted']) is True and bool(bool_val['is_specialists_sent']) is False:
        specialist_list = get_specialists(phone_number)
        specialists = '\n'.join(specialist_list)
        send_message(specialist_list_text + specialists, chat_id)
        update_table(['is_specialists_sent'], ['TRUE'], phone_number)


# отправка всех услуг в чат
def send_services(chat_id, phone_number):
    services_text = "Выберите услугу из списка, отправив ее номер: \n"
    api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
    response = api.get_service_info()
    service_list = [f"{str(i + 1)}. {val['title']}" for i, val in enumerate(response['data'])]
    services = '\n'.join(service_list)
    # menu_back = '\nДля возврата в меню напишите слово "Меню"'
    # send_message(services_text + services + menu_back, chat_id)
    send_message(services_text + services, chat_id)
    update_table(['is_services_sent'], ['TRUE'], phone_number)


# даты
def send_free_dates(bool_val, chat_id, phone_number):
    dates_list_text = "Выберите дату, на которую хотите записаться из списка, отправив номер даты: \n"
    if bool(bool_val['is_specialists_extracted']) is True and bool(bool_val['is_dates_sent']) is False:
        serv_name = get_values_by_columns(['service'], phone_number)[0]['service']
        staff_name = get_values_by_columns(['specialists'], phone_number)[0]['specialists']

        serv_id = get_serv_id_by_name(serv_name)
        staff_id = get_staff_id_by_name(staff_name)
        # staff_id = get_staff_id_by_name('Сотрудник 2')

        api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
        response = api.get_available_days(staff_id, serv_id)
        free_dates_list = []
        if len(response['data']['booking_dates']) <= 7:
            free_dates_list.extend(response['data']['booking_dates'])
        else:
            free_dates_list = [i for i in response['data']['booking_dates'][:7]]

        dates_list = [f"{str(i + 1)}. {val}" for i, val in enumerate(free_dates_list)]
        dates = '\n'.join(dates_list)

        send_message(dates_list_text + dates, chat_id)
        update_table(['is_dates_sent'], ['TRUE'], phone_number)


# извленние даты
def extract_dates(message, bool_val, phone_number):
    if bool(bool_val['is_dates_sent']) is True and bool(bool_val['is_dates_extracted']) is False:
        serv_name = get_values_by_columns(['service'], phone_number)[0]['service']
        staff_name = get_values_by_columns(['specialists'], phone_number)[0]['specialists']

        serv_id = get_serv_id_by_name(serv_name)
        staff_id = get_staff_id_by_name(staff_name)

        api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
        response = api.get_available_days(staff_id, serv_id)
        free_dates_list = []
        if len(response['data']['booking_dates']) <= 7:
            free_dates_list.extend(response['data']['booking_dates'])
        else:
            free_dates_list = [i for i in response['data']['booking_dates'][:7]]
        dates_list = [f"{str(i + 1)}. {val}" for i, val in enumerate(free_dates_list)]
        date = ''
        for st in dates_list:
            num, date = st.split('.')
            if message in num:
                update_table(['is_dates_extracted', 'selected_date'], ['TRUE', date],
                             phone_number)


# отправка свободного времени
def send_free_slotes(bool_val, chat_id, phone_number):
    times_list_text = "Выберите слот, на который хотите записаться из списка, отправив номер слота: \n"
    if bool(bool_val['is_dates_extracted']) is True and bool(bool_val['is_seances_sent']) is False:
        serv_name = get_values_by_columns(['service'], phone_number)[0]['service']
        staff_name = get_values_by_columns(['specialists'], phone_number)[0]['specialists']
        date = get_values_by_columns(['selected_date'], phone_number)[0]['selected_date']
        serv_id = get_serv_id_by_name(serv_name)
        staff_id = get_staff_id_by_name(staff_name)
        # staff_id = get_staff_id_by_name('Сотрудник 2')

        api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
        response = api.get_available_times(staff_id, serv_id, date)

        times_list = [f"{str(i + 1)}. {val['time']}" for i, val in enumerate(response['data'])]
        times = '\n'.join(times_list)

        send_message(times_list_text + times, chat_id)
        update_table(['is_seances_sent'], ['TRUE'], phone_number)


# извленеие выбранного слота
def extract_slotes(name, message, bool_val, phone_number, chat_id):
    if bool(bool_val['is_seances_sent']) is True and bool(bool_val['is_seances_extracted']) is False:
        serv_name = get_values_by_columns(['service'], phone_number)[0]['service']
        staff_name = get_values_by_columns(['specialists'], phone_number)[0]['specialists']
        date = get_values_by_columns(['selected_date'], phone_number)[0]['selected_date']
        serv_id = get_serv_id_by_name(serv_name)
        staff_id = get_staff_id_by_name(staff_name)
        # staff_id = get_staff_id_by_name('Сотрудник 2')

        api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
        response = api.get_available_times(staff_id, serv_id, date)

        times_list = [f"{str(i + 1)}. {val['time']}" for i, val in enumerate(response['data'])]
        times = '\n'.join(times_list)
        time = ''
        for st in times_list:
            num, time = st.split('.')
            if message in num:
                update_table(['is_seances_extracted', 'seances'], ['TRUE', time],
                             phone_number)
                break
        cost = get_cost(serv_name, staff_id)
        date = date.replace(' ', '')
        converted_date = datetime.datetime.strptime(date + time, "%Y-%m-%d %H:%M").isoformat()
        create_book(name, phone_number, serv_id, converted_date, staff_id)
        send_message(
            f"Вы записались на {date} {time} к {staff_name}. Стоимость {cost}. Для возврата в меню напишите слово 'Меню'",
            chat_id)
        update_table(['action'], ['0'], phone_number)


def get_all_products():
    api = YClientsAPI(token=TOKEN, company_id=CID, form_id=FID)
    USER_TOKEN = api.get_user_token('bodka@mail.ru', 'Qazqaz123$')
    url = "https://n{}.yclients.com/api/v1/goods/{}/".format(FID, CID)
    headers = {
        "Accept": "application/vnd.yclients.v2+json",
        'Accept-Language': 'ru-RU',
        'Authorization': "Bearer {}, User {}".format(TOKEN, USER_TOKEN),
        'Cache-Control': "no-cache"
    }
    response = httpx.request("GET", url, headers=headers)
    data = ujson.loads(response.text)
    product_list = []
    for i, prod in enumerate(data['data']):
        prod_cost = f"{i + 1}. {prod['value']}, стоимость {prod['actual_cost']}"
        product_list.append(prod_cost)
    return product_list


def send_products(chat_id, phone_number):
    products_list_text = "Выберите товар, который хотите приобрести, отправив номер товара: \n"
    product_list = get_all_products()
    products = '\n'.join(product_list)
    send_message(products_list_text + products, chat_id)


def extract_product(message):
    product_list = get_all_products()
    for st in product_list:
        num, product = st.split('.')
        if message in num:
            create_book(name="Товары", phone_number='71234567890', service_id=14198613,
                        date_time=datetime.datetime.today().isoformat(), staff_id=2865000)
            break


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


users_dialogs = {}


# главная функция по запросу что введено
def iterate_over_requests(data):
    for request in data['data']:
        if request['user_agent'] == 'WappiWH':
            content = json.loads(request['content'])
            content_data = content['messages'][0]
            # является ли сообщение файлом - картинка, голос и т.п.
            if content_data['chatId'] != '79262684110-1588248175@g.us':
                topic_text = ''
                chat_id, topic = content_data['chatId'], content_data['body']
                name = content_data['senderName']
                phone_number = content_data['from'][:-5]
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
                    pass
                    # send_message('Подождите, сообщение обрабатывается', chat_id)

                message = topic if topic_text == '' else topic_text

                if not is_user_chat_exist(name, phone_number):
                    send_message('Здравствуйте! Выберите действие: \n '
                                 '1. Записаться на прием \n '
                                 '2. Изменить запись на прием \n '
                                 '3. Узнать информацию о франшизе \n '
                                 '4. Узнать информацию о продуктах \n '
                                 '5. Узнать цены на косметику \n '
                                 'Для выбора отправьте число от 1 до 5.', chat_id)
                    insert_chat_history(0, message, 'action_choice', name, phone_number,
                                        datetime.datetime.today(), 'test', 'test', 'test', 'test', 'test')
                else:
                    action = get_values_by_columns(['action'], phone_number)[0]['action']
                    print(action)
                    if message.lower() == 'меню' and action in [0, 3, 4, 5]:
                        action = 0
                        send_message('Выберите действие: \n '
                                     '1. Записаться на прием \n '
                                     '2. Изменить запись на прием \n '
                                     '3. Узнать информацию о франшизе \n '
                                     '4. Узнать информацию о продуктах \n '
                                     '5. Узнать цены на косметику \n '
                                     'Для выбора отправьте число от 1 до 5.', chat_id)

                        update_table(['action'],
                                     [action],
                                     phone_number)
                        # update_table(['is_services_sent', 'is_service_extracted', 'is_specialists_sent',
                        #               'is_specialists_extracted', 'is_dates_sent', 'is_dates_extracted',
                        #               'is_seances_sent', 'is_seances_extracted'],
                        #              ['FALSE', 'FALSE', 'FALSE', 'FALSE', 'FALSE', 'FALSE', 'FALSE', 'FALSE'],
                        #              phone_number)
                        delete_webhook(token_id, request['uuid'], headers)
                        break
                    if action not in [0, 3, 4]:
                        try:
                            int(message)
                        except Exception as e:
                            send_message('Повторите выбор, число не распознано', chat_id)
                            delete_webhook(token_id, request['uuid'], headers)
                            break

                    if action == 0:
                        if message == '1':
                            bool_val = get_bool_values(phone_number)[0]
                            if all(bool(value) == True for value in bool_val.values()):
                                send_message('У вас уже имеется запись', chat_id)
                                delete_webhook(token_id, request['uuid'], headers)
                                break
                            update_table(['action'], [message], phone_number)
                            # send_message('Запись', chat_id)
                            send_services(chat_id, phone_number)
                        elif message == '2':
                            update_table(['action'], [message], phone_number)
                            send_message('Изменение записи', chat_id)
                            # edit_book()
                        elif message == '3' or message == '4':
                            send_message('Задайте вопрос в произвольной форме. ', chat_id)
                            update_table(['action'], [message], phone_number)
                        elif message == '5':
                            update_table(['action'], [message], phone_number)
                            send_products(chat_id, phone_number)

                        else:
                            send_message('Повторите выбор, число не распознано', chat_id)
                    elif action == 1:

                        # идем снизу вверх, т.е. есть ли у нас значения начиная от изъятых слотов заканчивая сотрудниками
                        bool_val = get_bool_values(phone_number)[0]

                        # есть ли уже запись
                        if all(bool(value) == True for value in bool_val.values()):
                            send_message('У вас уже имеется запись', chat_id)
                            delete_webhook(token_id, request['uuid'], headers)
                            break
                        # изымаем значения услуг
                        extract_service(message, bool_val, phone_number)
                        bool_val = get_bool_values(phone_number)[0]
                        if bool(bool_val['is_seances_sent']) is True:
                            extract_slotes(name, message, bool_val, phone_number, chat_id)
                        if bool(bool_val['is_dates_sent']) is True:
                            extract_dates(message, bool_val, phone_number)
                            bool_val = get_bool_values(phone_number)[0]
                            if bool(bool_val['is_dates_extracted']) is True:
                                send_free_slotes(bool_val, chat_id, phone_number)
                        if bool(bool_val['is_specialists_sent']) is True:
                            extract_specialists(message, bool_val, phone_number)
                            bool_val = get_bool_values(phone_number)[0]
                            if bool(bool_val['is_specialists_extracted']) is True:
                                send_free_dates(bool_val, chat_id, phone_number)
                        if bool(bool_val['is_service_extracted']) is True:
                            send_specialist_list(bool_val, chat_id, phone_number)
                    elif action in [3, 4]:

                        ans = run_dialog(system, db, message, phone_number)
                        send_message(ans + '\n\n Для возврата в меню напишите слово "меню"', chat_id)
                        try:
                            get_message_info(content_data, ans, message)
                        except Exception as db_e:
                            print(db_e)
                            pass
                        act = ['action']
                        vals = ['3']
                        update_table(act, vals, phone_number)
                    elif action == 5:
                        update_table(['action'], ['0'], phone_number)
                        extract_product(message)

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
        if data['data']:
            iterate_over_requests(data)

    except Exception as e:
        print(e)
        time.sleep(5)
