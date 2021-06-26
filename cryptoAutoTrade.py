
import pyupbit
import datetime
import time, calendar
import numpy as np
import requests

myToken = "xoxb-2213257365844-2194586687239-1jltbYSDJCUOpSaMSkeYTmYW"
access = "gEq6BEhaQioReV9HtgJ1Gx8nGN8CGL3Xp76Yd879"          # 본인 값으로 변경
secret = "T1Bp2HOMzA7nl9KFsHeSxjeTg21TNzjsuaxjpwL7"          # 본인 값으로 변경

def dbgout(message):
    # """인자로 받은 문자열을 파이썬 셸과 슬랙으로 동시에 출력한다."""
    print(datetime.datetime.now().strftime('[%m/%d %H:%M:%S]'), message)
    strbuf = datetime.datetime.now().strftime('[%m/%d %H:%M:%S] ') + message
    post_message(myToken,"#투자",strbuf)

def post_message(token, channel, text):
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )
    print(response)


def get_targetPrice(df, K) :
    print('best_k :' + str(K))
    range = df['high'][-2] - df['low'][-2]
    return df['open'][-1] + range * K

def buy_all(coin) :
    balance = upbit.get_balance("KRW") * 0.9995
    if balance >= 5000 :
        print(upbit.buy_market_order(coin, balance))
        dbgout("매수 체결.\n체결 단가 : "+str(pyupbit.get_current_price(coin))+" 원")

def sell_all(coin) :
    balance = upbit.get_balance(coin)
    price = pyupbit.get_current_price(coin)
    if price * balance >= 5000 :
        print(upbit.sell_market_order(coin, balance))
        dbgout("매도 체결.\n체결 단가 : "+str(pyupbit.get_current_price(coin))+" 원")

def get_crr(df, fees, K) :
    df['range'] = df['high'].shift(1) - df['low'].shift(1)
    df['targetPrice'] = df['open'] + df['range'] * K
    df['drr'] = np.where(df['high'] > df['targetPrice'], (df['close'] / (1 + fees)) / (df['targetPrice'] * (1 + fees)) , 1)
    return df['drr'].cumprod()[-2]

def get_best_K(coin, fees) :
    df = pyupbit.get_ohlcv(coin, interval = "day", count = 21)
    max_crr = 0
    best_K = 0.5
    for k in np.arange(0.0, 1.0, 0.1) :
        crr = get_crr(df, fees, k)
        if crr > max_crr :
            max_crr = crr
            best_K = k
            
    return best_K

if __name__ == '__main__': 
    try:
        upbit = pyupbit.Upbit(access, secret)

        # set variables
        coin = "KRW-BTC"
        fees = 0.0005
        K = 0.5
        
        start_balance = upbit.get_balance("KRW")
        df = pyupbit.get_ohlcv(coin, count = 2, interval = "day")
        targetPrice = get_targetPrice(df, get_best_K(coin, fees))
        print(datetime.datetime.now().strftime('%y/%m/%d %H:%M:%S'), "\t\tBalance :", start_balance, "KRW \t\tYield :", ((start_balance / start_balance) - 1) * 100, "% \t\tNew targetPrice :", targetPrice, "KRW")
        dbgout("자동매매를 시작합니다.\n잔액 : "+str(start_balance)+" 원\n목표매수가 : "+str(targetPrice)+" 원")

        while True :
            now = datetime.datetime.now()
            if now.hour == 9 and now.minute == 2 :    # when am 09:02:00
                sell_all(coin)
                time.sleep(10)

                df = pyupbit.get_ohlcv(coin, count = 2, interval = "day")
                targetPrice = get_targetPrice(df, get_best_K(coin, fees))

                cur_balance = upbit.get_balance("KRW")
                print(now.strftime('%y/%m/%d %H:%M:%S'), "\t\tBalance :", cur_balance, "KRW \t\tYield :", ((cur_balance / start_balance) - 1) * 100, "% \t\tNew targetPrice :", targetPrice, "KRW")
                dbgout("새로운 장 시작\n수익률 : "+str(((cur_balance / start_balance) - 1) * 100)+" %\n잔액 : "+str(cur_balance)+" 원\n목표매수가 : "+str(targetPrice)+" 원")
                time.sleep(60)

            elif targetPrice <= pyupbit.get_current_price(coin) :
                buy_all(coin)
                
                start_time = df.index[-1]
                end_time = start_time + datetime.timedelta(days=1)
                if end_time > now :
                    time.sleep((end_time - now).seconds)
    
            time.sleep(1)

    except Exception as e:
        print(e)
        dbgout(e)
        time.sleep(1)