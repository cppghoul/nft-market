import mongoose from 'mongoose';

const nftSchema = new mongoose.Schema({
  name: { 
    type: String, 
    required: true,
    trim: true,
    maxlength: 100
  },
  description: { 
    type: String,
    trim: true,
    maxlength: 500
  },
  imageUrl: { 
    type: String, 
    required: true,
    validate: {
      validator: function(url) {
        return url.startsWith('http://') || url.startsWith('https://');
      },
      message: 'Image URL must be a valid HTTP/HTTPS URL'
    }
  },
  price: { 
    type: Number, 
    required: true,
    min: [0, 'Price cannot be negative'],
    max: [10000, 'Price too high']
  },
  category: { 
    type: String, 
    required: true,
    enum: {
      values: ['stickers', 'emojis', 'animations', 'premium', 'custom'],
      message: 'Category must be one of: stickers, emojis, animations, premium, custom'
    }
  },
  telegramStickerId: { 
    type: String,
    trim: true
  },
  owner: { 
    type: mongoose.Schema.Types.ObjectId, 
    ref: 'User',
    required: true
  },
  isAvailable: { 
    type: Boolean, 
    default: true 
  },
  tags: [{
    type: String,
    trim: true,
    maxlength: 20
  }],
  metadata: {
    rarity: { type: String, enum: ['common', 'rare', 'epic', 'legendary'], default: 'common' },
    edition: { type: Number, default: 1 },
    totalEditions: { type: Number, default: 1 },
    attributes: mongoose.Schema.Types.Mixed
  },
  createdAt: { 
    type: Date, 
    default: Date.now 
  },
  updatedAt: { 
    type: Date, 
    default: Date.now 
  }
}, {
  timestamps: true,
  toJSON: { virtuals: true }
});

// Индексы для оптимизации запросов
nftSchema.index({ category: 1 });
nftSchema.index({ price: 1 });
nftSchema.index({ isAvailable: 1 });
nftSchema.index({ owner: 1 });
nftSchema.index({ createdAt: -1 });
nftSchema.index({ 'metadata.rarity': 1 });

// Middleware для обновления updatedAt
nftSchema.pre('save', function(next) {
  this.updatedAt = Date.now();
  next();
});

// Виртуальное поле для форматированной цены
nftSchema.virtual('formattedPrice').get(function() {
  return `$${this.price.toFixed(2)}`;
});

// Статический метод для поиска по категории
nftSchema.statics.findByCategory = function(category) {
  return this.find({ category, isAvailable: true })
    .populate('owner', 'telegramId firstName username')
    .sort({ createdAt: -1 });
};

// Статический метод для поиска по владельцу
nftSchema.statics.findByOwner = function(ownerId) {
  return this.find({ owner: ownerId })
    .populate('owner', 'telegramId firstName username')
    .sort({ createdAt: -1 });
};

// Метод экземпляра для пометки как проданного
nftSchema.methods.markAsSold = function() {
  this.isAvailable = false;
  return this.save();
};

// Метод экземпляра для обновления цены
nftSchema.methods.updatePrice = function(newPrice) {
  this.price = newPrice;
  return this.save();
};

export default mongoose.model('NFT', nftSchema);
