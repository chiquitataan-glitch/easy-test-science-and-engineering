const REQUIRED_VARS = [
  'PORT',
  'DATABASE_URL',
  'JWT_SECRET',
  'DEEPSEEK_API_KEY'
];

const DEFAULTS = {
  NODE_ENV: 'development',
  PORT: '3000',
  JWT_EXPIRES_IN: '24h',
  JWT_REFRESH_EXPIRES_IN: '7d',
  DEEPSEEK_API_URL: 'https://api.deepseek.com/v1/chat/completions',
  UPLOAD_DIR: './uploads',
  MAX_FILE_SIZE: '20971520',
  DEFAULT_USER_QUOTA: '10',
  CORS_ORIGIN: 'http://localhost:5173',
  WECHAT_APP_ID: '',
  WECHAT_APP_SECRET: '',
  STORAGE_PROVIDER: 'local',
  LOCAL_STORAGE_DIR: './uploads'
};

function validateEnv() {
  const missing = [];

  for (const key of REQUIRED_VARS) {
    if (!process.env[key]) {
      missing.push(key);
    }
  }

  if (missing.length > 0) {
    console.error(`[ENV] Missing required environment variables: ${missing.join(', ')}`);
    console.error('[ENV] Please check your .env file against .env.example');
    process.exit(1);
  }

  for (const [key, defaultVal] of Object.entries(DEFAULTS)) {
    if (!process.env[key]) {
      process.env[key] = defaultVal;
    }
  }

  console.log('[ENV] Environment validated successfully');
}

function getConfig() {
  return {
    nodeEnv: process.env.NODE_ENV,
    port: parseInt(process.env.PORT, 10),
    databaseUrl: process.env.DATABASE_URL,
    jwt: {
      secret: process.env.JWT_SECRET,
      expiresIn: process.env.JWT_EXPIRES_IN,
      refreshSecret: process.env.JWT_REFRESH_SECRET,
      refreshExpiresIn: process.env.JWT_REFRESH_EXPIRES_IN
    },
    deepseek: {
      apiKey: process.env.DEEPSEEK_API_KEY,
      apiUrl: process.env.DEEPSEEK_API_URL
    },
    upload: {
      dir: process.env.UPLOAD_DIR,
      maxFileSize: parseInt(process.env.MAX_FILE_SIZE, 10)
    },
    quota: {
      defaultUserQuota: parseInt(process.env.DEFAULT_USER_QUOTA, 10)
    },
    cors: {
      origin: process.env.CORS_ORIGIN
    },
    wechat: {
      appId: process.env.WECHAT_APP_ID,
      appSecret: process.env.WECHAT_APP_SECRET
    },
    storage: {
      provider: process.env.STORAGE_PROVIDER,
      localDir: process.env.LOCAL_STORAGE_DIR
    }
  };
}

module.exports = { validateEnv, getConfig };
