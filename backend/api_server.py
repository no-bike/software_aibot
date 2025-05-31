from flask import Flask, request, jsonify
from flask_cors import CORS
import configparser
import os

app = Flask(__name__)
CORS(app)

CONFIG_FILE = 'api.txt'

def load_models():
    """从配置文件加载模型信息"""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    
    models = []
    for section in config.sections():
        model = {
            'id': section.lower(),
            'name': section,
            'apiKey': config[section].get('API_KEY', ''),
            'url': config[section].get('API_BASE', '')
        }
        models.append(model)
    return models

def save_model(model_data):
    """保存新模型到配置文件"""
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    
    section = model_data['name'].upper()
    if section not in config:
        config[section] = {}
    
    config[section]['API_KEY'] = model_data['apiKey']
    config[section]['API_BASE'] = model_data['url']
    
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

def delete_model(model_name):
    """从配置文件中删除模型"""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    
    section = model_name.upper()
    if section in config:
        config.remove_section(section)
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)
        return True
    return False

@app.route('/api/models', methods=['GET'])
def get_models():
    """获取所有模型列表"""
    try:
        models = load_models()
        return jsonify(models)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/models', methods=['POST'])
def add_model():
    """添加新模型"""
    try:
        model_data = request.json
        if not all(k in model_data for k in ['name', 'apiKey', 'url']):
            return jsonify({'error': '缺少必要的字段'}), 400
        
        save_model(model_data)
        return jsonify({'message': '模型添加成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/models/<model_name>', methods=['DELETE'])
def remove_model(model_name):
    """删除指定模型"""
    try:
        if delete_model(model_name):
            return jsonify({'message': '模型删除成功'})
        return jsonify({'error': '模型不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 