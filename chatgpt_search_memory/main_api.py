#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import openai
import sys
import json
import time
import meilisearch
import tiktoken

class MainApi:
    chatgpt_messages = []
    log_dir_name = './save'
    model = 'gpt-3.5-turbo'
    chatgpt_functions = [{
        "name": "search_history",
        "description": """
Search the content of past conversations.
Please call if you are asked about the past contents or unknown things.
Please do it before saying "I don't know", "I have no idea" or "I don't have information" etc.
This call does not advance the conversation.

Please use this function as your memory.
Ostensibly say "memory" instead of "database" or "search".
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "Keywords for searching past content. If you have more than one, separate them with spaces.",
                },
            },
            "required": ["keywords"],
        },
    }]
    setting_content = ''
    setting_name = 'default'
    search_history_contents = []
    is_send_to_chatgpt = False
    last_time_chatgpt = 0.0
    log_index = -1
    meilisearch_url = 'http://localhost:7700'
    meilisearch_key = 'aSampleMasterKey'
    search_limit = 20

    def __init__(self, apikey=None, model=None):
        if model is not None:
            self.change_model(model)
        if apikey is not None:
            self.change_apikey(apikey)
        self.add_search_content()

    def change_apikey(self, apikey):
        openai.api_key = apikey

    def change_model(self, model):
        self.model = model

    def load_log(self, log):
        if log is None:
            return False
        try:
            if os.path.isfile(log):
                with open(log, 'r', encoding='UTF-8') as f:
                    loaded_json = json.load(f)
                    self.load_log_dict(int(os.path.splitext(os.path.basename(log))[0]), loaded_json['messages'], loaded_json['others'])
                return True
        except:
            pass
        return False

    def load_log_dict(self, index_id, messages, others):
        self.chatgpt_messages = messages[1:]
        self.setting_content = others['setting_content']
        self.setting_name = others['setting_name']
        self.search_history_contents = others['search_history_contents']
        self.log_index = index_id

    def remove_last_conversation(self, result=None, write_log=True):
        if result is None or self.chatgpt_messages[-1]["content"] == result:
            self.chatgpt_messages = self.chatgpt_messages[:-2]
            if write_log:
                self.write_log()

    def load_setting(self, chatgpt_setting):
        if os.path.isfile(chatgpt_setting):
            with open(chatgpt_setting, 'r', encoding='UTF-8') as f:
                self.setting_content = f.read()
            self.setting_name = os.path.splitext(os.path.basename(chatgpt_setting))[0]
        else:
            self.setting_content = ''
            self.setting_name = 'default'
        self.add_search_content()

    def send_to_chatgpt(self, content, write_log=True):
        self.chatgpt_messages.append({"role": "user", "content": content})
        result = self.send_to_chatgpt_main()
        self.chatgpt_messages.append({"role": "assistant", "content": result})
        if write_log:
            self.write_log()
        return result

    def get_system_content(self):
        system_content = '' + self.setting_content
        for search_history_content in self.search_history_contents:
            system_content += '\n* The meaning of "' + search_history_content[0] + '" is as follows:\n' + search_history_content[1] + '\n'
        return system_content

    def send_to_chatgpt_main(self, search=True):
        system_content = self.get_system_content()
        self.lock_chatgpt()
        if search:
            chatgpt_response = openai.ChatCompletion.create(
                model=self.model,
                messages=[{"role": "system", "content": system_content}] + self.chatgpt_messages,
                functions=self.chatgpt_functions
            )
        else:
            chatgpt_response = openai.ChatCompletion.create(
                model=self.model,
                messages=[{"role": "system", "content": system_content}] + self.chatgpt_messages
            )
        self.unlock_chatgpt()
        if "function_call" in chatgpt_response["choices"][0]["message"].keys():
            function_call = chatgpt_response["choices"][0]["message"]["function_call"]
            if function_call is not None and function_call["name"] == "search_history":
                func_args = json.loads(function_call["arguments"])
                keywords = func_args["keywords"]
                is_searched = False
                for item in self.search_history_contents:
                    if item[0] == keywords:
                        is_searched = True
                        break
                if is_searched:
                    result = self.send_to_chatgpt_main(False)
                else:
                    self.search_keywords(keywords)
                    result = self.send_to_chatgpt_main(True)
        else:
            result = str(chatgpt_response["choices"][0]["message"]["content"])
        #print(result, file=sys.stderr)
        return result

    def search_keywords(self, keywords):
        self.add_search_content()

        client = meilisearch.Client(self.meilisearch_url, self.meilisearch_key)
        index = client.index(self.setting_name)

        try:
            search_result = index.search(
                keywords,
                {
                    'limit': self.search_limit,
                    'sort': ['mtime:desc']
                })
        except:
            self.search_history_contents.append((keywords, 'Not Found.'))
            return
        if len(search_result['hits']) == 0:
            self.search_history_contents.append((keywords, 'Not Found.'))
            return

        encoding = tiktoken.encoding_for_model(self.model)
        chatgpt_messages_content = 'Summarize the information for "' + keywords + '" from the following conversations.\n\n'
        token_count_all = 0
        for hit in search_result['hits']:
            token_count = len(encoding.encode(hit['messages'])) + 1
            if token_count_all + token_count >= 4096 * 3 / 4:
                break
            chatgpt_messages_content += hit['messages'] + "\n"
            token_count_all += token_count

        self.lock_chatgpt()
        chatgpt_response = openai.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "user", "content": chatgpt_messages_content}],
        )
        self.unlock_chatgpt()
        self.search_history_contents.append((keywords, str(chatgpt_response["choices"][0]["message"]["content"])))

    def lock_chatgpt(self):
        while self.is_send_to_chatgpt:
            time.sleep(0)
        self.is_send_to_chatgpt = True
        sleep_time = 0.5 - (time.time() - self.last_time_chatgpt)
        if sleep_time > 0.0:
            time.sleep(sleep_time)
        self.last_time_chatgpt = time.time()

    def unlock_chatgpt(self):
        self.is_send_to_chatgpt = False

    def get_log_file_name(self):
        return os.path.join(self.log_dir_name, self.setting_name, f"{self.log_index:09}.json")

    def write_log(self):
        if self.log_dir_name is None:
            return
        log_dir_char_name = os.path.join(self.log_dir_name, self.setting_name)
        os.makedirs(log_dir_char_name, exist_ok=True)
        master_file_name = os.path.join(log_dir_char_name, 'master.json')
        if os.path.isfile(master_file_name):
            with open(master_file_name, 'r', encoding='UTF-8') as f:
                master_json = json.load(f)
        else:
            master_json = {}
            master_json['file_count'] = 0
            master_json['not_send_files'] = []
        if self.log_index <= 0:
            self.log_index = master_json['file_count']
            master_json['file_count'] += 1
        log_file_name = os.path.join(log_dir_char_name, f"{self.log_index:09}.json")
        with open(log_file_name, 'w', encoding='UTF-8') as f:
            json_contents = {
                'messages': [{"role": "system", "content": self.get_system_content()}] + self.chatgpt_messages,
                'others': {
                    'setting_content': self.setting_content,
                    'setting_name': self.setting_name,
                    'search_history_contents': self.search_history_contents
                }
            }
            json.dump(json_contents, f, ensure_ascii=False)
        if not self.log_index in master_json['not_send_files']:
            master_json['not_send_files'].append(self.log_index)
        with open(master_file_name, 'w', encoding='UTF-8') as f:
            json.dump(master_json, f, ensure_ascii=False)

    def clear(self):
        self.chatgpt_messages = []
        self.search_history_contents = []
        self.log_index = -1

    def add_search_content(self):
        log_dir_char_name = os.path.join(self.log_dir_name, self.setting_name)
        master_file_name = os.path.join(log_dir_char_name, 'master.json')
        if not os.path.isfile(master_file_name):
            return
        with open(master_file_name, 'r', encoding='UTF-8') as f:
            master_json = json.loads(f.read())
        if len(master_json['not_send_files']) <= 0:
            return
        contents = []
        for index in master_json['not_send_files']:
            log_file_name = os.path.join(log_dir_char_name, f"{index:09}.json")
            mtime = os.path.getmtime(log_file_name)
            with open(log_file_name, 'r', encoding='UTF-8') as f:
                log_json = json.load(f)
            contents.append({
                'id': index,
                'messages': json.dumps(log_json['messages'], ensure_ascii=False),
                'others': json.dumps(log_json['others'], ensure_ascii=False),
                'mtime': mtime
            })
        
        client = meilisearch.Client(self.meilisearch_url, self.meilisearch_key)
        index = client.index(self.setting_name)

        index.update_searchable_attributes([
            'messages'
        ])
        index.update_filterable_attributes([
            'id'
        ])
        index.update_sortable_attributes([
            'mtime'
        ])

        add_result = index.add_documents(contents)
        status = 'enqueued'
        while status == 'enqueued' or status == 'processing':
            time.sleep(0.1)
            status = client.get_task(add_result.task_uid).status
            if status == 'failed' or status == 'canceled':
                print('add_search_content() is ' + status + '.', file=sys.stderr)
                return

        update_files = master_json['not_send_files']
        master_json['not_send_files'] = []
        with open(master_file_name, 'w', encoding='UTF-8') as f:
            json.dump(master_json, f, ensure_ascii=False)

        for index in update_files:
            log_file_name = os.path.join(log_dir_char_name, f"{index:09}.json")
            os.remove(log_file_name)

    def search_log(self, setting_name, index_id):
        self.add_search_content()

        client = meilisearch.Client(self.meilisearch_url, self.meilisearch_key)
        index = client.index(setting_name)
        try:
            get_result = index.get_documents({
                'limit': 1,
                'filter': 'id = ' + str(index_id)
            })
        except Exception as e:
            print('This log is not found.', file=sys.stderr)
            return
        self.load_log_dict(index_id, json.loads(get_result.results[0].messages), json.loads(get_result.results[0].others))