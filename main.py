import subprocess

subprocess.run(['python3', './network/save_embeddings.py'])

def get_bot_token():
    bot_token = input('write your bot token here: ')
    return bot_token

if __name__ == '__main__':
    subprocess.run(['python3', './bot/bot.py'])
