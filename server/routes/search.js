const express = require('express');
const router = express.Router();
const { getDB } = require('../config/database');
const { AppError } = require('../middleware/errorHandler');

router.get('/', async (req, res, next) => {
  try {
    const db = getDB();
    const { query } = req.query;
    
    if (!query) {
      throw new AppError('Search query is required', 400);
    }
    
    const papers = await db.getPapersByTag('search'); // This will use search logic
    // Simple search implementation - in production would use full-text search
    const results = papers.filter(p => 
      p.title.toLowerCase().includes(query.toLowerCase()) ||
      p.abstract.toLowerCase().includes(query.toLowerCase()) ||
      p.authors.some(a => a.toLowerCase().includes(query.toLowerCase()))
    );
    
    res.status(200).json({
      status: 'success',
      data: { results, query }
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;