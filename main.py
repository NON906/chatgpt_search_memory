#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import gradio as gr
from chatgpt_search_memory.main_api import MainApi

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
        main_api = MainApi(f.read(), loaded_json['model'])
else:
    main_api = MainApi(None, loaded_json['model'])

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
    if not name in loaded_json['saves'].keys():
        return chat_history

    main_api.load_log(loaded_json['saves'][name])

    chat_history = []
    for loop in range(0, len(main_api.chatgpt_messages), 2):
        chat_history.append((main_api.chatgpt_messages[loop], main_api.chatgpt_messages[loop + 1]))

    return chat_history

def chatgpt_save(name: str):
    if name == '':
        return gr.update()
    main_api.write_log()
    loaded_json['saves'][name] = main_api.get_log_file_name()
    with open('./save/settings.json', 'w', encoding='UTF-8') as f:
        json.dump(loaded_json, f)
    return gr.update(choices=list(loaded_json['saves'].keys()))

def chatgpt_delete(name: str):
    if not name in loaded_json['saves'].keys():
        return gr.update()
    del loaded_json['saves'][name]
    with open('./save/settings.json', 'w', encoding='UTF-8') as f:
        json.dump(loaded_json, f)
    return gr.update(value='', choices=list(loaded_json['saves'].keys()))

if __name__ == "__main__":
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
                    txt_file_path = gr.Dropdown(label='Conversation Name', allow_custom_value=True, choices=loaded_json['saves'].keys())
                    with gr.Column():
                        btn_load = gr.Button(value='Load')
                        btn_load.click(fn=chatgpt_load, inputs=[txt_file_path, chatbot], outputs=chatbot)
                        btn_save = gr.Button(value='Save')
                        btn_save.click(fn=chatgpt_save, inputs=txt_file_path, outputs=txt_file_path)
                        btn_delete = gr.Button(value='Delete')
                        btn_delete.click(fn=chatgpt_delete, inputs=txt_file_path, outputs=txt_file_path)

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

    block_interface.launch()