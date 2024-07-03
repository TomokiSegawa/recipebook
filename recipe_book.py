import streamlit as st
from streamlit_tags import st_tags
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
    tags = ','.join(st.session_state.tags)

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

def get_all_tags(df):
    all_tags = set()
    for tags in df['タグ']:
        if isinstance(tags, str):
            all_tags.update(tag.strip() for tag in tags.split(','))
    return list(all_tags)

def main():
    st.title('レシピ管理アプリ')

    # レシピデータの読み込み
    df = load_recipes()

    # 全てのタグを取得
    all_tags = get_all_tags(df)

    # タブの作成
    tab1, tab2 = st.tabs(["レシピ追加", "レシピ一覧"])

    with tab1:
        st.header('新しいレシピを追加')
        
        # URL入力
        url = st.text_input('URLを入力してください：', key='url')
        if url:
            title = get_webpage_title(url)
            st.text_input('ウェブページのタイトル：', value=title, key='title')
        
        # メモの入力
        st.text_area('アレンジメモ：', key='memo')
        
        # タグの入力（チップ入力を使用）
        if 'tags' not in st.session_state:
            st.session_state.tags = []

        # st_tags の結果を直接変数に代入
        input_tags = st_tags(
            label='タグを入力してください:',
            text='エンターキーを押して追加',
            value=st.session_state.tags,  # 初期値として現在のタグを使用
            suggestions=all_tags,
            maxtags=10,
            key='tag_input'  # キーを変更
        )

        # セッション状態の更新（ウィジェットの外で行う）
        if input_tags != st.session_state.tags:
            st.session_state.tags = input_tags
        
        # 保存ボタン
        if st.button('レシピを保存'):
            df = save_recipe(df)
            # タグリストを更新
            all_tags = get_all_tags(df)
            st.experimental_rerun()  # ページを再読み込みして最新のタグリストを反映

    with tab2:
        st.header('保存したレシピ一覧')
        
        # タグでフィルタリング（複数選択可能）
        selected_tags = st.multiselect('タグでフィルタリング（複数選択可能）', all_tags)
        
        # レシピの表示
        if not selected_tags:  # タグが選択されていない場合は全てのレシピを表示
            filtered_df = df
        else:
            filtered_df = df[df['タグ'].apply(lambda x: any(tag in x.split(',') for tag in selected_tags))]
        
        for _, recipe in filtered_df.iterrows():
            with st.expander(recipe['タイトル']):
                st.write(f"URL: {recipe['URL']}")
                st.write(f"メモ: {recipe['メモ']}")
                st.write(f"タグ: {recipe['タグ']}")

if __name__ == '__main__':
    main()