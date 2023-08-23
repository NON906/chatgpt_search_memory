#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import gradio as gr
from chatgpt_search_memory.main_api import MainApi

if os.path.isfile('chatgpt_api.txt'):
    with open('chatgpt_api.txt', 'r', encoding='UTF-8') as f:
        main_api = MainApi(f.read())
else:
    main_api = MainApi()

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