import streamlit as st
import pandas as pd
import os
from datetime import datetime

# ファイル名
DATA_FILE = "sales_reports.csv"

# データの読み込み
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=["日付", "営業担当者", "訪問先", "活動内容", "成果"])

# データの保存
def save_data(new_data):
    data = load_data()
    data = pd.concat([data, new_data], ignore_index=True)
    data.to_csv(DATA_FILE, index=False)

# アプリのタイトル
st.title("営業日報報告アプリ")

# フォームの作成
st.sidebar.header("日報入力フォーム")
with st.sidebar.form("営業日報フォーム"):
    date = st.date_input("日付", datetime.now().date())
    salesperson = st.text_input("営業担当者名")
    client = st.text_input("訪問先")
    activity = st.text_area("活動内容")
    result = st.text_area("成果")
    
    submitted = st.form_submit_button("日報を送信")
    
    if submitted:
        if salesperson and client and activity and result:
            new_data = pd.DataFrame({
                "日付": [date],
                "営業担当者": [salesperson],
                "訪問先": [client],
                "活動内容": [activity],
                "成果": [result]
            })
            save_data(new_data)
            st.sidebar.success("日報を保存しました！")
        else:
            st.sidebar.error("すべてのフィールドを入力してください。")

# 保存済みデータの表示
st.header("日報データ")
data = load_data()

if not data.empty:
    st.dataframe(data)

    # 日付ごとの活動件数を可視化
    st.subheader("日付ごとの活動件数")
    activity_counts = data["日付"].value_counts().sort_index()
    st.bar_chart(activity_counts)
else:
    st.info("まだ日報がありません。")

