from random import shuffle
import asyncio
import os

from modules.utils import WindowName, TgReport, Proxy, sleeping, logger, sleep, choose_mode, show_settings
from modules.wallet import Wallet
from modules.browser import Browser
from modules import *
import settings


async def make_swaps(acc_data: dict, proxy_manager: Proxy):
    async with sem:
        try:
            await sleeping(settings.SLEEP_BEFORE_START[0], settings.SLEEP_BEFORE_START[1]) # задержка перед стартом аккаунта
            proxy = await proxy_manager.get_free_proxy()

            browser = Browser()
            await browser.create_session(proxy=proxy)
            tg_report = TgReport()
            windowname.update_accs()
            wallet = Wallet(privatekey=acc_data['privatekey'], recipient=acc_data['recipient'], tg_report=tg_report, browser=browser, proxy=browser.proxies)

            await wallet.wait_for_gwei()

            # actions
            izumi = Izumi(wallet=wallet)
            while True:
                try:
                    result = await izumi.swap()
                    if type(result) == str:
                        wallet.stats['status'] = result
                        break

                    await sleeping(settings.SLEEP_RANGE[0], settings.SLEEP_RANGE[1])

                except Exception as err:
                    wallet.stats['status'] = str(err)
                    break

            return True

        except Exception as err:
            try:
                wallet.stats['status'] = '❌ ' + str(err)
                logger.error(f'[-] {wallet.address} account error: {err}')
            except: logger.error(f'wallet in not defined. error: {err}')

        finally:
            await browser.session.close()
            proxy_manager.free_proxy(proxy=proxy)
            if not wallet.stats.get('status'): wallet.stats['status'] = '❌ no logs'

            tg_report.send_log(wallet=wallet, window_name=windowname)
            excel.edit_table(wallet=wallet)



async def bridge_to_zkfair(acc_data: dict, proxy_manager: Proxy):
    async with sem:
        try:
            await sleeping(settings.SLEEP_BEFORE_START[0], settings.SLEEP_BEFORE_START[1]) # задержка перед стартом аккаунта
            proxy = await proxy_manager.get_free_proxy()

            browser = Browser()
            tg_report = TgReport()
            windowname.update_accs()
            wallet = Wallet(privatekey=acc_data['privatekey'], recipient=acc_data['recipient'], tg_report=tg_report, browser=browser, proxy=browser.proxies)

            await wallet.wait_for_gwei()

            # actions
            orbiter = Orbiter(wallet=wallet)
            if await orbiter.bridge() == True:
                wallet.stats['status'] = '✅ Bridged'
                return True

        except Exception as err:
            try:
                wallet.stats['status'] = '❌ ' + str(err)
                logger.error(f'[-] {wallet.address} account error: {err}')
            except: logger.error(f'wallet in not defined. error: {err}')

        finally:
            # await browser.session.close()
            proxy_manager.free_proxy(proxy=proxy)
            if not wallet.stats.get('status'): wallet.stats['status'] = '❌ no logs'

            tg_report.send_log(wallet=wallet, window_name=windowname)
            excel.edit_table(wallet=wallet)


async def self_txs(acc_data: dict, proxy_manager: Proxy):
    async with sem:
        try:
            await sleeping(settings.SLEEP_BEFORE_START[0], settings.SLEEP_BEFORE_START[1]) # задержка перед стартом аккаунта
            proxy = await proxy_manager.get_free_proxy()

            browser = Browser()
            await browser.create_session(proxy=proxy)
            tg_report = TgReport()
            windowname.update_accs()
            wallet = Wallet(privatekey=acc_data['privatekey'], recipient=acc_data['recipient'], tg_report=tg_report, browser=browser, proxy=browser.proxies)

            await wallet.wait_for_gwei()

            # actions
            self_txs = SelfTX(wallet=wallet)
            while True:
                try:
                    result = await self_txs.send_tx()
                    if type(result) == str:
                        wallet.stats['status'] = result
                        break

                    await sleeping(settings.SLEEP_RANGE[0], settings.SLEEP_RANGE[1])

                except Exception as err:
                    wallet.stats['status'] = str(err)
                    break

            return True

        except Exception as err:
            try:
                wallet.stats['status'] = '❌ ' + str(err)
                logger.error(f'[-] {wallet.address} account error: {err}')
            except: logger.error(f'wallet in not defined. error: {err}')

        finally:
            await browser.session.close()
            proxy_manager.free_proxy(proxy=proxy)
            if not wallet.stats.get('status'): wallet.stats['status'] = '❌ no logs'

            tg_report.send_log(wallet=wallet, window_name=windowname)
            excel.edit_table(wallet=wallet)


async def claim(acc_data: dict, proxy_manager: Proxy):
    async with sem:
        try:
            await sleeping(settings.SLEEP_BEFORE_START[0], settings.SLEEP_BEFORE_START[1]) # задержка перед стартом аккаунта
            proxy = await proxy_manager.get_free_proxy()

            browser = Browser()
            await browser.create_session(proxy=proxy)
            tg_report = TgReport()
            windowname.update_accs()
            wallet = Wallet(privatekey=acc_data['privatekey'], recipient=acc_data['recipient'], tg_report=tg_report, browser=browser, proxy=browser.proxies)

            rewards = await browser.get_zkfair_rewards(wallet=wallet)
            if rewards["phases_data"] == None and rewards["airdrop_data"] == None:
                logger.info(f"{wallet.address} | No Airdrop and No Refunds")
                wallet.stats['status'] = 'No Airdrop and No Refunds'
                return True

            await wallet.wait_for_gwei()
            zk_fair = ZkFair(wallet=wallet)

            # actions
            if rewards["phases_data"]: # CLAIM REFUNDED USDC
                for phase in rewards["phases_data"]:
                    value_to_refund = int(rewards["phases_data"][phase]["account_refund"])
                    contract_to_refund = rewards["phases_data"][phase]["refund_contract_address"]
                    refund_index = rewards["phases_data"][phase]["refund_index"]

                    phase_num = int(phase[-1:])
                    amount_to_refund = round(value_to_refund / 1e18, 2)
                    logger.info(f'{wallet.address} | Refunding {amount_to_refund} USDC from Phase {phase_num}')

                    refund_merkle = await browser.get_refund_merkle(wallet=wallet, phase_num=phase_num)
                    status = await zk_fair.get_refund(contract_address=contract_to_refund, refund_value=value_to_refund, refund_index=refund_index, refund_merkle=refund_merkle)

            if rewards["airdrop_data"]:
                value_to_claim = int(rewards["airdrop_data"]["account_profit"])
                contract_to_claim = rewards["airdrop_data"]["contract_address"]
                claim_index = rewards["airdrop_data"]["index"]

                amount_to_claim = round(value_to_claim / 1e18, 2)
                logger.info(f'{wallet.address} | Claiming {amount_to_claim} ZKF')

                refund_merkle = await browser.get_airdrop_merkle(wallet=wallet)
                status = await zk_fair.get_airdrop(contract_address=contract_to_claim, claim_value=value_to_claim, claim_index=claim_index, airdrop_merkle=refund_merkle)
            wallet.stats['status'] = f'✅ success'

            return True

        except Exception as err:
            try:
                wallet.stats['status'] = '❌ ' + str(err)
                logger.error(f'[-] {wallet.address} account error: {err}')
            except: logger.error(f'wallet in not defined. error: {err}')

        finally:
            await browser.session.close()
            proxy_manager.free_proxy(proxy=proxy)
            if not wallet.stats.get('status'): wallet.stats['status'] = '❌ no logs'

            tg_report.send_log(wallet=wallet, window_name=windowname)
            excel.edit_table(wallet=wallet)




async def runner(accs_data: list, proxy_manager: Proxy, mode: str):
    funcs = {
        'orbiter bridge': bridge_to_zkfair,
        'make swaps': make_swaps,
        'self transactions': self_txs,
        'claim refund + rewards': claim,
    }

    results = await asyncio.gather(*[funcs[mode](acc_data, proxy_manager) for acc_data in accs_data])
    print('')
    logger.info(f'Successfully done {results.count(True)}/{len(results)} accounts')


if __name__ == '__main__':
    if not os.path.isdir('results'): os.mkdir('results')
    with open('privatekeys.txt') as f: p_keys = f.read().splitlines()
    # with open('recipients.txt') as f: recipients = f.read().splitlines()
    with open('proxies.txt') as f: proxies = f.read().splitlines()

    show_settings(len(p_keys), len(proxies))

    MODE = choose_mode()
    sem = asyncio.Semaphore(int(input(f'Threads number: ')))

    excel = Excel(len(p_keys))
    # accs_data = [{'privatekey': pk, 'recipient': recipient, 'index': index + 1} for index, (pk, recipient) in enumerate(list(zip(p_keys, recipients)))]
    accs_data = [{'privatekey': pk, 'recipient': None, 'index': index+1} for index, (pk) in enumerate(p_keys)]

    windowname = WindowName(len(p_keys))
    proxy_manager = Proxy(proxies)
    if settings.SHUFFLE_WALLETS: shuffle(accs_data)

    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(runner(accs_data=accs_data, proxy_manager=proxy_manager, mode=MODE))

    except Exception as err:
        logger.error(f'Global error: {err}')

    sleep(0.1)
    input(' > Exit')
