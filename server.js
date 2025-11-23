import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { TelegramClient } from 'telegram';
import { StringSession } from 'telegram/sessions';
import input from 'input';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

// 🎯 РЕАЛЬНЫЙ TELEGRAM CLIENT
class RealTelegramAuth {
  constructor() {
    this.apiId = parseInt(process.env.TELEGRAM_API_ID);
    this.apiHash = process.env.TELEGRAM_API_HASH;
    this.activeClients = new Map();
    this.authProcesses = new Map();
  }

  async startAuth(sessionId, phoneNumber) {
    try {
      console.log(`📱 Начало реальной авторизации для: ${phoneNumber}`);
      
      const stringSession = new StringSession('');
      const client = new TelegramClient(stringSession, this.apiId, this.apiHash, {
        connectionRetries: 3,
        useWSS: false,
        timeout: 30000
      });

      await client.connect();

      // Запускаем процесс авторизации
      await client.sendCode({
        apiId: this.apiId,
        apiHash: this.apiHash,
        phoneNumber,
      }, {});

      this.authProcesses.set(sessionId, {
        client,
        phoneNumber,
        status: 'waiting_code'
      });

      return {
        success: true,
        sessionId,
        message: '✅ Код отправлен в Telegram. Введите код.',
        nextStep: 'enter_code'
      };

    } catch (error) {
      console.error('❌ Ошибка авторизации:', error);
      return {
        success: false,
        error: error.toString()
      };
    }
  }

  async submitCode(sessionId, code) {
    try {
      const authProcess = this.authProcesses.get(sessionId);
      if (!authProcess) {
        return { success: false, error: 'Сессия не найдена' };
      }

      const { client, phoneNumber } = authProcess;

      try {
        const result = await client.signIn({
          phoneNumber,
          phoneCode: code,
        });

        // Сохраняем сессию
        const sessionString = client.session.save();
        
        this.activeClients.set(sessionId, {
          client,
          sessionString,
          user: result
        });

        this.authProcesses.delete(sessionId);

        return {
          success: true,
          sessionId,
          sessionString,
          user: {
            id: result.id,
            firstName: result.firstName,
            lastName: result.lastName,
            username: result.username,
            phone: result.phone
          },
          message: '✅ Успешная авторизация! Сессия сохранена.'
        };

      } catch (signInError) {
        if (signInError.errorMessage === 'SESSION_PASSWORD_NEEDED') {
          return {
            success: true,
            sessionId,
            message: '🔒 Требуется пароль от облачного хранилища.',
            nextStep: 'enter_password'
          };
        }
        throw signInError;
      }

    } catch (error) {
      return {
        success: false,
        error: error.toString()
      };
    }
  }

  async submitPassword(sessionId, password) {
    try {
      const authProcess = this.authProcesses.get(sessionId);
      if (!authProcess) {
        return { success: false, error: 'Сессия не найдена' };
      }

      const { client } = authProcess;

      const result = await client.signIn({
        password: password,
      });

      const sessionString = client.session.save();
      
      this.activeClients.set(sessionId, {
        client,
        sessionString,
        user: result
      });

      this.authProcesses.delete(sessionId);

      return {
        success: true,
        sessionId,
        sessionString,
        user: {
          id: result.id,
          firstName: result.firstName,
          lastName: result.lastName,
          username: result.username,
          phone: result.phone
        },
        message: '✅ Успешная авторизация с паролем!'
      };

    } catch (error) {
      return {
        success: false,
        error: 'Неверный пароль'
      };
    }
  }
}

const telegramAuth = new RealTelegramAuth();

// 🎯 API маршруты
app.post('/api/auth/start', async (req, res) => {
  const { phone } = req.body;
  const sessionId = 'tg_' + Date.now();
  const result = await telegramAuth.startAuth(sessionId, phone);
  res.json(result);
});

app.post('/api/auth/code', async (req, res) => {
  const { sessionId, code } = req.body;
  const result = await telegramAuth.submitCode(sessionId, code);
  res.json(result);
});

app.post('/api/auth/password', async (req, res) => {
  const { sessionId, password } = req.body;
  const result = await telegramAuth.submitPassword(sessionId, password);
  res.json(result);
});

app.listen(3000, () => {
  console.log('🚀 Сервер запущен с реальным Telegram клиентом');
});
