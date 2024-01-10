# ZkFair Airdrop Farmer

Софт на набив потраченного газа в ZkFair с многопотоком. Используются свапы на Izumi - самая высокая 
комиссия транзакций.

Настраиваете как нужно в `settings.py` и при запуске софта указываете количество потоков (рекомендуется не больше чем
количество прокси)


### UPD: 3 режима работы:
1. *orbiter bridge* - бриджит из оптимизма в zkfair через orbiter
2. *make swaps* - бесконечно крутит свапы пока баланс USDC не будет меньше чем `LEAVE_BALANCE`
3. <ins>*claim refund + rewards*</ins> - рефандит USDC за который не дали аллоку и клеймить аллокацию ZKF 

---

#### Claim Refund + Rewards
Для этого мода сделал автоматические гвей и газ лимит - клеймить при текущих значениях. Запускать софт можно без 
настройки, все готово к запуску.

---

#### Make Swaps
> Логика работы бесконечных свапов: 
> * если имеется ETH - свапает ETH -> USDC
> * если нету ETH - свапает USDC -> ETH
> 
> Получаются круговые свапы USDC - ETH - USDC - ETH - ...

По итогу можете ежемоментно сжигать газ сразу на нескольких кошельках, что бы точно успеть до закрытия 3kk USDC пула

---

Обычные прокси в `proxies.txt` указывать в формате `http://log:pass@ip:port`. \
Так же можно указывать мобильные прокси в формате 
`http://log:pass@ip:port,https://changeip.mobileproxy.space/?proxy_key=...&format=json`.
> Обычные прокси можно мешать с мобильными, на мобильных будет менять айпи, обычные будет юзать как обычно,
> указывать например так:
> ```
> http://log:pass@ip:port
> http://log:pass@ip:port
> http://log:pass@ip:port,https://changeip.mobileproxy.space/?proxy_key=...&format=json
> http://log:pass@ip:port,https://changeip.mobileproxy.space/?proxy_key=...&format=json
> ```

