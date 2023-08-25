#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import urllib.request
import subprocess
import platform
import argparse
import gradio as gr
from chatgpt_search_memory.main_api import MainApi

def wget(url: str, save_path: str):
    with urllib.request.urlopen(url) as u:
        with open(save_path, 'bw') as o:
            o.write(u.read())

if os.name == 'nt':
    if not os.path.isfile('./bin/meilisearch-windows-amd64.exe'):
        print('Download files...')
        os.makedirs('./bin', exist_ok=True)
        wget('https://github.com/meilisearch/meilisearch/releases/download/v1.3.1/meilisearch-windows-amd64.exe', './bin/meilisearch-windows-amd64.exe')
        wget('https://raw.githubusercontent.com/meilisearch/meilisearch/main/LICENSE', './bin/LICENSE')
    subprocess.Popen(['./bin/meilisearch-windows-amd64.exe', '--master-key', 'aSampleMasterKey'])
else:
    if not os.path.isfile('./bin/meilisearch'):
        print('Download files...')
        os.makedirs('./bin', exist_ok=True)
        os.chdir('./bin')
        subprocess.run('curl -L https://install.meilisearch.com | sh', shell=True)
        os.chdir('..')
    subprocess.Popen(['./bin/meilisearch', '--master-key', 'aSampleMasterKey'])

if os.path.isfile('./save/settings.json'):
    with open('./save/settings.json', 'r', encoding='UTF-8') as f:
        loaded_json = json.load(f)
else:
    loaded_json = {
        'model': 'gpt-3.5-turbo',
        'saves': {}
    }

if os.path.isfile('chatgpt_api.txt'):
    with open('chatgpt_api.txt', 'r', encoding='UTF-8') as f:
        txt_apikey_value = f.read()
        main_api = MainApi(txt_apikey_value, loaded_json['model'])
else:
    main_api = MainApi(None, loaded_json['model'])
    txt_apikey_value = ''

def chatgpt_generate(text_input_str: str, chat_history):
    result = main_api.send_to_chatgpt(text_input_str)
    chat_history.append((text_input_str, result))
    return ['', chat_history]

def chatgpt_regenerate(chat_history):
    if chat_history is not None and len(chat_history) > 0:
        input_text = chat_history[-1][0]
        chat_history = chat_history[:-1]

        main_api.remove_last_conversation()
        result = main_api.send_to_chatgpt(input_text)
        chat_history.append((input_text, result))
    return chat_history

def chatgpt_remove_last(text_input_str: str, chat_history):
    if chat_history is None or len(chat_history) <= 0:
        return [text_input_str, chat_history]

    input_text = chat_history[-1][0]
    chat_history = chat_history[:-1]

    main_api.remove_last_conversation()

    ret_text = text_input_str
    if text_input_str is None or text_input_str == '':
        ret_text = input_text
    
    return [ret_text, chat_history]

def chatgpt_clear():
    main_api.clear()
    return []

def chatgpt_load(name: str, chat_history):
    global loaded_json

    if not name in loaded_json['saves'].keys():
        return chat_history

    setting_name, id_index = loaded_json['saves'][name]
    main_api.search_log(setting_name, id_index)

    chat_history = []
    for loop in range(0, len(main_api.chatgpt_messages), 2):
        chat_history.append((main_api.chatgpt_messages[loop]['content'], main_api.chatgpt_messages[loop + 1]['content']))

    return chat_history

def chatgpt_save(name: str):
    global loaded_json

    if name == '':
        loop = 0
        name = 'Untitled-' + str(loop)
        while name in loaded_json['saves'].keys():
            loop += 1
            name = 'Untitled-' + str(loop)
    main_api.write_log()
    loaded_json['saves'][name] = (main_api.setting_name, main_api.log_index)
    with open('./save/settings.json', 'w', encoding='UTF-8') as f:
        json.dump(loaded_json, f, ensure_ascii=False)
    return gr.update(value=name, choices=list(loaded_json['saves'].keys()))

def chatgpt_delete(name: str):
    global loaded_json

    if not name in loaded_json['saves'].keys():
        return gr.update()
    del loaded_json['saves'][name]
    with open('./save/settings.json', 'w', encoding='UTF-8') as f:
        json.dump(loaded_json, f, ensure_ascii=False)
    return gr.update(value='', choices=list(loaded_json['saves'].keys()))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--disable_browser_open', action='store_true')
    args = parser.parse_args()

    with gr.Blocks() as block_interface:
        with gr.Row():
            gr.Markdown(value='## Chat')
        with gr.Row():
            with gr.Column():
                chatbot = gr.Chatbot()
                text_input = gr.Textbox(lines=2, label='')
                btn_generate = gr.Button(value='Chat', variant='primary')
                with gr.Row():
                    btn_regenerate = gr.Button(value='Regenerate')
                    btn_remove_last = gr.Button(value='Remove last')
                    btn_clear = gr.Button(value='Clear all')
                with gr.Row():
                    txt_file_path = gr.Dropdown(label='Conversation Name', allow_custom_value=True, choices=list(loaded_json['saves'].keys()))
                    with gr.Column():
                        btn_load = gr.Button(value='Load')
                        btn_load.click(fn=chatgpt_load, inputs=[txt_file_path, chatbot], outputs=chatbot)
                        btn_save = gr.Button(value='Save')
                        btn_save.click(fn=chatgpt_save, inputs=txt_file_path, outputs=txt_file_path)
                        btn_delete = gr.Button(value='Delete')
                        btn_delete.click(fn=chatgpt_delete, inputs=txt_file_path, outputs=txt_file_path)

        with gr.Row():
            gr.Markdown(value='## Settings')
        with gr.Row():
            txt_apikey = gr.Textbox(value=txt_apikey_value, label='API Key')
            btn_apikey_save = gr.Button(value='Save And Reflect')
            def apikey_save(setting_api: str):
                with open('./chatgpt_api.txt', 'w') as f:
                    f.write(setting_api)
                main_api.change_apikey(setting_api)
            btn_apikey_save.click(fn=apikey_save, inputs=txt_apikey)
        with gr.Row():
            txt_chatgpt_model = gr.Textbox(value=loaded_json['model'], label='ChatGPT Model Name')
            btn_chatgpt_model_save = gr.Button(value='Save And Reflect')
            def chatgpt_model_save(setting_model: str):
                loaded_json['model'] = setting_model
                with open('./save/settings.json', 'w') as f:
                    json.dump(loaded_json, f)
                main_api.change_model(setting_model)
            btn_chatgpt_model_save.click(fn=chatgpt_model_save, inputs=txt_chatgpt_model)

        btn_generate.click(fn=chatgpt_generate,
            inputs=[text_input, chatbot],
            outputs=[text_input, chatbot])
        btn_regenerate.click(fn=chatgpt_regenerate,
            inputs=chatbot,
            outputs=chatbot)
        btn_remove_last.click(fn=chatgpt_remove_last,
            inputs=[text_input, chatbot],
            outputs=[text_input, chatbot])
        btn_clear.click(fn=chatgpt_clear,
            outputs=chatbot)

    block_interface.launch(inbrowser=(not args.disable_browser_open))