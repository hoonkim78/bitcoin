import threading
import queue
import time
import pyupbit
import datetime
from collections import deque

class Consumer(threading.Thread):
    def __init__(self, q):
        super().__init__()
        self.q = q
        self.ticker = "KRW-BTC"

        self.ma15 = deque(maxlen=5) 
        self.ma50 = deque(maxlen=10)
        self.ma120 = deque(maxlen=15)

        # 초기값 설정
        df = pyupbit.get_ohlcv(self.ticker, interval="minute1") # 1분봉 200개 조회
        self.ma15.extend(df['close']) # maxlen=15 이기 때문에 최근 15개 값만 저장
        self.ma50.extend(df['close'])
        self.ma120.extend(df['close'])

        print(len(self.ma15), len(self.ma50), len(self.ma120))


    def run(self):    
        price_curr = None
        hold_flag = False # 매수상태 플래그 True:매수상태, False : 매수하기 전
        wait_flag = False

        access = "gEq6BEhaQioReV9HtgJ1Gx8nGN8CGL3Xp76Yd879"          
        secret = "T1Bp2HOMzA7nl9KFsHeSxjeTg21TNzjsuaxjpwL7"   
        upbit = pyupbit.Upbit(access, secret)
        cash  = upbit.get_balance()
        print("보유현금", cash)

        i = 0

        while True:   
            try:         
                if not self.q.empty(): # Queue가 비어있지 않다면, Queue에 데이터가 존재하면
                    if price_curr != None:
                        self.ma15.append(price_curr) # 0.2초 마다 조회한 현재가를 업데이트한다..
                        self.ma50.append(price_curr)
                        self.ma120.append(price_curr)

                    curr_ma15 = sum(self.ma15) / len(self.ma15) # 최근 15개 이동 평균을 구한다.
                    curr_ma50 = sum(self.ma50) / len(self.ma50) # 최근 50개 이동 평균을 구한다.
                    curr_ma120 = sum(self.ma120) / len(self.ma120) # 최근 120개 이동 평균을 구한다.

                    # Queue에서 데이터를 꺼내서 시작가 변수에 바인딩
                    # Queue에서 get하는 순가 Queue에서도 삭제된다. 
                    price_open = self.q.get() 
                    if hold_flag == False:
                        price_buy  = int(price_open * 1.0008) # 매수가, 목표가
                        price_sell = int(price_open * 1.002) # 매도가
                    wait_flag  = False
                
                # wait_flag 는 현재가가 급등하는 경우 한번의 1분봉 구간에서 매수/매도를 여러번 할 수 있기 때문에
                # 이를 제한하기 우해 Queue에서 1분봉 데이터를 새로 가져왔을 경우에만 매수/매도를 1번만 할 수 있도록
                # wait_flag를 사용한다.
                price_curr = pyupbit.get_current_price(self.ticker) # 현재가

                # 매수조건
                # 1. 현재가격 목표가격 보다 높을 때 시장가 매수
                # 2. 15일 이평선이 50일 이평선보다 높아야한다.
                # 4. 50일 이평선이 150일 이평선보다 높아야한다.
                # 3. 단기이평선이 장기이평선 대비 3%이상 넘어가지 않도록 제한 curr_ma15 <= curr_ma50 * 1.03 and 
                if hold_flag == False and wait_flag == False and \
                    price_curr >= price_buy and curr_ma15 >= curr_ma50 and \
                    curr_ma120 <= curr_ma50 :
                    # 0.05%
                    ret = upbit.buy_market_order(self.ticker, cash * 0.9995) # 시장가 매수주문
                    print("매수주문", ret)
                    time.sleep(1)

                    # 슬리피지란 의도했던 체결가와 실제 체결가간의 차이
                    volume = upbit.get_balance(self.ticker) # 비트코인 보유수량 조회
                    ret = upbit.sell_limit_order(self.ticker, price_sell, volume) # 지정가 매도주문
                    print("매도주문", ret)
                    hold_flag = True # 매도 주문이 완료되지 전까지는 매수 주문을 하지 못함
                # print(price_curr, curr_ma15, curr_ma50, curr_ma120)

                # 매도 체결여부 확인
                if hold_flag == True: # 매수한 상태라면
                    uncomp = upbit.get_order(self.ticker) # 미체결된 리스트 조회
                    if len(uncomp) == 0: # 길이가 0이라면, 모든 주문이 체결됐다면
                        cash = upbit.get_balance() # 보유현금
                        print("매도완료", cash)
                        hold_flag = False # 매수/매도가 완료되면 다음주문이 가능하도록 false 처리한다.
                        wait_flag = True

                # 3 minutes
                if i == (5 * 60):
                    print(f"[{datetime.datetime.now()}] 현재가 {price_curr}, 목표가 {price_buy}, ma {curr_ma15:.2f}/{curr_ma50:.2f}/{curr_ma120:.2f}, hold_flag {hold_flag}, wait_flag {wait_flag}")
                    i = 0
                i += 1
            except:
                print("error")
                
            time.sleep(0.2)
            
class Producer(threading.Thread):
    def __init__(self, q):
        super().__init__()
        self.q = q

    def run(self):
        while True:
            price = pyupbit.get_current_price("KRW-BTC")
            self.q.put(price)
            time.sleep(60)            
            
q = queue.Queue()
Producer(q).start()
Consumer(q).start()