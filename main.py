import streamlit as st 
import requests
import time
import smtplib
from email.mime.text import MIMEText
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="Crypto Tracker Pro",
    page_icon="📈",
    layout="wide"
)

# ========== CONFIGURATION ==========
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
REFRESH_INTERVAL = 120  # seconds

# Email configuration
EMAIL_SENDER = "****************************"  #=====security problems=====
EMAIL_PASSWORD = os.getenv( "***************************")
SMTP_SERVER = "smtp.mailersend.net"
SMTP_PORT = 587

# ========== CUSTOM CSS ==========
st.markdown("""
<style>
/* Hover effect for price cards */
.element-container:has(> .stMarkdown) div[data-testid="stMarkdownContainer"] {
  transition: all 0.3s ease;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 12px;
}

.element-container:has(> .stMarkdown):hover div[data-testid="stMarkdownContainer"] {
  border: 1px solid #000000;
  background-color: #f9f9f9;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

body, .main, .stApp {
  background-color: #ffffff;
  color: #000000;
}
</style>
""", unsafe_allow_html=True)

# ========== INITIALIZE SESSION STATE ==========
if 'alerts' not in st.session_state:
    st.session_state.alerts = []
if 'alert_log' not in st.session_state:
    st.session_state.alert_log = []
if 'currency' not in st.session_state:
    st.session_state.currency = 'inr'
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

# ========== HELPER FUNCTIONS ==========
def fetch_crypto_prices(coin_ids, currency='inr'):
    try:
        params = {
            'ids': ','.join(coin_ids),
            'vs_currencies': currency,
            'include_market_cap': 'true',
            'include_24hr_vol': 'true',
            'include_24hr_change': 'true'
        }
        response = requests.get(f"{COINGECKO_API_URL}/simple/price", params=params)
        response.raise_for_status()
        st.session_state.last_update = datetime.now()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching prices: {str(e)}")
        return None

def fetch_historical_data(coin_id, currency='inr', days=30):
    try:
        params = {
            'vs_currency': currency,
            'days': days
        }
        response = requests.get(f"{COINGECKO_API_URL}/coins/{coin_id}/market_chart", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching historical data: {e}")
        return None

def send_email_alert(receiver_email, subject, body):
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = "alerts@test-z0vklo60q5el7qrx.mlsender.net"
        msg['To'] = receiver_email

        with smtplib.SMTP("smtp.mailersend.net", 587) as server:
            server.starttls()
            server.login("MS_mszIzr@test-z0vklo60q5el7qrx.mlsender.net", "mssp.DqgnmO6.3z0vklo53ep47qrx.BTRgbe0")
            server.sendmail(msg['From'], [receiver_email], msg.as_string())

        log_entry = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'coin': subject.split()[0],
            'price': subject.split()[-1],
            'email': receiver_email,
            'currency': st.session_state.currency.upper()
        }
        st.session_state.alert_log.append(log_entry)

    except Exception as e:
        st.error(f"Failed to send email: {e}")

def check_alerts(prices):
    currency = st.session_state.currency
    symbol = '₹' if currency == 'inr' else '$'

    for alert in st.session_state.alerts[:]:
        coin_id, threshold, email, above = alert
        current_price = prices.get(coin_id, {}).get(currency, 0)

        if current_price:
            if above and current_price >= threshold:
                subject = f"{coin_id} price above {symbol}{threshold}"
                body = f"The price of {coin_id} is now {symbol}{current_price:,.2f}, which is above your alert threshold of {symbol}{threshold}."
                send_email_alert(email, subject, body)
                st.session_state.alerts.remove(alert)
            elif not above and current_price <= threshold:
                subject = f"{coin_id} price below {symbol}{threshold}"
                body = f"The price of {coin_id} is now {symbol}{current_price:,.2f}, which is below your alert threshold of {symbol}{threshold}."
                send_email_alert(email, subject, body)
                st.session_state.alerts.remove(alert)

def display_price_card(coin, data, currency):
    symbol = '₹' if currency == 'inr' else '$'
    change = data[f'{currency}_24h_change']
    change_color = 'green' if change >= 0 else 'red'

    st.markdown(f"""
    ### {coin.capitalize()}  
    **Price**: {symbol}{data[currency]:,.2f}  
    **24h Change**: :{change_color}[{change:.2f}%]  
    **Market Cap**: {symbol}{data[f'{currency}_market_cap']:,.0f}  
    **Volume**: {symbol}{data[f'{currency}_24h_vol']:,.0f}
    """)

def create_price_chart(historical_data, coin_name, currency):
    if not historical_data or 'prices' not in historical_data:
        return None

    df = pd.DataFrame(historical_data['prices'], columns=['timestamp', 'price'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')

    fig = px.line(df, x='date', y='price',
                  title=f"{coin_name.capitalize()} Price Trend (30 Days)",
                  labels={'price': f"Price ({currency.upper()})", 'date': 'Date'})
    return fig

# ========== MAIN APP ==========
def main():
    with st.sidebar:
        st.title("Crypto Tracker")

        st.markdown("---")
        st.subheader("Alert Settings")
        with st.form("alert_form"):
            alert_coin = st.selectbox("Coin", ['bitcoin', 'ethereum', 'ripple', 'cardano', 'solana', 'dogecoin'])
            alert_condition = st.selectbox("Condition", ["Above", "Below"])
            alert_threshold = st.number_input(
                f"Price Threshold ({'₹' if st.session_state.currency == 'inr' else '$'})",
                min_value=0.0, step=0.01
            )
            alert_email = st.text_input("Notification Email")

            if st.form_submit_button("💾 Save Alert"):
                if alert_email:
                    st.session_state.alerts.append((
                        alert_coin,
                        alert_threshold,
                        alert_email,
                        alert_condition == "Above"
                    ))
                    st.success("Alert saved successfully!")
                else:
                    st.error("Please enter an email address")

        st.markdown("---")
        st.caption("Data provided by CoinGecko API")

    st.header("📊 Live Cryptocurrency Prices")

    if st.session_state.last_update:
        last_update_str = st.session_state.last_update.strftime("%Y-%m-%d %H:%M:%S")
        st.caption(f"Last updated: {last_update_str} | Auto-refreshing every {REFRESH_INTERVAL//60} minutes")

    popular_coins = ['bitcoin', 'ethereum', 'ripple', 'cardano', 'solana', 'dogecoin']
    prices = fetch_crypto_prices(popular_coins, st.session_state.currency)

    if prices:
        check_alerts(prices)

        cols = st.columns(2)
        for i, coin in enumerate(popular_coins):
            with cols[i % 2]:
                display_price_card(coin, prices[coin], st.session_state.currency)

        st.markdown("---")
        st.header("📈 Price Trends")

        selected_coin = st.selectbox(
            "Select coin to view detailed trend",
            popular_coins,
            format_func=lambda x: x.capitalize()
        )

        historical_data = fetch_historical_data(selected_coin, st.session_state.currency)
        if historical_data:
            fig = create_price_chart(historical_data, selected_coin, st.session_state.currency)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.header("🔔 Your Active Alerts")

    if st.session_state.alerts:
        alert_df = pd.DataFrame([{
            'Coin': alert[0].capitalize(),
            'Condition': 'Above' if alert[3] else 'Below',
            'Threshold': f"{'₹' if st.session_state.currency == 'inr' else '$'}{alert[1]:,.2f}",
            'Email': alert[2]
        } for alert in st.session_state.alerts])

        st.dataframe(alert_df, use_container_width=True, hide_index=True)

        if st.button("Clear All Alerts"):
            st.session_state.alerts = []
            st.rerun()
    else:
        st.info("No active alerts. Set up alerts in the sidebar.")

    if st.session_state.alert_log:
        st.markdown("---")
        st.header("📝 Alert History")
        log_df = pd.DataFrame(st.session_state.alert_log)
        st.dataframe(log_df, use_container_width=True)

    time.sleep(REFRESH_INTERVAL)
    st.rerun()

if __name__ == "__main__":
    main()
