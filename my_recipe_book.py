import streamlit as st
from streamlit_tags import st_tags
import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from urllib.parse import urljoin

# Google Sheets設定
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
SHEET_ID = st.secrets["GOOGLE_SHEET_ID"]

def get_webpage_info(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.title.string if soup.title else "タイトルが見つかりません"
        
        # 画像URLの取得
        img_tag = soup.find('meta', property='og:image')
        img_url = img_tag['content'] if img_tag else None
        
        if not img_url:
            img_tag = soup.find('img')
            img_url = img_tag['src'] if img_tag else None
        
        # 相対パスを絶対パスに変換
        if img_url and not img_url.startswith(('http://', 'https://')):
            img_url = urljoin(url, img_url)
        
        return title, img_url
    except Exception as e:
        st.error(f"ウェブページの情報取得中にエラーが発生しました: {str(e)}")
        return "URLが無効です", None

def connect_to_sheet():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDS_JSON"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    return sheet

def load_recipes():
    sheet = connect_to_sheet()
    data = sheet.get_all_values()
    if len(data) > 1:
        return pd.DataFrame(data[1:], columns=data[0])
    return pd.DataFrame(columns=['URL', 'タイトル', 'メモ', 'タグ', '画像URL'])

def save_recipe(url, title, memo, tags, img_url):
    sheet = connect_to_sheet()
    existing_urls = sheet.col_values(1)[1:]  # ヘッダーを除外
    if url in existing_urls:
        return False, "このURLのレシピはすでに存在しています。"
    
    new_row = [url, title, memo, tags, img_url]
    sheet.append_row(new_row)
    return True, "レシピが保存されました！"

def update_recipe(index, url, title, memo, tags, img_url):
    sheet = connect_to_sheet()
    row = index + 2  # ヘッダー行とインデックスの調整
    sheet.update(f'A{row}:E{row}', [[url, title, memo, tags, img_url]])

def delete_recipe(index):
    sheet = connect_to_sheet()
    sheet.delete_row(index + 2)  # ヘッダー行とインデックスの調整

def get_all_tags():
    df = load_recipes()
    all_tags = set()
    for tags in df['タグ']:
        if isinstance(tags, str):
            all_tags.update(tag.strip() for tag in tags.split(','))
    return list(all_tags)

def main():
    st.title('ぼくのレシピ帳')
    st.write("Webサイト上のレシピをまとめて保存するためのアプリです")

    # 全てのタグを取得
    all_tags = get_all_tags()

    # セッション状態の初期化
    if 'show_success' not in st.session_state:
        st.session_state.show_success = False
    if 'clear_form' not in st.session_state:
        st.session_state.clear_form = False
    if 'form_key' not in st.session_state:
        st.session_state.form_key = 0

    # タブの作成
    tab1, tab2 = st.tabs(["レシピ追加", "レシピ一覧"])

    with tab1:
        st.header('新しいレシピを追加')
        
        # 成功メッセージの表示
        if st.session_state.show_success:
            st.success("保存しました！")
            st.session_state.show_success = False

        # フォームのキーを更新（フォームをリセットするため）
        if st.session_state.clear_form:
            st.session_state.form_key += 1
            st.session_state.clear_form = False

        # URL入力
        url = st.text_input('URLを入力してください：', key=f'url_{st.session_state.form_key}')
        if url:
            title, img_url = get_webpage_info(url)
            st.text_input('ウェブページのタイトル：', value=title, key=f'title_{st.session_state.form_key}')
            if img_url:
                try:
                    st.image(img_url, caption="レシピ画像", use_column_width=True)
                except Exception as e:
                    st.warning(f"画像の表示中にエラーが発生しました: {str(e)}")
            else:
                st.info("レシピ画像が見つかりませんでした。")
        else:
            st.text_input('ウェブページのタイトル：', key=f'title_{st.session_state.form_key}')
        
        # メモの入力
        memo = st.text_area('アレンジメモ：', key=f'memo_{st.session_state.form_key}')
        
        # タグの入力（既存タグの選択と新規入力の組み合わせ）
        selected_existing_tags = st.multiselect(
            '既存のタグから選択:',
            options=all_tags,
            key=f'existing_tags_{st.session_state.form_key}'
        )

        #新規タグ入力の説明文
        st.caption("新しいタグを入力し、Enterキーを押して追加してください。")

        # 新規タグの入力
        new_tags = st_tags(
            label='新しいタグを入力:',
            text='エンターキーを押して追加',
            value=[],
            suggestions=[tag for tag in all_tags if tag not in selected_existing_tags],
            maxtags=10,
            key=f'new_tag_input_{st.session_state.form_key}'
        )

        # 既存のタグと新規タグを組み合わせる
        combined_tags = list(set(selected_existing_tags + new_tags))
        
        # 保存ボタン
        if st.button('レシピを保存', key=f'save_button_{st.session_state.form_key}'):
            if url and st.session_state[f'title_{st.session_state.form_key}']:  # URLとタイトルが入力されているか確認
                success, message = save_recipe(url, st.session_state[f'title_{st.session_state.form_key}'], memo, ','.join(combined_tags), img_url)
                if success:
                    st.session_state.show_success = True
                    st.session_state.clear_form = True
                    st.experimental_rerun()
                else:
                    st.error(message)
            else:
                st.error("URLとタイトルを入力してください。")

    with tab2:
        st.header('保存したレシピ一覧')
        
        # レシピデータの読み込み
        df = load_recipes()
        
        # タグでフィルタリング（複数選択可能）
        selected_tags = st.multiselect('タグでフィルタリング（複数選択可能、AND条件）', all_tags)
        
        # レシピの表示（AND条件でフィルタリング）
        if not selected_tags:  # タグが選択されていない場合は全てのレシピを表示
            filtered_df = df
        else:
            filtered_df = df[df['タグ'].apply(lambda x: all(tag in str(x).split(',') for tag in selected_tags))]
        
        for index, recipe in filtered_df.iterrows():
            with st.expander(recipe['タイトル']):
                st.write(f"URL: {recipe['URL']}")
                st.write(f"メモ: {recipe['メモ']}")
                st.write(f"タグ: {recipe['タグ']}")
                if pd.notna(recipe['画像URL']):
                    try:
                        st.image(recipe['画像URL'], caption="レシピ画像", use_column_width=True)
                    except Exception as e:
                        st.warning(f"画像の表示中にエラーが発生しました: {str(e)}")
                else:
                    st.info("このレシピには画像が登録されていません。")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button('編集', key=f'edit_{index}'):
                        st.session_state.editing = index
                        st.session_state.edit_url = recipe['URL']
                        st.session_state.edit_title = recipe['タイトル']
                        st.session_state.edit_memo = recipe['メモ']
                        st.session_state.edit_tags = str(recipe['タグ']).split(',')
                        st.experimental_rerun()
                with col2:
                    if st.button('削除', key=f'delete_{index}'):
                        delete_recipe(index)
                        st.success('レシピが削除されました。')
                        st.experimental_rerun()

        # 編集モード
        
        if 'editing' in st.session_state:
            st.header('レシピの編集')
            edit_url = st.text_input('URL:', value=st.session_state.edit_url)
            edit_title = st.text_input('タイトル:', value=st.session_state.edit_title)
            edit_memo = st.text_area('メモ:', value=st.session_state.edit_memo)
            
            # 既存のタグを選択
            selected_existing_tags = st.multiselect(
                '既存のタグから選択:',
                options=all_tags,
                default=st.session_state.edit_tags
            )

            # 新規タグ入力の説明文
            st.caption("新しいタグを入力し、Enterキーを押して追加してください。追加後は手動で入力欄をクリアしてください。")
        
            # 新規タグの入力
            new_tags = st_tags(
                label='新しいタグを入力:',
                text='エンターキーを押して追加',
                value=[],
                suggestions=[tag for tag in all_tags if tag not in selected_existing_tags],
                maxtags=10,
                key=f'edit_new_tag_input_{st.session_state.editing}'
            )
        
            # 既存のタグと新規タグを組み合わせる
            combined_tags = list(set(selected_existing_tags + new_tags))
        
            if st.button('更新'):
                # 現在の画像URLを取得
                current_img_url = df.iloc[st.session_state.editing]['画像URL']
                update_recipe(st.session_state.editing, edit_url, edit_title, edit_memo, ','.join(combined_tags), current_img_url)
                st.success('レシピが更新されました。')
                del st.session_state.editing
                st.experimental_rerun()
        
            if st.button('キャンセル'):
                del st.session_state.editing
                st.experimental_rerun()

if __name__ == '__main__':
    main()
