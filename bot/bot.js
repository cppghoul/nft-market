import TelegramBot from 'node-telegram-bot-api';
import dotenv from 'dotenv';

dotenv.config();

// Проверяем наличие токена бота
if (!process.env.TELEGRAM_BOT_TOKEN) {
  console.warn('⚠️ TELEGRAM_BOT_TOKEN not found. Bot will not start.');
  process.exit(1);
}

const token = process.env.TELEGRAM_BOT_TOKEN;
const bot = new TelegramBot(token, { 
  polling: {
    interval: 300,
    autoStart: true,
    params: {
      timeout: 10
    }
  }
});

console.log('🤖 Telegram Bot starting...');

// Обработчик команды /start
bot.onText(/\/start/, async (msg) => {
  const chatId = msg.chat.id;
  const miniAppUrl = `https://t.me/${process.env.TELEGRAM_BOT_USERNAME}/marketplace`;
  
  const welcomeText = `🎁 *Добро пожаловать в NFT Маркетплейс подарков!*

*Что вас ждет:*
• 🔐 *Безопасная авторизация* через Telegram
• 🛍️ *Уникальные NFT подарки* для любых occasion
• 💝 *Простое дарение* друзьям и близким
• 🎨 *Эксклюзивные коллекции* стикеров и эмодзи

*Как начать:*
1. Нажмите кнопку "🛍️ Открыть маркетплейс"
2. Авторизуйтесь через Telegram
3. Выбирайте понравившиеся NFT подарки
4. Дарите радость друзьям!

_Для начала работы нажмите кнопку ниже_ 👇`;

  try {
    await bot.sendMessage(chatId, welcomeText, {
      parse_mode: 'Markdown',
      reply_markup: {
        inline_keyboard: [
          [{ text: '🛍️ Открыть маркетплейс', web_app: { url: miniAppUrl } }],
          [
            { text: '📱 Наш канал', url: 'https://t.me/your_channel' },
            { text: '💬 Поддержка', url: 'https://t.me/your_support' },
            { text: 'ℹ️ Помощь', callback_data: 'help' }
          ]
        ]
      }
    });
  } catch (error) {
    console.error('Error sending start message:', error);
  }
});

// Обработчик команды /help
bot.onText(/\/help/, (msg) => {
  const chatId = msg.chat.id;
  sendHelpMessage(chatId);
});

// Обработчик callback запросов
bot.on('callback_query', async (query) => {
  const chatId = query.message.chat.id;
  const messageId = query.message.message_id;
  
  try {
    if (query.data === 'help') {
      await sendHelpMessage(chatId);
    }
    
    if (query.data === 'marketplace') {
      const miniAppUrl = `https://t.me/${process.env.TELEGRAM_BOT_USERNAME}/marketplace`;
      await bot.sendMessage(chatId, 'Нажмите кнопку ниже чтобы открыть маркетплейс:', {
        reply_markup: {
          inline_keyboard: [
            [{ text: '🎁 Открыть маркетплейс', web_app: { url: miniAppUrl } }]
          ]
        }
      });
    }
    
    // Подтверждаем callback запрос
    await bot.answerCallbackQuery(query.id);
  } catch (error) {
    console.error('Callback query error:', error);
    await bot.answerCallbackQuery(query.id, { text: 'Произошла ошибка' });
  }
});

// Обработчик обычных сообщений
bot.on('message', async (msg) => {
  // Игнорируем команды и служебные сообщения
  if (msg.text && msg.text.startsWith('/')) return;
  if (msg.web_app_data) return;
  
  const chatId = msg.chat.id;
  const miniAppUrl = `https://t.me/${process.env.TELEGRAM_BOT_USERNAME}/marketplace`;
  
  try {
    await bot.sendMessage(chatId, 
      'Для покупки NFT подарков откройте маркетплейс через кнопку ниже:', {
      reply_markup: {
        inline_keyboard: [
          [{ text: '🎁 Открыть маркетплейс', web_app: { url: miniAppUrl } }]
        ]
      }
    });
  } catch (error) {
    console.error('Message handler error:', error);
  }
});

// Обработчик ошибок бота
bot.on('error', (error) => {
  console.error('🤖 Bot error:', error);
});

// Обработчик polling ошибок
bot.on('polling_error', (error) => {
  console.error('🤖 Polling error:', error);
});

// Функция отправки справки
async function sendHelpMessage(chatId) {
  const helpText = `❓ *Часто задаваемые вопросы*

*1. Как купить NFT подарок?*
— Откройте маркетплейс
— Выберите понравившийся подарок
— Нажмите "Купить"
— Подтвердите покупку

*2. Как подарить NFT другу?*
— После покупки NFT будет в вашей коллекции
— Используйте функцию "Подарить"
— Выберите друга из списка контактов

*3. Что такое облачный пароль?*
— Это дополнительная защита вашего аккаунта
— Настраивается в настройках Telegram
— Рекомендуем включить для безопасности

*4. Поддерживаются ли возвраты?*
— NFT покупки окончательны
— Проверяйте подарки перед покупкой

*5. Есть ли техническая поддержка?*
— Да! Пишите нам: @your_support

📞 *Контакты поддержки:* @your_support
📢 *Новости и обновления:* @your_channel`;

  try {
    await bot.sendMessage(chatId, helpText, { 
      parse_mode: 'Markdown',
      reply_markup: {
        inline_keyboard: [
          [{ text: '🛍️ Открыть маркетплейс', callback_data: 'marketplace' }]
        ]
      }
    });
  } catch (error) {
    console.error('Error sending help message:', error);
  }
}

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('🤖 Bot shutting down...');
  bot.stopPolling();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('🤖 Bot shutting down...');
  bot.stopPolling();
  process.exit(0);
});

console.log('✅ Telegram Bot started successfully');
console.log(`📱 Bot username: @${process.env.TELEGRAM_BOT_USERNAME}`);

export default bot;
