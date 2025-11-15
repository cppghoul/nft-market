const tg = window.Telegram.WebApp;
let currentUser = null;
let currentCategory = 'all';
let authToken = null;
let allNFTs = [];

// Инициализация
tg.expand();
tg.setHeaderColor('#667eea');
tg.setBackgroundColor('#f8f9fa');

document.addEventListener('DOMContentLoaded', async () => {
    await initMarketplace();
});

// Инициализация маркетплейса
async function initMarketplace() {
    try {
        console.log('Initializing marketplace...');
        
        // Получаем данные из localStorage
        const userData = localStorage.getItem('nft_marketplace_user');
        authToken = localStorage.getItem('nft_marketplace_token');
        
        if (userData && authToken) {
            currentUser = JSON.parse(userData);
            updateUserInfo();
        } else {
            // Если данных нет, проверяем Telegram auth
            if (tg.initData) {
                await verifyAndLoadUser();
            } else {
                showError('Требуется авторизация');
                return;
            }
        }
        
        await loadNFTs('all');
        await createSampleNFTs(); // Создаем демо-данные при первом запуске
        
    } catch (error) {
        console.error('Marketplace init error:', error);
        showError('Ошибка загрузки маркетплейса: ' + error.message);
    }
}

// Проверка и загрузка пользователя
async function verifyAndLoadUser() {
    try {
        const response = await fetch('/api/telegram/verify-auth', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ initData: tg.initData })
        });

        const data = await response.json();
        
        if (data.success) {
            currentUser = data.user;
            authToken = data.token;
            
            // Сохраняем для будущего использования
            localStorage.setItem('nft_marketplace_user', JSON.stringify(currentUser));
            localStorage.setItem('nft_marketplace_token', authToken);
            
            updateUserInfo();
        } else {
            throw new Error(data.error || 'Authentication failed');
        }
    } catch (error) {
        console.error('User verification error:', error);
        throw error;
    }
}

// Загрузка NFT
async function loadNFTs(category) {
    try {
        currentCategory = category;
        
        // Обновляем активные кнопки категорий
        document.querySelectorAll('.category-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Активируем текущую кнопку
        const activeBtn = Array.from(document.querySelectorAll('.category-btn'))
            .find(btn => btn.textContent.includes(getCategoryName(category)));
        if (activeBtn) activeBtn.classList.add('active');
        
        // Показываем загрузку
        document.getElementById('nftGrid').innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p>Загрузка ${getCategoryName(category)} подарков...</p>
            </div>
        `;
        
        const response = await fetch(`/api/nft?category=${category}`);
        const data = await response.json();
        
        if (data.success) {
            allNFTs = data.nfts;
            displayNFTs(allNFTs);
            updateNFTCount(data.nfts.length);
            updateSectionTitle(category);
        } else {
            throw new Error(data.error || 'Failed to load NFTs');
        }
    } catch (error) {
        console.error('Load NFTs error:', error);
        document.getElementById('nftGrid').innerHTML = 
            '<div class="error">Ошибка загрузки NFT подарков</div>';
    }
}

// Поиск NFT
async function searchNFTs() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    
    if (!searchTerm) {
        displayNFTs(allNFTs);
        return;
    }
    
    const filteredNFTs = allNFTs.filter(nft => 
        nft.name.toLowerCase().includes(searchTerm) ||
        nft.description.toLowerCase().includes(searchTerm)
    );
    
    displayNFTs(filteredNFTs);
    updateNFTCount(filteredNFTs.length);
}

// Отображение NFT
function displayNFTs(nfts) {
    const nftGrid = document.getElementById('nftGrid');
    
    if (nfts.length === 0) {
        nftGrid.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🎁</div>
                <h3>Подарки не найдены</h3>
                <p>Попробуйте выбрать другую категорию или изменить поисковый запрос</p>
                <button class="btn btn-primary" onclick="loadNFTs('all')">
                    Показать все подарки
                </button>
            </div>
        `;
        return;
    }
    
    nftGrid.innerHTML = nfts.map(nft => `
        <div class="nft-card" data-nft-id="${nft._id}">
            <div class="nft-image-container">
                <img src="${nft.imageUrl}" alt="${nft.name}" class="nft-image" 
                     onerror="this.src='https://via.placeholder.com/300x300/667eea/ffffff?text=NFT'">
                ${nft.metadata?.rarity === 'premium' ? '<div class="premium-badge">💎 Премиум</div>' : ''}
            </div>
            <div class="nft-info">
                <h3 class="nft-name">${nft.name}</h3>
                <p class="nft-description">${nft.description}</p>
                <div class="nft-meta">
                    <span class="nft-category">${getCategoryIcon(nft.category)} ${getCategoryName(nft.category)}</span>
                    <span class="nft-rarity ${nft.metadata?.rarity || 'common'}">${getRarityName(nft.metadata?.rarity)}</span>
                </div>
                <div class="nft-price">${nft.formattedPrice || `$${nft.price.toFixed(2)}`}</div>
                <button class="btn btn-buy" onclick="showPurchaseModal('${nft._id}')">
                    <span class="btn-icon">🛒</span>
                    Купить за $${nft.price.toFixed(2)}
                </button>
            </div>
        </div>
    `).join('');
}

// Покупка NFT
async function showPurchaseModal(nftId) {
    const modal = document.getElementById('purchaseModal');
    modal.classList.remove('hidden');
    
    // Можно добавить дополнительную логику для конкретного NFT
    tg.HapticFeedback.impactOccurred('medium');
}

// Закрытие модального окна
function closeModal() {
    const modal = document.getElementById('purchaseModal');
    modal.classList.add('hidden');
}

// Создание демо-данных
async function createSampleNFTs() {
    try {
        // Проверяем, есть ли уже NFT
        const response = await fetch('/api/nft?category=all');
        const data = await response.json();
        
        if (data.success && data.nfts.length === 0) {
            // Создаем демо-данные только если нет существующих NFT
            await fetch('/api/nft/create-sample', { method: 'POST' });
            console.log('Sample NFTs created');
        }
    } catch (error) {
        console.error('Create sample error:', error);
    }
}

// Обновление информации о пользователе
function updateUserInfo() {
    if (currentUser) {
        const greeting = `Привет, ${currentUser.firstName}!`;
        document.getElementById('userGreeting').textContent = greeting;
    }
}

// Обновление счетчика NFT
function updateNFTCount(count) {
    document.getElementById('nftCount').textContent = `${count} подарк${getPluralEnding(count)}`;
}

// Обновление заголовка секции
function updateSectionTitle(category) {
    const title = document.getElementById('nftSectionTitle');
    title.textContent = getCategoryName(category);
}

// Вспомогательные функции
function getCategoryName(category) {
    const names = {
        'all': 'Все подарки',
        'stickers': 'Стикеры',
        'emojis': 'Эмодзи',
        'animations': 'Анимации',
        'premium': 'Премиум подарки'
    };
    return names[category] || category;
}

function getCategoryIcon(category) {
    const icons = {
        'stickers': '🖼️',
        'emojis': '😊',
        'animations': '✨',
        'premium': '💎'
    };
    return icons[category] || '🎁';
}

function getRarityName(rarity) {
    const names = {
        'common': 'Обычный',
        'rare': 'Редкий',
        'epic': 'Эпический',
        'legendary': 'Легендарный'
    };
    return names[rarity] || 'Обычный';
}

function getPluralEnding(count) {
    if (count % 10 === 1 && count % 100 !== 11) return '';
    if (count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 10 || count % 100 >= 20)) return 'а';
    return 'ов';
}

function showError(message) {
    const nftGrid = document.getElementById('nftGrid');
    nftGrid.innerHTML = `
        <div class="error-state">
            <div class="error-icon">⚠️</div>
            <h3>Ошибка</h3>
            <p>${message}</p>
            <button class="btn btn-primary" onclick="location.reload()">
                Перезагрузить
            </button>
        </div>
    `;
}

// Обработчики событий
document.getElementById('searchInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        searchNFTs();
    }
});

// Закрытие модального окна по клику вне его
document.getElementById('purchaseModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeModal();
    }
});

// Экспортируем функции для глобального использования
window.loadNFTs = loadNFTs;
window.searchNFTs = searchNFTs;
window.showPurchaseModal = showPurchaseModal;
window.closeModal = closeModal;
