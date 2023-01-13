import time
import streamlit as st
import pandas as pd
import base64
import pymongo
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import calendar

st.set_page_config(
    page_title="Dash board App",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "# This is a header. This is an *extremely* cool app!"
    }
)

with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def add_bg_from_local(image_file):
    with open(image_file, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    st.markdown(
    f"""
    <style>
    [data-testid="stSidebar"]  {{
        background-image: url(data:image/{"png"};base64,{encoded_string.decode()});
        background-size: 250px;
        background-repeat: no-repeat;
        background-position: 4px 20px;
    }}
    </style>
    """,
    unsafe_allow_html=True
    )
add_bg_from_local('CollegeAhuntsic_Logo.png')

#st.sidebar.header('Dashboard `Version 2`')

client = pymongo.MongoClient("localhost")
#client = pymongo.MongoClient("mongodb+srv://toucanfortune:rouedefortune@toucanfortune.gzo0glz.mongodb.net/?retryWrites=true&writeConcern=majority")
db = client.toucan
collection = db.energydata_complete

df = pd.DataFrame(list(collection.find()))
df = df.drop(['_id'], axis=1)
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d %H:%M:%S')
df = df.set_index('date')

# # Outliers removal
df = df.dropna()
df = df.drop(df[(df.Appliances > 790) | (df.Appliances <0)].index)

# Append more columns to the dataframe based on datetime
df['month'] = df.index.month
df['weekday'] = df.index.weekday
df['hour'] = df.index.hour
df['week'] = df.index.week

# 数据右偏，在做线性回归的时候假设数据正态分布，一般用log函数校正
df['log_appliances'] = np.log(df.Appliances)


# Average house temperature and humidity
df['house_temp'] =df.T1
df['house_hum'] =df.RH_1

# Products of several features to remove additive assumption(An Introducton to Statistical learning p. 87,88)
df['hour*light']= df.hour * df.lights


# Calculate average energy load per weekday and hour
def code_mean(data, cat_feature, real_feature):
    """
    Returns a dictionary where keys are unique categories of the cat_feature,
    and values are means over real_feature
    """
    return dict(data.groupby(cat_feature)[real_feature].mean())

# Average energy consumption per weekday and hour
df['weekday_avg'] = list(map(
    code_mean(df[:], 'weekday', "Appliances").get, df.weekday))
df['hour_avg'] = list(map(
    code_mean(df[:], 'hour', "Appliances").get, df.hour))
df_hour = df.resample('1H').mean()
df_30min =df.resample('30min').mean()


df['low_consum'] = (df.Appliances+25<(df.hour_avg))*1
df['high_consum'] = (df.Appliances+100>(df.hour_avg))*1

df_hour['low_consum'] = (df_hour.Appliances+25<(df_hour.hour_avg))*1
df_hour['high_consum'] = (df_hour.Appliances+25>(df_hour.hour_avg))*1

df_30min['low_consum'] = (df_30min.Appliances+25<(df_30min.hour_avg))*1
df_30min['high_consum'] = (df_30min.Appliances+35>(df_30min.hour_avg))*1

figure = plt.figure(figsize=(16,6))
plt.plot(df_hour.Appliances)
plt.xticks(rotation=45)
plt.xlabel('Date')
plt.ylabel('Appliances consumption in Wh')
st.header('Appliances consumption')
st.pyplot(figure)

# Functions to be used from the plots

def daily(x,df=df):
    return df.groupby('weekday')[x].mean()
def hourly(x,df=df):
    return df.groupby('hour')[x].mean()

def monthly_daily(x,df=df):
    by_day = df.pivot_table(index='weekday',
                            columns=['month'],
                            values=x,
                            aggfunc='mean')
    return round(by_day, ndigits=2)

figure2 = plt.figure()
# plt.bar(df.index, daily('appliances'))
daily('Appliances').plot(kind = 'bar', figsize=(10,8))
ticks = list(range(0, 7, 1))
labels = "Mon Tues Weds Thurs Fri Sat Sun".split()
plt.xlabel('Day')
plt.ylabel('Appliances consumption in Wh')
plt.xticks(ticks, labels)
st.header('Mean Energy Consumption per Day of Week')
st.pyplot(figure2)

figure3 = plt.figure()
hourly('Appliances').plot()
plt.xlabel('Hour')
plt.ylabel('Appliances consumption in Wh')
ticks = list(range(0, 24, 1))
plt.xticks(ticks)
st.header('Mean Energy Consumption per Hour of a Day')
st.pyplot(figure3)

figure4 = plt.figure()

y_label = [calendar.month_name[i] for i in pd.unique(df.index.month)]

ax=sns.heatmap(monthly_daily('Appliances').T,cmap="YlGnBu",
               xticklabels="Mon Tues Weds Thurs Fri Sat Sun".split(),
               # yticklabels="January February March April May".split(),
                yticklabels=y_label,
               annot=True, fmt='g')
st.header('Mean consumption per Weekday of Month')
st.pyplot(figure4)

f, axes = plt.subplots(1, 2,)

sns.distplot(df_hour.Appliances, hist=True, color = 'blue',hist_kws={'edgecolor':'black'},ax=axes[0])
axes[0].set_title("Appliance's consumption")
axes[0].set_xlabel('Appliances wH')

sns.distplot(df_hour.log_appliances, hist=True, color = 'blue',hist_kws={'edgecolor':'black'},ax=axes[1])
axes[1].set_title("Log Appliance's consumption")
axes[1].set_xlabel('Appliances log(wH)')

st.header("Histogram of Appliance's consumption")
st.pyplot(f)

# Pearson Correlation among the variables
col = ['log_appliances', 'lights', 'T1', 'RH_1', 'T_out', 'Press_mm_hg', 'RH_out', 'Windspeed', 'Visibility', 'Tdewpoint','hour']
corr = df[col].corr()
figure5 = plt.figure()
sns.set(font_scale=1)
sns.heatmap(corr, cbar = True, annot=True, square = True, fmt = '.2f', xticklabels=col, yticklabels=col)
st.header("Pearson Correlation among the variables")
st.pyplot(figure5)

