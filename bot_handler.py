import asyncio
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import sqlite3
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Конфигурация бота
BOT_TOKEN = "8502577994:AAECfAO5batElBKd6H4eOnnLRCZvNLseQ-8"
API_ID = 39292191
API_HASH = "17e072b5e32301241934eb46ee82f918"

# История действий пользователей
USER_ACTIONS_DB = "user_actions.db"

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(USER_ACTIONS_DB)
    try:
        yield conn
    finally:
        conn.close()

def add_user_action(user_id, action_type, details="", from_user="", link=""):
    """Добавление действия в историю пользователя"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_actions (user_id, action_type, action_details, from_user, link)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, action_type, details, from_user, link))
            conn.commit()
        
        logger.info(f"📝 Добавлено действие для user_id {user_id}: {action_type}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления действия: {e}")
        return False

class CosmoMarketBot:
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.api_id = API_ID
        self.api_hash = API_HASH
        self.app = None
        
        self.welcome_message = """🎉 <b>Welcome to Cosmo - The Market of NFT with the Least Commission on Telegram!</b>

🌟 <b>Why choose Cosmo?</b>
✅ <b>Lowest commissions</b> in the market
✅ <b>Secure transactions</b> with smart contracts
✅ <b>Instant NFT transfers</b>
✅ <b>24/7 support</b>

📊 <b>Current statistics:</b>
🖼️ NFTs listed: <code>8,754+</code>

📣 <b>Start your NFT journey today!</b>"""
    
    def create_welcome_keyboard(self, user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📜 History of Actions", callback_data=f"history_{user_id}")],
            [InlineKeyboardButton("🛒 Browse NFTs", web_app=WebAppInfo(url="https://nft-market-production.up.railway.app/"))],
            [InlineKeyboardButton("📢 Join Channel", url="https://t.me/Cosmomrkt")]
        ])
        return keyboard
    
    def create_history_keyboard(self, user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 View Gifts", callback_data=f"gifts_{user_id}")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data=f"back_{user_id}")]
        ])
        return keyboard
    
    async def start_bot(self):
        try:
            self.app = Client(
                "cosmomarketrobot",
                api_id=self.api_id,
                api_hash=self.api_hash,
                bot_token=self.bot_token,
                in_memory=True
            )
            
            # Обработчик команды /start
            @self.app.on_message(filters.command("start"))
            async def start_handler(client, message):
                await self.handle_start(client, message)
            
            # Обработчик команды /sentnft
            @self.app.on_message(filters.command("sentnft"))
            async def sentnft_handler(client, message):
                await self.handle_sentnft(client, message)
            
            # Обработчик других команд
            @self.app.on_message(filters.command(["history", "mygifts", "gifts"]))
            async def commands_handler(client, message):
                await self.handle_commands(client, message)
            
            # Обработчик всех остальных сообщений
            @self.app.on_message(filters.private & ~filters.command(["start", "sentnft", "history", "mygifts", "gifts"]))
            async def message_handler(client, message):
                await self.handle_message(client, message)
            
            # Обработчик callback запросов
            @self.app.on_callback_query()
            async def callback_handler(client, callback_query):
                await self.handle_callback(client, callback_query)
            
            logger.info("🤖 Бот CosmoMarket запускается...")
            await self.app.start()
            logger.info("✅ Бот CosmoMarket успешно запущен")
            
            await self.idle()
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска бота: {e}")
        finally:
            if self.app:
                await self.app.stop()
    
    async def handle_start(self, client, message):
        """Обработка команды /start"""
        try:
            user_id = message.from_user.id
            
            await client.send_message(
                chat_id=user_id,
                text=self.welcome_message,
                reply_markup=self.create_welcome_keyboard(user_id),
                parse_mode=enums.ParseMode.HTML
            )
            
            # НЕ добавляем действие приветствия - только подарки
            logger.info(f"✅ Отправлено приветствие user_id: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки /start: {e}")
    
    async def handle_sentnft(self, client, message):
        """Обработка команды /sentnft"""
        try:
            user_id = message.from_user.id
            
            if user_id not in [7843338024]:
                await client.send_message(
                    user_id,
                    "❌ This command is for administrators only.",
                    parse_mode=enums.ParseMode.HTML
                )
                return
            
            parts = message.text.split()
            
            if len(parts) < 4:
                await client.send_message(
                    user_id,
                    "❌ <b>Usage:</b> <code>/sentnft &lt;user_id&gt; &lt;gift_link&gt; &lt;sender&gt;</code>\n\n"
                    "<b>Example:</b> <code>/sentnft 12345678 https://t.me/nft/giftexample @username</code>",
                    parse_mode=enums.ParseMode.HTML
                )
                return
            
            target_user_id = int(parts[1])
            gift_link = parts[2]
            sender_username = parts[3]
            
            if not gift_link.startswith(('http://', 'https://', 't.me/')):
                gift_link = f"https://{gift_link}"
            
            # Добавляем подарок в историю
            success = add_user_action(
                user_id=target_user_id,
                action_type="nft_gift",
                details="Был получен подарок",  # ← Форматированное сообщение
                from_user=sender_username,
                link=gift_link
            )
            
            if success:
                # Подтверждение администратору
                await client.send_message(
                    user_id,
                    f"✅ <b>Gift recorded successfully!</b>\n\n"
                    f"👤 <b>To user:</b> <code>{target_user_id}</code>\n"
                    f"🎁 <b>Gift link:</b> {gift_link}\n"
                    f"👤 <b>From:</b> {sender_username}\n\n"
                    f"✅ Action added to user's history.",
                    parse_mode=enums.ParseMode.HTML
                )
                
                # Уведомление пользователю о новом подарке
                try:
                    await client.send_message(
                        target_user_id,
                        f"🎉 <b>You received a new NFT gift!</b>\n\n"
                        f"🎁 <b>Gift from:</b> {sender_username}\n"
                        f"🔗 <b>View gift:</b> {gift_link}\n\n"
                        f"Check your gifts with /mygifts",
                        parse_mode=enums.ParseMode.HTML
                    )
                    logger.info(f"✅ Уведомление отправлено user_id: {target_user_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось отправить уведомление: {e}")
                
                logger.info(f"✅ Записан NFT подарок для {target_user_id} от {sender_username}")
            else:
                await client.send_message(
                    user_id,
                    "❌ Failed to record gift.",
                    parse_mode=enums.ParseMode.HTML
                )
                
        except ValueError:
            await client.send_message(
                message.from_user.id,
                "❌ <b>Error:</b> Invalid user ID.",
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"❌ Ошибка /sentnft: {e}")
            await client.send_message(
                message.from_user.id,
                f"❌ <b>Error:</b> {str(e)}",
                parse_mode=enums.ParseMode.HTML
            )
    
    async def handle_commands(self, client, message):
        """Обработка других команд"""
        try:
            user_id = message.from_user.id
            text = message.text.lower()
            
            if "/help" in text or "помощь" in text:
                await self.send_help(client, user_id)
            elif "/history" in text:
                await self.show_history(client, user_id)  # Показываем только подарки
            elif "/mygifts" in text or "/gifts" in text:
                await self.show_gifts(client, user_id)  # Показываем подарки
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки команды: {e}")
    
    async def handle_message(self, client, message):
        """Обработка обычных сообщений"""
        try:
            user_id = message.from_user.id
            
            await client.send_message(
                chat_id=user_id,
                text=self.welcome_message,
                reply_markup=self.create_welcome_keyboard(user_id),
                parse_mode=enums.ParseMode.HTML
            )
            
            logger.info(f"📨 Ответ на сообщение от user_id: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
    
    async def handle_callback(self, client, callback_query):
        """Обработка callback запросов"""
        try:
            user_id = callback_query.from_user.id
            data = callback_query.data
            
            if data.startswith("history_"):
                await self.show_history(client, user_id, callback_query.message.id)
            elif data.startswith("gifts_"):
                await self.show_gifts(client, user_id, callback_query.message.id)
            elif data.startswith("back_"):
                await client.edit_message_text(
                    chat_id=user_id,
                    message_id=callback_query.message.id,
                    text=self.welcome_message,
                    reply_markup=self.create_welcome_keyboard(user_id),
                    parse_mode=enums.ParseMode.HTML
                )
            
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"❌ Ошибка callback: {e}")
            await callback_query.answer("Error!", show_alert=True)
    async def show_history(self, client, user_id, edit_message_id=None):
        """Показываем только подарки (историю)"""
        gifts = self.get_user_gifts(user_id)
        
        if not gifts:
            text = "📜 <b>Your Gift History</b>\n\nNo gifts received yet."
        else:
            text = "📜 <b>Your Gift History</b>\n\n"
            for i, gift in enumerate(gifts, 1):
                time_str = datetime.fromisoformat(gift['timestamp']).strftime("%Y-%m-%d %H:%M")
                
                # Форматируем как "Был получен подарок t.me/nft/giftexample от пользователя @username"
                gift_text = f"{gift['details']}"
                if gift['link']:
                    # Извлекаем короткую ссылку из полного URL
                    if 't.me/' in gift['link']:
                        short_link = gift['link'].split('t.me/')[-1]
                        gift_text += f" t.me/{short_link}"
                    else:
                        gift_text += f" {gift['link']}"
                
                if gift['from_user']:
                    gift_text += f" от пользователя {gift['from_user']}"
                
                text += f"{i}. {gift_text}\n"
                text += f"   ⏰ {time_str}\n\n"
        
        if edit_message_id:
            await client.edit_message_text(
                user_id, edit_message_id, text,
                reply_markup=self.create_history_keyboard(user_id),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            await client.send_message(
                user_id, text,
                reply_markup=self.create_history_keyboard(user_id),
                parse_mode=enums.ParseMode.HTML
            )
    
    async def show_gifts(self, client, user_id, edit_message_id=None):
        """Показываем подарки (альтернативный вид)"""
        gifts = self.get_user_gifts(user_id)
        
        if not gifts:
            text = "🎁 <b>Your Gifts</b>\n\nNo gifts received yet."
        else:
            text = "🎁 <b>Your Gifts</b>\n\n"
            for i, gift in enumerate(gifts, 1):
                time_str = datetime.fromisoformat(gift['timestamp']).strftime("%Y-%m-%d %H:%M")
                
                text += f"{i}. <b>{gift['details']}</b>\n"
                if gift['link']:
                    text += f"   🔗 <a href=\"{gift['link']}\">View Gift</a>\n"
                if gift['from_user']:
                    text += f"   👤 From: {gift['from_user']}\n"
                text += f"   ⏰ {time_str}\n\n"
        
        if edit_message_id:
            await client.edit_message_text(
                user_id, edit_message_id, text,
                reply_markup=self.create_history_keyboard(user_id),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            await client.send_message(
                user_id, text,
                reply_markup=self.create_history_keyboard(user_id),
                parse_mode=enums.ParseMode.HTML
            )
    
    def get_user_actions(self, user_id, limit=10):
        """Получаем только действия типа nft_gift"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT action_type, action_details, from_user, link, timestamp
                    FROM user_actions 
                    WHERE user_id = ? AND action_type = 'nft_gift'
                    ORDER BY timestamp DESC LIMIT ?
                ''', (user_id, limit))
                
                return [{
                    'type': row[0],
                    'details': row[1],
                    'from_user': row[2],
                    'link': row[3],
                    'timestamp': row[4]
                } for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Ошибка получения действий: {e}")
            return []
    
    def get_user_gifts(self, user_id):
        """Получение всех подарков пользователя"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT action_type, action_details, from_user, link, timestamp
                    FROM user_actions
                    WHERE user_id = ? AND action_type = 'nft_gift'
                    ORDER BY timestamp DESC
                ''', (user_id,))
                
                return [{
                    'type': row[0],
                    'details': row[1],
                    'from_user': row[2],
                    'link': row[3],
                    'timestamp': row[4]
                } for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Ошибка получения подарков: {e}")
            return []
    
    async def idle(self):
        await asyncio.Event().wait()

async def main():
    bot = CosmoMarketBot()
    await bot.start_bot()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger.info("🚀 Запуск бота CosmoMarket...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
