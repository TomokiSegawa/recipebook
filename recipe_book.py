import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

# CSVファイルのパス
CSV_FILE = 'recipe_list.csv'

def get_webpage_title(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup.title.string if soup.title else "タイトルが見つかりません"
    except:
        return "URLが無効です"

def load_recipes():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    return pd.DataFrame(columns=['URL', 'タイトル', 'メモ', 'タグ'])

def save_recipe(df):
    url = st.session_state.url
    title = st.session_state.title
    memo = st.session_state.memo
    tags = st.session_state.tags

    new_recipe = pd.DataFrame({
        'URL': [url],
        'タイトル': [title],
        'メモ': [memo],
        'タグ': [tags]
    })
    
    df = pd.concat([df, new_recipe], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)
    st.success('レシピが保存されました！')
    return df

def main():
    st.title('レシピ管理アプリ')

    # レシピデータの読み込み
    df = load_recipes()

    # タブの作成
    tab1, tab2 = st.tabs(["レシピ追加", "レシピ一覧"])

    with tab1:
        st.header('新しいレシピを追加')
        
        # URL入力
        url = st.text_input('URLを入力してください：', key='url')
        if url:
            title = get_webpage_title(url)
            st.text_input('ウェブページのタイトル：', value=title, key='title')
        
        # メモとタグの入力
        st.text_area('アレンジメモ：', key='memo')
        st.text_input('タグ（コンマ区切り）：', key='tags')
        
        # 保存ボタン
        if st.button('レシピを保存'):
            df = save_recipe(df)

    with tab2:
        st.header('保存したレシピ一覧')
        
        # タグでフィルタリング
        all_tags = set(tag.strip() for tags in df['タグ'] for tag in tags.split(',') if tag)
        selected_tag = st.selectbox('タグでフィルタリング', ['すべて表示'] + list(all_tags))
        
        # レシピの表示
        filtered_df = df if selected_tag == 'すべて表示' else df[df['タグ'].str.contains(selected_tag)]
        
        for _, recipe in filtered_df.iterrows():
            with st.expander(recipe['タイトル']):
                st.write(f"URL: {recipe['URL']}")
                st.write(f"メモ: {recipe['メモ']}")
                st.write(f"タグ: {recipe['タグ']}")

if __name__ == '__main__':
    main()