
import pyupbit
import datetime
import time, calendar
import numpy as np
import requests
import schedule

myToken = ""
access = "gEq6BEhaQioReV9HtgJ1Gx8nGN8CGL3Xp76Yd879"          
secret = "T1Bp2HOMzA7nl9KFsHeSxjeTg21TNzjsuaxjpwL7"          


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

def printlog(message, *args):
    """인자로 받은 문자열을 파이썬 셸에 출력한다."""
    print(datetime.datetime.now().strftime('[%m/%d %H:%M:%S]'), message, *args)

def get_ma10_minute240(coin):
    """15일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(coin, interval="minute240", count=10)
    ma10 = df['close'].rolling(10).mean().iloc[-1]
    return ma10

def get_ma5_minute240(coin):
    """15일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(coin, interval="minute240", count=5)
    ma5 = df['close'].rolling(5).mean().iloc[-1]
    return ma5

def buy_all(coin) :
    print(get_ma5_minute240(coin),get_ma10_minute240(coin))
    balance = upbit.get_balance("KRW") * 0.9995
    if balance >= 5000 :
        upbit.buy_market_order(coin, balance) # 시장가 매수
        dbgout("매수 체결.\n원화잔고 : "+str(balance)+" 원\n체결 단가 : "+str(pyupbit.get_current_price(coin))+" 원\nma5 : "+str(get_ma5_minute240(coin))+" 원\nma10 : "+str(get_ma10_minute240(coin))+" 원")

def sell_all(coin) :
    print(get_ma5_minute240(coin),get_ma10_minute240(coin))
    balance = upbit.get_balance(coin)
    price = pyupbit.get_current_price(coin)
    if price * balance >= 5000 :
        upbit.sell_market_order(coin, balance) # 시장가 매도
        dbgout("매도 체결.\n원화잔고 : "+str(price * balance)+" 원\n체결 단가 : "+str(pyupbit.get_current_price(coin))+" 원\nma5 : "+str(get_ma5_minute240(coin))+" 원\nma10 : "+str(get_ma10_minute240(coin))+" 원")

def send_alarm():
    try:
        coin = "KRW-BTC"
        balance = upbit.get_balance(coin)
        price = pyupbit.get_current_price(coin)
        dbgout(".\n원화잔고 : "+str(price * balance)+" 원\n현재가 : "+str(price)+" 원\nma5 : "+str(get_ma5_minute240(coin))+" 원\nma10 : "+str(get_ma10_minute240(coin))+" 원")

    except Exception as ex:
        dbgout("send_alarm() -> exception! " + str(ex))

schedule.every(60).minutes.do(send_alarm) #60분마다 실행

if __name__ == '__main__': 
    try:
        upbit = pyupbit.Upbit(access, secret)

        # set variables
        coin = "KRW-BTC"

        while True :         
            ma5 = get_ma5_minute240(coin)
            ma10 = get_ma10_minute240(coin)

            if ma5 > ma10:
                buy_all(coin)
            else:
                sell_all(coin)

            schedule.run_pending()
            time.sleep(10)
            
            
    except Exception as ex:
        dbgout("main() -> exception! " + str(ex))
        time.sleep(1)
