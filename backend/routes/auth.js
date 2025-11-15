const express = require('express');
const router = express.Router();
const crypto = require('crypto');
const User = require('../../database/models/User');

// Верификация данных от Telegram Web App
router.post('/verify-auth', async (req, res) => {
  try {
    const { initData } = req.body;
    
    // Проверяем подпись данных
    const isValid = verifyTelegramWebAppData(initData);
    if (!isValid) {
      return res.status(401).json({ success: false, error: 'Invalid Telegram data' });
    }
    
    // Парсим данные
    const params = new URLSearchParams(initData);
    const userData = JSON.parse(params.get('user'));
    
    // Сохраняем/обновляем пользователя
    let user = await User.findOne({ telegramId: userData.id });
    if (!user) {
      user = new User({
        telegramId: userData.id,
        phone: userData.phone_number || '',
        firstName: userData.first_name,
        lastName: userData.last_name || '',
        username: userData.username || '',
        isVerified: true
      });
    } else {
      user.phone = userData.phone_number || user.phone;
      user.firstName = userData.first_name;
      user.lastName = userData.last_name || user.lastName;
      user.username = userData.username || user.username;
      user.isVerified = true;
    }
    
    await user.save();
    
    res.json({
      success: true,
      user: {
        id: user.telegramId,
        phone: user.phone,
        firstName: user.firstName,
        lastName: user.lastName,
        username: user.username
      }
    });
    
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Функция верификации данных Telegram
function verifyTelegramWebAppData(initData) {
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get('hash');
  urlParams.delete('hash');
  
  // Сортируем параметры по ключу
  const dataCheckString = Array.from(urlParams.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}=${value}`)
    .join('\n');
  
  // Создаем секретный ключ
  const secretKey = crypto.createHmac('sha256', 'WebAppData')
    .update(process.env.TELEGRAM_BOT_TOKEN)
    .digest();
  
  // Вычисляем хеш
  const calculatedHash = crypto.createHmac('sha256', secretKey)
    .update(dataCheckString)
    .digest('hex');
  
  return calculatedHash === hash;
}

// Получение информации о пользователе через Telegram API
router.get('/user-info', async (req, res) => {
  try {
    const { telegramId } = req.query;
    
    const response = await fetch(`https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/getChat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        chat_id: telegramId
      })
    });
    
    const data = await response.json();
    
    if (data.ok) {
      res.json({ success: true, user: data.result });
    } else {
      res.status(404).json({ success: false, error: 'User not found' });
    }
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;
