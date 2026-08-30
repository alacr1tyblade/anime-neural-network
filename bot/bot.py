import telebot
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import network.embedder
from network.search import search
from main import get_bot_token

api_token = get_bot_token()
bot = telebot.TeleBot(api_token)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, 'write anime')

@bot.message_handler(func=lambda message: True)
def handle_search(message):
    query = message.text
    try:
        results = search(query)
        if results.empty:
            bot.send_message(message.chat.id, 'nothing has found')
            return
        
        response = 'found:\n\n'
        for row in results.iterrows():
            response += f"   {row['title']}\n"
            response += f"   genres: {row['genres']}\n"
        
        bot.send_message(message.chat.id, response)
    except Exception as e:
        bot.send_message(message.chat.id, f"error: {str(e)}")       
    
bot.infinity_polling()