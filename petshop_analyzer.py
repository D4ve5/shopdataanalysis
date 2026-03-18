
# petshop_analyzer.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from io import StringIO, BytesIO
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title='Pet Shop Inventory Analyzer', layout='wide')


def main():
    st.title('🐶 Pet Shop Inventory & Expiry Analyzer')
    st.markdown('Upload your **Square CSV** (Item Sales Summary) or **paste data** to get trends, seasonality, and expiry alerts.')

    # Option 1: Upload CSV
    uploaded_file = st.file_uploader('Upload Square CSV (e.g., exports from Reports → Item Sales Summary)', type=['csv'])

    # Option 2: Paste data (for Excel / copy‑paste)
    paste_data = st.text_area('Or paste CSV data here (from Excel, columns Date, Item Name, Quantity Sold, Gross Sales, Cost, Expiry_Date):')

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file, encoding='utf-8')
    elif paste_data and paste_data.strip():
        df = pd.read_csv(StringIO(paste_data), encoding='utf-8')
    else:
        st.info('Upload a CSV file or paste data to continue.')
        return

    # Required columns (what Square exports)
    required_cols = ['Date', 'Item Name', 'Quantity Sold', 'Gross Sales']
    if not all(c in df.columns for c in required_cols):
        st.error(f"Columns needed: {', '.join(required_cols)}. Add column 'Cost' and 'Expiry_Date' (YYYY-MM-DD) for extra analysis if you can.")
        st.dataframe(df.head())
        return

    # Clean and rename
    df['Date'] = pd.to_datetime(df['Date'])
    df['Cost'] = df.get('Cost', 0)
    df['Cost'] = pd.to_numeric(df['Cost'], errors='coerce').fillna(0)
    df['Profit'] = df['Gross Sales'] - df['Cost']
    df['Margin %'] = ((df['Profit'] / df['Gross Sales']) * 100).round(1)
    df = df.rename(columns={'Item Name': 'Item'})

    # Expiry (optional but useful)
    expiring = pd.DataFrame()
    if 'Expiry_Date' in df.columns:
        df['Expiry_Date'] = pd.to_datetime(df['Expiry_Date'], errors='coerce')
        df['Days_To_Expire'] = (df['Expiry_Date'] - datetime.now()).dt.days
        expiring = df[df['Days_To_Expire'] < 30].copy()

    # Monthly trends and seasonality
    df['YearMonth'] = df['Date'].dt.to_period('M')
    monthly = df.groupby(['YearMonth', 'Item']).agg({
        'Quantity Sold': 'sum',
        'Gross Sales': 'sum',
        'Profit': 'sum',
        'Margin %': 'mean'
    }).round(2).reset_index()

    df['Quarter'] = df['Date'].dt.to_period('Q')
    quarterly = df.groupby('Quarter')['Gross Sales'].sum().round(2)

    # Summary section
    st.subheader('📊 Summary Report')
    st.write(f"Period: **{df['Date'].min().strftime('%Y-%m-%d')}** to **{df['Date'].max().strftime('%Y-%m-%d')}**")
    st.write(f"Total Revenue: **£{df['Gross Sales'].sum():,.2f}**")
    st.write(f"Total Profit: **£{df['Profit'].sum():,.2f}**")
    st.write(f"Average Margin: **{df['Margin %'].mean():.1f}%**")

    # Top 5 items
    st.subheader('📈 Top Items')
    top_items = monthly.nlargest(5, 'Gross Sales')[['Item', 'YearMonth', 'Gross Sales', 'Quantity Sold', 'Profit']]
    st.dataframe(top_items)

    # Expiry alerts (if column exists)
    if not expiring.empty:
        st.subheader('⚠️ Expiring Soon (<30 days)')
        st.dataframe(expiring[['Item', 'Days_To_Expire', 'Gross Sales', 'Quantity Sold']])
        st.warning('Consider discounting or moving these items quickly.')

    # Seasonality (quarterly)
    st.subheader('📉 Seasonality (Quarterly Revenue)')
    st.bar_chart(quarterly)

    # Download detailed CSV
    def df_to_csv(df):
        buffer = BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        return buffer.getvalue()

    csv = df_to_csv(monthly.reset_index(drop=True))
    st.download_button(
        label='💾 Download Detailed Report CSV',
        data=csv,
        file_name='pet_shop_analysis.csv',
        mime='text/csv'
    )

    # Charts
    st.subheader('🖼 Charts')
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Revenue trends by month
    monthly_pivot = monthly.pivot(index='YearMonth', columns='Item', values='Gross Sales').fillna(0)
    monthly_pivot.plot(ax=axes[0,0])
    axes[0,0].set_title('Revenue Trends by Month')
    axes[0,0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    axes[0,0].tick_params(axis='x', rotation=45)

    # 2. Revenue share by item
    perf = monthly.groupby('Item').agg({'Gross Sales': 'sum', 'Profit': 'sum'})
    perf.plot(kind='pie', y='Gross Sales', ax=axes[0,1], autopct='%1.1f%%', startangle=90)
    axes[0,1].set_title('Revenue Share by Item')

    # 3. Avg margin by item
    monthly.groupby('Item')['Margin %'].mean().plot(kind='bar', ax=axes[1,0])
    axes[1,0].set_title('Avg Margin by Item')
    axes[1,0].tick_params(axis='x', rotation=45)

    # 4. Quarterly revenue
    quarterly.plot(kind='bar', ax=axes[1,1])
    axes[1,1].set_title('Quarterly Revenue')

    plt.tight_layout()
    st.pyplot(fig)


if __name__ == '__main__':
    main()
