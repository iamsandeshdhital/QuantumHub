const express = require('express');
const router = express.Router();
const { getDB } = require('../config/database');
const { AppError } = require('../middleware/errorHandler');
const { validatePaperQuery } = require('../validators/paperValidator');

// GET /api/papers - Get all papers with filtering and pagination
router.get('/', validatePaperQuery, async (req, res, next) => {
  try {
    const db = getDB();
    const result = await db.getAllPapers(req.query);
    
    res.status(200).json({
      status: 'success',
      data: result
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/papers/:id - Get a single paper by ID
router.get('/:id', async (req, res, next) => {
  try {
    const db = getDB();
    const paper = await db.getPaperById(req.params.id);
    
    if (!paper) {
      throw new AppError('Paper not found', 404);
    }
    
    res.status(200).json({
      status: 'success',
      data: { paper }
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/papers/institution/:institution - Get papers by institution
router.get('/institution/:institution', async (req, res, next) => {
  try {
    const db = getDB();
    const papers = await db.getPapersByInstitution(req.params.institution);
    
    res.status(200).json({
      status: 'success',
      data: { papers }
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/papers/tag/:tag - Get papers by tag
router.get('/tag/:tag', async (req, res, next) => {
  try {
    const db = getDB();
    const papers = await db.getPapersByTag(req.params.tag);
    
    res.status(200).json({
      status: 'success',
      data: { papers }
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;
