# -*- coding: utf-8 -*-
import sqlite3


# Функции для взаимодействия с БД файлом wappi.py
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
                      action INT,
                      question TEXT,
                      answer TEXT,
                      name TEXT,
                      phone_number INT,
                      date DATETIME,
                      service TEXT,
                      specialists TEXT,
                      selected_date DATETIME,
                      seances TEXT,
                      seance_date TEXT,
                      is_services_sent BOOL DEFAULT false,
                      is_service_extracted BOOL DEFAULT false,
                      is_specialists_sent BOOL DEFAULT false,
                      is_specialists_extracted BOOL DEFAULT false,
                      is_dates_sent BOOL DEFAULT false,
                      is_dates_extracted BOOL DEFAULT false,
                      is_seances_sent BOOL DEFAULT false,
                      is_seances_extracted BOOL DEFAULT false,
                      PRIMARY KEY (id)
                    );''')
        conn.commit()


def insert_incoming_message(phone_number, time_incoming, sender_name, question, answer, time_answer):
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
    print("Record inserted successfully into IncomingMessages table ", cursor.rowcount)
    cursor.close()


def insert_chat_history(action, question, ans, name_from_topic, phone_number,
                        date, service_from_topic, specialists, selected_date,
                        seances, seance_date):
    conn = sqlite3.connect('wappi_neuro.db')  # You can create a new database by changing the name within the quotes
    if table_exists(conn, 'ChatHistory') is False:
        create_table_chat_history(conn)
    cursor = conn.cursor()
    sqlite_insert_query = f"""INSERT INTO ChatHistory
                                      (action, question, answer, name, phone_number, date, service, specialists, selected_date,
                                       seances, seance_date)
                                       VALUES ("{action}","{question}","{ans}","{name_from_topic}","{phone_number}","{date}",
                                       "{service_from_topic}", "{specialists}", "{selected_date}","{seances}", 
                                       "{seance_date}")"""

    count = cursor.execute(sqlite_insert_query)
    conn.commit()
    print("Record inserted successfully into ChatHistory table ", cursor.rowcount)
    cursor.close()


def is_user_chat_exist(name, phone_number):
    conn = sqlite3.connect('wappi_neuro.db')  # You can create a new database by changing the name within the quotes
    if table_exists(conn, 'ChatHistory') is False:
        create_table_chat_history(conn)
    cursor = conn.cursor()
    query = f"""SELECT * FROM ChatHistory WHERE name = "{name}" AND phone_number = "{phone_number}" """
    cursor.execute(query)
    record = cursor.fetchone()
    cursor.close()
    if record:
        return True
    else:
        return False


def get_values_by_columns(columns, phone_number):
    conn = sqlite3.connect('wappi_neuro.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Формируем строку с названиями столбцов для запроса
    column_names = ','.join(columns)

    # Строим запрос и выполняем его
    query = f"SELECT {column_names} FROM ChatHistory WHERE {phone_number}"
    cursor.execute(query)

    # Получаем и возвращаем результат запроса
    result = cursor.fetchall()
    # Закрываем соединение
    conn.close()
    return [dict(row) for row in result]


def update_table(columns, values, condition):
    conn = sqlite3.connect('wappi_neuro.db')
    cursor = conn.cursor()
    if len(columns) != len(values):
        print("Количество столбцов и значений должно быть одинаковым")
        return

    set_string = ", ".join([f"{column} = ?" for column in columns])
    sql = f"UPDATE ChatHistory SET {set_string} WHERE {condition}"

    cursor.execute(sql, values)
    conn.commit()


def get_bool_values(phone_number):
    conn = sqlite3.connect('wappi_neuro.db')
    if table_exists(conn, 'ChatHistory') is False:
        create_table_chat_history(conn)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = f"""SELECT 
    is_services_sent , is_service_extracted , 
    is_specialists_sent, is_specialists_extracted, 
    is_dates_sent, is_dates_extracted, 
    is_seances_sent, is_seances_extracted  
    FROM ChatHistory 
    WHERE phone_number = "{phone_number}" """
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in result]


# Конец функций для взаимодействия с БД файлом wappi.py

# Функций для взаимодействия с БД файлом wappi_collab.py

def create_table_dialog_history(conn):
    with conn:
        c = conn.cursor()

        c.execute('''CREATE TABLE DialogHistory
                     (id INTEGER PRIMARY KEY,
                      phone_number  varchar(20) NOT NULL,
                      message TEXT NOT NULL,
                      answer TEXT NOT NULL
                      )''')
        conn.commit()

def count_dialogs_by_phone_number(conn, phone_number):
    # Устанавливаем соединение с базой данных
    cursor = conn.cursor()

    # Выполняем запрос для подсчета количества записей по полю phone_number
    cursor.execute('SELECT COUNT(*) FROM DialogHistory WHERE phone_number = ?', (phone_number,))
    count = cursor.fetchone()[0]

    # Закрываем соединение
    cursor.close()
    conn.close()

    return count

def delete_record_if_more_than_10(conn, phone_number):
    # Подключаемся к базе данных
    cursor = conn.cursor()

    # Получаем количество записей с указанным номером телефона
    query = "SELECT COUNT(*) FROM DialogHistory WHERE phone_number = ?"
    cursor.execute(query, (phone_number,))
    count = cursor.fetchone()[0]

    # Удаляем первую запись, если количество превышает 10
    if count > 10:
        query = """
    DELETE FROM DialogHistory WHERE id IN (
  SELECT id FROM DialogHistory WHERE phone_number=? LIMIT 1)"""
        cursor.execute(query, (phone_number,))
        conn.commit()

    # Закрываем соединение
    cursor.close()



def insert_dialog_history(phone_number, message, answer):
    # conn = sqlite3.connect('/content/drive/MyDrive/wappi_neuro.db')  # You can create a new database by changing the name within the quotes
    conn = sqlite3.connect('wappi_neuro.db')  # You can create a new database by changing the name within the quotes
    if table_exists(conn, 'DialogHistory') is False:
        create_table_dialog_history(conn)
    delete_record_if_more_than_10(conn, phone_number)

    cursor = conn.cursor()
    sqlite_insert_query = f"""INSERT INTO DialogHistory
                                  (phone_number, message, answer) 
                                   VALUES ("{phone_number}","{message}","{answer}")"""

    count = cursor.execute(sqlite_insert_query)
    conn.commit()
    print("Record inserted successfully into DialogHistory ", cursor.rowcount)
    cursor.close()

def get_user_dialogs(phone_number):
    conn = sqlite3.connect('wappi_neuro.db')
    cursor = conn.cursor()
    if table_exists(conn, 'DialogHistory') is False:
        create_table_dialog_history(conn)

    # Выполняем SQL-запрос с фильтрацией по полю "phone_number"
    query = "SELECT message, answer FROM DialogHistory WHERE phone_number = ?"
    cursor.execute(query, (phone_number,))

    # Получаем результаты запроса в виде списка кортежей [(message, answer)]
    results = cursor.fetchall()

    # Закрываем соединение с базой данных
    conn.close()

    return results

# Конец функций для взаимодействия с БД файлом wappi_collab.py
