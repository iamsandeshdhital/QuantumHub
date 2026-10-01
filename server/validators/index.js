const { body, param, query } = require('express-validator');

// Validate pagination query parameters
const validatePaperQuery = [
  query('page').optional().isInt({ min: 1 }).withMessage('Page must be a positive integer'),
  query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
  query('sortBy').optional().isIn(['year', 'citations', 'title']).withMessage('Invalid sortBy parameter'),
  query('sortOrder').optional().isIn(['asc', 'desc']).withMessage('Invalid sortOrder parameter'),
  query('institution').optional().isString().withMessage('Institution must be a string'),
  query('type').optional().isIn(['institution', 'company', 'independent']).withMessage('Invalid type'),
  query('difficulty').optional().isIn(['beginner', 'intermediate', 'advanced', 'expert']).withMessage('Invalid difficulty parameter'),
  query('tag').optional().isString().withMessage('Tag must be a string'),
  query('search').optional().isString().withMessage('Search must be a string'),
];

// Validate paper ID parameter
const validatePaperId = [
  param('id').isInt({ min: 1 }).withMessage('Paper ID must be a positive integer'),
];

// Validate paper creation (for admin use)
const validatePaperCreation = [
  body('title').trim().notEmpty().withMessage('Title is required').isLength({ max: 200 }).withMessage('Title must not exceed 200 characters'),
  body('authors').optional().isArray().withMessage('Authors must be an array'),
  body('institution').trim().notEmpty().withMessage('Institution is required'),
  body('type').optional().isIn(['institution', 'company', 'independent']).withMessage('Invalid type'),
  body('year').optional().isInt({ min: 1900, max: new Date().getFullYear() + 1 }).withMessage('Invalid year'),
  body('abstract').trim().notEmpty().withMessage('Abstract is required').isLength({ max: 10000 }).withMessage('Abstract must not exceed 10000 characters'),
  body('tags').optional().isArray().withMessage('Tags must be an array'),
  body('difficulty').optional().isIn(['beginner', 'intermediate', 'advanced', 'expert']).withMessage('Invalid difficulty'),
];

module.exports = {
  validatePaperQuery,
  validatePaperId,
  validatePaperCreation,
};