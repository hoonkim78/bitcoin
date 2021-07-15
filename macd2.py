import requests
import pandas as pd
import time
import pyupbit 
import numpy as np
import datetime


#####################################################
# Made By NJW 2021-07-09                            
# 업비트 API, MACD 지표를 활용한 자동매수매도 프로그램
# Ver 0.0.1
# Desc : 최초버전
#####################################################
# Made By NJW 2021-07-12                            
# Ver 0.0.2
# Desc : Slack Message 추가
#####################################################

# 매수 목표가 조회 (1시간봉 종가배팅)
def get_target_price(ticker):
    df = pyupbit.get_ohlcv(ticker, interval="minute60", count=1)
    target_price = df.iloc[::-1]['close'] 
    return target_price

# 잔고 조회
def get_balance(ticker):
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0    

# 현재가 조회 (BTC)
def get_current_price(ticker):
    return pyupbit.get_orderbook(tickers=ticker)[0]["orderbook_units"][0]["ask_price"]


def send_slackMsg(msg=""):
        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers={
                'Authorization': 'Bearer '+ slackToken
            },
            data={
                # Slack 채널명:trade
                'channel':'#투자',
                'text': datetime.datetime.now().strftime('[%m/%d %H:%M:%S] ') + msg
            }
        )
        #print('slackMsg Result: ' + response)
        return 0
        

# access, secret 값 선언
access = "gEq6BEhaQioReV9HtgJ1Gx8nGN8CGL3Xp76Yd879"          
secret = "T1Bp2HOMzA7nl9KFsHeSxjeTg21TNzjsuaxjpwL7"  
slackToken = ""

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")
start_slackMsg = send_slackMsg("autotrade start")

while True:

    #현재시간 구하기
    now = datetime.datetime.now()
    excel_date_string = now.strftime('%Y%m%d%H%M%S')
    print_date_string = now.strftime('%Y:%m:%d:%H:%M:%S')
    #print(date_string)

    #업비트 60분봉 URL 호출
    url = "https://api.upbit.com/v1/candles/minutes/60" 

    #원화시장 BTC 캔들갯수 MAX:200 / 카운트:100
    querystring = {"market":"KRW-BTC","count":"100"}
        
    #업비트 원화시장 BTC 60분봉 100개 조회 결과 저장
    response = requests.request("GET", url, params=querystring)
        
    #해당 데이터 저장
    data = response.json()

    #해당 데이터로 데이터프레임 생성
    df = pd.DataFrame(data)
    print(df)

    #데이터 프레임 오름차순 정렬 7/10 ~ 7/14 순으로 오름차순
    df=df.iloc[::-1]

    #종가만 데이터 프레임 저장
    df=df['trade_price']

    #지수이동평균 구하기 span: 기간 
    exp1 = df.ewm(span=12, adjust=False).mean()
    exp2 = df.ewm(span=26, adjust=False).mean()

    #MACD 지표 계산 (단기지수이동평균 - 장기지수이동평균)
    macd = exp1-exp2

    #시그널 지표 계산 (MACD 9일 주가 이동평균치, ※ 1시간봉이기 때문에 현재 9시간 기준)
    signal = macd.ewm(span=9, adjust=False).mean()

    #현재 MACD, Signal 값 출력        
    print(print_date_string, '[Trace]', 'current_data -> ', 'MACD:',macd[0], ' Signal: ', signal[0])


    #현재 Signal - MACD
    #current_data=signal[0]-macd[0]
    current_data=macd[0]-signal[0]
    #print('current_data: ', current_data)

    #이전 Signal - MACD
    #before_data=signal[1]-macd[1]
    before_data=macd[1]-signal[1]
    #print('before_data: ', before_data)

    print(print_date_string, '[Trace]', 'current_data:',current_data, ' before_data: ', before_data)

    call='Not Buy & Not Sell'

    print(print_date_string, '[Trace]', 'current_data <-> before_data comparing...')    

    if macd[0] > signal[0] and signal[1] > macd[1]:
        call='Sell'
        btc = get_balance("BTC")
        #시장가 매도
        sell_result = ''
        #sell_result = upbit.sell_market_order("KRW-BTC", btc*0.9995)
        send_slackMsg("BTC Sell : " +str(sell_result))
        
        
    if  signal[0] > macd[0] and macd[1] > signal[1]:
        call='Buy'
        try:
            target_price = get_target_price("KRW-BTC")
            current_price = get_current_price("KRW-BTC")
            if current_price > target_price:
                krw = get_balance("KRW")
                #현재 잔고의 5% 금액으로 매매 진행
                krw = krw * 0.1
                if krw > 5000:
                    #시장가 매수
                    buy_result = ''
                    #buy_result = upbit.buy_market_order("KRW-BTC", krw*0.9995)
                    send_slackMsg("BTC Buy : " +str(buy_result))
                    call=call + ': current_price: ' + current_price + ' target_price: ' + target_price + ' balance: ' + krw
                    
                call='be short of balance'
        except Exception as e:
            print(e)
            send_slackMsg(e)
            


    print(print_date_string, '[Trace]','AutoTradeResult:', call)
    send_slackMsg(call)

    #30분당 조회
    time.sleep(1800)
    #################################################### 
    #엑셀로 결과 출력
    ####################################################
    # now = datetime.datetime.now()
    # date_string = now.strftime('%Y%m%d%H%M%S')
    # print(date_string)
    # excel_name = date_string + "_AutoTradeRecord.xlsx"
    # df.to_excel(excel_name)

