#!/usr/bin/env python

from flask import Flask, render_template, request
from sqloptitree import SQLQuery

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/optimize', methods=['POST'])
def optimize():
    sql = SQLQuery(request.form['sql'])
    if not sql.is_valid():
        error = 'Your SQL Query syntax is invalid!'
        return render_template('error.html', error=error)

    return render_template('results.html', steps=sql.optimize())

if __name__ == '__main__':
    app.run(port=5000, debug=True)
