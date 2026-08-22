# Cartly Streamlit Frontend Server
# Serves CartlyStorefront UI connected to FastAPI Backend API (port 4444)

import streamlit as st
import streamlit.components.v1 as components
import os

st.set_page_config(
    page_title="Cartly — Voice-First Grocery List",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide Streamlit header/footer padding for edge-to-edge UI
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0rem !important;
        padding-right: 0rem !important;
        max-width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

# Path to CartlyStorefront index.html
html_path = os.path.join(os.path.dirname(__file__), "index.html")

if os.path.exists(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        html_code = f.read()
    
    # Render CartlyStorefront inside Streamlit
    components.html(html_code, height=1000, scrolling=True)
else:
    st.error(f"Could not find CartlyStorefront at {html_path}")