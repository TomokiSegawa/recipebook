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

def save_recipe(df, url, title, memo, tags):
    # URLの重複チェック
    if url in df['URL'].values:
        return df, False, "このURLのレシピはすでに存在しています。"

    new_recipe = pd.DataFrame({
        'URL': [url],
        'タイトル': [title],
        'メモ': [memo],
        'タグ': [tags]
    })
    
    df = pd.concat([df, new_recipe], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)
    return df, True, "レシピが保存されました！"

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
        memo = st.text_area('アレンジメモ：', key='memo')
        
        # タグの入力（既存タグの選択と新規入力の組み合わせ）
        if 'tags' not in st.session_state:
            st.session_state.tags = []

        # 既存のタグから選択
        selected_existing_tags = st.multiselect(
            '既存のタグから選択:',
            options=all_tags,
            default=st.session_state.tags
        )

        # 新規タグの入力
        new_tags = st_tags(
            label='新しいタグを入力:',
            text='エンターキーを押して追加',
            value=[tag for tag in st.session_state.tags if tag not in selected_existing_tags],
            suggestions=[tag for tag in all_tags if tag not in selected_existing_tags],
            maxtags=10,
            key='new_tag_input'
        )

        # 既存のタグと新規タグを組み合わせる
        combined_tags = list(set(selected_existing_tags + new_tags))
        
        # セッション状態の更新
        if combined_tags != st.session_state.tags:
            st.session_state.tags = combined_tags
        
        # 保存ボタン
        if st.button('レシピを保存'):
            if url and title:  # URLとタイトルが入力されているか確認
                df, success, message = save_recipe(df, url, title, memo, ','.join(st.session_state.tags))
                if success:
                    st.success(message)
                    # タグリストを更新
                    all_tags = get_all_tags(df)
                    st.experimental_rerun()  # ページを再読み込みして最新のタグリストを反映
                else:
                    st.error(message)
            else:
                st.error("URLとタイトルを入力してください。")

    with tab2:
        st.header('保存したレシピ一覧')
        
        # タグでフィルタリング（複数選択可能）
        selected_tags = st.multiselect('タグでフィルタリング（複数選択可能、AND条件）', all_tags)
        
        # レシピの表示（AND条件でフィルタリング）
        if not selected_tags:  # タグが選択されていない場合は全てのレシピを表示
            filtered_df = df
        else:
            filtered_df = df[df['タグ'].apply(lambda x: all(tag in x.split(',') for tag in selected_tags))]
        
        for _, recipe in filtered_df.iterrows():
            with st.expander(recipe['タイトル']):
                st.write(f"URL: {recipe['URL']}")
                st.write(f"メモ: {recipe['メモ']}")
                st.write(f"タグ: {recipe['タグ']}")

if __name__ == '__main__':
    main()