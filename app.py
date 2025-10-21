# app.py - Flask entrypoint
from flask import Flask, request, jsonify, render_template
from search.finder import find_official_url

app = Flask(__name__, template_folder="templates", static_folder="static")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def api_search():
    body = request.get_json(force=True, silent=True) or {}
    name = body.get('name') or request.form.get('name') or ''
    result = {'url': None, 'verified': False}
    if not name:
        return jsonify(result)
    url = find_official_url(name)
    if url:
        result['url'] = url
        result['verified'] = True
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)
