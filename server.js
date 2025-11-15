import express from 'express';
import cors from 'cors';
import mongoose from 'mongoose';
import dotenv from 'dotenv';

dotenv.config();

const app = express();

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('frontend'));

// Simple User model
const userSchema = new mongoose.Schema({
  telegramId: { type: Number, required: true, unique: true },
  phone: { type: String },
  firstName: { type: String, required: true },
  lastName: { type: String },
  username: { type: String },
  isVerified: { type: Boolean, default: false },
  createdAt: { type: Date, default: Date.now }
});

const User = mongoose.model('User', userSchema);

// Simple NFT model
const nftSchema = new mongoose.Schema({
  name: { type: String, required: true },
  description: { type: String },
  imageUrl: { type: String, required: true },
  price: { type: Number, required: true },
  category: { type: String, required: true },
  isAvailable: { type: Boolean, default: true },
  createdAt: { type: Date, default: Date.now }
});

const NFT = mongoose.model('NFT', nftSchema);

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
    const nfts = await NFT.find({ isAvailable: true });
    res.json({ success: true, nfts });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/nft/create-sample', async (req, res) => {
  try {
    const sampleNFTs = [
      {
        name: "Golden Star",
        description: "Блестящая золотая звезда",
        imageUrl: "https://via.placeholder.com/300x300/FFD700/000000?text=⭐",
        price: 0.99,
        category: "stickers"
      },
      {
        name: "Heart Gift",
        description: "Подарок в виде сердца",
        imageUrl: "https://via.placeholder.com/300x300/FF69B4/FFFFFF?text=💝",
        price: 1.49,
        category: "stickers"
      },
      {
        name: "Diamond Premium",
        description: "Роскошный бриллиант",
        imageUrl: "https://via.placeholder.com/300x300/B9F2FF/000000?text=💎",
        price: 2.99,
        category: "premium"
      }
    ];

    await NFT.deleteMany({});
    const createdNFTs = await NFT.insertMany(sampleNFTs);

    res.json({ 
      success: true, 
      message: 'Sample NFTs created',
      nfts: createdNFTs 
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Telegram auth verification
app.post('/api/telegram/verify-auth', async (req, res) => {
  try {
    const { initData } = req.body;
    
    // Simple validation - in production use proper Telegram validation
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
    
    let user = await User.findOne({ telegramId: userData.id });
    if (!user) {
      user = new User({
        telegramId: userData.id,
        firstName: userData.first_name,
        lastName: userData.last_name,
        username: userData.username,
        isVerified: true
      });
      await user.save();
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

// Connect to MongoDB and start server
async function startServer() {
  try {
    console.log('🔄 Connecting to MongoDB...');
    await mongoose.connect(process.env.MONGODB_URI);
    console.log('✅ MongoDB connected successfully');
    
    // Create sample NFTs if none exist
    const nftCount = await NFT.countDocuments();
    if (nftCount === 0) {
      await NFT.create({
        name: "Welcome NFT",
        description: "Your first NFT gift",
        imageUrl: "https://via.placeholder.com/300x300/667eea/ffffff?text=WELCOME",
        price: 0.99,
        category: "premium"
      });
      console.log('✅ Sample NFT created');
    }
    
    const PORT = process.env.PORT || 3000;
    app.listen(PORT, () => {
      console.log(`🚀 Server running on port ${PORT}`);
      console.log(`📱 Health check: http://localhost:${PORT}/health`);
      console.log(`🏠 Main page: http://localhost:${PORT}/`);
      console.log(`🛍️ Marketplace: http://localhost:${PORT}/marketplace`);
    });
    
  } catch (error) {
    console.error('❌ Server startup error:', error);
    process.exit(1);
  }
}

startServer();
