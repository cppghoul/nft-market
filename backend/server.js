const express = require('express');
const cors = require('cors');
const mongoose = require('mongoose');
require('dotenv').config();

const app = express();

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('frontend'));

// Routes
app.use('/api/auth', require('./routes/auth'));
app.use('/api/nft', require('./routes/nft'));
app.use('/api/telegram', require('./routes/telegram'));

// Database connection
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/telegram-nft')
  .then(() => console.log('MongoDB connected'))
  .catch(err => console.log(err));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
