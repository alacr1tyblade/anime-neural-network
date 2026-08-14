# import telebot
# import sys
# import os

# # Добавляем корневую папку проекта в путь поиска
# sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# # Теперь можно импортировать из utils
# import network.embedder
# from network.search import get_search

# api_token = '8600033266:AAGcUk6JEl6peCZd93ITeA5rDrngcne6VFo'
# bot = telebot.TeleBot(api_token)

# @bot.message_handler(commands=['start'])
# def send_welcome(message):
#     bot.send_message(message.chat.id, 'write anime')

# @bot.message_handler(func=lambda message: True)
# def handle_search(message):
#     query = message.text
#     try:
#         results = get_search(query)
#         if results.empty:
#             bot.send_message(message.chat.id, "Ничего не найдено. Попробуй другой запрос.")
#             return
        
#         response = "🔍 Вот что я нашёл:\n\n"
#         for idx, row in results.iterrows():
#             response += f"📌 {row['title']}\n"
#             response += f"   Жанры: {row['genres']}\n"
#             response += f"   Сходство: {row['score']:.3f}\n\n"
        
#         bot.send_message(message.chat.id, response)
#     except Exception as e:
#         bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")       
    
# bot.infinity_polling()

import telebot

bot = telebot.TeleBot('8600033266:AAGcUk6JEl6peCZd93ITeA5rDrngcne6VFo')

@bot.message_handler(content_types=['text'])
def test(message):
    bot.send_message(message.chat.id, f"Ты написал: {message.text}")

bot.infinity_polling()