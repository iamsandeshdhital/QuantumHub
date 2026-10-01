const express = require('express');
const router = express.Router();
const { getDB } = require('../config/database');

router.get('/', async (req, res, next) => {
  try {
    const db = getDB();
    const analytics = await db.getAnalytics();
    
    res.status(200).json({
      status: 'success',
      data: { analytics }
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;