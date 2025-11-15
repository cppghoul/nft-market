const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

const userSchema = new mongoose.Schema({
  telegramId: { type: Number, required: true, unique: true },
  phone: { type: String, required: true },
  cloudPassword: { type: String },
  isVerified: { type: Boolean, default: false },
  createdAt: { type: Date, default: Date.now }
});

userSchema.pre('save', async function(next) {
  if (this.cloudPassword && this.isModified('cloudPassword')) {
    this.cloudPassword = await bcrypt.hash(this.cloudPassword, 10);
  }
  next();
});

userSchema.methods.compareCloudPassword = async function(candidatePassword) {
  if (!this.cloudPassword) return true; // Если пароль не установлен
  return bcrypt.compare(candidatePassword, this.cloudPassword);
};

module.exports = mongoose.model('User', userSchema);
