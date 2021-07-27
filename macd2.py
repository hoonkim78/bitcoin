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

        while True:

            #현재시간 구하기
            now = datetime.datetime.now()
            # 59분마다 수행
            if now.minute == 59 :

                excel_date_string = now.strftime('%Y%m%d%H%M%S')
                print_date_string = now.strftime('%Y:%m:%d:%H:%M:%S')

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

                call='Not Buy & Not Sell'

                if signal[0] > macd[0] and macd[1] > signal[1] and bought_flag == True: # 매수상태이면

                    call='Sell'
                    btc = get_balance("BTC")
                    #시장가 매도
                    sell_result = upbit.sell_market_order("KRW-BTC", btc*0.9995)
                    # 매도 체결여부 확인
                    uncomp = upbit.get_order("KRW-BTC") # 미체결된 리스트 조회
                    if len(uncomp) == 0: # 길이가 0이라면, 모든 주문이 체결됐다면                    
                        d = int(buy_price["KRW-BTC"]) # 매수가
                        e = int(get_current_price("KRW-BTC")) # 현재가
                        f = ((( e / d ) - 1 ) * 100 )

                        bought_flag = False # 매도가 완료되면 다음주문이 가능하도록 false 처리한다.                    
                        buy_price.update({ "KRW-BTC" : 0 }) # 매수가 초기화

                        send_slackMsg("BTC Sell : " + str(sell_result))                    
                        send_slackMsg("수익률 :" + "%.2f" % (f) + "%") 
                    
                    
                if macd[0] > signal[0] and signal[1] > macd[1] and bought_flag == False:

                    call='Buy'
                    try:
                        target_price = get_target_price("KRW-BTC") # 1시간봉 종가 -> 1시간 평균가
                        current_price = get_current_price("KRW-BTC") # 현재가
                        if current_price > target_price:
                            krw = get_balance("KRW")
                            #현재 잔고의 5% 금액으로 매매 진행
                            krw = krw * 0.1
                            if krw > 5000:
                                #시장가 매수
                                buy_result = upbit.buy_market_order("KRW-BTC", krw*0.9995)         
                                buy_price.update({ "KRW-BTC" : int(current_price) })
                                send_slackMsg("BTC Buy : " +str(buy_result))                   
                                
                                bought_flag = True # True:매수상태, 
                                
                    except Exception as e:
                        send_slackMsg(e)      

                send_slackMsg(call)
                #################################################### 
                #엑셀로 결과 출력
                ####################################################
                # now = datetime.datetime.now()
                # date_string = now.strftime('%Y%m%d%H%M%S')
                # print(date_string)
                # excel_name = date_string + "_AutoTradeRecord.xlsx"
                # df.to_excel(excel_name)    
            time.sleep(10)    
    except Exception as ex:
        time.sleep(1)
