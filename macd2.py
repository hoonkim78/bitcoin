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
    #target_price = df.iloc[::-1]['close'] 
    target_price = df['close'][-1]
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

def buy_all(ticker):
    try:
        # target_price = get_target_price(ticker) # 1시간봉 종가 -> 1시간 평균가
        current_price = get_current_price(ticker) # 현재가
        # if current_price > target_price:
        krw = upbit.get_balance("KRW") * 0.9995
        #현재 잔고의 5% 금액으로 매매 진행
        #krw = krw * 0.1
        if krw > 5000:
            #시장가 매수
            buy_result = upbit.buy_market_order(ticker, krw)         
            buy_price.update({ ticker : int(current_price) })
            send_slackMsg("BTC Buy : " +str(buy_result))       
    except Exception as e:
        send_slackMsg(str(e))    

def sell_all(ticker):  
    try:
        btc = upbit.get_balance(ticker)
        #시장가 매도
        sell_result = upbit.sell_market_order(ticker, btc)
        # 매도 체결여부 확인
        uncomp = upbit.get_order(ticker) # 미체결된 리스트 조회
        if len(uncomp) == 0: # 길이가 0이라면, 모든 주문이 체결됐다면    
            if int(buy_price[ticker]) > 0:
                d = int(buy_price[ticker]) # 매수가
                e = int(get_current_price(ticker)) # 현재가
                f = ((( e / d ) - 1 ) * 100 )                              
                send_slackMsg("수익률 :" + "%.2f" % (f) + "%")      

            buy_price.update({ ticker : 0 }) # 매수가 초기화
            send_slackMsg("BTC Sell : " + str(sell_result))  
                
    except Exception as e:
        send_slackMsg(str(e))    

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

if __name__ == '__main__': 
    
    try:
        # 로그인
        upbit = pyupbit.Upbit(access, secret)
        start_slackMsg = send_slackMsg("autotrade start")
        
        # 매수상태 플래그 True:매수상태, False : 매수하기 전
        bought_flag = False 

        #매수 구매 가격
        buy_price = {}
        buy_price.update({ "KRW-BTC" : 0 }) 

        call='Wait'

        while True:

            #현재시간 구하기
            now = datetime.datetime.now()
            # 59분마다 수행하다보니 매수타이밍으로 변경된 시점보다 늦게 매수가되어
            # 중간에 30분에도 한 번더 수행될 수 있도록 수정
            #업비트 30분봉 URL 호출
            url = "https://api.upbit.com/v1/candles/minutes/60" 

            #원화시장 BTC 캔들갯수 MAX:200 / 카운트:100
            querystring = {"market":"KRW-BTC","count":"200"}
                
            #업비트 원화시장 BTC 60분봉 100개 조회 결과 저장
            response = requests.request("GET", url, params=querystring)
                
            #해당 데이터 저장
            data = response.json()

            #해당 데이터로 데이터프레임 생성
            df = pd.DataFrame(data)                

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

            btc = upbit.get_balance("KRW-BTC")
            if btc > 0:
                bought_flag = True
            else:
                bought_flag = False

            
            if bought_flag == True and int(buy_price["KRW-BTC"]) > 0:  # 매수상태이고

                d = int(buy_price["KRW-BTC"]) # 매수가
                e = int(get_current_price("KRW-BTC")) # 현재가
                f = ((( e / d ) - 1 ) * 100 )

                # 1000원 1%이면 10원
                # 10,000원 1%이면 100원
                # 100,000원 1%이면 1000원
                # 1,000,000원 1%이면 10,000원
                # 10,000,000원 1%이면 100,000원

                if f <= -0.3 : # 수익률을 비교해서 -2%이면 무조건 매도
                    call='Forced_Sell'
                    sell_all("KRW-BTC")
                    # bought_flag = False # 매도가 완료되면 다음주문이 가능하도록 false 처리한다. 


            if now.minute >= 55:


                if signal[0] > macd[0] and macd[1] > signal[1] and bought_flag == True: # 매수상태이면

                    call='Sell'
                    sell_all("KRW-BTC")               
                    
                    
                if macd[0] > signal[0] and signal[1] > macd[1] and bought_flag == False:

                    call='Buy'                 
                    buy_all("KRW-BTC")                    

                send_slackMsg(call + "|" + str(bought_flag))

            time.sleep(30)    

    except Exception as ex:
        send_slackMsg(str(ex))
        time.sleep(1)
