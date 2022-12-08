import requests
from datetime import datetime
from credenciais import token, chat_id

class TelegramBot:
    def __init__(self):
        self.url = f"https://api.telegram.org/bot{token}/getUpdates"     


    def envia_mensagem(self, mensagem):
        url = f'https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={mensagem}'
        requests.get(url)

if __name__ == '__main__':
    telegram_bot = TelegramBot()
    telegram_bot.envia_mensagem( datetime.now() )
