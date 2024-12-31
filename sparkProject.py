import streamlit as st
import pandas as pd
import yfinance as yf
import yahoo_fin.stock_info as si
from yahoo_fin.stock_info import get_data
import plotly.graph_objects as go
from datetime import timedelta, datetime
from io import StringIO

def dataEng(data):
    df = data
    df.reset_index(inplace=True)
    df.rename(columns={"index": "date"}, inplace=True)
    df["date"] = pd.to_datetime(df["date"])  # Type de données date
    df["ticker"] = df["ticker"].astype("string")
    df["variation"] = df["high"] - df["low"]
    df = df.dropna()
    return df

def sharpRatioLabel(ratio):
    if ratio<0:
        return "Bad"
    if ((ratio>0) & (ratio<1)):
        return "Not so bad"
    if ((ratio>=1) & (ratio<2)):
        return "Good"
    if (ratio >=2):
        return "Amazing"

def longTermScore(line):
    score=0
    if ((line["peRatio"]!=None) and (line["peRatio"]<20)): #PE ratio is how much investor pays to get a $ of benefice
        score+=3 #PE ratio is 1.5 more important than the revenue growth and the beta ratio -> PE ratio <20 -> company under-evaluated
    if ((line["revenueGrowth"]!=None)and(line["revenueGrowth"]>0.1)):
        score+=2 #ratio of revenue growth is how much % the revenues of the company grew -> 0.1=10% 
    if ((line["betaRatio"]!=None)and(line["betaRatio"]<1)):
        score+=2 #betaratio is the volability of comparated to the global market -> if < 1 then it's less volatible than the global market
    if ((line["averageVolume"]!=None)and(line["averageVolume"]>1000000)):
        score += 1 #We count the average volume of transaction as a criteria for long term investments -> meaning it's pretty active
    if ((line["latestClose"]!=None)and(line["SMA50"]!=None)and(line["SMA200"]!=None)and(line["latestClose"]>line["SMA200"])and(line["SMA50"]>line["SMA200"])):
        #checking if the actual price is higher than the moving average on 200 days, meaning it's actually going up, and checking if the
        #moving average on 50 days is higher than the moving average on 200 days, meaning it tends to price up
        score+=2
    return score

def shortTermScore(line):
    score=0
    if ((line["sharpReturn"]!=None)and(line["sharpReturn"]>1)):
        score+=3 #return adjusted to the risk -> we use it to see if the return is worth the risk ->> if it's >1 then the return is worth the risk
    if ((line["betaRatio"]!=None)and(line["betaRatio"]>1)):
        score+=2 #betaratio >1 so more volatible than the global market
    if ((line["vola"]!=None)and(line["vola"]>0.02)):
        score+=2 #high volability -> more likely to be good a short term investment -> volability is the "écart type" of the return (indicates if it's stable)
    if ((line["dailyVolume"]!=None)and(line["dailyVolume"]>line["averageVolume"])):
        score+=2 #if there is an un-normal recent activity then it's more likely to be a good short term investment
    if ((line["latestClose"]!=None)and(line["SMA50"]!=None)and(line["latestClose"]>line["SMA50"])): #latest close value > MA 50 days -> recent price up and activity
        score+=1
    return score

@st.cache_data
def initData():
    nas_aapl=get_data("aapl",start_date="11/30/2019",end_date="11/30/2024",index_as_date =False,interval="1d")

    nas_list=si.tickers_nasdaq()
    nasdaq_list=nas_list[0:30]

    dfday=pd.DataFrame()
    dfmin=pd.DataFrame()
    date7days=(datetime.today()-timedelta(days=7)).strftime("%Y-%m-%d")
    valid_nasdaq_list=[]

    for ticker in nasdaq_list:
        try:
            data_tickers_min=get_data(ticker,start_date=date7days,index_as_date=True,interval="1m")
            data_tickers_d= get_data(ticker,start_date="11/30/2014",index_as_date=True,interval="1d")
            if((data_tickers_min["close"].count()>100)and(data_tickers_d["close"].count()>100)): #we put this treshold to remove tickers with small amount of data
                dfmin=pd.concat([dfmin,data_tickers_min])
                dfday=pd.concat([dfday,data_tickers_d])
                valid_nasdaq_list.append(ticker)
            else:
                print(f"{ticker} removed")
        except:
            print(f"{ticker} not avalaible now")

    df_day=dataEng(dfday)
    df_min=dataEng(dfmin)

    df_day["return"]=df_day.groupby("ticker")["close"].pct_change()
    df_day["SMA50"]=df_day.groupby("ticker")["close"].transform(lambda x:x.rolling(window=50).mean()) #SMA (Simple Moving Average) for 50 days
    df_day["SMA200"]=df_day.groupby("ticker")["close"].transform(lambda x:x.rolling(window=200).mean()) #for 200 days

    sharpReturnDf=pd.DataFrame()
    sharpReturnDf["ticker"]=valid_nasdaq_list
    risk_free=0.02/252 #2%/per year cause there are 252 days of open stock market per year

    for ticker in valid_nasdaq_list:
        tick=yf.Ticker(ticker)
        info=tick.info
        
        peRatio=info.get("trailingPE")
        betaRatio=info.get("beta")
        revenueGrowth=info.get("revenueGrowth")
        dailyVolume=info.get("volume")
        averageVolume=info.get("averageVolume")
        
        dfreturn=df_day[df_day["ticker"]==ticker]
        returnR=dfreturn["return"].mean()
        vola=dfreturn["return"].std()

        latestClose=dfreturn["close"].iloc[-1]
        sma50=dfreturn["SMA50"].iloc[-1]if not dfreturn["SMA50"].isna().all() else None
        sma200=dfreturn["SMA200"].iloc[-1]if not dfreturn["SMA200"].isna().all() else None

        sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"latestClose"]=latestClose
        sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"SMA50"]=sma50
        sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"SMA200"]=sma200
        sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"sharpReturn"]=(returnR-risk_free)/vola
        sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"peRatio"]=peRatio
        sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"betaRatio"]=betaRatio
        sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"vola"]=vola
        sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"revenueGrowth"]=revenueGrowth
        sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"dailyVolume"]=dailyVolume
        sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"averageVolume"]=averageVolume

        sharpReturnDf["sharpRatioMeaning"]=sharpReturnDf["sharpReturn"].apply(sharpRatioLabel)
        sharpReturnDf["longTermScore"]=sharpReturnDf.apply(longTermScore,axis=1)
        sharpReturnDf["shortTermScore"]=sharpReturnDf.apply(shortTermScore,axis=1)

    return sharpReturnDf,df_min,df_day,valid_nasdaq_list,nas_aapl,nas_list

sharpReturnDf,df_min,df_day,valid_nasdaq_list,nas_aapl,nas_list=initData()

def recommandations(termTime):
    
    if(termTime=="Long Term"):
        sortDF=sharpReturnDf.sort_values(by=["longTermScore","sharpReturn"],ascending=[False,False])
        st.write("Best companies to invest in for long time term investment: ")
        st.dataframe(sortDF[["ticker", "longTermScore","sharpReturn"]])
    else:
        sortDF=sharpReturnDf.sort_values(by=["shortTermScore","sharpReturn"],ascending=[False,False])
        st.write("Best companies to invest in for short time term investment: ")
        st.dataframe(sortDF[["ticker","shortTermScore","sharpReturn"]])


def plotCloseEvol(ticker,periode):
    dateToday=datetime.today()

    if periode=="1 Day":
        yesterday=dateToday-timedelta(days=1)
        start_date=yesterday.replace(hour=0,minute=0,second=0,microsecond=0)
    elif periode=="1 Week":
        start_date=dateToday-timedelta(weeks=1)
    elif periode=="1 Month":
        start_date=dateToday-timedelta(weeks=4)
    elif periode=="6 Months":
        start_date=dateToday-timedelta(weeks=26)
    elif periode=="1 Year":
        start_date=dateToday-timedelta(weeks=52)
    elif periode=="5 Years":
        start_date=dateToday-timedelta(weeks=260)

    if (periode=="1 Day") or (periode=="1 Week"):
        filtered=df_min[(df_min["date"]>=start_date)&(df_min["ticker"]==ticker)]
    else:
        filtered=df_day[(df_day["date"]>=start_date)&(df_day["ticker"]==ticker)]
    
    filtered=filtered.sort_values(by="date")
    fig =go.Figure()
    fig.add_trace(go.Scatter(x=filtered["date"],y=filtered["close"],mode="lines",name=f"Close value ({ticker})"))
    fig.update_layout(title=f"Close values for {ticker} ({periode})",xaxis_title="Date",yaxis_title="Close value (in $)",template="plotly_white")
    st.plotly_chart(fig)

def informationsTicker(tick):
    infoTick=sharpReturnDf[sharpReturnDf["ticker"]==tick]
    st.dataframe(infoTick)

st.title("Investments advices page :")

st.write("To give some advices about investments, we are using the yahoo_fin and the yfinance libraries: ")
librairies="""
import yfinance
import yahoo_fin
"""
st.code(librairies,language="python")

st.write("Thanks to a function we can access to the data of a specific 'ticker'. A ticker is a company valued in a market place for example APPLE :")
data="""
nas_aapl=get_data("aapl",start_date="11/30/2019",end_date="11/30/2024",index_as_date =False,interval="1d")
"""
st.code(data,language="python")
st.write(nas_aapl.head(40))

st.write("We can check some infos about the data recolted :")
st.code("""print(nas_aapl.info())""",language="python")
buffer=StringIO()
nas_aapl.info(buf=buffer)
out=buffer.getvalue()
st.code(out,language="text")
st.code("""print(nas_aapl["close"].describe())""",language="python")
st.write(nas_aapl["close"].describe())

st.write("These data are transactions at a given time (we can chose that time from 1 minute to 3 months), we can see the date of the transaction, the open and close values (values at the start and the end of the time area), the highest and the lowest value, the volume of shares in these transactions, the name of the company (ticker) and the adjusted close value (close value with dividends depreciated).")
st.write("For this project we will only work on NASDAQ marketplace and we will limit the number of companies for computer capacity purposes :")
st.code("""
        nas_list=si.tickers_nasdaq()
        nasdaq_list=nas_list[0:30]
        """,language="python")
st.write("Tickers in Nasdaq:",len(nas_list))
st.write("Our list of tickers: ",nas_list[0:30])
st.write("We then create two dataframes that we fill with the data of all the tickers we just chose. One dataframe is filled with 1m interval transactions from the last week and the other is filled with 1 day interval transactions from the last 10 years. We do this to have more details about the last week's transactions.")
st.write("We also filter the tickers with an inferior amount of transactions than a treshold (we chose to put 100 transactions) so we are sure the companies are a bit actives :")
st.code("""
dfday=pd.DataFrame()
dfmin=pd.DataFrame()
dateToday=datetime.today().strftime("%Y-%m-%d")
date7days=(datetime.today()-timedelta(days=7)).strftime("%Y-%m-%d")
valid_nasdaq_list=[]

for ticker in nasdaq_list:
    try:
        data_tickers_min=get_data(ticker,start_date=date7days,index_as_date=True,interval="1m")
        data_tickers_d= get_data(ticker,start_date="11/30/2014",index_as_date=True,interval="1d")
        if((data_tickers_min["close"].count()>100)and(data_tickers_d["close"].count()>100)): #we put this treshold to remove tickers with small amount of data
            dfmin=pd.concat([dfmin,data_tickers_min])
            dfday=pd.concat([dfday,data_tickers_d])
            valid_nasdaq_list.append(ticker)
        else:
            print(f"{ticker} removed")
    except:
        print(f"{ticker} not avalaible now")
""",language="python")
st.write("Then, we change the type of some columns in order to be able to work with it properly. We also delete null values for each dataframe: ")
st.code("""
def dataEng(data):
df=data
df.reset_index(inplace=True)
df.rename(columns={"index":"date"}, inplace=True)
df["date"]=pd.to_datetime(df["date"]) #To put the right date type
df["ticker"]=df["ticker"].astype("string") #Was an object type and we put it as a String type
df=df.dropna()
return df

df_day=dataEng(dfday)
df_min=dataEng(dfmin)
""",language="python")
st.write("Finally, we calculated the return rate per day (difference between close value from the last day and the actual day) and the moving average on 50 and 200 days. Moving average are the average of close values on the given time (here 50 and 200 days): ")
st.code("""
df_day["return"]=df_day.groupby("ticker")["close"].pct_change()
df_day["SMA50"]=df_day.groupby("ticker")["close"].transform(lambda x:x.rolling(window=50).mean()) #SMA (Simple Moving Average) for 50 days
df_day["SMA200"]=df_day.groupby("ticker")["close"].transform(lambda x:x.rolling(window=200).mean()) #for 200 days
""",language="python")
st.write("Here is how looks like our dataframes :")
st.write(df_day.head(5))
st.write(df_min.head(5))
st.write("We can check if there are any missing value :")
st.write(df_min.isna().sum())

st.write("We can check what's the frequency for each ticker: ")
st.code("""for ticker in valid_nasdaq_list:
    counter=df_min[df_min["ticker"]==ticker]["ticker"].count()
    """,language="python")
for ticker in valid_nasdaq_list:
    counter=df_min[df_min["ticker"]==ticker]["ticker"].count()
    st.write(f"{ticker} : {counter}")

st.write("Now that we have those informations, we can now calculate some ratio that will help us for the investments advices :")
st.code("""
sharpReturnDf=pd.DataFrame()
sharpReturnDf["ticker"]=valid_nasdaq_list
risk_free=0.02/252 #2%/per year cause there are 252 days of open stock market per year

for ticker in valid_nasdaq_list:
    tick=yf.Ticker(ticker)
    info=tick.info
    
    peRatio=info.get("trailingPE")
    betaRatio=info.get("beta")
    revenueGrowth=info.get("revenueGrowth")
    dailyVolume=info.get("volume")
    averageVolume=info.get("averageVolume")
    
    dfreturn=df_day[df_day["ticker"]==ticker]
    returnR=dfreturn["return"].mean()
    vola=dfreturn["return"].std()

    latestClose=dfreturn["close"].iloc[-1]
    sma50=dfreturn["SMA50"].iloc[-1]if not dfreturn["SMA50"].isna().all() else None
    sma200=dfreturn["SMA200"].iloc[-1]if not dfreturn["SMA200"].isna().all() else None

    sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"latestClose"]=latestClose
    sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"SMA50"]=sma50
    sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"SMA200"]=sma200
    sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"sharpReturn"]=(returnR-risk_free)/vola
    sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"peRatio"]=peRatio
    sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"betaRatio"]=betaRatio
    sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"vola"]=vola
    sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"revenueGrowth"]=revenueGrowth
    sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"dailyVolume"]=dailyVolume
    sharpReturnDf.loc[sharpReturnDf["ticker"]==ticker,"averageVolume"]=averageVolume
""",language="python")
st.write("We chose to use ratio such as :")
st.write("-The sharp return ratio, which is the return adjusted to the risk. It is used to see if the risk is worth the return (the higher it is the worther it is too). A sharp return ratio superior to 1 means that it's worth.")
st.write("-The PE ratio (Price to Earnings ratio) which indicated the price investors are ready to pay for each unit (here $) generated by the company. This ratio is useful to know if investors trust a company and believe it will work (a PE ratio <20 might indicates a company is under-evaluated so it can be a good long term investment).")
st.write("-Volatibility indicator which is the standard deviation of the close value and indicates if the price is stable or not (the more it's far from 0 the less it's stable)")
st.write("-Beta ratio which is the volatibility compared to the market place, if the value is 1 then it's as volatible as the average.")
st.write("-Revenue Growth which is the percentage of how much the company's revenue grew.")
st.write("-Daily and average volume of transactions, which can indicates how much the company shares market is active.")
st.write("We are then using these metrics and ratios to calculate a short term and a long term score, which will help us chosing which company a short or long term investment will be adapted.")
st.write("We ponderate the score in fonction of the metrics and ratio. For example, a PE ratio inferior to 20 is 1.5 times more important than a beta ratio inferior to 1: ")
st.code("""
def sharpRatioLabel(ratio):
    if ratio<0:
        return "Bad"
    if ((ratio>0) & (ratio<1)):
        return "Not so bad"
    if ((ratio>=1) & (ratio<2)):
        return "Good"
    if (ratio >=2):
        return "Amazing"

def longTermScore(line):
    score=0
    if ((line["peRatio"]!=None) and (line["peRatio"]<20)): #PE ratio is how much investor pays to get a $ of benefice
        score+=3 #PE ratio is 1.5 more important than the revenue growth and the beta ratio -> PE ratio <20 -> company under-evaluated
    if ((line["revenueGrowth"]!=None)and(line["revenueGrowth"]>0.1)):
        score+=2 #ratio of revenue growth is how much % the revenues of the company grew -> 0.1=10% 
    if ((line["betaRatio"]!=None)and(line["betaRatio"]<1)):
        score+=2 #betaratio is the volability of comparated to the global market -> if < 1 then it's less volatible than the global market
    if ((line["averageVolume"]!=None)and(line["averageVolume"]>1000000)):
        score += 1 #We count the average volume of transaction as a criteria for long term investments -> meaning it's pretty active
    if ((line["latestClose"]!=None)and(line["SMA50"]!=None)and(line["SMA200"]!=None)and(line["latestClose"]>line["SMA200"])and(line["SMA50"]>line["SMA200"])):
        #checking if the actual price is higher than the moving average on 200 days, meaning it's actually going up, and checking if the
        #moving average on 50 days is higher than the moving average on 200 days, meaning it tends to price up
        score+=2
    return score

def shortTermScore(line):
    score=0
    if ((line["sharpReturn"]!=None)and(line["sharpReturn"]>1)):
        score+=3 #return adjusted to the risk -> we use it to see if the return is worth the risk ->> if it's >1 then the return is worth the risk
    if ((line["betaRatio"]!=None)and(line["betaRatio"]>1)):
        score+=2 #betaratio >1 so more volatible than the global market
    if ((line["vola"]!=None)and(line["vola"]>0.02)):
        score+=2 #high volability -> more likely to be good a short term investment -> volability is the "écart type" of the return (indicates if it's stable)
    if ((line["dailyVolume"]!=None)and(line["dailyVolume"]>line["averageVolume"])):
        score+=2 #if there is an un-normal recent activity then it's more likely to be a good short term investment
    if ((line["latestClose"]!=None)and(line["SMA50"]!=None)and(line["latestClose"]>line["SMA50"])): #latest close value > MA 50 days -> recent price up and activity
        score+=1
    return score

sharpReturnDf["sharpRatioMeaning"]=sharpReturnDf["sharpReturn"].apply(sharpRatioLabel)
sharpReturnDf["longTermScore"]=sharpReturnDf.apply(longTermScore,axis=1)
sharpReturnDf["shortTermScore"]=sharpReturnDf.apply(shortTermScore,axis=1)
""",language="python")

st.dataframe(sharpReturnDf)
st.write("Now, chose what time term you want to invest in (short term investments are often more risky but have a better return than long term that are safer): ")

termTime=st.selectbox("Chose your time term :",["Long Term","Short Term"])
recommandations(termTime)

st.write("If you want to check all the metrics and ratio about a specific ticker you can check it there: ")

tickChoice=st.selectbox("Chose a ticker you want informations about: ",valid_nasdaq_list)
informationsTicker(tickChoice)

st.write("Finally, to have some additionnal informations about a ticker you are interested in, you can check the variation of it's value here over a time area you can change. You can also see the return rate on the given time area :")

ticker=st.selectbox("Chose a ticker :",valid_nasdaq_list)
periode=st.selectbox("Chose the time range :",["1 Day","1 Week","1 Month","6 Months","1 Year","5 Years"])

plotCloseEvol(ticker,periode)