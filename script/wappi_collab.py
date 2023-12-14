# -*- coding: utf-8 -*-
import time

# импортируем необходимые библиотеки
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain.vectorstores import FAISS
from langchain.document_loaders import TextLoader
import os
import getpass
import re
import requests
import openai
import tiktoken
import matplotlib.pyplot as plt

from db import *


os.environ["OPENAI_API_KEY"] = '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'
openai.api_key = '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'

# функция для загрузки документа по ссылке из гугл драйв
def load_document_text(url: str) -> str:
    # Extract the document ID from the URL
    match_ = re.search('/document/d/([a-zA-Z0-9-_]+)', url)
    if match_ is None:
        raise ValueError('Invalid Google Docs URL')
    doc_id = match_.group(1)

    # Download the document as plain text
    response = requests.get(f'https://docs.google.com/document/d/{doc_id}/export?format=txt')
    response.raise_for_status()
    text = response.text

    return text

# База знаний, которая будет подаваться в langChain
try:
    database= load_document_text('https://docs.google.com/document/d/1JJb2Y2vmWwFzeHv8Ghv3vNxbrR89PBHAynm1QNDQQQk')
except:
    time.sleep(20)
    database = load_document_text('https://docs.google.com/document/d/1JJb2Y2vmWwFzeHv8Ghv3vNxbrR89PBHAynm1QNDQQQk')

def duplicate_headers_without_hashes(text):
    """
    Дублирует заголовки в тексте, убирая из дубликатов хэши.

    Например:
    '# Заголовок' превращается в:
    '# Заголовок
    Заголовок'
    """

    # Вспомогательная функция, которая будет вызываться для каждого найденного совпадения в тексте
    def replacer(match):
        # match.group() вернет найденный заголовок с хэшами.
        # затем мы добавляем к нему перенос строки и ту же строку, но без хэшей
        return match.group() + "\n" + match.group().replace("#", "").strip()

    # re.sub ищет в тексте все заголовки, начинающиеся с 1 до 3 хэшей, и заменяет их
    # с помощью функции replacer
    result = re.sub(r'#{1,3} .+', replacer, text)

    return result

database=duplicate_headers_without_hashes(database)
# при необходимости предобработанную БЗ можно сохранить:
with open('Postoplan.txt', 'w', encoding='utf8') as f:
    f.write(database)



def split_text(text):
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    fragments = markdown_splitter.split_text(text)

    return fragments
source_chunks=split_text(database)

# Инициализирум модель эмбеддингов
embeddings = OpenAIEmbeddings()

# Создадим индексную базу из разделенных фрагментов текста
db = FAISS.from_documents(source_chunks, embeddings)
system="Очень подробно и детально ответь на вопрос пользователя, опираясь точно на документ с информацией для ответа клиенту. Не придумывай ничего от себя. Ответ дай не более 5 предложений. Не упоминай в ответе дату, имя, услугу на которую можно записаться. Если точно не можешь найти информацию в документе, то предоставь наиболее близкую. Не обращай внимание на информацию о том, что что то не нашлось, ищи вне зависимости от результатов предыдущего диалога."
def insert_newlines(text: str, max_len: int = 170) -> str:
    """
    Функция разбивает длинный текст на строки определенной максимальной длины.
    """
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line + " " + word) > max_len:
            lines.append(current_line)
            current_line = ""
        current_line += " " + word
    lines.append(current_line)
    return "\n".join(lines)

def answer_index(system, topic, user_question, search_index, temp=0, verbose=0) -> str:
    """
    Функция возвращает ответ модели на основе заданной темы.
    """
    # находим наиболее релевантные вопросу пользователя чанки:
    docs = search_index.similarity_search(user_question, k=4)

    message_content = re.sub(r'\n{2}', ' ', '\n '.join([f'\nОтрывок документа №{i+1}\n=====================' + doc.page_content + '\n' for i, doc in enumerate(docs)]))

    # если параметр verbose=1, то выводим релевантные чанки
    if verbose:
        print('message_content :\n', message_content)

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Документ с информацией для ответа пользователю: {message_content}\n\nВопрос пользователя: \n{topic}"}
    ]

    completion = openai.ChatCompletion.create(
        model="gpt-4-0613",
        messages=messages,
        temperature=temp
    )

    return insert_newlines(completion.choices[0].message.content)

def summarize_questions(dialog):
    """
    Функция возвращает саммаризированный текст диалога.
    """
    messages = [
        {"role": "system", "content": "Ты - нейро-саммаризатор. Твоя задача - саммаризировать диалог, который тебе пришел. Если пользователь назвал свое имя, обязательно отрази его в саммаризированном диалоге"},
        {"role": "user", "content": "Саммаризируй следующий диалог консультанта и пользователя: " + " ".join(dialog)}
    ]

    completion = openai.ChatCompletion.create(
        model="gpt-4-0613",     # используем gpt4 для более точной саммаризации
        messages=messages,
        temperature=0,          # Используем более низкую температуру для более определенной суммаризации
    )

    return completion.choices[0].message.content

def answer_user_question_dialog(system, db, user_question, question_history, phone_number):
    """
    Функция возвращает ответ на вопрос пользователя.
    """
    summarized_history = ""
    # Если в истории более одного вопроса, применяем суммаризацию
    if len(question_history) > 0:
        summarized_history = "Вот краткий обзор предыдущего диалога: " + summarize_questions([q + ' ' + (a if a else '') for q, a in question_history])

    # Добавляем явное разделение между историей диалога и текущим вопросом
    input_text = summarized_history + "\n\nТекущий вопрос: " + user_question

    # Извлекаем наиболее похожие отрезки текста из базы знаний и получение ответа модели
    answer_text = answer_index(system, input_text, user_question, db)

    # Добавляем вопрос пользователя и ответ системы в историю
    question_history.append((user_question, answer_text if answer_text else ''))
    insert_dialog_history(phone_number, user_question, answer_text)

    # Выводим саммаризированный текст, который видит модель
    if summarized_history:
        print('****************************')
        print(insert_newlines(summarized_history))
        print('****************************')

    return insert_newlines(answer_text)

# def run_dialog(system_doc_url, knowledge_base_url):
#     """
#     Функция запускает диалог между пользователем и нейро-консультантом.
#     """
#     #список кортежей, где каждый кортеж содержит пару вопрос-ответ, для отслеживания истории вопросов и ответов во время сессии диалога.
#     question_history = []
#     while True:
#         user_question = input('Пользователь: ')
#         if user_question.lower() == 'stop':
#             break
#         answer = answer_user_question_dialog(system_doc_url, knowledge_base_url, user_question, question_history)
#         print('Консультант:', answer)
#
#     return


def run_dialog(system_doc_url, knowledge_base_url, user_question, phone_number):
    """
    Функция запускает диалог между пользователем и нейро-консультантом.
    """
    #список кортежей, где каждый кортеж содержит пару вопрос-ответ, для отслеживания истории вопросов и ответов во время сессии диалога.
    user_dialogs = get_user_dialogs(phone_number)
    if user_dialogs:
        pass
    else:
        user_dialogs = []

    answer = answer_user_question_dialog(system_doc_url, knowledge_base_url, user_question, user_dialogs, phone_number)
    return answer



