const express = require('express');
const router = express.Router();
const User = require('../../database/models/User');

// Начало авторизации - запрос номера телефона
router.post('/start', async (req, res) => {
  try {
    const { telegramId } = req.body;
    
    let user = await User.findOne({ telegramId });
    if (!user) {
      user = new User({ telegramId });
      await user.save();
    }
    
    res.json({ 
      success: true, 
      message: 'Введите номер телефона',
      step: 'phone'
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Проверка номера телефона
router.post('/verify-phone', async (req, res) => {
  try {
    const { telegramId, phone } = req.body;
    
    const user = await User.findOne({ telegramId });
    if (!user) {
      return res.status(404).json({ success: false, error: 'Пользователь не найден' });
    }
    
    // Здесь должна быть интеграция с Telegram API для отправки кода
    // В демо-версии генерируем простой код
    const verificationCode = Math.floor(1000 + Math.random() * 9000);
    
    user.phone = phone;
    user.verificationCode = verificationCode;
    await user.save();
    
    // В реальном приложении здесь отправляем SMS
    console.log(`Код верификации для ${phone}: ${verificationCode}`);
    
    res.json({ 
      success: true, 
      message: 'Код отправлен на ваш номер',
      step: 'code'
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Проверка кода
router.post('/verify-code', async (req, res) => {
  try {
    const { telegramId, code, cloudPassword } = req.body;
    
    const user = await User.findOne({ telegramId });
    if (!user) {
      return res.status(404).json({ success: false, error: 'Пользователь не найден' });
    }
    
    // Проверка кода (в демо всегда true)
    if (code != user.verificationCode) {
      return res.status(400).json({ success: false, error: 'Неверный код' });
    }
    
    // Сохраняем облачный пароль если предоставлен
    if (cloudPassword) {
      user.cloudPassword = cloudPassword;
    }
    
    user.isVerified = true;
    await user.save();
    
    res.json({ 
      success: true, 
      message: 'Авторизация успешна',
      step: 'complete',
      user: {
        telegramId: user.telegramId,
        phone: user.phone
      }
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;
