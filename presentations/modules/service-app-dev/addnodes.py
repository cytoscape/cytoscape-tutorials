#!/usr/bin/env python3
"""
Minimal Flask version of the Cytoscape Web Service-App example.

Run:
    pip install Flask flask-cors ndex2
    python addnodes.py
"""

import json
import random
import uuid
from time import time

from flask import Flask
from flask import jsonify
from flask import make_response
from flask import request
from ndex2.cx2 import RawCX2NetworkFactory


APP_VERSION = '1.0'
BASE_PATH = '/addnodes'
CY_WEB_ACTION = 'updateNetwork'
CORS_ALLOW_METHODS = 'DELETE, GET, PUT, POST, OPTIONS'
CORS_ALLOW_HEADERS = 'Content-Type, Authorization'

app = Flask(__name__)
app.url_map.strict_slashes = False

tasks = {}


def now_millis():
    return int(time() * 1000)


def extract_request_data(payload):
    data = payload.get('data') if isinstance(payload, dict) else payload
    if isinstance(data, str):
        try:
            return json.loads(data)
        except ValueError:
            return data
    return data


def add_random_nodes_to_cx2(data):
    """"""
    if not isinstance(data, list):
        return data

    # create a CX2 network from the input data, add two random nodes, and return the updated CX2
    network = RawCX2NetworkFactory().get_cx2network(data)
    for _ in range(50):
        suffix = random.randint(100000, 999999)
        network.add_node(
            attributes={
                'name': 'Random Node {0}'.format(suffix),
                'type': 'generated',
            },
            x=random.uniform(0, 1000),
            y=random.uniform(0, 1000))

    return network.to_cx2()


def task_status(task_id, task):
    return {
        'id': task_id,
        'status': task['status'],
        'message': task['message'],
        'progress': task['progress'],
        'wallTime': task['wallTime'],
        'startTime': task['startTime'],
    }


@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        response = make_response('', 204)
        response.headers['Allow'] = CORS_ALLOW_METHODS
        return response
    return None


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = CORS_ALLOW_METHODS
    response.headers['Access-Control-Allow-Headers'] = request.headers.get(
        'Access-Control-Request-Headers',
        CORS_ALLOW_HEADERS)
    return response


@app.get(BASE_PATH)
def get_metadata():
    return jsonify({
        'name': 'Python-Flask Simple Service-App',
        'version': APP_VERSION,
        'description': 'Adds two random nodes to the current CX2 network',
        'author': 'Cy Toscape',
        'email': 'NotSet',
        'citation': 'NA',
        'codeRepository': 'https://github.com/cytoscape/cytoscape-tutorials',
        'tutorial': 'https://github.com/cytoscape/cytoscape-tutorials',
        'website': 'https://tutorials.cytoscape.org',
        'parameters': [],
        'cyWebActions': [CY_WEB_ACTION],
        'cyWebMenuItem': {
            'root': 'Apps',
            'path': [
                {'name': 'Example Service App', 'gravity': 10},
                {'name': 'Python-Flask Simple Add Nodes', 'gravity': 10},
            ],
        },
        'serviceInputDefinition': {
            'type': 'network',
            'scope': 'dynamic',
            'inputNetwork': {
                'model': 'network',
                'format': 'cx2',
            },
        },
    })


@app.get(BASE_PATH + '/status')
def get_server_status():
    return jsonify({'status': 'ok', 'version': APP_VERSION})


@app.post(BASE_PATH)
def submit_task():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({'message': 'Request body must be JSON'}), 400

    task_id = str(uuid.uuid4())
    start_time = now_millis()
    result_data = add_random_nodes_to_cx2(extract_request_data(payload))
    tasks[task_id] = {
        'status': 'complete',
        'message': None,
        'progress': 100,
        'wallTime': now_millis() - start_time,
        'startTime': start_time,
        'result': [{'action': CY_WEB_ACTION, 'data': result_data}],
    }

    response = jsonify({'id': task_id})
    response.status_code = 202
    response.headers['Location'] = BASE_PATH + '/' + task_id
    return response


@app.get(BASE_PATH + '/<task_id>/status')
def get_task_status(task_id):
    task = tasks.get(task_id)
    if task is None:
        return jsonify({
            'id': task_id,
            'status': 'failed',
            'message': 'Task not found',
            'progress': 100,
            'wallTime': 0,
            'startTime': 0,
        }), 400

    return jsonify(task_status(task_id, task))


@app.get(BASE_PATH + '/<task_id>')
def get_task_result(task_id):
    task = tasks.get(task_id)
    if task is None:
        return jsonify({
            'id': task_id,
            'status': 'failed',
            'message': 'Task not found',
            'progress': 100,
            'wallTime': 0,
            'startTime': 0,
            'result': [],
        }), 400

    result = task_status(task_id, task)
    result['result'] = task['result']
    return jsonify(result)


@app.delete(BASE_PATH + '/<task_id>')
def delete_task(task_id):
    if task_id not in tasks:
        return jsonify({'message': 'Task not found'}), 400

    del tasks[task_id]
    return '', 204


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080)
