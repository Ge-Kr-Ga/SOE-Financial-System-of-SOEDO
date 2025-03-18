import streamlit as st
import requests

# 获取外部 IP 地址
def get_external_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json')
        ip_info = response.json()
        return ip_info['ip']
    except Exception as e:
        return f"无法获取 IP 地址: {str(e)}"

# Streamlit 应用
st.title("获取外部 IP 地址")
external_ip = get_external_ip()
st.write(f"您的外部 IP 地址是: {external_ip}")