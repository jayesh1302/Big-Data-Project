from application import app, db
from application.models import Usa_stock
from flask import render_template, request
import datetime
import random
import yfinance as yf
import math
import re
import json
import plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import requests
import os


def rand_news(num=3):
    history = []
    stock = []
    for i in range(num):
        rand = random.randint(1, 30)
        while rand in history:
            rand = random.randint(1, 30)

        usa_stock = Usa_stock.objects(ref_id=rand).first()

        stock.append(usa_stock.short)
        history.append(rand)
    return stock


def all_stock():
    usa_stock = []
    query = Usa_stock.objects().all()
    for item in query:
        usa_stock.append(item.short)
    return usa_stock


def ago(t):
    """
        Calculate a '3 hours ago' type string from a python datetime.
    """
    units = {
        'days': lambda diff: diff.days,
        'hours': lambda diff: diff.seconds / 3600,
        'minutes': lambda diff: diff.seconds % 3600 / 60,
    }
    diff = datetime.datetime.now() - t
    for unit in units:
        dur = units[unit](diff)  # Run the lambda function to get a duration
        if dur >= 1:
            # De-pluralize if duration is 1 ('1 day' vs '2 days')
            unit = unit[:-dur] if dur == 1 else unit
            return '%s %s ago' % (math.floor(dur), unit)
    return 'just now'


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
@app.route("/index/<search>", methods=["GET", "POST"])
def index(search=""):
    # Get stock news
    num_news = 2
    stocks = rand_news(num_news)
    all_stocks = all_stock()
    tickers = yf.Tickers(" ".join(stocks))
    info = {}
    news = {}
    for stock in stocks:
        info[stock] = tickers.tickers[stock].info
        # print(f"info : {info[stock]}")
        new = tickers.tickers[stock].news
        # print(f"news:{new}")
        news[stock] = new[random.randint(0, math.floor((len(new)-1)/2))]
        news[stock] = tickers.tickers[stock].news
        # lastHourDateTime = datetime.datetime.now() - datetime.datetime.fromtimestamp(news[stock][0]['providerPublishTime'])
        news[stock][0]['providerPublishTime'] = ago(
            datetime.datetime.fromtimestamp(news[stock][0]['providerPublishTime']))
        if info[stock]['regularMarketChangePercent'] > 0:
            info[stock]['regularMarketChangePercentText'] = f"+{info[stock]['regularMarketChangePercent']:.2f}%"
        else:
            info[stock]['regularMarketChangePercentText'] = f"{info[stock]['regularMarketChangePercent']:.2f}%"
        try:
            news[stock][0]['url'] = news[stock][0]['thumbnail']['resolutions'][0]['url']
        except:
            news[stock][0]['url'] = ""
        # print(news[stock])
        # print(len(news[stock]))
    # print(info)
    # print(news)

    if request.form.get("search"):
        search = request.form.get("search")
    if search:
        regex = re.compile(fr".*{search}.*", re.IGNORECASE)
        # print(regex)
        quotes = list(Usa_stock.objects.aggregate([
            {'$sort': {'short': 1}},
            {'$match': {'short': regex}},
            {'$group': {'_id': '$short',
                        'short': {'$addToSet': "$short"},
                        'name': {'$addToSet': "$name"},
                        }},
            {'$unwind': "$short"},
            {'$unwind': "$name"},
            {'$limit': 3},
        ]))
    else:
        search = ""
        quotes = None
    return render_template("index.html", title="Home Page", all_stocks=all_stocks, stocks=stocks, info=info, news=news, quotes=quotes)


def human_format(num):
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])


@app.route("/quote/<name>", methods=["GET"])
@app.route("/quote/<name>/<period>", methods=["GET"])
def quote(name, period="1mo"):
    m = {'K': 3, 'M': 6, 'B': 9, 'T': 12}
    # print(period)
    periods = {
                # "1d": "1D",
               "5d": "5D",
               "1mo": "1M",
               "6mo": "6M",
               "ytd": "YTD",
               "1y": "1Y",
            #    "5y": "5Y",
            #    "max": "Max"
               }
    
    intervals = {
                # "1d": "1m",
                 "5d": "1d",  # 15m
                 "1mo": "1d",
                 "6mo": "1d",
                 "ytd": "1d",
                 "1y": "1d",
                #  "5y": "1wk",
                #  "max": "3mo"
                 }
    ticker = yf.Ticker(name)
    # print(ticker.shares)
    tick = ticker.info
    # print(tick)
    tick['regularMarketPrice'] = f"{tick['regularMarketPrice']:.2f}"

    if tick['regularMarketChange'] >= 0:
        color = "success"
        tick['regularMarketChange'] = f"+{tick['regularMarketChange']:.2f}"
        tick['regularMarketChangePercent'] = f"+{tick['regularMarketChangePercent']:.2f}"
    else:
        color = "danger"
        tick['regularMarketChange'] = f"{tick['regularMarketChange']:.2f}"
        tick['regularMarketChangePercent'] = f"{tick['regularMarketChangePercent']:.2f}"

    # print(tick['bidSize'])
    # print(tick['askSize'])
    tick['bid'] = f"{tick['bid']:.2f}"
    tick['ask'] = f"{tick['ask']:.2f}"
    tick['bidSize'] = f"{tick['bidSize'] * 100}"
    tick['askSize'] = f"{tick['askSize'] * 100}"

    regularMarketDayRange = tick['regularMarketDayRange'].split("-")
    tick['regularMarketDayRange'] = f"{float(regularMarketDayRange[0].strip()):.2f} - {float(regularMarketDayRange[1].strip()):.2f}"
    fiftyTwoWeekRange = tick['fiftyTwoWeekRange'].split("-")
    tick['fiftyTwoWeekRange'] = f"{float(fiftyTwoWeekRange[0].strip()):.2f} - {float(fiftyTwoWeekRange[1].strip()):.2f}"
    tick['regularMarketVolume'] = f"{tick['regularMarketVolume']:,}"
    tick['averageDailyVolume3Month'] = f"{tick['averageDailyVolume3Month']:,}"

    tick['regularMarketPreviousClose'] = f"{tick['regularMarketPreviousClose']:.2f}"
    tick['marketCap'] = f"{human_format(tick['marketCap'])}"
    try:
        tick['trailingPE'] = f"{tick['trailingPE']:.2f}"
    except:
        tick['trailingPE'] = "N/A"

    tick['trailingAnnualDividendYield'] = f"{tick['trailingAnnualDividendYield']*100:.2f}"

    if 'dividendDate' in tick:
        dividendDate = datetime.datetime.fromtimestamp(tick['dividendDate'])
        tick['dividendDate'] = dividendDate.strftime("%b %d, %Y")
    earningsTimestampStart = datetime.datetime.fromtimestamp(
        tick['earningsTimestampStart'])
    tick['earningsTimestampStart'] = earningsTimestampStart.strftime(
        "%b %d, %Y")
    earningsTimestampEnd = datetime.datetime.fromtimestamp(
        tick['earningsTimestampEnd'])
    tick['earningsTimestampEnd'] = earningsTimestampEnd.strftime("%b %d, %Y")


    news_setiment_stock = getnews(name)
    news_setiment_blank = getnews("", 3)

    length = 5
    predict_df, infer_df, _ = get_lstm(name)
    predict_df = predict_df.tail(length)
    predict_df = pd.concat([predict_df, infer_df], ignore_index=True).rename(columns={"Actual":"actual", "Date":"date", "Predicted":"predicted"})
    predict_df["actual_change"] = predict_df.actual.diff(1)
    predict_df["predicted_change"] = predict_df.predicted.diff(1)
    predict_df["actual_%change"] = predict_df.actual.pct_change(fill_method="bfill")
    predict_df["predicted_%change"] = predict_df.predicted.pct_change(fill_method="bfill")
    predict_df["date"] = pd.to_datetime(predict_df.date).dt.strftime('%d %b')
    predict_df = predict_df.fillna("")
    predict_dict = predict_df.to_dict(orient="records")
    day = 1
    for i, predict in enumerate(predict_dict):
        
        predict['predicted'] = f"{predict['predicted']:.2f}"
        if i >= length:
            if i == length:
                predicted_change = predict['predicted_change']
            predict['date'] = f"+{day}day"
            if day != 1:
                predict['date']  += "s"
            day += 1
        else:
            predict['date'] = predict['date'].replace(" ", "")
            predict['actual'] = f"{predict['actual']:.2f}"

    # for row in enumerate(news_setiment_blank):

    #     print(row['sentiment'][row['likely']])
    print (news_setiment_stock)
    if len(news_setiment_stock) > 0:
        if predicted_change > 0 and news_setiment_stock[0]['likely'] == 'positive':
            suggestion = "BUY signal "
            signal_color = "success"
            font_color = "light"
        elif predicted_change < 0 and news_setiment_stock[0]['likely'] == 'negative':
            suggestion = "SELL signal"
            signal_color = "danger"
            font_color = "dark"
        else:
            suggestion = "HOLD signal"
            signal_color = "warning"
            font_color = "dark"
    else:
        suggestion = "HOLD signal"
        signal_color = "warning"
        font_color = "dark"

    # news_setiment_stock
    # print(predict_dict)
    return render_template("quote.html", title=f"Quote - {tick['longName']} ({name})", name=name, tick=tick, color=color, intervals=intervals, periods=periods, period=period, news_setiment_stock=news_setiment_stock, news_setiment_blank=news_setiment_blank, predict_dict=predict_dict, suggestion=suggestion, signal_color=signal_color, font_color=font_color)

def getnews(name, max=None):
    
    news_extract_server = os.getenv("NEWS_EXTRACT_SERVER")
    news_extract_request = requests.get(f"http://{news_extract_server}/getnews/{name}")
    news_extract_string = json.loads(news_extract_request.text)
    result_string = None
    result_array = []
    result_dict = {}
    pick_list = None
    if max is not None:
        pick_list = [random.randint(0, len(news_extract_string)) for i in range(max)]
    # print(f"pick list {pick_list}")
    if news_extract_string is not None:
        for c, news in enumerate(news_extract_string):
            if pick_list is not None:
                if c not in pick_list:
                    continue
            result_dict = news_extract_string[c]
            ag = ago(datetime.datetime.strptime(news['date'], '%m-%d-%Y'))
            result_dict['date'] = ag
            likely_key = ""
            likely_val = -1
            for key, val in news['sentiment'].items():
                
                if float(val) > likely_val:
                    likely_key = key
                    likely_val = val
                result_dict['sentiment'][key] = f"{val*100:.2f}%"
            result_dict['likely'] = likely_key
            result_dict['link'] = f"https://www.google.com/search?q={news['headline']}"
            result_array.append(result_dict)
            result_dict = {}
        result_string = result_array
        # print(result_string)
    return result_string


@app.route('/callback/<endpoint>')
def cb(endpoint):
    if endpoint == "getStock":
        return gm(request.args.get('data'), request.args.get('period'), request.args.get('interval'), request.args.get('color'))
    elif endpoint == "getInfo":
        stock = request.args.get('data')
        st = yf.Ticker(stock)
        return json.dumps(st.info)
    else:
        return "Bad endpoint", 400

def get_lstm(stock):
    # Retrieve API
    # Getting inferencial data
    lstm_server = os.getenv("LSTM_SERVER")
    # lstm_url =  f"http://{lstm_server}/inference/{stock}"
    # print(lstm_url)
    infer_request = requests.get(f"http://{lstm_server}/inference/{stock}")
    infer_string = json.loads(infer_request.text)
    new_datapoint = []
    td = datetime.date.today()
    infer_dict = {}
    infer_array = []
    i = 0
    for key, val in infer_string.items():
        infer_dict['Date'] = td
        infer_dict['Predicted'] = val
        infer_array.append(infer_dict)
        infer_dict = {}
        if i != 0:
            new_datapoint.append(td)

        td = td+datetime.timedelta(days=1)
        while td.weekday() in [5, 6]:
            td = td+datetime.timedelta(days=1)
        i += 1

    infer_df = pd.DataFrame(infer_array)

    # Getting historical data
    request = requests.get(f"http://{lstm_server}/lstm_data_view/{stock}")
    # js_string = json.loads(request.text)
    # print(request.text)
    # Use pandas.DataFrame.from_dict() to Convert JSON to DataFrame
    predict_df = pd.read_json(request.text, orient='index')
    predict_df.columns = ["Actual", "Date", "Predicted"]
    predict_df.Date = predict_df.Date.dt.date

    return predict_df, infer_df, new_datapoint

# Return the JSON data for the Plotly graph
def gm(stock, period, interval, color):
    st = yf.Ticker(stock)
    # print(period)
    # print(interval)

    predict_df, infer_df, new_datapoint = get_lstm(stock)
    # print(infer_df)
    # Mix historical and inferencial data
    predict_df = pd.concat([predict_df, infer_df], ignore_index=True)

    # Create a line graph
    df = st.history(period=(period), interval=interval)
    df = df.reset_index()
    df.columns = ['Date-Time']+list(df.columns[1:])
    df["Date"] = df["Date-Time"].dt.date

    # Prepare inferrencial data points
    df = pd.concat([df, pd.DataFrame(new_datapoint, columns=['Date'])])
    df = df.reset_index().drop(columns=["index"])

    # Fill future na date
    df_date = pd.to_datetime(df['Date'])
    df_date = df_date.dt.tz_localize('US/Eastern').dt.tz_convert('US/Eastern')
    df['Date-Time'].fillna(df_date, inplace = True)

    # Merge requested API
    df = pd.merge(df, predict_df, how="left", on="Date")

    # print(df)

    max_open = (df['Close'].max() if df['Close'].max() > df['Predicted'].max() else df['Predicted'].max())
    min_open = (df['Close'].min() if df['Close'].min() < df['Predicted'].min() else df['Predicted'].min())
    range_open = max_open - min_open
    # margin_open = range_open * 0.05
    margin_open = range_open * 0.4
    # margin_open = range_open
    max_open = max_open + margin_open
    min_open = min_open - margin_open

    max_vol = (df['Volume'].max())
    min_vol = (df['Volume'].min())

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # Add traces
    # color='#007560'
    if color == "success":
        color = "#007560"
    elif color == "danger":
        color = "#bd1414"

    fig.add_trace(
        go.Scatter(x=df['Date-Time'], y=df["Close"],
                   fill='tozeroy', name="Close",
                   fillpattern_fillmode="overlay",
                   mode='lines',
                   line=dict(width=0.5, color=color),
                   fillcolor=color,
                   ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(x=df['Date-Time'], y=df["Predicted"],
                   fill='tozeroy', name="Predicted",
                   fillpattern_fillmode="overlay",
                   mode='lines',
                   line=dict(width=0.5, color="blue"),
                   ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(x=df['Date-Time'], y=df["Volume"], name="Volume",
               # marker_line_color='#007560',
               # marker_line_width=0.5, opacity=0.6),
               marker=dict(
            line_color=color,
            line_width=0.5,
            color='white',
            opacity=0.5
        )
        ),
        secondary_y=True,
    )

    fig.update_layout(
        showlegend=True,
        margin=dict(l=10, r=0, t=10, b=10),
    )
    # fig.update_layout(legend=dict(
    # yanchor="top",
    # y=0.99,
    # xanchor="left",
    # x=0.01
    # ))
    fig.update_layout(dict(yaxis2={'anchor': 'x', 'overlaying': 'y', 'side': 'left'},
                           yaxis={'anchor': 'x', 'domain': [0.0, 1.0], 'side': 'right'}))
    

    # Set x-axis title
    # print(df['Date-Time'].iloc[1])
    # print(df['Date-Time'].iloc[-1])
    fig.update_xaxes(fixedrange=True)
    if period in ["1mo"]:
        fig.update_xaxes(
            rangebreaks=[
                # NOTE: Below values are bound (not single values), ie. hide x to y
                # hide weekends, eg. hide sat to before mon
                dict(bounds=["sat", "mon"]),
                # dict(bounds=[15.5, 9.5], pattern="hour"),
                # hide hours outside of 9.30am-4pm
                
                # dict(values=["2020-12-25", "2021-01-01"])  # hide holidays (Christmas and New Year's, etc)
            ]
        )
    if period in ["1d", "5d"]:
        fig.update_xaxes(
            rangebreaks=[
                # NOTE: Below values are bound (not single values), ie. hide x to y
                # hide weekends, eg. hide sat to before mon
                dict(bounds=["sat", "mon"]),
                # dict(bounds=[16, 9.5], pattern="hour"),
                # hide hours outside of 9.30am-4pm
               
                # dict(values=["2020-12-25", "2021-01-01"])  # hide holidays (Christmas and New Year's, etc)
            ]
        )
    if period in ["6mo", "ytd", "1y", "5y"]:
        fig.update_xaxes(
            rangebreaks=[
                # NOTE: Below values are bound (not single values), ie. hide x to y
                # hide weekends, eg. hide sat to before mon
                dict(bounds=["sat", "mon"]),
                # dict(bounds=[16, 9.5], pattern="hour"),  # hide hours outside of 9.30am-4pm
                # dict(values=["2020-12-25", "2021-01-01"])  # hide holidays (Christmas and New Year's, etc)
            ]
        )
    # tick0 set to first time in index
    # dtick work out number of milliseconds between first and second times in index
    # reversed appears your code was trying to do this
    # tickformat only want hours & minutes

    # Set y-axes titles
    if period == "max":
        min_open = 0
        min_vol = 0

    fig.update_yaxes(
        # title_text="<b>primary</b> yaxis title",
        fixedrange=True,
        range=[min_open, max_open],
        side="right",
        # rangemode='tozero',
        # scaleanchor='y',
        secondary_y=False
    )

    # print(min_vol)

    fig.update_yaxes(
        # title_text="<b>secondary</b> yaxis title",
        # fixedrange=True,
        range=[min_vol, max_vol*2],
        showticklabels=False,
        side="left",
        # rangemode='tozero',
        # scaleanchor='y2',
        secondary_y=True
    )

    # Create a JSON representation of the graph
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON
