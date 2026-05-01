const { PrismaClient } = require('@prisma/client');
const { QuotaExceededError } = require('../utils/errors');

const prisma = new PrismaClient();

async function getQuotaInfo(userId) {
  let quota = await prisma.userQuota.findUnique({ where: { userId } });

  if (!quota) {
    const defaultQuota = parseInt(process.env.DEFAULT_USER_QUOTA, 10) || 10;
    quota = await prisma.userQuota.create({
      data: {
        userId,
        quotaTotal: defaultQuota,
        quotaUsed: 0
      }
    });
  }

  return {
    quotaTotal: quota.quotaTotal,
    quotaUsed: quota.quotaUsed,
    quotaRemaining: quota.quotaTotal - quota.quotaUsed
  };
}

async function checkQuota(userId) {
  const info = await getQuotaInfo(userId);

  if (info.quotaRemaining <= 0) {
    throw new QuotaExceededError('生成次数已用完，请等待重置或联系管理员');
  }
}

async function deductQuota(userId, action, resourceType, resourceId, clientType) {
  await prisma.$transaction(async (tx) => {
    const quota = await tx.userQuota.findUnique({ where: { userId } });

    if (!quota || quota.quotaUsed >= quota.quotaTotal) {
      throw new QuotaExceededError('生成次数已用完');
    }

    const newUsed = quota.quotaUsed + 1;

    await tx.userQuota.update({
      where: { userId },
      data: { quotaUsed: newUsed }
    });

    await tx.usageRecord.create({
      data: {
        userId,
        action,
        delta: -1,
        balanceAfter: quota.quotaTotal - newUsed,
        clientType: clientType || 'web',
        resourceType,
        resourceId
      }
    });
  });
}

async function getUsageRecords(userId, options = {}) {
  const page = Math.max(1, parseInt(options.page, 10) || 1);
  const pageSize = Math.min(100, Math.max(1, parseInt(options.pageSize, 10) || 20));
  const skip = (page - 1) * pageSize;

  const [records, total] = await Promise.all([
    prisma.usageRecord.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' },
      skip,
      take: pageSize
    }),
    prisma.usageRecord.count({ where: { userId } })
  ]);

  return { items: records, total, page, pageSize };
}

module.exports = { getQuotaInfo, checkQuota, deductQuota, getUsageRecords };
