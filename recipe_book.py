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

def update_recipe(df, index, url, title, memo, tags):
    df.at[index, 'URL'] = url
    df.at[index, 'タイトル'] = title
    df.at[index, 'メモ'] = memo
    df.at[index, 'タグ'] = tags
    df.to_csv(CSV_FILE, index=False)
    return df

def delete_recipe(df, index):
    df = df.drop(index)
    df = df.reset_index(drop=True)
    df.to_csv(CSV_FILE, index=False)
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

    # 全てのタグを取得し、セッション状態のタグも含める
    all_tags = set(get_all_tags(df))
    if 'tags' in st.session_state:
        all_tags.update(st.session_state.tags)
    all_tags = list(all_tags)

    # フォームクリアフラグの初期化
    if 'clear_form' not in st.session_state:
        st.session_state.clear_form = False

    # タブの作成
    tab1, tab2 = st.tabs(["レシピ追加", "レシピ一覧"])

    with tab1:
        st.header('新しいレシピを追加')
        
        # URL入力
        url = st.text_input('URLを入力してください：', value="" if st.session_state.clear_form else st.session_state.get('url', ""), key='url')
        if url and not st.session_state.clear_form:
            title = get_webpage_title(url)
            st.text_input('ウェブページのタイトル：', value=title, key='title')
        else:
            st.text_input('ウェブページのタイトル：', value="" if st.session_state.clear_form else st.session_state.get('title', ""), key='title')
        
        # メモの入力
        memo = st.text_area('アレンジメモ：', value="" if st.session_state.clear_form else st.session_state.get('memo', ""), key='memo')
        
        # タグの入力（既存タグの選択と新規入力の組み合わせ）
        if 'tags' not in st.session_state or st.session_state.clear_form:
            st.session_state.tags = []

        # 既存のタグから選択
        selected_existing_tags = st.multiselect(
            '既存のタグから選択:',
            options=all_tags,
            default=[] if st.session_state.clear_form else st.session_state.tags
        )

        # 新規タグの入力
        new_tags = st_tags(
            label='新しいタグを入力:',
            text='エンターキーを押して追加',
            value=[] if st.session_state.clear_form else [tag for tag in st.session_state.tags if tag not in selected_existing_tags],
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
            if url and st.session_state.title:  # URLとタイトルが入力されているか確認
                df, success, message = save_recipe(df, url, st.session_state.title, memo, ','.join(st.session_state.tags))
                if success:
                    st.success(message)
                    st.session_state.clear_form = True
                    st.experimental_rerun()  # ページを再読み込み
                else:
                    st.error(message)
            else:
                st.error("URLとタイトルを入力してください。")

        # フォームクリアフラグをリセット
        if st.session_state.clear_form:
            st.session_state.clear_form = False

    with tab2:
        st.header('保存したレシピ一覧')
        
        # タグでフィルタリング（複数選択可能）
        selected_tags = st.multiselect('タグでフィルタリング（複数選択可能、AND条件）', all_tags)
        
        # レシピの表示（AND条件でフィルタリング）
        if not selected_tags:  # タグが選択されていない場合は全てのレシピを表示
            filtered_df = df
        else:
            filtered_df = df[df['タグ'].apply(lambda x: all(tag in x.split(',') for tag in selected_tags))]
        
        for index, recipe in filtered_df.iterrows():
            with st.expander(recipe['タイトル']):
                st.write(f"URL: {recipe['URL']}")
                st.write(f"メモ: {recipe['メモ']}")
                st.write(f"タグ: {recipe['タグ']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button('編集', key=f'edit_{index}'):
                        st.session_state.editing = index
                        st.session_state.edit_url = recipe['URL']
                        st.session_state.edit_title = recipe['タイトル']
                        st.session_state.edit_memo = recipe['メモ']
                        st.session_state.edit_tags = recipe['タグ'].split(',')
                        st.experimental_rerun()
                with col2:
                    if st.button('削除', key=f'delete_{index}'):
                        df = delete_recipe(df, index)
                        st.success('レシピが削除されました。')
                        st.experimental_rerun()

        # 編集モード
        if 'editing' in st.session_state:
            st.header('レシピの編集')
            edit_url = st.text_input('URL:', value=st.session_state.edit_url)
            edit_title = st.text_input('タイトル:', value=st.session_state.edit_title)
            edit_memo = st.text_area('メモ:', value=st.session_state.edit_memo)
            edit_tags = st_tags(
                label='タグ:',
                text='エンターキーを押して追加',
                value=st.session_state.edit_tags,
                suggestions=all_tags,
                maxtags=10,
                key='edit_tags'
            )

            if st.button('更新'):
                df = update_recipe(df, st.session_state.editing, edit_url, edit_title, edit_memo, ','.join(edit_tags))
                st.success('レシピが更新されました。')
                del st.session_state.editing
                st.experimental_rerun()

            if st.button('キャンセル'):
                del st.session_state.editing
                st.experimental_rerun()

if __name__ == '__main__':
    main()