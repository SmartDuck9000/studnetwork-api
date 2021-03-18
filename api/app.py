from flask import Flask, request, jsonify, render_template
from flask_cors import CORS, cross_origin

import config
from Controller import controller

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

@app.route('/<path:path>', methods=['GET'])
@cross_origin()
def index(path):
    return app.send_static_file(path)

@app.route('/api/login/<string:code>', methods=['GET'])
@cross_origin()
def login(code):
    token = controller.login(code)
    return jsonify({"token": token})


@app.route('/api/users/<string:token>', methods=['GET', 'POST'])
@cross_origin()
def user_request(token):
    if request.method == 'GET':
        return jsonify(controller.get_user(token))
    elif request.method == 'POST':
        controller.post_user(token, request.get_json(force=True))
        return jsonify({})


@app.route('/api/users/exit/<string:token>', methods=['POST'])
@cross_origin()
def exit_user(token):
    status_code = controller.exit_user(token)
    return jsonify({}), status_code


@app.route('/api/graph/<int:depth>/<string:token>', methods=['POST'])
@cross_origin()
def get_graph(depth, token):
    filters = request.get_json(force=True)
    graph = controller.get_graph(token, filters, depth)
    return jsonify(graph)


if __name__ == "__main__":
    app.run(host=config.host, port=config.port)
