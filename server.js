import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';

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
  },
  {
    id: 4,
    name: "Celebration Cake",
    description: "Торт для праздников",
    imageUrl: "https://via.placeholder.com/300x300/FF6B6B/FFFFFF?text=🎂",
    price: 1.99,
    category: "emojis",
    isAvailable: true
  },
  {
    id: 5,
    name: "Magic Wand",
    description: "Волшебная палочка",
    imageUrl: "https://via.placeholder.com/300x300/9B59B6/FFFFFF?text=✨",
    price: 1.79,
    category: "animations",
    isAvailable: true
  },
  {
    id: 6,
    name: "Crown King",
    description: "Королевская корона",
    imageUrl: "https://via.placeholder.com/300x300/F1C40F/000000?text=👑",
    price: 3.49,
    category: "premium",
    isAvailable: true
  }
];

// Mock users storage (in memory)
let users = [];

// Routes
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    message: 'NFT Marketplace is running!',
    timestamp: new Date().toISOString(),
    database: 'Memory Storage'
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

// Telegram auth verification
app.post('/api/telegram/verify-auth', async (req, res) => {
  try {
    const { initData } = req.body;
    
    if (!initData) {
      return res.status(400).json({ success: false, error: 'No init data' });
    }

    // Mock user data for testing
    const userData = { 
      id: Math.floor(Math.random() * 1000000), 
      first_name: 'Telegram',
      last_name: 'User', 
      username: 'telegram_user'
    };
    
    // Check if user exists
    let user = users.find(u => u.telegramId === userData.id);

    if (!user) {
      // Create new user
      user = {
        id: users.length + 1,
        telegramId: userData.id,
        firstName: userData.first_name,
        lastName: userData.last_name,
        username: userData.username,
        isVerified: true,
        createdAt: new Date()
      };
      users.push(user);
    }

    res.json({
      success: true,
      user: {
        id: user.telegramId,
        firstName: user.firstName,
        lastName: user.lastName,
        username: user.username,
        isVerified: user.isVerified
      }
    });
    
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Create sample NFTs endpoint
app.post('/api/nft/create-sample', async (req, res) => {
  try {
    res.json({ success: true, message: 'Sample NFTs are pre-loaded' });
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
  
  console.log(`✅ Ready! NFTs in memory: ${sampleNFTs.length}`);
});
