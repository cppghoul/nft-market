import express from 'express';
import cors from 'cors';
import { Pool } from 'pg';
import dotenv from 'dotenv';

dotenv.config();

const app = express();

// PostgreSQL connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('frontend'));

// Create tables if they don't exist
async function initializeDatabase() {
  try {
    // Create users table
    await pool.query(`
      CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        telegram_id BIGINT UNIQUE NOT NULL,
        phone VARCHAR(20),
        first_name VARCHAR(100) NOT NULL,
        last_name VARCHAR(100),
        username VARCHAR(50),
        is_verified BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create nfts table
    await pool.query(`
      CREATE TABLE IF NOT EXISTS nfts (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        image_url TEXT NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        category VARCHAR(50) NOT NULL,
        is_available BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Insert sample NFTs if table is empty
    const nftCount = await pool.query('SELECT COUNT(*) FROM nfts');
    if (parseInt(nftCount.rows[0].count) === 0) {
      await pool.query(`
        INSERT INTO nfts (name, description, image_url, price, category) VALUES
        ('Golden Star', 'Блестящая золотая звезда', 'https://via.placeholder.com/300x300/FFD700/000000?text=⭐', 0.99, 'stickers'),
        ('Heart Gift', 'Подарок в виде сердца', 'https://via.placeholder.com/300x300/FF69B4/FFFFFF?text=💝', 1.49, 'stickers'),
        ('Diamond Premium', 'Роскошный бриллиант', 'https://via.placeholder.com/300x300/B9F2FF/000000?text=💎', 2.99, 'premium'),
        ('Celebration Cake', 'Торт для праздников', 'https://via.placeholder.com/300x300/FF6B6B/FFFFFF?text=🎂', 1.99, 'emojis'),
        ('Magic Wand', 'Волшебная палочка', 'https://via.placeholder.com/300x300/9B59B6/FFFFFF?text=✨', 1.79, 'animations')
      `);
      console.log('✅ Sample NFTs created');
    }

    console.log('✅ Database initialized successfully');
  } catch (error) {
    console.error('❌ Database initialization error:', error);
  }
}

// Routes
app.get('/health', async (req, res) => {
  try {
    // Test database connection
    await pool.query('SELECT 1');
    res.json({ 
      status: 'OK', 
      message: 'NFT Marketplace is running!',
      timestamp: new Date().toISOString(),
      database: 'PostgreSQL ✅'
    });
  } catch (error) {
    res.status(500).json({ 
      status: 'ERROR', 
      error: 'Database connection failed',
      timestamp: new Date().toISOString()
    });
  }
});

app.get('/', (req, res) => {
  res.sendFile('frontend/index.html', { root: '.' });
});

app.get('/marketplace', (req, res) => {
  res.sendFile('frontend/marketplace.html', { root: '.' });
});

// API Routes
app.get('/api/nft', async (req, res) => {
  try {
    const { category } = req.query;
    
    let query = 'SELECT * FROM nfts WHERE is_available = true';
    let params = [];
    
    if (category && category !== 'all') {
      query += ' AND category = $1';
      params.push(category);
    }
    
    query += ' ORDER BY created_at DESC';
    
    const result = await pool.query(query, params);
    res.json({ success: true, nfts: result.rows });
  } catch (error) {
    console.error('NFT fetch error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Telegram auth verification
app.post('/api/telegram/verify-auth', async (req, res) => {
  try {
    const { initData } = req.body;
    
    if (!initData) {
      return res.status(400).json({ success: false, error: 'No init data' });
    }

    // For demo - in production use real Telegram validation
    const userData = { 
      id: Math.floor(Math.random() * 1000000), 
      first_name: 'Telegram',
      last_name: 'User', 
      username: 'telegram_user'
    };
    
    // Check if user exists
    let userResult = await pool.query(
      'SELECT * FROM users WHERE telegram_id = $1',
      [userData.id]
    );

    let user;
    if (userResult.rows.length === 0) {
      // Create new user
      const newUser = await pool.query(
        `INSERT INTO users (telegram_id, first_name, last_name, username, is_verified) 
         VALUES ($1, $2, $3, $4, $5) RETURNING *`,
        [userData.id, userData.first_name, userData.last_name, userData.username, true]
      );
      user = newUser.rows[0];
    } else {
      user = userResult.rows[0];
    }

    res.json({
      success: true,
      user: {
        id: user.telegram_id,
        firstName: user.first_name,
        lastName: user.last_name,
        username: user.username,
        isVerified: user.is_verified
      }
    });
    
  } catch (error) {
    console.error('Auth error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Create sample NFTs endpoint
app.post('/api/nft/create-sample', async (req, res) => {
  try {
    await pool.query('DELETE FROM nfts'); // Clear existing
    
    await pool.query(`
      INSERT INTO nfts (name, description, image_url, price, category) VALUES
      ('Golden Star', 'Блестящая золотая звезда', 'https://via.placeholder.com/300x300/FFD700/000000?text=⭐', 0.99, 'stickers'),
      ('Heart Gift', 'Подарок в виде сердца', 'https://via.placeholder.com/300x300/FF69B4/FFFFFF?text=💝', 1.49, 'stickers'),
      ('Diamond Premium', 'Роскошный бриллиант', 'https://via.placeholder.com/300x300/B9F2FF/000000?text=💎', 2.99, 'premium')
    `);
    
    res.json({ success: true, message: 'Sample NFTs created' });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Connect to database and start server
async function startServer() {
  try {
    console.log('🔄 Initializing database...');
    await initializeDatabase();
    
    const PORT = process.env.PORT || 3000;
    app.listen(PORT, () => {
      console.log(`🚀 Server running on port ${PORT}`);
      console.log(`📱 Environment: ${process.env.NODE_ENV}`);
      console.log(`🎮 Health check: http://localhost:${PORT}/health`);
      
      if (process.env.TELEGRAM_BOT_USERNAME) {
        console.log(`🤖 Bot: https://t.me/${process.env.TELEGRAM_BOT_USERNAME}`);
      }
    });
    
  } catch (error) {
    console.error('❌ Server startup error:', error);
    process.exit(1);
  }
}

startServer();
