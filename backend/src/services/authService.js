const bcrypt = require('bcryptjs');
const { PrismaClient } = require('@prisma/client');
const { signToken } = require('./tokenService');
const { ValidationError, InvalidCredentialsError, AuthRequiredError } = require('../utils/errors');

const prisma = new PrismaClient();

const VALID_CLIENT_TYPES = ['web', 'wechat_mini_program', 'admin'];
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 8;
const BCRYPT_ROUNDS = 12;

async function register(email, password, displayName, clientType) {
  if (!EMAIL_REGEX.test(email)) {
    throw new ValidationError('邮箱格式不正确', { field: 'email' });
  }

  if (!password || password.length < MIN_PASSWORD_LENGTH) {
    throw new ValidationError(`密码长度不能少于${MIN_PASSWORD_LENGTH}位`, { field: 'password' });
  }

  if (!VALID_CLIENT_TYPES.includes(clientType)) {
    throw new ValidationError('无效的客户端类型', { field: 'clientType' });
  }

  const defaultQuota = parseInt(process.env.DEFAULT_USER_QUOTA, 10) || 10;
  const passwordHash = await bcrypt.hash(password, BCRYPT_ROUNDS);

  const result = await prisma.$transaction(async (tx) => {
    const existing = await tx.userIdentity.findUnique({
      where: {
        provider_identifier: {
          provider: 'password',
          identifier: email
        }
      }
    });

    if (existing) {
      throw new ValidationError('该邮箱已注册', { field: 'email' });
    }

    const user = await tx.user.create({
      data: {
        displayName: displayName || null
      }
    });

    await tx.userIdentity.create({
      data: {
        userId: user.id,
        provider: 'password',
        identifier: email,
        passwordHash
      }
    });

    await tx.userQuota.create({
      data: {
        userId: user.id,
        quotaTotal: defaultQuota,
        quotaUsed: 0
      }
    });

    return {
      userId: user.id,
      displayName: user.displayName
    };
  });

  const token = signToken(result.userId, clientType, 'password');

  return {
    user: {
      id: result.userId,
      displayName: result.displayName,
      email
    },
    token
  };
}

async function login(email, password, clientType) {
  if (!EMAIL_REGEX.test(email)) {
    throw new InvalidCredentialsError('邮箱或密码错误');
  }

  if (!password) {
    throw new InvalidCredentialsError('邮箱或密码错误');
  }

  if (!VALID_CLIENT_TYPES.includes(clientType)) {
    throw new ValidationError('无效的客户端类型', { field: 'clientType' });
  }

  const identity = await prisma.userIdentity.findUnique({
    where: {
      provider_identifier: {
        provider: 'password',
        identifier: email
      }
    },
    include: {
      user: {
        include: {
          quotas: true
        }
      }
    }
  });

  if (!identity || !identity.passwordHash) {
    throw new InvalidCredentialsError('邮箱或密码错误');
  }

  const valid = await bcrypt.compare(password, identity.passwordHash);
  if (!valid) {
    throw new InvalidCredentialsError('邮箱或密码错误');
  }

  const user = identity.user;
  const token = signToken(user.id, clientType, 'password');

  return {
    user: {
      id: user.id,
      displayName: user.displayName,
      email
    },
    token
  };
}

async function getMe(userId) {
  const user = await prisma.user.findUnique({
    where: { id: userId },
    include: {
      identities: {
        select: {
          id: true,
          provider: true,
          identifier: true
        }
      },
      quotas: {
        select: {
          quotaTotal: true,
          quotaUsed: true
        }
      }
    }
  });

  if (!user) {
    throw new AuthRequiredError('用户不存在');
  }

  const quota = user.quotas[0] || null;

  return {
    id: user.id,
    displayName: user.displayName,
    avatarUrl: user.avatarUrl,
    createdAt: user.createdAt,
    identities: user.identities,
    quota: quota ? {
      total: quota.quotaTotal,
      used: quota.quotaUsed,
      remaining: quota.quotaTotal - quota.quotaUsed
    } : null
  };
}

module.exports = { register, login, getMe };
