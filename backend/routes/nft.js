import express from 'express';
import NFT from '../../database/models/NFT.js';
import User from '../../database/models/User.js';
import { authenticateToken } from './auth.js';

const router = express.Router();

// Get all NFTs with optional filtering
router.get('/', async (req, res) => {
  try {
    const { category, search, minPrice, maxPrice, sortBy = 'createdAt', sortOrder = 'desc' } = req.query;
    
    let query = { isAvailable: true };
    
    // Apply filters
    if (category && category !== 'all') {
      query.category = category;
    }
    
    if (search) {
      query.$or = [
        { name: { $regex: search, $options: 'i' } },
        { description: { $regex: search, $options: 'i' } }
      ];
    }
    
    if (minPrice || maxPrice) {
      query.price = {};
      if (minPrice) query.price.$gte = parseFloat(minPrice);
      if (maxPrice) query.price.$lte = parseFloat(maxPrice);
    }
    
    // Sort options
    const sortOptions = {};
    sortOptions[sortBy] = sortOrder === 'desc' ? -1 : 1;
    
    const nfts = await NFT.find(query)
      .populate('owner', 'telegramId firstName username')
      .sort(sortOptions);
    
    res.json({ 
      success: true, 
      nfts,
      total: nfts.length
    });
  } catch (error) {
    console.error('Get NFTs error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get NFT by ID
router.get('/:id', async (req, res) => {
  try {
    const nft = await NFT.findById(req.params.id)
      .populate('owner', 'telegramId firstName username');
    
    if (!nft) {
      return res.status(404).json({ success: false, error: 'NFT not found' });
    }
    
    res.json({ success: true, nft });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Create new NFT (protected)
router.post('/', authenticateToken, async (req, res) => {
  try {
    const { name, description, imageUrl, price, category, telegramStickerId } = req.body;
    
    // Validate required fields
    if (!name || !imageUrl || !price || !category) {
      return res.status(400).json({ 
        success: false, 
        error: 'Missing required fields: name, imageUrl, price, category' 
      });
    }
    
    const user = await User.findById(req.user.userId);
    if (!user) {
      return res.status(404).json({ success: false, error: 'User not found' });
    }
    
    const nft = new NFT({
      name,
      description,
      imageUrl,
      price: parseFloat(price),
      category,
      telegramStickerId,
      owner: user._id
    });
    
    await nft.save();
    await nft.populate('owner', 'telegramId firstName username');
    
    res.status(201).json({ 
      success: true, 
      message: 'NFT created successfully',
      nft 
    });
  } catch (error) {
    console.error('Create NFT error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Create sample NFTs (for demo)
router.post('/create-sample', async (req, res) => {
  try {
    const sampleNFTs = [
      {
        name: "Golden Star",
        description: "Блестящая золотая звезда для особых достижений",
        imageUrl: "https://via.placeholder.com/300x300/FFD700/000000?text=⭐",
        price: 0.99,
        category: "stickers",
        telegramStickerId: "gold_star_1"
      },
      {
        name: "Heart Gift",
        description: "Подарок в виде сердца с любовью",
        imageUrl: "https://via.placeholder.com/300x300/FF69B4/FFFFFF?text=💝",
        price: 1.49,
        category: "stickers",
        telegramStickerId: "heart_gift_1"
      },
      {
        name: "Diamond Premium",
        description: "Роскошный бриллиант премиум класса",
        imageUrl: "https://via.placeholder.com/300x300/B9F2FF/000000?text=💎",
        price: 2.99,
        category: "premium",
        telegramStickerId: "diamond_1"
      },
      {
        name: "Celebration Cake",
        description: "Торт для праздничных мероприятий",
        imageUrl: "https://via.placeholder.com/300x300/FF6B6B/FFFFFF?text=🎂",
        price: 1.99,
        category: "emojis",
        telegramStickerId: "cake_1"
      },
      {
        name: "Magic Wand",
        description: "Волшебная палочка для чудес",
        imageUrl: "https://via.placeholder.com/300x300/9B59B6/FFFFFF?text=✨",
        price: 1.79,
        category: "animations",
        telegramStickerId: "magic_wand_1"
      },
      {
        name: "Crown King",
        description: "Королевская корона для победителей",
        imageUrl: "https://via.placeholder.com/300x300/F1C40F/000000?text=👑",
        price: 3.49,
        category: "premium",
        telegramStickerId: "crown_1"
      }
    ];

    // Clear existing sample NFTs
    await NFT.deleteMany({ 
      telegramStickerId: { $in: sampleNFTs.map(nft => nft.telegramStickerId) } 
    });

    const createdNFTs = [];
    for (const nftData of sampleNFTs) {
      const nft = new NFT(nftData);
      await nft.save();
      createdNFTs.push(nft);
    }

    res.json({ 
      success: true, 
      message: `Created ${createdNFTs.length} sample NFTs`,
      nfts: createdNFTs 
    });
  } catch (error) {
    console.error('Create sample NFTs error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Update NFT (protected)
router.put('/:id', authenticateToken, async (req, res) => {
  try {
    const nft = await NFT.findById(req.params.id);
    
    if (!nft) {
      return res.status(404).json({ success: false, error: 'NFT not found' });
    }
    
    // Check ownership
    const user = await User.findById(req.user.userId);
    if (nft.owner.toString() !== user._id.toString()) {
      return res.status(403).json({ success: false, error: 'Not authorized to update this NFT' });
    }
    
    const updates = req.body;
    Object.keys(updates).forEach(key => {
      if (key !== 'owner' && key !== '_id') {
        nft[key] = updates[key];
      }
    });
    
    await nft.save();
    await nft.populate('owner', 'telegramId firstName username');
    
    res.json({ 
      success: true, 
      message: 'NFT updated successfully',
      nft 
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Delete NFT (protected)
router.delete('/:id', authenticateToken, async (req, res) => {
  try {
    const nft = await NFT.findById(req.params.id);
    
    if (!nft) {
      return res.status(404).json({ success: false, error: 'NFT not found' });
    }
    
    // Check ownership
    const user = await User.findById(req.user.userId);
    if (nft.owner.toString() !== user._id.toString()) {
      return res.status(403).json({ success: false, error: 'Not authorized to delete this NFT' });
    }
    
    await NFT.findByIdAndDelete(req.params.id);
    
    res.json({ 
      success: true, 
      message: 'NFT deleted successfully' 
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

export default router;
