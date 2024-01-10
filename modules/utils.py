from random import randint
from requests import post
from loguru import logger
from time import sleep
import asyncio
import ctypes
import sys
import os
sys.__stdout__ = sys.stdout # error with `import inquirer` without this string in some system
from inquirer import prompt, List

import settings


logger.remove()
logger.add(sys.stderr, format="<white>{time:HH:mm:ss}</white> | <level>{message}</level>")
windll = ctypes.windll if os.name == 'nt' else None # for Mac users


class Proxy:
    def __init__(self, proxy_list: list):
        self.free_proxies = {proxy:True for proxy in proxy_list}
        self.lock = asyncio.Lock()

    async def get_free_proxy(self):
        async with self.lock:
            while True:
                if list(self.free_proxies.values()).count(True) == 0:
                    logger.warning(f'all {len(self.free_proxies)} proxies are busy...')
                    await asyncio.sleep(5)
                else:
                    for proxy in self.free_proxies:
                        if self.free_proxies[proxy]:
                            self.free_proxies[proxy] = False
                            return proxy

    def free_proxy(self, proxy: str):
        self.free_proxies[proxy] = True


class WindowName:
    def __init__(self, accs_amount):

        self.accs_amount = accs_amount
        self.accs_done = 0
        self.modules_amount = 0
        self.modules_done = 0

        self.update_name()

    def update_name(self):
        if os.name == 'nt':
            windll.kernel32.SetConsoleTitleW(f'ZkFair Gas Burner v1.02 [{self.accs_done}/{self.accs_amount}]')

    def update_accs(self):
        self.accs_done += 1
        self.modules_amount = 0
        self.modules_done = 0
        self.update_name()

    def update_modules(self):
        self.modules_done += 1
        self.update_name()

    def set_modules(self, modules_amount: int):
        self.modules_amount = modules_amount
        self.update_name()


class TgReport:
    def __init__(self):
        self.logs = ''


    def update_logs(self, text: str):
        self.logs += f'{text}\n'


    def send_log(self, wallet, window_name):
        notification_text = f'[{window_name.accs_done}/{window_name.accs_amount}] <i>{wallet.address}</i>\n\n' \
                            f'{self.logs}\n'
        if wallet.stats.get('status'): notification_text += f'{wallet.stats["status"]}'

        texts = []
        while len(notification_text) > 0:
            texts.append(notification_text[:1900])
            notification_text = notification_text[1900:]

        if settings.TG_BOT_TOKEN:
            for tg_id in settings.TG_USER_ID:
                for text in texts:
                    try:
                        r = post(f'https://api.telegram.org/bot{settings.TG_BOT_TOKEN}/sendMessage?parse_mode=html&chat_id={tg_id}&text={text}')
                        if r.json().get('ok') != True: raise Exception(f'{r.text}')
                    except Exception as err: logger.error(f'[-] TG | Send Telegram message error to {tg_id}: {err}')


async def sleeping(*timing):
    if type(timing[0]) == list: timing = timing[0]
    if len(timing) == 2: x = randint(timing[0], timing[1])
    else: x = timing[0]
    await asyncio.sleep(x)


def choose_mode():
    questions = [
        List('prefered_path', message="What path do you prefer?",
             choices=[
                'orbiter bridge',
                'make swaps',
                'self transactions',
                'claim refund + rewards',
             ]
        )
    ]
    return prompt(questions)['prefered_path']


def make_text_border(text: str):
    new_text = ''
    max_len = max([len(string) for string in text.split('\n')])

    new_text += '+' + '-' * (max_len + 8) + '+\n'
    for string in text.split('\n'): new_text += f'\t{string}\n'
    new_text += '+' + '-' * (max_len + 8) + '+\n'

    return new_text


def show_settings(p_keys_amount, proxies_amount):
    settings_dict = {
        'КОШЕЛЬКИ': p_keys_amount,
        # 'ПОЛУЧАТЕЛИ': recips_amount,
        'ПРОКСИ': proxies_amount

    }
    max_len = max([len(val) for val in list(settings_dict.keys())]) + 2
    max_value = max(p_keys_amount, proxies_amount)

    print('')
    for setting in settings_dict:
        if settings_dict[setting] < max_value:
            logger.error(f'{setting}{"".join([" " for _ in range(max_len - len(setting))])}| {settings_dict[setting]}')
        else:
            logger.info(f'{setting}{"".join([" " for _ in range(max_len-len(setting))])}| {settings_dict[setting]}')
    print('\n')
    sleep(0.2)
