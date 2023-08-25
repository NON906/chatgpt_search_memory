# chatgpt_search_memory

[ChatGPT](https://openai.com/blog/chatgpt)に会話内容を疑似的に記憶・思い出しながら会話するためのリポジトリです。  
会話内容を[meilisearch](https://github.com/meilisearch/meilisearch)に追加・検索する仕組みです。

## 導入方法

1. [ChatGPTのAPIキー](https://platform.openai.com/account/api-keys)が必要です（一部を除いて有料）。  
持っていない場合は、登録して発行してください。

2. PythonやGitも必要なので、インストールしてください。

3. 以下のコマンドを実行してください。
```
git clone https://github.com/NON906/chatgpt_search_memory.git
cd chatgpt_search_memory
pip install -r requirements.txt
python main.py
```

一度行った後は、``python main.py``で実行できます。