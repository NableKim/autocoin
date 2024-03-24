import os
from dotenv import load_dotenv
load_dotenv()
import pyupbit
import pandas as pd
import pandas_ta as ta
import json
from openai import OpenAI
import schedule
import time
from datetime import datetime
import slack_notification as sn

# Setup
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
upbit = pyupbit.Upbit(os.getenv("UPBIT_ACCESS_KEY"), os.getenv("UPBIT_SECRET_KEY"))

def get_current_status():
    orderbook = pyupbit.get_orderbook(ticker="KRW-BTC")
    current_time = orderbook['timestamp']
    btc_balance = 0
    krw_balance = 0
    btc_avg_buy_price = 0
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == "BTC":
            btc_balance = b['balance']
            btc_avg_buy_price = b['avg_buy_price']
        if b['currency'] == "KRW":
            krw_balance = b['balance']     

    current_status = {'current_time': current_time, 'orderbook': orderbook, 'btc_balance': btc_balance, 'krw_balance': krw_balance, 'btc_avg_buy_price': btc_avg_buy_price}
    return json.dumps(current_status)


def fetch_and_prepare_data():
    # Fetch data
    df_daily = pyupbit.get_ohlcv("KRW-BTC", "day", count=30)
    df_hourly = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=24)

    # Define a helper function to add indicators
    def add_indicators(df):
        # Moving Averages
        df['SMA_10'] = ta.sma(df['close'], length=10)
        df['EMA_10'] = ta.ema(df['close'], length=10)

        # RSI
        df['RSI_14'] = ta.rsi(df['close'], length=14)

        # Stochastic Oscillator
        stoch = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3, smooth_k=3)
        df = df.join(stoch)

        # MACD
        ema_fast = df['close'].ewm(span=12, adjust=False).mean()
        ema_slow = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema_fast - ema_slow
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Histogram'] = df['MACD'] - df['Signal_Line']

        # Bollinger Bands
        df['Middle_Band'] = df['close'].rolling(window=20).mean()
        # Calculate the standard deviation of closing prices over the last 20 days
        std_dev = df['close'].rolling(window=20).std()
        # Calculate the upper band (Middle Band + 2 * Standard Deviation)
        df['Upper_Band'] = df['Middle_Band'] + (std_dev * 2)
        # Calculate the lower band (Middle Band - 2 * Standard Deviation)
        df['Lower_Band'] = df['Middle_Band'] - (std_dev * 2)

        return df

    # Add indicators to both dataframes
    df_daily = add_indicators(df_daily)
    df_hourly = add_indicators(df_hourly)

    combined_df = pd.concat([df_daily, df_hourly], keys=['daily', 'hourly'])
    combined_data = combined_df.to_json(orient='split')

    # make combined data as string and print length
    print(len(combined_data))

    return json.dumps(combined_data)

def get_instructions(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            instructions = file.read()
        return instructions
    except FileNotFoundError:
        print("File not found.")
    except Exception as e:
        print("An error occurred while reading the file:", e)

def analyze_data_with_gpt4(data_json):
    print("Getting an advise from GPT...")
    instructions_path = "instructions.md"
    try:
        instructions = get_instructions(instructions_path)
        if not instructions:
            print("No instructions found.")
            return None

        current_status = get_current_status()
        response = client.chat.completions.create(
            #model="gpt-4-turbo-preview",
            #model="gpt-3.5-turbo-1106",
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": data_json},
                {"role": "user", "content": current_status}
            ],
            response_format={"type":"json_object"}
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in analyzing data with GPT-4: {e}")
        return None

def execute_buy(percentage):
    print("Attempting to buy BTC...")
    try:
        balance_krw = upbit.get_balance("KRW")
        percentage = percentage / 100 # 백분율 만들기
        amount = balance_krw * percentage

        print(f"buy. current_balance: {balance_krw}, percentage: {percentage*100}%, amount: {amount}")
        
        # 업비트 최소 거래 금액 5000원 이상
        if amount > 5000:
            print(f"구매 실행. 현금보유량: {balance_krw}, 실제 매수량: {amount*0.9995}")
            result = upbit.buy_market_order("KRW-BTC", amount*0.9995)
            print("Buy order successful:", result)
    except Exception as e:
        print(f"Failed to execute buy order: {e}")

def execute_sell(percentage):
    print("Attempting to sell BTC...")
    try:
        btc_balance = upbit.get_balance("BTC") # 현재 보유한 코인 수
        percentage = percentage / 100 # 백분율 만들기
        btc_to_sell = btc_balance * percentage

        print(f"sell. current_balance: {btc_balance}, percentage: {percentage*100}%, btc_to_sell: {btc_to_sell}")

        current_price = pyupbit.get_orderbook(ticker="KRW-BTC")['orderbook_units'][0]["ask_price"]
        if current_price*btc_to_sell > 5000:
            print(f"판매 실행. 보유량: {btc_balance}, 실제 매도량: {btc_to_sell}")
            result = upbit.sell_market_order("KRW-BTC", btc_to_sell)
            print("Sell order successful:", result)
        else:
            print(f"판매 실패. 보유량: {btc_balance}, 실제 매도량: {btc_to_sell}")
    except Exception as e:
        print(f"Failed to execute sell order: {e}")

def make_decision_and_execute():
    current_datetime = datetime.now()
    print("현재 날짜와 시간:", current_datetime.strftime("%Y-%m-%d %H:%M:%S"))
    print("Making decision and executing...")
    data_json = fetch_and_prepare_data()
    advice_json = analyze_data_with_gpt4(data_json)

    try:
        advice = json.loads(advice_json)
        decision = advice.get('decision')
        reason = advice.get('reason')
        percentage = advice.get('percentage')
        
        print(advice)

        if decision == "buy":
            execute_buy(percentage)
        elif decision == "sell":
            execute_sell(percentage)

        # slack notification
        sn.send_msg(f"decision: {decision} \npercentage: {percentage} \nreason: {reason}")

    except Exception as e:
        print(f"Failed to parse the advice as JSON: {e}")

if __name__ == "__main__":
    print("started...")
    make_decision_and_execute()
    schedule.every().hour.at(":01").do(make_decision_and_execute)

    while True:
        schedule.run_pending()
        time.sleep(1)