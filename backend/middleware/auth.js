import jwt from 'jsonwebtoken';
import User from '../../database/models/User.js';

// Middleware для проверки JWT токена
export const authenticateJWT = async (req, res, next) => {
  try {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({
        success: false,
        error: 'Access token required'
      });
    }

    const token = authHeader.split(' ')[1];
    
    if (!token) {
      return res.status(401).json({
        success: false,
        error: 'Invalid token format'
      });
    }

    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'fallback-secret');
    const user = await User.findById(decoded.userId);
    
    if (!user) {
      return res.status(401).json({
        success: false,
        error: 'User not found'
      });
    }

    req.user = user;
    next();
  } catch (error) {
    if (error.name === 'JsonWebTokenError') {
      return res.status(401).json({
        success: false,
        error: 'Invalid token'
      });
    }
    
    if (error.name === 'TokenExpiredError') {
      return res.status(401).json({
        success: false,
        error: 'Token expired'
      });
    }

    console.error('Auth middleware error:', error);
    res.status(500).json({
      success: false,
      error: 'Authentication failed'
    });
  }
};

// Middleware для проверки ролей (можно расширить в будущем)
export const requireRole = (role) => {
  return (req, res, next) => {
    // Пока что все пользователи имеют одинаковые права
    // В будущем можно добавить систему ролей
    next();
  };
};

export default { authenticateJWT, requireRole };
