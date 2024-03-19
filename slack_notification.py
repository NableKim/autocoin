import os
from dotenv import load_dotenv
load_dotenv()
import json
import sys
import requests
import os

def send_msg(msg):
    url = os.getenv("SLACK_API")
    tail = "<https://upbit.com/exchange?code=CRIX.UPBIT.KRW-BTC|현재시세>"
    message = (f"{msg} \n {tail}") 
    title = "Advisor say..."
    slack_data = {
        "username": "AutoTradeNotificationBot",
        "icon_emoji": ":moneybag:",
        "channel" : "#auto-trade-notification",
        "text" : "Now Investment Decision Message :koala:",
        "attachments": [
            {
                "color": "#33ee46",
                "fields": [
                    {
                        "title": title,
                        "value": message,
                        "short": "false",
                    }
                ]
            }
        ]
    }
    byte_length = str(sys.getsizeof(slack_data))
    headers = {'Content-Type': "application/json", 'Content-Length': byte_length}
    response = requests.post(url, data=json.dumps(slack_data), headers=headers)
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
