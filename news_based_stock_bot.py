import urllib.parse
from bs4 import BeautifulSoup as bs
import requests
import http.client
import json
from datetime import datetime
import time

class StockAnalyzer:
    MAX_SHARES = 15
    NUM_TICKERS = 20

    def __init__(self):
        self.tickers = []
        self.sell_list = []
        self.buy_list = []
        self.positive_stocks = []
        self.negative_stocks = []
        self.current_cash = 0

    def get_top_tickers(self):
        url = 'https://finance.yahoo.com/trending-tickers/'
        page = requests.get(url)

        if page.status_code == 200:
            soup = bs(page.content, 'html.parser')
            table_body = soup.find('tbody')
            rows = table_body.find_all('tr')

            self.tickers = [row.find('td', {'aria-label': 'Symbol'}).find('a').text for row in rows[:self.NUM_TICKERS]]
            print(f'\nTop {self.NUM_TICKERS} tickers: {self.tickers}\n')
        else:
            print("Failed to retrieve tickers")

    def get_stock_price(self, ticker):
        url = f'https://finance.yahoo.com/quote/{ticker}/'
        page = requests.get(url)

        if page.status_code == 200:
            soup = bs(page.text, 'html.parser')
            element = soup.find('fin-streamer', {'class': 'Fw(b) Fz(36px) Mb(-4px) D(ib)',
                                                 'data-symbol': {ticker},
                                                 'data-test': 'qsp-price',
                                                 'data-field': 'regularMarketPrice'})
            value = element.get('value')
            return float(value) if value else 0
        else:
            return 0

    def get_stocks(self, sentiment):
        api_token = 'YOUR TOKEN GOES HERE'
        conn = http.client.HTTPSConnection('api.marketaux.com')
        symbols = ','.join(self.tickers)
        countries = 'us'

        print(f'Getting articles published on {self.published_on}')

        params = urllib.parse.urlencode([('api_token', api_token),
                                         ('symbols', symbols),
                                         ('countries', countries),
                                         (sentiment, 0),
                                         ('published_on', self.published_on)])

        conn.request('GET', f'/v1/news/all?{params}')
        res = conn.getresponse()
        data = res.read()
        obj = json.loads(data.decode('utf-8'))

        if sentiment == 'sentiment_gte':
            self.add_to_list(self.positive_stocks, obj)
        elif sentiment == 'sentiment_lte':
            self.add_to_list(self.negative_stocks, obj)

    def add_to_list(self, stocks_list, obj):
        for article in obj.get('data', []):
            for entity in article.get('entities', []):
                symbol = entity.get('symbol')
                sentiment_score = entity.get('sentiment_score', 0)
                if sentiment_score != 0:
                    stocks_list.append((symbol, sentiment_score))

    def compare_pos_neg(self):
        common_symbols = set(pos[0] for pos in self.positive_stocks) & set(neg[0] for neg in self.negative_stocks)

        for symbol in common_symbols:
            pos_score = next((score for sym, score in self.positive_stocks if sym == symbol), None)
            neg_score = next((score for sym, score in self.negative_stocks if sym == symbol), None)

            if pos_score is not None and neg_score is not None and pos_score * neg_score < 0:
                self.positive_stocks = [(sym, score) for sym, score in self.positive_stocks if sym != symbol]
                self.negative_stocks = [(sym, score) for sym, score in self.negative_stocks if sym != symbol]

    def print_stocks(self, stocks):
        for stock in stocks:
            print(stock)

    def calculate_trades(self, stocks):
        for ticker, score in stocks:
            if score < -0.1:
                self.sell_list.append(ticker)
            elif score > 0:
                shares_to_buy = min(int(score * self.MAX_SHARES), self.MAX_SHARES)
                self.buy_list.append((ticker, shares_to_buy))

    def average_duplicates(self, stocks):
        ticker_scores = {}
        ticker_counts = {}

        for ticker, score in stocks:
            ticker_scores[ticker] = ticker_scores.get(ticker, 0) + score
            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1

        self.buy_list = sorted([(ticker, round(ticker_scores[ticker] / ticker_counts[ticker]))
                                for ticker in ticker_scores], key=lambda x: -x[1])

    def filter_tickers(self, stocks):
        stocks[:] = [stock for stock in stocks if '.' not in stock[0] and '^' not in stock[0]]

    def adjust_to_afford(self):
        total_cost = 0
        adjusted_buy_list = self.buy_list[:]
        
        stock_prices = {ticker: self.get_stock_price(ticker) for ticker, _ in self.buy_list if self.get_stock_price(ticker) is not None}

        for ticker, shares in self.buy_list:
            stock_price = stock_prices[ticker]

            total_cost += stock_price * shares

        while total_cost > self.current_cash and adjusted_buy_list:
            most_expensive_ticker = max(adjusted_buy_list, key=lambda x: stock_prices[x[0]] * x[1])
            ticker, shares = most_expensive_ticker

            if shares > 1:
                adjusted_shares = shares - 1
                adjusted_buy_list = [(t, s - 1) if t == ticker else (t, s) for t, s in adjusted_buy_list]
                total_cost -= stock_prices[ticker]
                print(f"Total Cost: ${total_cost}. Reducing shares for {ticker} to {adjusted_shares} due to budget constraints.")
            else:
                adjusted_buy_list.remove(most_expensive_ticker)
                print(f"Cannot reduce shares further for {ticker}. Removing from the buy list.")

            time.sleep(0.1)

        self.buy_list = adjusted_buy_list

    def get_cash_num(self):
        while True:
            cash = input('Enter current expendable cash: ')
            if input('Confirm Amount. Enter Y/N: ').lower() == 'y':
                break
        self.current_cash = float(cash)

    def add_extra_tickers(self):
        print('\nAdd any tickers. If you dont want any additional tickers or are done, input DONE')
        while True:
            ticker = input()
            if ticker == "DONE":
                break
            self.tickers.append(ticker)

    def set_published_on(self):
        self.published_on = input('Enter date of news desired (Ex. 2023-12-22): ')

if __name__ == '__main__':
    stock_analyzer = StockAnalyzer()
    stock_analyzer.get_cash_num()
    stock_analyzer.set_published_on()
    stock_analyzer.get_top_tickers()
    stock_analyzer.add_extra_tickers()
    stock_analyzer.get_stocks('sentiment_gte')
    stock_analyzer.get_stocks('sentiment_lte')
    stock_analyzer.compare_pos_neg()

    stock_analyzer.filter_tickers(stock_analyzer.positive_stocks)
    stock_analyzer.filter_tickers(stock_analyzer.negative_stocks)

    stock_analyzer.calculate_trades(stock_analyzer.positive_stocks)
    stock_analyzer.calculate_trades(stock_analyzer.negative_stocks)

    stock_analyzer.average_duplicates(stock_analyzer.buy_list)
    stock_analyzer.adjust_to_afford()

    print("\nSell List:")
    stock_analyzer.print_stocks(stock_analyzer.sell_list)
    print("\nBuy List:")
    stock_analyzer.print_stocks(stock_analyzer.buy_list)
    print()
