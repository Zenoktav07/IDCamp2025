import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import json
import requests

url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
brazil_geo = requests.get(url).json()

sns.set_theme(style="darkgrid")
plt.rcParams['figure.facecolor'] = 'none'
plt.rcParams['axes.facecolor'] = 'none'

plt.rcParams.update({
    "text.color": "white",
    "axes.labelcolor": "white",
    "xtick.color": "white",
    "ytick.color": "white"
})

#
st.set_page_config(
    page_title="E-Commerce Sales Dashboard",
    layout="wide"
)

#
st.title("E-Commerce Sales Dashboard")

#
@st.cache_data
def load_data():
    df = pd.read_csv("dashboard/main_data.csv")
    df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
    return df

main_data = load_data()

#
st.sidebar.header("Filter Data")

selected_year = st.sidebar.multiselect(
    "Pilih Tahun",
    options=sorted(main_data['year'].unique()),
    default=sorted(main_data['year'].unique())
)

month_dict = {
    1:"Jan", 2:"Feb", 3:"Mar", 4:"Apr",
    5:"May", 6:"Jun", 7:"Jul", 8:"Aug",
    9:"Sep", 10:"Oct", 11:"Nov", 12:"Dec"
}

main_data['month_name'] = main_data['month'].map(month_dict)

selected_month = st.sidebar.multiselect(
    "Pilih Bulan",
    options=sorted(main_data['month_name'].unique()),
    default=sorted(main_data['month_name'].unique())
)

selected_state = st.sidebar.multiselect(
    "Pilih State",
    options=sorted(main_data['customer_state'].unique()),
    default=sorted(main_data['customer_state'].unique())
)

filtered_data = main_data[
    (main_data['year'].isin(selected_year)) &
    (main_data['month_name'].isin(selected_month)) &
    (main_data['customer_state'].isin(selected_state))
]

#
total_revenue = filtered_data['total_order_value'].sum()
total_orders = filtered_data['order_id'].nunique()
total_customers = filtered_data['customer_id'].nunique()
avg_order_value = filtered_data['total_order_value'].mean()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Revenue", f"${total_revenue:,.0f}")
col2.metric("Total Orders", total_orders)
col3.metric("Total Customers", total_customers)
col4.metric("Avg Order Value", f"${avg_order_value:,.2f}")

#
monthly_revenue = (
    filtered_data
    .groupby(pd.Grouper(key='order_purchase_timestamp', freq='M'))
    ['total_order_value']
    .sum()
)

st.line_chart(monthly_revenue)

#
snapshot_date = filtered_data['order_purchase_timestamp'].max() + pd.Timedelta(days=1)

rfm_df = filtered_data.groupby('customer_id').agg({
    'order_purchase_timestamp': 'max',
    'order_id': 'nunique',
    'total_order_value': 'sum'
}).reset_index()

rfm_df.columns = ['customer_id','max_date','frequency','monetary']

rfm_df['recency'] = (snapshot_date - rfm_df['max_date']).dt.days
rfm_df.drop('max_date', axis=1, inplace=True)

#
rfm_df['R_score'] = pd.qcut(rfm_df['recency'], 5, labels=[5,4,3,2,1])
rfm_df['F_score'] = pd.qcut(rfm_df['frequency'].rank(method='first'), 5, labels=[1,2,3,4,5])
rfm_df['M_score'] = pd.qcut(rfm_df['monetary'], 5, labels=[1,2,3,4,5])

rfm_df['RFM_score'] = (
    rfm_df['R_score'].astype(int) +
    rfm_df['F_score'].astype(int) +
    rfm_df['M_score'].astype(int)
)

#
if len(rfm_df) >= 5:

    rfm_df['R_score'] = pd.qcut(rfm_df['recency'], 5, labels=[5,4,3,2,1])
    rfm_df['F_score'] = pd.qcut(rfm_df['frequency'].rank(method='first'), 5, labels=[1,2,3,4,5])
    rfm_df['M_score'] = pd.qcut(rfm_df['monetary'], 5, labels=[1,2,3,4,5])

    rfm_df['RFM_score'] = (
        rfm_df['R_score'].astype(int) +
        rfm_df['F_score'].astype(int) +
        rfm_df['M_score'].astype(int)
    )

#
def segment_customer(score):
    if score >= 10:
        return "Champions"
    elif score >= 8:
        return "Loyal Customers"
    elif score >= 6:
        return "Potential Loyalist"
    else:
        return "At Risk"

rfm_df['segment'] = rfm_df['RFM_score'].apply(segment_customer)

#
col1, col2 = st.columns(2)

with col1:
    segment_summary = rfm_df['segment'].value_counts()

    st.subheader("Customer Segmentation")

    fig, ax = plt.subplots(figsize=(6,6))

    colors = sns.color_palette("viridis", len(segment_summary))

    wedges, texts, autotexts = ax.pie(
        segment_summary.values,
        labels=segment_summary.index,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors,
        wedgeprops={'edgecolor': 'none'}
    )

    for text in texts:
        text.set_color("white")

    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_weight("bold")

    ax.set_facecolor("none")
    fig.patch.set_alpha(0)

    st.pyplot(fig)
 
with col2:
    state_revenue = (
        filtered_data
        .groupby('customer_state')['total_order_value']
        .sum()
        .sort_values(ascending=False)
    )

    state_df = state_revenue.reset_index()
    state_df.columns = ["state", "revenue"]

    state_df["contribution_%"] = (
        state_df["revenue"] / state_df["revenue"].sum() * 100
    )

    top_state = state_df.head(10)


    st.subheader("Kontribusi Revenue per State (Top 10)")

    fig, ax = plt.subplots(figsize=(10,7))

    bars = ax.barh(top_state["state"], top_state["contribution_%"])

    ax.grid(False)
    ax.set_xlabel("Contribution (%)")

    for bar in bars:
        width = bar.get_width()
        ax.text(width,
                bar.get_y() + bar.get_height()/2,
                f'{width:.2f}%',
                va='center',
                color='white')

    ax.invert_yaxis()
    ax.set_facecolor("none")
    fig.patch.set_alpha(0)

    st.pyplot(fig)

#
st.subheader("Top 10 Customer berdasarkan Total Transaksi")

top_customer = (
    rfm_df.sort_values("monetary", ascending=False)
    .head(10)
)

fig, ax = plt.subplots(figsize=(10,5))
bars = ax.bar(top_customer["customer_id"], top_customer["monetary"])

ax.grid(False)
ax.set_xticklabels(top_customer["customer_id"], rotation=90)
ax.set_ylabel("Total Transaksi")

for bar in bars:
    yval = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2,
            yval,
            f'{yval:,.0f}',
            ha='center',
            va='bottom',
            color='white')

ax.set_facecolor("none")
fig.patch.set_alpha(0)

st.pyplot(fig)

#
state_revenue_map = (
    filtered_data
    .groupby("customer_state")["total_order_value"]
    .sum()
    .reset_index()
)

#
st.subheader("Revenue Distribution Map")

fig = px.choropleth(
    state_revenue_map,
    geojson=brazil_geo,
    locations="customer_state",
    featureidkey="properties.sigla",
    color="total_order_value",
    color_continuous_scale="Viridis",
    projection="mercator",
)

fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(
    margin={"r":0,"t":0,"l":0,"b":0},
)

st.plotly_chart(fig, use_container_width=True)
