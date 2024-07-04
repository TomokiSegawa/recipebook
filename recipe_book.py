import streamlit as st
from streamlit_tags import st_tags
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import base64
from urllib.parse import urljoin

# CSVファイルのパス
CSV_FILE = 'recipe_list.csv'

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

def load_recipes():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    return pd.DataFrame(columns=['URL', 'タイトル', 'メモ', 'タグ', '画像URL'])

def save_recipe(df, url, title, memo, tags, img_url):
    if url in df['URL'].values:
        return df, False, "このURLのレシピはすでに存在しています。"

    new_recipe = pd.DataFrame({
        'URL': [url],
        'タイトル': [title],
        'メモ': [memo],
        'タグ': [tags],
        '画像URL': [img_url]
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

def get_csv_download_link(df):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="recipes.csv">CSVファイルをダウンロード</a>'
    return href

def import_csv(uploaded_file, existing_df):
    if uploaded_file is not None:
        imported_df = pd.read_csv(uploaded_file)
        # URLの重複チェックと統合
        merged_df = pd.concat([existing_df, imported_df]).drop_duplicates(subset='URL', keep='last')
        merged_df = merged_df.reset_index(drop=True)
        merged_df.to_csv(CSV_FILE, index=False)
        return merged_df
    return existing_df

def main():
    st.title('ぼくのレシピ帳')
    st.write("Webサイト上のレシピをまとめて保存するためのアプリです")

    # レシピデータの読み込み
    df = load_recipes()

    # セッション状態の初期化
    if 'tags' not in st.session_state:
        st.session_state.tags = []
    if 'new_tags' not in st.session_state:
        st.session_state.new_tags = []
    if 'show_success' not in st.session_state:
        st.session_state.show_success = False
    if 'success_message' not in st.session_state:
        st.session_state.success_message = ""
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {"url": "", "title": "", "memo": "", "img_url": None}
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "レシピ追加"

    # 全てのタグを取得し、セッション状態のタグも含める
    all_tags = set(get_all_tags(df))
    all_tags.update(st.session_state.tags)
    all_tags = list(all_tags)

    # タブの作成
    tab1, tab2, tab3 = st.tabs(["レシピ追加", "レシピ一覧", "インポート/エクスポート"])

    if st.session_state.current_tab == "レシピ追加":
        tab1.header('新しいレシピを追加')
        
        # 成功メッセージの表示
        if st.session_state.show_success:
            tab1.success(st.session_state.success_message)
            st.session_state.show_success = False

        # URL入力
        url = tab1.text_input('URLを入力してください：', value=st.session_state.form_data["url"], key='input_url')
        if url and url != st.session_state.form_data["url"]:
            title, img_url = get_webpage_info(url)
            st.session_state.form_data["title"] = title
            st.session_state.form_data["img_url"] = img_url
            tab1.text_input('ウェブページのタイトル：', value=title, key='input_title')
            if img_url:
                try:
                    tab1.image(img_url, caption="レシピ画像", use_column_width=True)
                except Exception as e:
                    tab1.warning(f"画像の表示中にエラーが発生しました: {str(e)}")
            else:
                tab1.info("レシピ画像が見つかりませんでした。")
        else:
            tab1.text_input('ウェブページのタイトル：', value=st.session_state.form_data["title"], key='input_title')
        
        # メモの入力
        memo = tab1.text_area('アレンジメモ：', value=st.session_state.form_data["memo"], key='input_memo')
        
        # タグの入力（既存タグの選択と新規入力の組み合わせ）
        selected_existing_tags = tab1.multiselect(
            '既存のタグから選択:',
            options=all_tags,
            default=st.session_state.tags
        )

        # 新規タグの入力
        new_tags = st_tags(
            label='新しいタグを入力:',
            text='エンターキーを押して追加',
            value=st.session_state.new_tags,
            suggestions=[tag for tag in all_tags if tag not in selected_existing_tags],
            maxtags=10,
            key='new_tag_input'
        )

        # 既存のタグと新規タグを組み合わせる
        combined_tags = list(set(selected_existing_tags + new_tags))
        
        # セッション状態の更新
        st.session_state.tags = selected_existing_tags
        st.session_state.new_tags = new_tags
        
        # 保存ボタン
        if tab1.button('レシピを保存'):
            if url and st.session_state.form_data["title"]:  # URLとタイトルが入力されているか確認
                df, success, message = save_recipe(df, url, st.session_state.form_data["title"], memo, ','.join(combined_tags), st.session_state.form_data["img_url"])
                if success:
                    st.session_state.show_success = True
                    st.session_state.success_message = message
                    st.session_state.form_data = {"url": "", "title": "", "memo": "", "img_url": None}
                    st.session_state.tags = []
                    st.session_state.new_tags = []
                    st.experimental_rerun()
                else:
                    tab1.error(message)
            else:
                tab1.error("URLとタイトルを入力してください。")

        # フォームデータの更新
        st.session_state.form_data["url"] = url
        st.session_state.form_data["title"] = st.session_state.form_data["title"]
        st.session_state.form_data["memo"] = memo

    elif st.session_state.current_tab == "レシピ一覧":
        tab2.header('保存したレシピ一覧')
        
        # タグでフィルタリング（複数選択可能）
        selected_tags = tab2.multiselect('タグでフィルタリング（複数選択可能、AND条件）', all_tags)
        
        # レシピの表示（AND条件でフィルタリング）
        if not selected_tags:  # タグが選択されていない場合は全てのレシピを表示
            filtered_df = df
        else:
            filtered_df = df[df['タグ'].apply(lambda x: all(tag in x.split(',') for tag in selected_tags))]
        
        for index, recipe in filtered_df.iterrows():
            with tab2.expander(recipe['タイトル']):
                st.write(f"URL: {recipe['URL']}")
                st.write(f"メモ: {recipe['メモ']}")
                st.write(f"タグ: {recipe['タグ']}")
                if '画像URL' in recipe and recipe['画像URL']:
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
                        st.session_state.edit_tags = recipe['タグ'].split(',')
                        st.experimental_rerun()
                with col2:
                    if st.button('削除', key=f'delete_{index}'):
                        df = delete_recipe(df, index)
                        st.success('レシピが削除されました。')
                        st.experimental_rerun()

        # 編集モード
        if 'editing' in st.session_state:
            tab2.header('レシピの編集')
            edit_url = tab2.text_input('URL:', value=st.session_state.edit_url)
            edit_title = tab2.text_input('タイトル:', value=st.session_state.edit_title)
            edit_memo = tab2.text_area('メモ:', value=st.session_state.edit_memo)
            edit_tags = st_tags(
                label='タグ:',
                text='エンターキーを押して追加',
                value=st.session_state.edit_tags,
                suggestions=all_tags,
                maxtags=10,
                key='edit_tags'
            )

            if tab2.button('更新'):
                df = update_recipe(df, st.session_state.editing, edit_url, edit_title, edit_memo, ','.join(edit_tags))
                tab2.success('レシピが更新されました。')
                del st.session_state.editing
                st.experimental_rerun()

            if tab2.button('キャンセル'):
                del st.session_state.editing
                st.experimental_rerun()

    elif st.session_state.current_tab == "インポート/エクスポート":
        tab3.header('レシピのインポート/エクスポート')

        # CSVファイルのインポート
        tab3.subheader('CSVファイルからレシピをインポート')
        uploaded_file = tab3.file_uploader("CSVファイルを選択してください", type="csv")
        if tab3.button('インポート'):
            if uploaded_file is not None:
                df = import_csv(uploaded_file, df)
                tab3.success('レシピがインポートされました！')
                st.experimental_rerun()
            else:
                tab3.error('CSVファイルをアップロードしてください。')

        # CSVダウンロードリンク
        tab3.subheader('レシピをCSVファイルでエクスポート')
        tab3.markdown(get_csv_download_link(df), unsafe_allow_html=True)

    # タブの状態を更新
    if tab1:
        st.session_state.current_tab = "レシピ追加"
    elif tab2:
        st.session_state.current_tab = "レシピ一覧"
    elif tab3:
        st.session_state.current_tab = "インポート/エクスポート"

if __name__ == '__main__':
    main()