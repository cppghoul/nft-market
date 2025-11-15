const mongoose = require('mongoose');

const nftSchema = new mongoose.Schema({
  name: { type: String, required: true },
  description: { type: String },
  imageUrl: { type: String, required: true },
  price: { type: Number, required: true },
  category: { type: String, required: true },
  telegramStickerId: { type: String },
  owner: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  isAvailable: { type: Boolean, default: true },
  createdAt: { type: Date, default: Date.now }
});

module.exports = mongoose.model('NFT', nftSchema);
