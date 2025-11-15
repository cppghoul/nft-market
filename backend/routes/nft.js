const express = require('express');
const router = express.Router();
const NFT = require('../../database/models/NFT');

// Получить все NFT
router.get('/', async (req, res) => {
  try {
    const nfts = await NFT.find({ isAvailable: true })
      .populate('owner', 'telegramId phone')
      .sort({ createdAt: -1 });
    
    res.json({ success: true, nfts });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Получить NFT по категории
router.get('/category/:category', async (req, res) => {
  try {
    const nfts = await NFT.find({ 
      category: req.params.category,
      isAvailable: true 
    }).populate('owner', 'telegramId phone');
    
    res.json({ success: true, nfts });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Создать NFT
router.post('/', async (req, res) => {
  try {
    const { name, description, imageUrl, price, category, telegramStickerId, ownerId } = req.body;
    
    const nft = new NFT({
      name,
      description,
      imageUrl,
      price,
      category,
      telegramStickerId,
      owner: ownerId
    });
    
    await nft.save();
    res.json({ success: true, nft });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;
