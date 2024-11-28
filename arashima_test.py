import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
from docx import Document
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
import openai

# OpenAI APIキーをStreamlitのシークレットから設定
openai.api_key = st.secrets["openai_api_key"]

# サービスアカウント認証情報
SERVICE_ACCOUNT_FILE = 'service_account.json'
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents'
]

# Google API認証
def authenticate_google_services():
    with open(SERVICE_ACCOUNT_FILE, 'r') as f:
        service_account_info = json.load(f)
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES
    )
    return credentials

# Google Docs APIでドキュメントの内容を取得する関数
def get_document_text(docs_service, document_id):
    try:
        document = docs_service.documents().get(documentId=document_id).execute()
        content = document.get('body').get('content')
        document_text = ''
        for element in content:
            if 'paragraph' in element:
                for text_run in element.get('paragraph').get('elements'):
                    if 'textRun' in text_run:
                        document_text += text_run.get('textRun').get('content')
        return document_text
    except Exception as e:
        st.error(f"ドキュメントの読み取り中にエラーが発生しました: {e}")
        return ""

# F列がFALSEで直近50件を取得
def get_sheet_data(sheet_service, sheet_id, range_name):
    try:
        sheet = sheet_service.spreadsheets()
        result = sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute()
        values = result.get('values', [])
        
        # F列がFALSEの行をフィルタリング
        filtered_values = [row for row in values if len(row) > 5 and row[5].strip().lower() == "false"]
        recent_values = filtered_values[-50:]
        return recent_values
    except Exception as e:
        st.error(f"スプレッドシートデータ取得中にエラーが発生しました: {e}")
        return []

# テキスト抽出関数
def extract_text_from_file(uploaded_file):
    file_type = uploaded_file.type
    extracted_text = ""

    if file_type == "application/pdf":
        pdf_reader = PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            extracted_text += page.extract_text()
    elif file_type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
        df = pd.read_excel(uploaded_file)
        extracted_text = df.to_string()
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(uploaded_file)
        for paragraph in doc.paragraphs:
            extracted_text += paragraph.text + "\n"
    else:
        st.error("対応しているファイル形式はPDF、Excel、Wordです。")
    return extracted_text

# Streamlitアプリケーション
st.title("AI MATCHING")

# タブの作成
tab1, tab2 = st.tabs(["人材要件から最適案件検索", "案件概要から最適人材検索"])

with tab1:
    # 人材情報入力フォーム
    with st.form("input_form"):
        st.subheader("人材情報入力フォーム")
        skill_sheet = st.file_uploader("【必須】スキルシートアップロード（PDF、Excel、Word形式）", type=["pdf", "xlsx", "xls", "docx"])
        email_content = st.text_area("【必須】人材要件のメール文を貼り付け", placeholder="ここにメール文を貼り付けてください")
        submitted = st.form_submit_button("人材に最適な案件を検索")
    
    if submitted:
        if not skill_sheet or not email_content.strip():
            st.error("すべての必須項目を入力してください。")
        else:
            extracted_text = extract_text_from_file(skill_sheet)
            if extracted_text:
    
                # Google APIサービスの認証
                credentials = authenticate_google_services()
                docs_service = build('docs', 'v1', credentials=credentials)
                sheet_service = build('sheets', 'v4', credentials=credentials)
    
                # Google DocsとSheetsのデータ取得
                document_text = get_document_text(docs_service, "1HjjtYZ1RCTPSXLxW5ujCviIwCdMi2a4gTB7y5wARht0")
                sheet_data = get_sheet_data(sheet_service, "1amJJDVMr3__OmLgWo1Z9w6FXZ9aMaNm0WRlx1_TYXnE", "'【自動】raw'!A:L")
    
                # 案件情報をプロンプトに追加
                case_info = "\n".join([
                    f"案件 {i+1}:\n日時: {row[0]}\n件名: {row[3]}\n本文: {row[4]}"
                    for i, row in enumerate(sheet_data)
                ])
    
                # プロンプトの作成
                combined_prompt = (
                    f"プロンプト:\n{document_text}\n\n"
                    f"候補者情報:\n{email_content.strip()}\n\n"
                    f"候補者のスキルシート:\n{extracted_text}\n\n"
                    f"案件情報:\n{case_info}"
                )

                with st.spinner("AIによるマッチング率計算中..."):
                    # AIにプロンプトを送信
                    response = openai.chat.completions.create(
                        model="gpt-4o-2024-08-06",
                        messages=[
                            {"role": "system", "content": "あなたは案件をマッチングするエージェントです。"},
                            {"role": "user", "content": combined_prompt},
                        ]
                    )
                    raw_response = response.choices[0].message.content.strip()
                st.write(raw_response)

with tab2:
    # 案件情報入力フォーム
    with st.form("input_form_case"):
        st.subheader("案件情報入力フォーム")
        email_content = st.text_area("【必須】案件概要のメール文を貼り付け", placeholder="ここにメール文を貼り付けてください")
        submitted = st.form_submit_button("案件に最適な人材を検索")

    if submitted:
        if not email_content.strip():
            st.error("案件概要を入力してください。")
        else:
            # Google APIサービスの認証
            credentials = authenticate_google_services()
            docs_service = build('docs', 'v1', credentials=credentials)

            # 指定されたGoogle Docsファイルのデータ取得
            document_text = get_document_text(docs_service, "1ltCJ2yi4Ksz98d_ubjDlC0p8GQsLvnm18mg9YNU9LVo")

            # プロンプトの作成
            combined_prompt = (
                f"プロンプト:\n{document_text}\n\n"
                f"案件情報:\n{email_content.strip()}"
            )

            with st.spinner("AIによるマッチング率計算中..."):
                # AIにプロンプトを送信
                response = openai.chat.completions.create(
                    model="gpt-4o-2024-08-06",
                    messages=[
                        {"role": "system", "content": "あなたは案件をマッチングするエージェントです。"},
                        {"role": "user", "content": combined_prompt},
                    ]
                )
                raw_response = response.choices[0].message.content.strip()
            st.write(raw_response)
