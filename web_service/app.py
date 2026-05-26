from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='static', static_url_path='')

# 模拟数据库
USERS = {"admin": "password123", "testuser": "testpass"}
ITEMS = [
    {"id": 1, "name": "Apple", "category": "fruit", "price": 1.2},
    {"id": 2, "name": "Banana", "category": "fruit", "price": 0.5},
    {"id": 3, "name": "Carrot", "category": "vegetable", "price": 0.8},
    {"id": 4, "name": "Laptop", "category": "electronics", "price": 999.0},
]
VALID_TOKEN = "test-token-abc123"

# ================= 工具路由 =================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"code": 200, "msg": "ok", "data": {"status": "healthy"}})

# ================= API 路由 (供 pytest 测试) =================

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if username in USERS and USERS[username] == password:
        return jsonify({"code": 200, "msg": "success", "data": {"token": VALID_TOKEN, "username": username}})
    return jsonify({"code": 401, "msg": "Invalid credentials", "data": None}), 401

@app.route('/api/query', methods=['GET'])
def api_query():
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f"Bearer {VALID_TOKEN}":
        return jsonify({"code": 401, "msg": "Unauthorized", "data": None}), 401
        
    keyword = request.args.get('keyword', '').lower()
    category = request.args.get('category', '').lower()
    
    results = ITEMS
    if keyword:
        results = [item for item in results if keyword in item['name'].lower()]
    if category:
        results = [item for item in results if category in item['category'].lower()]
        
    return jsonify({"code": 200, "msg": "success", "data": results})

# ================= UI 路由 (供 Selenium 测试) =================

@app.route('/')
@app.route('/login')
def login_page():
    return send_from_directory('static', 'login.html')

@app.route('/query')
def query_page():
    return send_from_directory('static', 'query.html')

if __name__ == '__main__':
    print("Server running on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
