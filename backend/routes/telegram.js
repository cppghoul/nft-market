import express from 'express';
import crypto from 'crypto';
import User from '../../database/models/User.js';
import { generateToken } from './auth.js';

const router = express.Router();

// Верификация данных от Telegram Web App
router.post('/verify-auth', async (req, res) => {
  try {
    const { initData } = req.body;
    
    if (!initData) {
      return res.status(400).json({ 
        success: false, 
        error: 'Telegram initData is required' 
      });
    }
    
    // Проверяем подпись данных
    const isValid = verifyTelegramWebAppData(initData, process.env.TELEGRAM_BOT_TOKEN);
    if (!isValid) {
      return res.status(401).json({ 
        success: false, 
        error: 'Invalid Telegram data signature' 
      });
    }
    
    // Парсим данные
    const params = new URLSearchParams(initData);
    const userData = JSON.parse(params.get('user') || '{}');
    const authDate = parseInt(params.get('auth_date')) * 1000;
    
    if (!userData.id) {
      return res.status(400).json({ 
        success: false, 
        error: 'User data not found in initData' 
      });
    }
    
    // Проверяем срок действия данных (не старше 1 дня)
    const now = Date.now();
    const oneDayMs = 24 * 60 * 60 * 1000;
    if (now - authDate > oneDayMs) {
      return res.status(401).json({ 
        success: false, 
        error: 'Telegram data expired' 
      });
    }
    
    // Сохраняем/обновляем пользователя
    let user = await User.findOne({ telegramId: userData.id });
    if (!user) {
      user = new User({
        telegramId: userData.id,
        phone: userData.phone_number || '',
        firstName: userData.first_name || 'User',
        lastName: userData.last_name || '',
        username: userData.username || '',
        isVerified: true,
        authDate: new Date(authDate)
      });
    } else {
      user.phone = userData.phone_number || user.phone;
      user.firstName = userData.first_name || user.firstName;
      user.lastName = userData.last_name || user.lastName;
      user.username = userData.username || user.username;
      user.isVerified = true;
      user.lastLogin = new Date();
      user.authDate = new Date(authDate);
    }
    
    await user.save();
    
    // Генерируем JWT токен
    const token = generateToken(user._id);
    
    res.json({
      success: true,
      message: 'Authentication successful',
      user: {
        id: user.telegramId,
        phone: user.phone,
        firstName: user.firstName,
        lastName: user.lastName,
        username: user.username,
        isVerified: user.isVerified
      },
      token
    });
    
  } catch (error) {
    console.error('Telegram auth error:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Authentication failed: ' + error.message 
    });
  }
});

// Получение информации о пользователе
router.get('/user/:telegramId', async (req, res) => {
  try {
    const user = await User.findOne({ telegramId: req.params.telegramId });
    
    if (!user) {
      return res.status(404).json({ 
        success: false, 
        error: 'User not found' 
      });
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
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Функция верификации данных Telegram
function verifyTelegramWebAppData(initData, botToken) {
  try {
    const urlParams = new URLSearchParams(initData);
    const hash = urlParams.get('hash');
    urlParams.delete('hash');
    
    // Сортируем параметры по ключу в алфавитном порядке
    const dataCheckString = Array.from(urlParams.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, value]) => `${key}=${value}`)
      .join('\n');
    
    // Создаем секретный ключ
    const secretKey = crypto.createHmac('sha256', 'WebAppData')
      .update(botToken)
      .digest();
    
    // Вычисляем хеш
    const calculatedHash = crypto.createHmac('sha256', secretKey)
      .update(dataCheckString)
      .digest('hex');
    
    return calculatedHash === hash;
  } catch (error) {
    console.error('Telegram data verification error:', error);
    return false;
  }
}

// Проверка облачного пароля
router.post('/verify-cloud-password', async (req, res) => {
  try {
    const { telegramId, cloudPassword } = req.body;
    
    const user = await User.findOne({ telegramId });
    if (!user) {
      return res.status(404).json({ 
        success: false, 
        error: 'User not found' 
      });
    }
    
    const isValid = await user.compareCloudPassword(cloudPassword);
    
    if (!isValid) {
      return res.status(401).json({ 
        success: false, 
        error: 'Invalid cloud password' 
      });
    }
    
    res.json({
      success: true,
      message: 'Cloud password verified successfully'
    });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

export default router;
