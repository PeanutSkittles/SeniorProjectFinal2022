# -*- coding: utf-8 -*-
"""
Created on Sun Apr 10 13:43:56 2022

@author: Mike
"""

from flask import Flask, render_template, request
import threading
# from time import sleep

power_level = '-'

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/power')
@app.route('/power/<level>')
def power(level=None):
    global power_level

    if level != None:
        power_level = level

    return str(power_level)

@app.route('/set_filter_value', methods=['POST'])
def set_filter_value():
    json       = request.get_json()
    name       = json['name']        # 'filter1_color', 'filter1_freq', etc.
    filter_num = int(json['filter']) # 1, 2, 3
    key        = json['key']         # 'color', 'freq'
    value      = json['value']       # '#RRGGBB', '1000', '2000', etc.

    print(json)

    if key == 'color':
        pass

    if key == 'freq':
        pass

    return ''

if __name__ == "__main__":
    app.run(debug=False)
