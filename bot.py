import telebot

from semantic import get_titles


def start_bot(api_token):
    bot = telebot.TeleBot(api_token)

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        bot.send_message(message.chat.id, 'write anime')

    @bot.message_handler(func=lambda message: True)
    def handle_search(message):
        query = message.text
        try:
            results = get_titles(query)
            if results.empty:
                bot.send_message(message.chat.id, 'nothing has found')
                return

            response = 'found:\n\n'
            for _, row in results.iterrows():
                title = row['title_english']
                if not isinstance(title, str) or not title.strip():
                    title = row['title_romaji']
                response += f"   {title}\n"
                response += f"   genres: {row['genres']}\n"

            bot.send_message(message.chat.id, response)
        except Exception as e:
            bot.send_message(message.chat.id, f"error: {str(e)}")

    bot.infinity_polling()
