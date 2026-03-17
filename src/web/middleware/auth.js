/**
 * JWT authentication middleware
 */

import jwt from 'jsonwebtoken';
import { AuthenticationError, ValidationError } from './error_handler.js';

// Get JWT secret from environment variable (required)
const JWT_SECRET = process.env.JWT_SECRET;
if (!JWT_SECRET) {
  throw new Error('JWT_SECRET environment variable is required');
}
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '7d';

/**
 * Generate JWT token
 * @param {number} accountId - Account ID
 * @param {string} sessionId - Session ID
 * @returns {string} JWT token
 */
export function generateToken(accountId, sessionId) {
  if (!accountId) {
    throw new ValidationError('Account ID is required for token generation');
  }

  if (!sessionId) {
    throw new ValidationError('Session ID is required for token generation');
  }

  const payload = {
    accountId,
    sessionId,
    iat: Math.floor(Date.now() / 1000),
  };

  return jwt.sign(payload, JWT_SECRET, {
    expiresIn: JWT_EXPIRES_IN,
  });
}

/**
 * Verify JWT token
 * @param {string} token - JWT token
 * @returns {Object} Decoded token payload
 */
export function verifyToken(token) {
  if (!token) {
    throw new AuthenticationError('No token provided');
  }

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    return decoded;
  } catch (error) {
    if (error.name === 'TokenExpiredError') {
      throw new AuthenticationError('Token has expired');
    } else if (error.name === 'JsonWebTokenError') {
      throw new AuthenticationError('Invalid token');
    } else {
      throw error;
    }
  }
}

/**
 * Authentication middleware (required)
 * Verifies JWT token and sets req.user
 * @param {Request} req - Express request object
 * @param {Response} res - Express response object
 * @param {Function} next - Next middleware function
 */
export function authMiddleware(req, res, next) {
  try {
    // Extract token from Authorization header
    const authHeader = req.headers.authorization;

    if (!authHeader) {
      throw new AuthenticationError('No authorization header provided');
    }

    // Check Bearer token format
    const parts = authHeader.split(' ');
    if (parts.length !== 2 || parts[0] !== 'Bearer') {
      throw new AuthenticationError('Invalid authorization header format. Expected: Bearer <token>');
    }

    const token = parts[1];

    // Verify token
    const decoded = verifyToken(token);

    // Set user info in request
    req.user = {
      accountId: decoded.accountId,
      sessionId: decoded.sessionId,
      iat: decoded.iat,
      exp: decoded.exp,
    };

    next();
  } catch (error) {
    next(error);
  }
}

/**
 * Optional authentication middleware
 * Sets req.user if valid token is provided, but doesn't fail if missing
 * @param {Request} req - Express request object
 * @param {Response} res - Express response object
 * @param {Function} next - Next middleware function
 */
export function optionalAuthMiddleware(req, res, next) {
  try {
    const authHeader = req.headers.authorization;

    if (!authHeader) {
      // No token provided, but that's okay for optional auth
      req.user = null;
      return next();
    }

    const parts = authHeader.split(' ');
    if (parts.length !== 2 || parts[0] !== 'Bearer') {
      // Invalid format, but don't fail
      req.user = null;
      return next();
    }

    const token = parts[1];

    try {
      const decoded = verifyToken(token);
      req.user = {
        accountId: decoded.accountId,
        sessionId: decoded.sessionId,
        iat: decoded.iat,
        exp: decoded.exp,
      };
    } catch (error) {
      // Token verification failed, but that's okay for optional auth
      req.user = null;
    }

    next();
  } catch (error) {
    next(error);
  }
}

/**
 * Middleware to check account ownership
 * Ensures the authenticated user owns the specified account
 * @param {Request} req - Express request object
 * @param {Response} res - Express response object
 * @param {Function} next - Next middleware function
 */
export function checkAccountOwnership(req, res, next) {
  try {
    if (!req.user) {
      throw new AuthenticationError('Authentication required');
    }

    // Get account ID from request body or params
    const requestAccountId = req.body.account_id || req.params.accountId;

    if (!requestAccountId) {
      throw new ValidationError('Account ID not provided in request');
    }

    if (parseInt(requestAccountId) !== req.user.accountId) {
      throw new AuthorizationError('You do not have permission to access this account');
    }

    next();
  } catch (error) {
    next(error);
  }
}
