import mongoose from 'mongoose';
import bcrypt from 'bcryptjs';

const userSchema = new mongoose.Schema({
  telegramId: { 
    type: Number, 
    required: true, 
    unique: true,
    index: true
  },
  phone: { 
    type: String,
    trim: true
  },
  firstName: { 
    type: String, 
    required: true,
    trim: true,
    maxlength: 100
  },
  lastName: { 
    type: String,
    trim: true,
    maxlength: 100
  },
  username: { 
    type: String,
    trim: true,
    lowercase: true,
    maxlength: 50
  },
  cloudPassword: { 
    type: String,
    select: false // Не возвращать по умолчанию при запросах
  },
  isVerified: { 
    type: Boolean, 
    default: false 
  },
  authDate: { 
    type: Date 
  },
  createdAt: { 
    type: Date, 
    default: Date.now 
  },
  lastLogin: { 
    type: Date, 
    default: Date.now 
  },
  preferences: {
    language: { type: String, default: 'ru' },
    currency: { type: String, default: 'USD' },
    notifications: { type: Boolean, default: true }
  }
}, {
  timestamps: true,
  toJSON: {
    transform: function(doc, ret) {
      delete ret.cloudPassword;
      return ret;
    }
  }
});

// Индексы для оптимизации запросов
userSchema.index({ username: 1 });
userSchema.index({ phone: 1 });
userSchema.index({ createdAt: -1 });

// Хеширование облачного пароля перед сохранением
userSchema.pre('save', async function(next) {
  if (this.cloudPassword && this.isModified('cloudPassword')) {
    try {
      this.cloudPassword = await bcrypt.hash(this.cloudPassword, 12);
    } catch (error) {
      return next(error);
    }
  }
  next();
});

// Метод для сравнения облачного пароля
userSchema.methods.compareCloudPassword = async function(candidatePassword) {
  if (!this.cloudPassword) {
    return true; // Если пароль не установлен, считаем валидным
  }
  
  try {
    return await bcrypt.compare(candidatePassword, this.cloudPassword);
  } catch (error) {
    throw new Error('Password comparison failed');
  }
};

// Метод для обновления времени последнего входа
userSchema.methods.updateLastLogin = function() {
  this.lastLogin = new Date();
  return this.save();
};

// Статический метод для поиска по Telegram ID
userSchema.statics.findByTelegramId = function(telegramId) {
  return this.findOne({ telegramId });
};

// Виртуальное поле для полного имени
userSchema.virtual('fullName').get(function() {
  return this.lastName 
    ? `${this.firstName} ${this.lastName}`
    : this.firstName;
});

export default mongoose.model('User', userSchema);
