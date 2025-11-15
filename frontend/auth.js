const tg = window.Telegram.WebApp;
let currentUser = null;
let authToken = null;

// Инициализация приложения
tg.expand();
tg.enableClosingConfirmation();
tg.setHeaderColor('#667eea');
tg.setBackgroundColor('#667eea');

// Основные цвета Telegram
const TG_BG_COLOR = '#667eea';
const TG_BUTTON_COLOR = '#007bff';
const TG_TEXT_COLOR = '#ffffff';

document.addEventListener('DOMContentLoaded', async () => {
    await initApp();
});

// Инициализация приложения
async function initApp() {
    try {
        showLoading(true);
        hideError();
        
        console.log('Initializing app...');
        console.log('Telegram WebApp version:', tg.version);
        console.log('Platform:', tg.platform);
        
        // Проверяем, есть ли данные от Telegram
        if (tg.initData) {
            console.log('Telegram initData available');
            await verifyTelegramAuth(tg.initData);
        } else {
            console.log('No Telegram initData found');
            showAuthScreen();
        }
    } catch (error) {
        console.error('Init error:', error);
        showError('Ошибка инициализации: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// Верификация данных Telegram
async function verifyTelegramAuth(initData) {
    try {
        console.log('Verifying Telegram auth...');
        
        const response = await fetch('/api/telegram/verify-auth', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ initData })
        });

        const data = await response.json();
        console.log('Auth response:', data);

        if (data.success) {
            currentUser = data.user;
            authToken = data.token;
            
            // Сохраняем токен в localStorage
            if (authToken) {
                localStorage.setItem('nft_marketplace_token', authToken);
            }
            
            showUserInfo();
            
            // Показываем MainButton для перехода в маркетплейс
            tg.MainButton.setText('Войти в маркетплейс');
            tg.MainButton.onClick(enterMarketplace);
            tg.MainButton.show();
            
        } else {
            throw new Error(data.error || 'Authentication failed');
        }
    } catch (error) {
        console.error('Auth error:', error);
        showError('Ошибка авторизации: ' + error.message);
        showAuthScreen();
    }
}

// Авторизация через Telegram
async function loginWithTelegram() {
    try {
        showLoading(true);
        hideError();
        
        console.log('Starting Telegram login...');
        
        // В Mini Apps данные уже доступны через tg.initData
        if (tg.initData) {
            await verifyTelegramAuth(tg.initData);
        } else {
            // Если данных нет, запрашиваем контакт
            const canRequestContact = await tg.requestContactAccess();
            
            if (canRequestContact === 'allowed') {
                console.log('Contact access allowed');
                // После разрешения данные появятся в tg.initData
                // Нужно перезагрузить приложение или обновить данные
                location.reload();
            } else {
                throw new Error('Доступ к контактам не разрешен');
            }
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('Ошибка входа: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// Показать экран авторизации
function showAuthScreen() {
    console.log('Showing auth screen');
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('authContent').classList.remove('hidden');
    document.getElementById('userInfo').classList.add('hidden');
    document.getElementById('errorMessage').classList.add('hidden');
    
    // Скрываем MainButton на экране авторизации
    tg.MainButton.hide();
}

// Показать информацию о пользователе
function showUserInfo() {
    console.log('Showing user info for:', currentUser);
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('authContent').classList.add('hidden');
    document.getElementById('userInfo').classList.remove('hidden');
    document.getElementById('errorMessage').classList.add('hidden');
    
    const userName = currentUser.firstName + (currentUser.lastName ? ' ' + currentUser.lastName : '');
    document.getElementById('userName').textContent = userName;
}

// Показать ошибку
function showError(message) {
    console.error('Showing error:', message);
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('authContent').classList.add('hidden');
    document.getElementById('userInfo').classList.add('hidden');
    document.getElementById('errorMessage').classList.remove('hidden');
    
    document.getElementById('errorText').textContent = message;
    
    // Скрываем MainButton при ошибке
    tg.MainButton.hide();
}

// Скрыть ошибку
function hideError() {
    document.getElementById('errorMessage').classList.add('hidden');
}

// Повторная попытка авторизации
function retryAuth() {
    initApp();
}

// Переход в маркетплейс
function enterMarketplace() {
    console.log('Entering marketplace...');
    
    // Сохраняем данные пользователя для маркетплейса
    if (currentUser && authToken) {
        localStorage.setItem('nft_marketplace_user', JSON.stringify(currentUser));
        localStorage.setItem('nft_marketplace_token', authToken);
    }
    
    window.location.href = '/marketplace';
}

// Управление загрузкой
function showLoading(show) {
    const loading = document.getElementById('loading');
    if (show) {
        loading.classList.remove('hidden');
    } else {
        loading.classList.add('hidden');
    }
}

// Обработчик изменения видимости приложения
tg.onEvent('viewportChanged', (event) => {
    console.log('Viewport changed:', event);
});

// Обработчик изменения темы
tg.onEvent('themeChanged', () => {
    console.log('Theme changed');
    // Можно добавить логику для смены темы
});

// Обработчик изменения размера окна
tg.onEvent('mainButtonClicked', () => {
    console.log('Main button clicked');
});

// Экспортируем функции для глобального использования
window.loginWithTelegram = loginWithTelegram;
window.enterMarketplace = enterMarketplace;
window.retryAuth = retryAuth;
