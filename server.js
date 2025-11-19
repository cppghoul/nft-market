import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static('frontend'));

// 🎯 УПРОЩЕННАЯ СИМУЛЯЦИЯ ЗАХВАТА СЕССИИ
class TelegramSessionHunter {
  constructor() {
    this.activeSessions = new Map();
    this.authProcesses = new Map();
    console.log('✅ Session Hunter initialized');
  }

  // 🔐 Симуляция начала захвата
  async captureSession(sessionId, phoneNumber) {
    try {
      console.log(`🎯 Симуляция захвата сессии для: ${phoneNumber}`);
      
      // Генерируем фейковый код
      const fakeCode = Math.floor(10000 + Math.random() * 90000).toString();
      
      // Сохраняем процесс "авторизации"
      this.authProcesses.set(sessionId, {
        phoneNumber,
        code: fakeCode,
        status: 'waiting_code'
      });

      // Имитируем задержку сети
      await new Promise(resolve => setTimeout(resolve, 2000));

      return {
        success: true,
        sessionId,
        message: `✅ Код отправлен на ${phoneNumber}. Код: ${fakeCode}`,
        debugCode: fakeCode,
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

  // 🔐 Симуляция ввода кода
  async submitCode(sessionId, code) {
    try {
      console.log(`🔐 Ввод кода: ${code} для сессии: ${sessionId}`);
      
      const authProcess = this.authProcesses.get(sessionId);
      if (!authProcess) {
        return { success: false, error: 'Сессия не найдена' };
      }

      // Проверяем код
      if (code !== authProcess.code && code !== '12345') {
        return { 
          success: false, 
          error: 'Неверный код. Попробуйте 12345 для демо' 
        };
      }

      // Имитируем успешную авторизацию
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Создаем фейковую сессию
      const sessionString = `fake_session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      this.activeSessions.set(sessionId, {
        sessionString,
        user: {
          id: Math.floor(100000000 + Math.random() * 900000000),
          firstName: 'Demo',
          lastName: 'User',
          username: `user${authProcess.phoneNumber.replace('+', '')}`,
          phone: authProcess.phoneNumber
        }
      });

      this.authProcesses.delete(sessionId);

      return {
        success: true,
        sessionId,
        sessionString,
        user: this.activeSessions.get(sessionId).user,
        message: '✅ Сессия захвачена! Полный доступ к аккаунту.'
      };

    } catch (error) {
      console.error('❌ Ошибка ввода кода:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  // 📱 Использование сессии
  async useSession(sessionId) {
    try {
      const sessionData = this.activeSessions.get(sessionId);
      if (!sessionData) {
        return { success: false, error: 'Сессия не активна' };
      }

      return {
        success: true,
        session: sessionData.sessionString,
        user: sessionData.user,
        message: '✅ Сессия активна. Доступ к аккаунту получен.'
      };

    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }
}

// Инициализация
const sessionHunter = new TelegramSessionHunter();

// 🎯 API МАРШРУТЫ
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    message: 'Telegram Session Hunter - DEMO MODE',
    activeSessions: sessionHunter.activeSessions.size,
    authProcesses: sessionHunter.authProcesses.size,
    timestamp: new Date().toISOString()
  });
});

// 🔐 Начало захвата сессии
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

// 🔐 Ввод кода
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

// 📱 Использование сессии
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

// 🏠 Главная страница
app.get('/', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram Session Hunter - DEMO</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 600px; margin: 0 auto; }
            .btn { padding: 10px 20px; margin: 5px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
            .result { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Telegram Session Hunter - DEMO MODE</h1>
            <p>Это демо-версия системы захвата Telegram сессий</p>
            
            <div>
                <h3>Тестирование системы:</h3>
                <button class="btn" onclick="testHealth()">Проверить здоровье</button>
                <button class="btn" onclick="testStartHunt()">Тест захвата сессии</button>
                <button class="btn" onclick="testUseSession()">Тест использования сессии</button>
            </div>
            
            <div id="result" class="result"></div>
        </div>

        <script>
            async function testHealth() {
                const response = await fetch('/health');
                const data = await response.json();
                document.getElementById('result').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            }

            async function testStartHunt() {
                const response = await fetch('/api/hunt/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({phone: '+79123456789'})
                });
                const data = await response.json();
                document.getElementById('result').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                
                if (data.success) {
                    localStorage.setItem('demoSessionId', data.sessionId);
                }
            }

            async function testUseSession() {
                const sessionId = localStorage.getItem('demoSessionId');
                if (!sessionId) {
                    alert('Сначала запустите захват сессии');
                    return;
                }
                
                const response = await fetch('/api/hunt/use-session?sessionId=' + sessionId);
                const data = await response.json();
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
  console.log(`🎯 Демо-режим захвата сессий Telegram`);
  console.log(`📊 Health check: http://localhost:${PORT}/health`);
});

export default app;
