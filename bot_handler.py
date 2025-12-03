import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
        
        # Сообщения с HTML форматированием
        self.welcome_message = """🎉 <b>Welcome to Cosmo - The Market of NFT with the Least Commission on Telegram!</b>

🌟 <b>Why choose Cosmo?</b>
✅ <b>Lowest commissions</b> in the market
✅ <b>Secure transactions</b> with smart contracts
✅ <b>Instant NFT transfers</b>
✅ <b>24/7 support</b>

📊 <b>Current statistics:</b>
👥 Users: <code>15,432+</code>
🖼️ NFTs listed: <code>8,754+</code>
💎 Total volume: <code>2,450 ETH</code>

📣 <b>Start your NFT journey today!</b>"""
        
        self.help_message = """🆘 <b>Help Center</b>

<b>Available commands:</b>
/start - Welcome message and main menu
/history - View your action history
/mygifts - Check your received gifts
/market - Browse NFT marketplace
/help - Show this help message

<b>For administrators:</b>
/sentnft [user_id] [gift_link] [sender] - Record NFT gift

<b>Support:</b>
If you need assistance, contact @cosmo_support"""
        
        self.marketplace_message = """🛒 <b>NFT Marketplace</b>

<b>Featured Collections:</b>
🎨 <b>Cosmo Genesis</b> - Limited edition artworks
🐲 <b>DragonVerse</b> - Fantasy dragon NFTs
🌌 <b>Space Explorers</b> - Cosmic adventure series
🎭 <b>Digital Masks</b> - Anonymous art collective

<b>Hot Auctions:</b>
🔥 #001 - "Cosmic Dawn" - Current bid: 2.5 ETH
🔥 #042 - "Digital Dragon" - Current bid: 1.8 ETH
🔥 #099 - "Neon Dreams" - Current bid: 3.2 ETH

<b>Browse more:</b>
👉 <a href="https://t.me/cosmonftbot?start=market">View All NFTs</a>
👉 <a href="https://t.me/cosmonftbot?start=auctions">Live Auctions</a>
👉 <a href="https://t.me/cosmonftbot?start=new">New Listings</a>"""
    
    def create_welcome_keyboard(self, user_id):
        """Создание клавиатуры с кнопкой истории"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📜 History of Actions", callback_data=f"history_{user_id}")],
            [InlineKeyboardButton("🛒 Browse NFTs", url="https://t.me/cosmonftbot?start=market")],
            [InlineKeyboardButton("📢 Join Channel", url="https://t.me/cosmonft")]
        ])
        return keyboard
    
    def create_history_keyboard(self, user_id):
        """Создание клавиатуры для истории"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 View Gifts", callback_data=f"gifts_{user_id}")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data=f"back_{user_id}")]
        ])
        return keyboard
    
    async def start_bot(self):
        """Запуск бота"""
        try:
            self.app = Client(
                "cosmo_market_bot",
                api_id=self.api_id,
                api_hash=self.api_hash,
                bot_token=self.bot_token,
                in_memory=True
            )
            
            # Регистрируем обработчики
            self.app.on_message(filters.private)(self.handle_message)
            self.app.on_callback_query()(self.handle_callback)
            
            logger.info("🤖 Бот CosmoMarket запускается...")
            await self.app.start()
            logger.info("✅ Бот CosmoMarket успешно запущен")
            
            # Бесконечный цикл
            await self.idle()
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска бота: {e}")
        finally:
            if self.app:
                await self.app.stop()
    
    async def handle_message(self, client, message):
        """Обработка входящих сообщений"""
        try:
            user_id = message.from_user.id
            user_name = message.from_user.username or message.from_user.first_name
            
            logger.info(f"📨 Сообщение от user_id: {user_id}, текст: {message.text}")
            
            # Отправляем приветственное сообщение
            await client.send_message(
                chat_id=user_id,
                text=self.welcome_message,
                reply_markup=self.create_welcome_keyboard(user_id),
                parse_mode="HTML"
            )
            
            logger.info(f"👋 Отправлено приветствие user_id: {user_id}")
            
            # Добавляем действие "received_welcome" в историю
            add_user_action(
                user_id=user_id,
                action_type="received_welcome",
                action_details="Получено приветственное сообщение от бота",
                from_user="@cosmo_bot"
            )
            
            # Обрабатываем команды
            if message.text:
                await self.process_commands(client, message)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
    
    async def process_commands(self, client, message):
        """Обработка команд пользователя"""
        text = message.text.lower()
        user_id = message.from_user.id
        
        if "/start" in text:
            # Уже обработано
            pass
        elif "/help" in text or "помощь" in text:
            await self.send_help_message(client, user_id)
        elif "/history" in text:
            await self.show_history(client, user_id)
        elif "/sentnft" in text:
            await self.process_sent_nft_command(client, message)
        elif "/mygifts" in text or "/gifts" in text:
            await self.show_user_gifts(client, user_id)
        elif "/market" in text:
            await self.show_marketplace(client, user_id)
    
    async def send_help_message(self, client, user_id):
        """Отправка сообщения помощи"""
        await client.send_message(
            user_id,
            self.help_message,
            parse_mode="HTML"
        )
    
    async def show_history(self, client, user_id, edit_message_id=None):
        """Показать историю действий пользователя"""
        actions = self.get_user_actions(user_id, limit=10)
        
        if not actions:
            history_text = "📜 <b>Your Action History</b>\n\nNo actions yet. Start interacting with Cosmo!"
        else:
            history_text = "📜 <b>Your Action History</b>\n\n"
            for i, action in enumerate(actions, 1):
                time_str = datetime.fromisoformat(action['timestamp']).strftime("%Y-%m-%d %H:%M")
                details = action['details'] if action['details'] else action['type']
                
                emoji = "🎁" if "gift" in action['type'] else "📝"
                
                if action['from_user']:
                    history_text += f"{emoji} <b>{details}</b>\n   👤 From: {action['from_user']}\n   ⏰ {time_str}\n\n"
                else:
                    history_text += f"{emoji} <b>{details}</b>\n   ⏰ {time_str}\n\n"
        
        if edit_message_id:
            await client.edit_message_text(
                chat_id=user_id,
                message_id=edit_message_id,
                text=history_text,
                reply_markup=self.create_history_keyboard(user_id),
                parse_mode="HTML"
            )
        else:
            await client.send_message(
                user_id,
                history_text,
                reply_markup=self.create_history_keyboard(user_id),
                parse_mode="HTML"
            )
    
    async def process_sent_nft_command(self, client, message):
        """Обработка команды /sentnft для записи NFT подарка"""
        try:
            # Проверяем, является ли отправитель администратором
            user_id = message.from_user.id
            if user_id not in [7843338024]:  # Ваш ID
                await client.send_message(
                    user_id,
                    "❌ This command is for administrators only.",
                    parse_mode="HTML"
                )
                return
            
            # Разбираем команду: /sentnft [target_user_id] [gift_link] [sender_username]
            parts = message.text.split()
            
            if len(parts) < 4:
                await client.send_message(
                    user_id,
                    "❌ <b>Usage:</b> <code>/sentnft &lt;target_user_id&gt; &lt;gift_link&gt; &lt;sender_username&gt;</code>\n\n"
                    "<b>Example:</b> <code>/sentnft 12345678 https://t.me/nft/giftexample @username</code>",
                    parse_mode="HTML"
                )
                return
            
            target_user_id = int(parts[1])
            gift_link = parts[2]
            sender_username = parts[3]
            
            # Проверяем ссылку
            if not gift_link.startswith(('http://', 'https://', 't.me/')):
                gift_link = f"https://{gift_link}"
            
            # Добавляем действие в историю
            success = add_user_action(
                user_id=target_user_id,
                action_type="nft_gift",
                action_details="Получен подарок NFT",
                from_user=sender_username,
                link=gift_link
            )
            
            if success:
                # Отправляем подтверждение администратору
                await client.send_message(
                    user_id,
                    f"✅ <b>Gift recorded successfully!</b>\n\n"
                    f"👤 <b>To user:</b> <code>{target_user_id}</code>\n"
                    f"🎁 <b>Gift link:</b> {gift_link}\n"
                    f"👤 <b>From:</b> {sender_username}\n\n"
                    f"✅ Action added to user's history.",
                    parse_mode="HTML"
                )
                
                # Отправляем уведомление пользователю о новом подарке
                try:
                    await client.send_message(
                        target_user_id,
                        f"🎉 <b>You received a new NFT gift!</b>\n\n"
                        f"🎁 <b>Gift from:</b> {sender_username}\n"
                        f"🔗 <b>View gift:</b> {gift_link}\n\n"
                        f"Check your gifts with /mygifts",
                        parse_mode="HTML"
                    )
                    
                    logger.info(f"✅ Уведомление о подарке отправлено user_id: {target_user_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось отправить уведомление пользователю: {e}")
                
                logger.info(f"✅ Записан NFT подарок для user_id {target_user_id} от {sender_username}")
            else:
                await client.send_message(
                    user_id,
                    "❌ Failed to record gift. Check server logs.",
                    parse_mode="HTML"
                )
                
        except ValueError:
            await client.send_message(
                message.from_user.id,
                "❌ <b>Error:</b> Invalid user ID format. User ID must be a number.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка обработки команды /sentnft: {e}")
            await client.send_message(
                message.from_user.id,
                f"❌ <b>Error:</b> {str(e)}",
                parse_mode="HTML"
            )
    
    async def handle_callback(self, client, callback_query):
        """Обработка callback запросов от кнопок"""
        try:
            user_id = callback_query.from_user.id
            data = callback_query.data
            
            if data.startswith("history_"):
                target_user_id = int(data.split("_")[1])
                if target_user_id == user_id:
                    await self.show_history(client, user_id, callback_query.message.id)
                else:
                    await callback_query.answer("This history is not for you!", show_alert=True)
            
            elif data.startswith("gifts_"):
                target_user_id = int(data.split("_")[1])
                if target_user_id == user_id:
                    await self.show_user_gifts(client, user_id, callback_query.message.id)
                else:
                    await callback_query.answer("These gifts are not for you!", show_alert=True)
            
            elif data.startswith("back_"):
                target_user_id = int(data.split("_")[1])
                if target_user_id == user_id:
                    await client.edit_message_text(
                        chat_id=user_id,
                        message_id=callback_query.message.id,
                        text=self.welcome_message,
                        reply_markup=self.create_welcome_keyboard(user_id),
                        parse_mode="HTML"
                    )
                else:
                    await callback_query.answer("Access denied!", show_alert=True)
            
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки callback: {e}")
            await callback_query.answer("Error occurred!", show_alert=True)
    
    def get_user_actions(self, user_id, limit=10):
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
    
    async def show_user_gifts(self, client, user_id, edit_message_id=None):
        """Показать подарки пользователя"""
        gifts = self.get_user_gifts(user_id)
        
        if not gifts:
            gifts_text = "🎁 <b>Your Gifts</b>\n\nNo gifts received yet. Keep interacting with the community!"
        else:
            gifts_text = "🎁 <b>Your Gifts</b>\n\n"
            for i, gift in enumerate(gifts, 1):
                time_str = datetime.fromisoformat(gift['timestamp']).strftime("%Y-%m-%d %H:%M")
                
                if gift['link']:
                    gifts_text += f"{i}. <b>{gift['details']}</b>\n   🔗 <a href=\"{gift['link']}\">View Gift</a>\n   👤 From: {gift['from_user']}\n   ⏰ {time_str}\n\n"
                else:
                    gifts_text += f"{i}. <b>{gift['details']}</b>\n   👤 From: {gift['from_user']}\n   ⏰ {time_str}\n\n"
        
        if edit_message_id:
            await client.edit_message_text(
                chat_id=user_id,
                message_id=edit_message_id,
                text=gifts_text,
                reply_markup=self.create_history_keyboard(user_id),
                parse_mode="HTML"
            )
        else:
            await client.send_message(
                user_id,
                gifts_text,
                reply_markup=self.create_history_keyboard(user_id),
                parse_mode="HTML"
            )
    
    def get_user_gifts(self, user_id):
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
    
    async def show_marketplace(self, client, user_id):
        """Показать маркетплейс NFT"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ Browse All", url="https://t.me/cosmonftbot?start=market")],
            [InlineKeyboardButton("🔥 Live Auctions", url="https://t.me/cosmonftbot?start=auctions")],
            [InlineKeyboardButton("💎 Premium NFTs", url="https://t.me/cosmonftbot?start=premium")]
        ])
        
        await client.send_message(
            user_id,
            self.marketplace_message,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    async def idle(self):
        """Бесконечное ожидание"""
        await asyncio.Event().wait()

async def main():
    """Основная функция запуска"""
    bot = CosmoMarketBot()
    await bot.start_bot()

if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🚀 Запуск бота CosmoMarket...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
