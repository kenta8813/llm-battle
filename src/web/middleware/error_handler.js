/**
 * Error handling middleware for unified error responses
 */

// Custom error classes
export class ApiError extends Error {
  constructor(message, statusCode = 500, code = 'INTERNAL_ERROR') {
    super(message);
    this.statusCode = statusCode;
    this.code = code;
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }
}

export class ValidationError extends ApiError {
  constructor(message, details = null) {
    super(message, 400, 'VALIDATION_ERROR');
    this.details = details;
  }
}

export class AuthenticationError extends ApiError {
  constructor(message = 'Authentication required') {
    super(message, 401, 'AUTHENTICATION_ERROR');
  }
}

export class AuthorizationError extends ApiError {
  constructor(message = 'Insufficient permissions') {
    super(message, 403, 'AUTHORIZATION_ERROR');
  }
}

export class NotFoundError extends ApiError {
  constructor(resource = 'Resource') {
    super(`${resource} not found`, 404, 'NOT_FOUND');
  }
}

export class ConflictError extends ApiError {
  constructor(message) {
    super(message, 409, 'CONFLICT');
  }
}

export class DatabaseError extends ApiError {
  constructor(message, originalError = null) {
    super(message, 500, 'DATABASE_ERROR');
    this.originalError = originalError;
  }
}

/**
 * Error handler middleware
 * @param {Error} err - Error object
 * @param {Request} req - Express request object
 * @param {Response} res - Express response object
 * @param {Function} next - Next middleware function
 */
export function errorHandler(err, req, res, next) {
  // Log error
  const timestamp = new Date().toISOString();
  console.error(`[${timestamp}] ${err.name}: ${err.message}`);

  if (err.stack && process.env.NODE_ENV === 'development') {
    console.error(err.stack);
  }

  // Handle known errors
  if (err instanceof ApiError) {
    const response = {
      error: {
        code: err.code,
        message: err.message,
      }
    };

    // Add details for validation errors
    if (err.details) {
      response.error.details = err.details;
    }

    return res.status(err.statusCode).json(response);
  }

  // Handle SQLite errors
  if (err.code && err.code.startsWith('SQLITE_')) {
    let message = 'Database error';
    let statusCode = 500;

    if (err.code === 'SQLITE_CONSTRAINT') {
      message = 'Data constraint violation';
      statusCode = 409;
    } else if (err.code === 'SQLITE_BUSY') {
      message = 'Database is busy, please try again';
      statusCode = 503;
    }

    return res.status(statusCode).json({
      error: {
        code: err.code,
        message: message,
      }
    });
  }

  // Handle JWT errors
  if (err.name === 'JsonWebTokenError') {
    return res.status(401).json({
      error: {
        code: 'INVALID_TOKEN',
        message: 'Invalid authentication token',
      }
    });
  }

  if (err.name === 'TokenExpiredError') {
    return res.status(401).json({
      error: {
        code: 'TOKEN_EXPIRED',
        message: 'Authentication token has expired',
      }
    });
  }

  // Handle unknown errors
  const statusCode = err.statusCode || 500;
  const message = process.env.NODE_ENV === 'production'
    ? 'Internal server error'
    : err.message;

  res.status(statusCode).json({
    error: {
      code: 'INTERNAL_ERROR',
      message: message,
    }
  });
}

/**
 * Not found handler middleware
 */
export function notFoundHandler(req, res) {
  res.status(404).json({
    error: {
      code: 'NOT_FOUND',
      message: `Route ${req.method} ${req.path} not found`,
    }
  });
}
