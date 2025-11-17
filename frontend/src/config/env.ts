/**
 * Environment configuration and validation
 * Ensures all required environment variables are set
 */

interface EnvConfig {
  API_URL: string;
  ENABLE_DEBUG: boolean;
  ENABLE_ANALYTICS: boolean;
  APP_VERSION: string;
  BUILD_TIME: string;
  MONACO_CDN_URL?: string;
}

class EnvironmentError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'EnvironmentError';
  }
}

/**
 * Validates and returns environment configuration
 */
function validateEnv(): EnvConfig {
  const API_URL = import.meta.env.VITE_API_URL;

  if (!API_URL) {
    throw new EnvironmentError(
      'Missing required environment variable: VITE_API_URL\n' +
      'Please create a .env file in the frontend directory with:\n' +
      'VITE_API_URL=http://localhost:8000'
    );
  }

  // Validate URL format
  try {
    new URL(API_URL);
  } catch {
    throw new EnvironmentError(
      `Invalid API URL format: ${API_URL}\n` +
      'VITE_API_URL must be a valid URL (e.g., http://localhost:8000)'
    );
  }

  return {
    API_URL,
    ENABLE_DEBUG: import.meta.env.VITE_ENABLE_DEBUG === 'true',
    ENABLE_ANALYTICS: import.meta.env.VITE_ENABLE_ANALYTICS === 'true',
    APP_VERSION: import.meta.env.VITE_APP_VERSION || '1.0.0',
    BUILD_TIME: import.meta.env.VITE_BUILD_TIME || new Date().toISOString(),
    MONACO_CDN_URL: import.meta.env.VITE_MONACO_CDN_URL,
  };
}

// Validate environment on module load
const env = validateEnv();

// Export individual config values for easy access
export const API_URL = env.API_URL;
export const ENABLE_DEBUG = env.ENABLE_DEBUG;
export const ENABLE_ANALYTICS = env.ENABLE_ANALYTICS;
export const APP_VERSION = env.APP_VERSION;
export const BUILD_TIME = env.BUILD_TIME;
export const MONACO_CDN_URL = env.MONACO_CDN_URL;

// Export full config object
export default env;

// Log configuration in development
if (import.meta.env.DEV && ENABLE_DEBUG) {
  console.log('Environment Configuration:', {
    API_URL,
    ENABLE_DEBUG,
    ENABLE_ANALYTICS,
    APP_VERSION,
    BUILD_TIME,
    MONACO_CDN_URL: MONACO_CDN_URL || 'default',
  });
}