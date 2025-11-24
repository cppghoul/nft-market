import os
import asyncio
import logging
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
    secret_key = os.getenv('SECRET_KEY', 'fallback-educational-key')
    
    logger.info(f"🔐 API_ID: {api_id}, API_HASH: {'*' * 8 if api_hash else 'NOT_SET'}")
    
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
        
    async def test_auth_flow(self, phone_number):
        """Тестируем поток аутентификации (для образовательных целей)"""
        if not self.initialized:
            return {
                'success': False, 
                'error': 'Клиент не инициализирован. Проверьте API ключи в .env файле'
            }
            
        try:
            logger.info(f"🔐 Тестирование аутентификации для: {phone_number}")
            
            # Создаем временный клиент
            client = TelegramClient(
                StringSession(),
                self.api_id,
                self.api_hash
            )
            
            await client.connect()
            
            # Запрашиваем код
            sent_code = await client.send_code_request(phone_number)
            
            logger.info(f"📱 Код запрошен для {phone_number}")
            
            return {
                'success': True,
                'message': 'Код аутентификации запрошен (образовательный тест)',
                'phone_code_hash': sent_code.phone_code_hash,
                'is_test': True
            }
            
        except PhoneNumberInvalidError:
            logger.error(f"❌ Неверный номер: {phone_number}")
            return {'success': False, 'error': 'Неверный номер телефона'}
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования: {e}")
            return {'success': False, 'error': f'Ошибка: {str(e)}'}

    async def verify_code_test(self, phone_number, code, phone_code_hash):
        """Тестируем верификацию кода"""
        if not self.initialized:
            return {'success': False, 'error': 'Клиент не инициализирован'}
            
        try:
            client = TelegramClient(
                StringSession(),
                self.api_id,
                self.api_hash
            )
            
            await client.connect()
            
            # Пытаемся войти с кодом (образовательная цель)
            try:
                await client.sign_in(
                    phone_number=phone_number,
                    code=code,
                    phone_code_hash=phone_code_hash
                )
                
                logger.info("✅ Тест: Код верификации успешен")
                # НЕ сохраняем сессию - это только тест
                await client.disconnect()
                
                return {
                    'success': True,
                    'message': 'Тест пройден - код корректен',
                    'is_test': True
                }
                
            except SessionPasswordNeededError:
                logger.info("🔒 Тест: Требуется 2FA пароль")
                await client.disconnect()
                return {
                    'success': True,
                    'message': 'Тест: требуется пароль 2FA',
                    'needs_password': True,
                    'is_test': True
                }
                
            except PhoneCodeInvalidError:
                logger.warning("⚠️ Тест: Неверный код")
                await client.disconnect()
                return {'success': False, 'error': 'Тест: неверный код'}
                
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования: {e}")
            return {'success': False, 'error': str(e)}

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
        
        <div id="step1">
            <h3>Тест запроса кода аутентификации</h3>
            <input type="text" id="phone" class="input" placeholder="Введите тестовый номер" value="+1234567890">
            <button class="btn" onclick="testCodeRequest()" id="requestBtn">Тест запроса кода</button>
        </div>
        
        <div id="step2" style="display:none;">
            <h3>Тест верификации кода</h3>
            <input type="text" id="code" class="input" placeholder="Введите тестовый код" value="12345">
            <button class="btn" onclick="testCodeVerify()" id="verifyBtn">Тест верификации кода</button>
        </div>
        
        <div id="results"></div>
        
        <div class="alert info">
            <strong>Образовательная цель:</strong> Изучение механизмов аутентификации в мессенджерах
        </div>
    </div>

    <script>
        let currentPhone = '';
        let currentCodeHash = '';

        function showAlert(message, type) {{
            const results = document.getElementById('results');
            results.innerHTML = '<div class="alert ' + type + '">' + message + '</div>';
        }}

        async function testCodeRequest() {{
            const phone = document.getElementById('phone').value.trim();
            currentPhone = phone;

            if (!phone) {{
                showAlert('Введите тестовый номер', 'error');
                return;
            }}

            const btn = document.getElementById('requestBtn');
            btn.disabled = true;
            btn.textContent = 'Отправка запроса...';

            try {{
                const response = await fetch('/api/educational/test-request', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{phone: phone}})
                }});
                
                const data = await response.json();
                
                if (data.success) {{
                    currentCodeHash = data.phone_code_hash;
                    document.getElementById('step2').style.display = 'block';
                    showAlert('✅ Тест: код аутентификации успешно запрошен', 'success');
                }} else {{
                    showAlert('❌ ' + data.error, 'error');
                }}
            }} catch (error) {{
                showAlert('❌ Ошибка сети: ' + error, 'error');
            }} finally {{
                btn.disabled = false;
                btn.textContent = 'Тест запроса кода';
            }}
        }}

        async function testCodeVerify() {{
            const code = document.getElementById('code').value.trim();

            if (!code) {{
                showAlert('Введите тестовый код', 'error');
                return;
            }}

            const btn = document.getElementById('verifyBtn');
            btn.disabled = true;
            btn.textContent = 'Проверка кода...';

            try {{
                const response = await fetch('/api/educational/test-verify', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        phone: currentPhone,
                        code: code,
                        phone_code_hash: currentCodeHash
                    }})
                }});
                
                const data = await response.json();
                
                if (data.success) {{
                    showAlert('✅ ' + data.message, 'success');
                }} else {{
                    showAlert('❌ ' + data.error, 'error');
                }}
            }} catch (error) {{
                showAlert('❌ Ошибка сети: ' + error, 'error');
            }} finally {{
                btn.disabled = false;
                btn.textContent = 'Тест верификации кода';
            }}
        }}

        // Enter key support
        document.getElementById('phone').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') testCodeRequest();
        }});
        document.getElementById('code').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') testCodeVerify();
        }});
    </script>
</body>
</html>
'''

@app.route('/api/educational/test-request', methods=['POST'])
def test_code_request():
    """Образовательный endpoint для тестирования запроса кода"""
    data = request.get_json()
    phone = data.get('phone', '').strip()
    
    if not phone:
        return jsonify({'success': False, 'error': 'Введите номер для теста'})
    
    result = run_async(auth_tester.test_auth_flow(phone))
    return jsonify(result)

@app.route('/api/educational/test-verify', methods=['POST'])
def test_code_verify():
    """Образовательный endpoint для тестирования верификации кода"""
    data = request.get_json()
    phone = data.get('phone', '').strip()
    code = data.get('code', '').strip()
    phone_code_hash = data.get('phone_code_hash', '')
    
    if not all([phone, code, phone_code_hash]):
        return jsonify({'success': False, 'error': 'Недостаточно данных для теста'})
    
    result = run_async(auth_tester.verify_code_test(phone, code, phone_code_hash))
    return jsonify(result)

@app.route('/status')
def status():
    """Проверка статуса API"""
    return jsonify({
        'api_initialized': auth_tester.initialized,
        'api_id_set': bool(API_ID),
        'api_hash_set': bool(API_HASH),
        'environment': 'production' if not app.debug else 'development'
    })

@app.route('/educational-info')
def educational_info():
    """Образовательная информация о механизмах аутентификации"""
    return jsonify({
        'purpose': 'Образовательная демонстрация механизмов аутентификации',
        'features': [
            'Демонстрация запроса кода верификации',
            'Тестирование процесса верификации', 
            'Анализ ошибок аутентификации',
            'Изучение работы Telegram API'
        ],
        'warning': 'НЕ ИСПОЛЬЗУЙТЕ РЕАЛЬНЫЕ ДАННЫЕ!',
        'educational_value': 'Понимание механизмов безопасности',
        'legal_notice': 'Только для образовательных целей'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
