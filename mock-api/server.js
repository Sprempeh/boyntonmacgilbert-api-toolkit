/**
 * Payment Refund API - Mock Server
 * =================================
 * 
 * A fully functional mock server that simulates the Payment Refund API.
 * Use this for demos, testing, and development.
 * 
 * Start: npm start
 * Base URL: http://localhost:3000/v2
 */

const express = require('express');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// In-memory storage
const refunds = new Map();
const transactions = new Map();

// Seed some test transactions
const seedTransactions = () => {
  const testTransactions = [
    { id: 'txn_1234567890abcdef', amount: 5000, currency: 'USD', status: 'captured' },
    { id: 'txn_0987654321fedcba', amount: 10000, currency: 'USD', status: 'captured' },
    { id: 'txn_test_success_full', amount: 7500, currency: 'USD', status: 'captured' },
    { id: 'txn_test_success_partial', amount: 15000, currency: 'USD', status: 'captured' },
    { id: 'txn_test_not_captured', amount: 3000, currency: 'USD', status: 'authorized' },
    { id: 'txn_test_max_refunds', amount: 5000, currency: 'USD', status: 'captured', refundCount: 5 },
    { id: 'txn_test_expired', amount: 2000, currency: 'USD', status: 'captured', createdAt: '2023-01-01' },
  ];
  
  testTransactions.forEach(txn => transactions.set(txn.id, txn));
};

seedTransactions();

// Logger middleware
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} | ${req.method} ${req.path}`);
  next();
});

// Auth middleware (simplified for demo)
const authenticate = (req, res, next) => {
  const authHeader = req.headers.authorization;
  
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({
      error: 'UNAUTHORIZED',
      message: 'Authentication token is required',
      details: { requiredAuth: 'Bearer token (OAuth 2.0 or JWT)' },
      code: 'AUTHENTICATION_ERROR',
      timestamp: new Date().toISOString()
    });
  }
  
  // For demo purposes, accept any token
  next();
};

// =============================================================================
// ENDPOINTS
// =============================================================================

// Health Check
app.get('/v2/health', (req, res) => {
  res.json({
    status: 'healthy',
    version: '2.1.0',
    timestamp: new Date().toISOString(),
    dependencies: {
      database: 'healthy',
      paymentGateway: 'healthy',
      notificationService: 'healthy'
    }
  });
});

// Create Refund
app.post('/v2/refunds', authenticate, (req, res) => {
  const { transactionId, amount, currency, reason, notifyCustomer, metadata } = req.body;
  
  // Validate required fields
  if (!transactionId) {
    return res.status(400).json({
      error: 'VALIDATION_ERROR',
      message: 'transactionId is required',
      details: { field: 'transactionId', issue: 'Missing required field' },
      code: 'VALIDATION_ERROR',
      timestamp: new Date().toISOString()
    });
  }
  
  if (!reason) {
    return res.status(400).json({
      error: 'VALIDATION_ERROR',
      message: 'reason is required',
      details: { field: 'reason', issue: 'Missing required field' },
      code: 'VALIDATION_ERROR',
      timestamp: new Date().toISOString()
    });
  }
  
  // Check if transaction exists
  const transaction = transactions.get(transactionId);
  if (!transaction) {
    return res.status(404).json({
      error: 'TRANSACTION_NOT_FOUND',
      message: 'The specified transaction does not exist',
      details: { transactionId },
      code: 'RESOURCE_NOT_FOUND',
      timestamp: new Date().toISOString()
    });
  }
  
  // Check if transaction is captured
  if (transaction.status !== 'captured') {
    return res.status(400).json({
      error: 'TRANSACTION_NOT_ELIGIBLE',
      message: "Refunds can only be issued for transactions in 'captured' status",
      details: {
        transactionId,
        currentStatus: transaction.status,
        eligibleStatuses: ['captured']
      },
      code: 'BUSINESS_RULE_VIOLATION',
      timestamp: new Date().toISOString()
    });
  }
  
  // Check max refunds
  if (transaction.refundCount >= 5) {
    return res.status(400).json({
      error: 'MAX_REFUNDS_EXCEEDED',
      message: 'Maximum of 5 refunds allowed per transaction',
      details: {
        transactionId,
        currentRefundCount: transaction.refundCount,
        maxRefunds: 5
      },
      code: 'BUSINESS_RULE_VIOLATION',
      timestamp: new Date().toISOString()
    });
  }
  
  // Calculate refund amount
  const refundAmount = amount || transaction.amount;
  
  // Check if amount exceeds transaction
  if (refundAmount > transaction.amount) {
    return res.status(400).json({
      error: 'INVALID_REFUND_AMOUNT',
      message: 'Refund amount exceeds the original transaction amount',
      details: {
        transactionId,
        originalAmount: transaction.amount,
        requestedRefundAmount: refundAmount,
        currency: transaction.currency
      },
      code: 'VALIDATION_ERROR',
      timestamp: new Date().toISOString()
    });
  }
  
  // Create the refund
  const refundId = `rfnd_${uuidv4().replace(/-/g, '').substring(0, 12)}`;
  const now = new Date().toISOString();
  const estimatedCompletion = new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString(); // 4 hours later
  
  const refund = {
    refundId,
    transactionId,
    status: 'pending',
    amount: transaction.amount,
    currency: transaction.currency,
    refundAmount,
    refundCurrency: currency || transaction.currency,
    reason,
    notifyCustomer: notifyCustomer || false,
    createdAt: now,
    updatedAt: now,
    estimatedCompletionTime: estimatedCompletion,
    metadata: metadata || {},
    statusHistory: [
      { status: 'pending', timestamp: now, message: 'Refund request created' }
    ],
    links: {
      self: `/refunds/${refundId}`,
      status: `/refunds/${refundId}/status`,
      cancel: `/refunds/${refundId}/cancel`
    }
  };
  
  refunds.set(refundId, refund);
  
  // Update transaction refund count
  transaction.refundCount = (transaction.refundCount || 0) + 1;
  
  res.status(201).json(refund);
});

// List Refunds
app.get('/v2/refunds', authenticate, (req, res) => {
  const { status, transactionId, page = 1, pageSize = 20 } = req.query;
  
  let results = Array.from(refunds.values());
  
  // Filter by status
  if (status) {
    results = results.filter(r => r.status === status);
  }
  
  // Filter by transaction
  if (transactionId) {
    results = results.filter(r => r.transactionId === transactionId);
  }
  
  // Sort by created date (newest first)
  results.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  
  // Paginate
  const startIndex = (page - 1) * pageSize;
  const paginatedResults = results.slice(startIndex, startIndex + parseInt(pageSize));
  
  res.json({
    refunds: paginatedResults.map(r => ({
      refundId: r.refundId,
      transactionId: r.transactionId,
      status: r.status,
      amount: r.amount,
      refundAmount: r.refundAmount,
      currency: r.currency,
      createdAt: r.createdAt
    })),
    pagination: {
      page: parseInt(page),
      pageSize: parseInt(pageSize),
      totalPages: Math.ceil(results.length / pageSize),
      totalItems: results.length,
      hasNext: startIndex + parseInt(pageSize) < results.length,
      hasPrevious: page > 1
    }
  });
});

// Get Refund Details
app.get('/v2/refunds/:refundId', authenticate, (req, res) => {
  const { refundId } = req.params;
  
  const refund = refunds.get(refundId);
  
  if (!refund) {
    return res.status(404).json({
      error: 'REFUND_NOT_FOUND',
      message: 'The specified refund does not exist',
      details: { refundId },
      code: 'RESOURCE_NOT_FOUND',
      timestamp: new Date().toISOString()
    });
  }
  
  res.json(refund);
});

// Get Refund Status
app.get('/v2/refunds/:refundId/status', authenticate, (req, res) => {
  const { refundId } = req.params;
  
  const refund = refunds.get(refundId);
  
  if (!refund) {
    return res.status(404).json({
      error: 'REFUND_NOT_FOUND',
      message: 'The specified refund does not exist',
      details: { refundId },
      code: 'RESOURCE_NOT_FOUND',
      timestamp: new Date().toISOString()
    });
  }
  
  res.json({
    refundId: refund.refundId,
    status: refund.status,
    updatedAt: refund.updatedAt,
    completedAt: refund.completedAt,
    failedAt: refund.failedAt,
    estimatedCompletionTime: refund.estimatedCompletionTime,
    statusHistory: refund.statusHistory
  });
});

// Cancel Refund
app.post('/v2/refunds/:refundId/cancel', authenticate, (req, res) => {
  const { refundId } = req.params;
  const { reason } = req.body;
  
  const refund = refunds.get(refundId);
  
  if (!refund) {
    return res.status(404).json({
      error: 'REFUND_NOT_FOUND',
      message: 'The specified refund does not exist',
      details: { refundId },
      code: 'RESOURCE_NOT_FOUND',
      timestamp: new Date().toISOString()
    });
  }
  
  if (refund.status !== 'pending') {
    return res.status(400).json({
      error: 'REFUND_NOT_CANCELLABLE',
      message: `Refund in '${refund.status}' status cannot be cancelled`,
      details: {
        refundId,
        currentStatus: refund.status,
        cancellableStatuses: ['pending']
      },
      code: 'BUSINESS_RULE_VIOLATION',
      timestamp: new Date().toISOString()
    });
  }
  
  const now = new Date().toISOString();
  
  refund.status = 'cancelled';
  refund.updatedAt = now;
  refund.cancelledAt = now;
  refund.cancellationReason = reason || 'No reason provided';
  refund.statusHistory.push({
    status: 'cancelled',
    timestamp: now,
    message: `Refund cancelled: ${reason || 'No reason provided'}`
  });
  
  // Remove cancel link since it's no longer applicable
  delete refund.links.cancel;
  
  res.json({
    refundId: refund.refundId,
    status: 'cancelled',
    cancelledAt: now,
    cancellationReason: refund.cancellationReason
  });
});

// Simulate refund processing (for demo purposes)
app.post('/v2/refunds/:refundId/simulate-complete', authenticate, (req, res) => {
  const { refundId } = req.params;
  
  const refund = refunds.get(refundId);
  
  if (!refund) {
    return res.status(404).json({
      error: 'REFUND_NOT_FOUND',
      message: 'The specified refund does not exist',
      details: { refundId },
      code: 'RESOURCE_NOT_FOUND',
      timestamp: new Date().toISOString()
    });
  }
  
  const now = new Date().toISOString();
  
  // Add processing status
  refund.statusHistory.push({
    status: 'processing',
    timestamp: new Date(Date.now() - 1000).toISOString(),
    message: 'Refund is being processed'
  });
  
  // Complete the refund
  refund.status = 'completed';
  refund.updatedAt = now;
  refund.completedAt = now;
  refund.statusHistory.push({
    status: 'completed',
    timestamp: now,
    message: 'Refund completed successfully'
  });
  
  delete refund.links.cancel;
  
  res.json({
    refundId: refund.refundId,
    status: 'completed',
    completedAt: now,
    message: 'Refund simulated to completion (demo only)'
  });
});

// OAuth Token endpoint (mock)
app.post('/oauth/token', (req, res) => {
  const { grant_type, client_id, client_secret } = req.body;
  
  if (grant_type !== 'client_credentials') {
    return res.status(400).json({
      error: 'unsupported_grant_type',
      error_description: 'Only client_credentials grant type is supported'
    });
  }
  
  if (!client_id || !client_secret) {
    return res.status(400).json({
      error: 'invalid_client',
      error_description: 'Client credentials are required'
    });
  }
  
  // Generate a mock token
  const token = `mock_token_${uuidv4()}`;
  
  res.json({
    access_token: token,
    token_type: 'Bearer',
    expires_in: 3600,
    scope: 'refunds:read refunds:write'
  });
});

// =============================================================================
// START SERVER
// =============================================================================

app.listen(PORT, () => {
  console.log(`
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   Payment Refund API - Mock Server                           ║
║                                                               ║
║   Base URL: http://localhost:${PORT}/v2                         ║
║   Health:   http://localhost:${PORT}/v2/health                  ║
║                                                               ║
║   Test Transactions:                                          ║
║   - txn_1234567890abcdef (captured, $50.00)                  ║
║   - txn_test_success_full (captured, $75.00)                 ║
║   - txn_test_not_captured (authorized - will fail)           ║
║   - txn_test_max_refunds (max refunds reached)               ║
║                                                               ║
║   Get a token: POST /oauth/token                             ║
║   (any client_id/client_secret will work)                    ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
  `);
});
