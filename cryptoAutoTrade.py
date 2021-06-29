
import pyupbit
import datetime
import time, calendar
import numpy as np
import requests
import schedule

myToken = ""
access = ""
secret = ""


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

def get_targetPrice(df, K) :
    range = df['high'][-2] - df['low'][-2]
    return df['open'][-1] + range * K

def buy_all(coin) :
    balance = upbit.get_balance("KRW") * 0.9995
    if balance >= 5000 :
        upbit.buy_market_order(coin, balance) # 시장가 매수
        dbgout("매수 체결.\n원화 잔고 : "+str(balance)+" 원\n체결 단가 : "+str(pyupbit.get_current_price(coin))+" 원")

def sell_all(coin) :
    balance = upbit.get_balance(coin)
    price = pyupbit.get_current_price(coin)
    if price * balance >= 5000 :
        upbit.sell_market_order(coin, balance) # 시장가 매도
        dbgout("매도 체결.\n원화 잔고 : "+str(price * balance)+" 원\n체결 단가 : "+str(pyupbit.get_current_price(coin))+" 원")

def get_crr(df, fees, K) :
    # DataFrame 객체에서 각 컬럼은 Series 객체이지요? 
    # Series 객체에 대해 shift() 메서드를 사용하면 데이터를 위/아래로 시프트 시킬 수 있습니다. 
    # shift(1)을 호출하면 데이터를 한 행 밑으로 내릴 수 있고 
    # shift(-1)을 호출하면 데이터를 한 행 위로 올릴 수 있습니다.
    df['range'] = df['high'].shift(1) - df['low'].shift(1)
    df['targetPrice'] = df['open'] + df['range'] * K

    # numpy.where(조건, 조건이 참 일 때의 값, 조건이 거짓일 때의 값)
    df['drr'] = np.where(df['high'] > df['targetPrice'], (df['close'] / (1 + fees)) / (df['targetPrice'] * (1 + fees)) , 1)
    # 모든 값을 곱해주는 메서드로 cumprod()가 있습니다. drr 컬럼의 값을 모두 곱해서 누적 수익률을 계산합니다.
    # drr 컬럼에 대해 cumprod()를 호출하면 Series 객체가 리턴됩니다. 리턴되는 Series 객체에서 끝에서 2번째 값을 drr 변수가 바인딩합니다.

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
    
      
    return best_K - 0.1

def get_ma10(ticker):
    """15일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=10)
    ma10 = df['close'].rolling(10).mean().iloc[-1]
    return ma10

def get_ma5(ticker):
    """5일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=5)
    ma5 = df['close'].rolling(5).mean().iloc[-1]
    return ma5

def sell_all_hour():

    try:
        fees = 0.0005
        coin = 'KRW-BTC'
        df = pyupbit.get_ohlcv(coin, count = 2, interval = "day")
        best_k = get_best_K(coin, fees)
        targetPrice = get_targetPrice(df, best_k)
        currentPrice = pyupbit.get_current_price(coin)
        ma10 = get_ma10(coin)
        ma5 = get_ma5(coin)

        dbgout("스케줄링.\n현재가 : "+str(currentPrice)+" 원\n10일 이동평균가 : "+str(ma10)+" 원\n목표매수가 : "+str(targetPrice)+" 원\nbest_K : " + str(best_k))
        # 현재가가 10일 이동평균가보다 크고
        # 현재가가 목표가보다 큰 경우 -> 매수
        if currentPrice >= ma10 and currentPrice >= targetPrice :
            buy_all(coin) # 원화 잔고가 5000원 이상이면 -> 매수

        # 현재가가 10일 이동평균가보다 작은 경우 -> 매도
        elif currentPrice < ma10:
            sell_all(coin) # 비트코인 잔고가 5000원 이상이면 -> 메도

    except Exception as ex:
        dbgout("sell_all_hour() -> exception! " + str(ex))
        

# schedule.every(30).minutes.do(sell_all_hour('KRW-BTC')) #30분마다 실행
# schedule.every().monday.at("00:10").do(sell_all_hour('KRW-BTC')) #월요일 00:10분에 실행
# schedule.every().day.at("10:30").do(sell_all_hour('KRW-BTC')) #매일 10시30분에

schedule.every(30).minutes.do(sell_all_hour) #30분마다 실행

if __name__ == '__main__': 
    try:
        upbit = pyupbit.Upbit(access, secret)

        # set variables
        coin = "KRW-BTC"
        fees = 0.0005
        K = 0.5
        
        start_balance = upbit.get_balance("KRW")
        df = pyupbit.get_ohlcv(coin, count = 2, interval = "day")
        best_k = get_best_K(coin, fees)
        targetPrice = get_targetPrice(df, best_k)
        currentPrice = pyupbit.get_current_price(coin)
        ma10 = get_ma10(coin)
        #print(datetime.datetime.now().strftime('%y/%m/%d %H:%M:%S'), "\t\tBalance :", start_balance, "KRW \t\tYield :", ((start_balance / start_balance) - 1) * 100, "% \t\tNew targetPrice :", targetPrice, "KRW")
        dbgout("자동매매를 시작합니다.\n잔액 : "+str(start_balance)+" 원\n현재가 : "+str(currentPrice)+" 원\n목표매수가 : "+str(targetPrice)+" 원\nbest_K : " + str(best_k))
        printlog('main() -> 잔액 : ' +str(start_balance))
        printlog('main() -> best_k :' + str(best_k) + ', targetPrice : ' + str(targetPrice)+ ', currentPrice : ' + str(currentPrice)+ ', ma10 : ' + str(ma10))
        printlog('main() -> while문 진입.....')

        while True :            
            now = datetime.datetime.now()
            if now.hour == 9 and now.minute == 2 :    # when am 09:02:00
                printlog('main() -> sell_all() 호출')
                sell_all(coin) # 비트코인 잔고가 5000원 이상이면 -> 메도
                time.sleep(10)

                df = pyupbit.get_ohlcv(coin, count = 2, interval = "day")
                best_k = get_best_K(coin, fees)
                targetPrice = get_targetPrice(df, best_k)
                currentPrice = pyupbit.get_current_price(coin)
                cur_balance = upbit.get_balance("KRW")

                dbgout("새로운 장 시작\n수익률 : "+str(((cur_balance / start_balance) - 1) * 100)+" %\n잔액 : "+str(start_balance)+" 원\n현재가 : "+str(currentPrice)+" 원\n목표매수가 : "+str(targetPrice)+" 원\nbest_K : " + str(best_k))
                time.sleep(60)

            # 현재가가 목표가보다 큰 경우 -> 매수
            elif targetPrice <= pyupbit.get_current_price(coin) :
                printlog('main() -> buy_all() 호출')
                buy_all(coin) # 원화 잔고가 5000원 이상이면 -> 매수
                
                # start_time = df.index[-1]
                # end_time = start_time + datetime.timedelta(days=1)
                # if end_time > now :
                #     time.sleep((end_time - now).seconds)
            
            schedule.run_pending()
            time.sleep(1)

    except Exception as ex:
        dbgout("main() -> exception! " + str(ex))
        time.sleep(1)
