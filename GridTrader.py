from datetime import datetime
from dotenv import load_dotenv
import os
import plotly.graph_objects as go
from client import FtxClient
load_dotenv()
import requests
import pandas as pd
import time, json
from time import sleep
import client
import re
from pathlib import Path
from decimal import Decimal
from retry import retry


class FtxTrader(object):

    
    
    def __init__(self, market, top, bottom, GridNum, qty):
        self.client = client.FtxClient(api_key=os.getenv("FTX_API_KEY"), api_secret=os.getenv("FTX_API_SECRET"),subaccount_name = '4')
        self.endpoint_url = 'https://ftx.com/api/markets'
        self.mar = market
        self.gap = (top - bottom)/GridNum
        self.GridNum = GridNum
        self.bottom = bottom
        self.top = top
        self.qty = qty
        self.buy_orders = []
        self.sell_orders = []
        self.grid_price = []
        self.filled_buy = []
        self.earn = 0
        self.earnnum = 0
        self.start_price = 0

        
    @retry(delay=7,tries=10)   
    def get_open_order(self, id):
        return self.client.get_open_orders(id)
    
    @retry(delay=7,tries=10)    
    def place_order(self, market, side, price, type, size):
        return self.client.place_order(market, side,price , type, size)



    #round to minimum unit
    def round_to(self, value: float, target:float):
        value = Decimal(str(value))
        target = Decimal(str(target))
        rounded = float(int(round(value / target)) * target)
        return rounded
    
    @retry(delay=7,tries=10) 
    def get_bid_ask_price(self):
        request_url = f'{self.endpoint_url}/{self.mar}'
        market = requests.get(request_url).json()
        ask_price = market['result']['ask']
        bid_price = market['result']['bid']
        return bid_price, ask_price

    @retry(delay=7,tries=10) 
    def get_min_qty_price(self):
        request_url = f'{self.endpoint_url}/{self.mar}'
        market = requests.get(request_url).json()
        min_price = market['result']['priceIncrement']
        min_qty = market['result']['sizeIncrement']
        return min_price, min_qty

    

                
    def start(self):        
        min_price, min_qty = self.get_min_qty_price()
        self.qty = self.round_to(self.qty, min_qty)
        bid_price, ask_price = self.get_bid_ask_price()
        
        buy_delete_orders = []  
        sell_delete_orders = []  
            
        for buy_order in self.buy_orders:
            check_order = self.get_open_order(buy_order.get("id"))
            if check_order.get("status") == "closed":
                buy_delete_orders.append(buy_order)
                if check_order.get("filledSize") == check_order.get("size"):
                    stop = 0
                    print(f"buy order was filled, time: {datetime.now()}, price:{check_order.get('price')}")
                    self.filled_buy.append(buy_order)
                    sell_price = self.grid_price[(self.grid_price.index(check_order.get("price")))+1]
                    for order in self.sell_orders:
                        if sell_price == order.get("price"):
                            print("Already exist, stop place order")
                            stop = 1
                    if stop == 0:    
                        new_sell_order = self.place_order(self.mar, "sell",sell_price , "limit", self.qty)
                        if new_sell_order:
                            self.sell_orders.append(new_sell_order)
                elif check_order.get("filledSize") == 0:
                    print("The order was canceled")
                    new_buy_order = self.place_order(self.mar, "buy",check_order.get("price") , "limit", self.qty)
                    if new_buy_order:
                        self.buy_orders.append(new_buy_order)

            elif check_order.get("status") == "open":
                pass
            else:
                print(f"buy order status is not above options: {check_order.get('status')}, time: {datetime.now()}")
        for delete_order in buy_delete_orders:
            self.buy_orders.remove(delete_order)

        

        
        


        for sell_order in self.sell_orders:
            check_order = self.get_open_order(sell_order.get("id"))
            if check_order.get("status") == "closed":
                sell_delete_orders.append(sell_order)
                if check_order.get("filledSize") == check_order.get("size"):
                    check_price = check_order.get("price")
                    buy_price = self.grid_price[(self.grid_price.index(check_price))-1]
                    stop = 0
                    print(f"sell order was filled, time: {datetime.now()}, price:{check_price}")
                    find = 0
                    for order in self.filled_buy:
                        if order.get("price") == buy_price:
                            find = 1
                            self.filled_buy.remove(order)
                            self.earnnum += 1
                            self.earn += (check_price*self.qty) - (buy_price*self.qty)
                            print("earn",self.earnnum,"times")
                            print("already earn:", round(self.earn,2))
                    if find == 0:
                        self.earnnum += 1
                        self.earn += (check_price*self.qty) - (self.start_price*self.qty)
                        print("earn",self.earnnum,"times")
                        print("already earn:", self.earn)
                    for order in self.buy_orders:
                        if buy_price == order.get("price"):
                            print("Already exist, stop place order")
                            stop = 1
                    if stop == 0:
                        new_buy_order = self.place_order(self.mar, "buy",buy_price , "limit", self.qty)
                        if new_buy_order:
                            self.buy_orders.append(new_buy_order)
                elif check_order.get("filledSize") == 0:
                    print("The order was canceled")
                    new_sell_order = self.place_order(self.mar, "sell",check_order.get("price") , "limit", self.qty)
                    if new_sell_order:
                        self.sell_orders.append(new_sell_order)
                
            elif check_order.get("status") == "open":
                pass
            else:
                print(f"sell order status is not above options: {check_order.get('status')}, time: {datetime.now()}")

        for delete_order in sell_delete_orders:
            self.sell_orders.remove(delete_order)


        if len(self.sell_orders) <= 0 and len(self.buy_orders) <= 0:
            for i in range(self.GridNum+1):
                price = self.bottom+(i*self.gap)
                self.grid_price.append(self.round_to(price, min_price))
            sell = 0
            for i in range(len(self.grid_price)):
                if self.grid_price[i] > ask_price:
                    sell += 1
            buy_qty = self.qty * (sell)
            buy_order = self.place_order(self.mar, "buy", None , "market", buy_qty)
            while True:
                if buy_order:
                    check_order = self.get_open_order(buy_order.get("id"))
                    self.start_price = check_order.get("avgFillPrice")
                    print("success")
                    print("Current price:", self.start_price)
                    break


        if len(self.buy_orders) <= 0 and len(self.sell_orders) <= 0:
            if ask_price > 0:
                for i in range(len(self.grid_price)):
                    if self.grid_price[i] > ask_price:
                        sell_order = self.place_order(self.mar, "sell",self.grid_price[i] , "limit", self.qty)
                        if sell_order:
                            self.sell_orders.append(sell_order)
            if bid_price > 0:
                for i in range(len(self.grid_price)):
                    if self.grid_price[i] < bid_price:
                        buy_order = self.place_order(self.mar, "buy",self.grid_price[i] , "limit", self.qty)
                        if buy_order:
                            self.buy_orders.append(buy_order)

                  