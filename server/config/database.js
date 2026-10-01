const { v4: uuidv4 } = require('uuid');

// In-memory database for demonstration
// In production, replace with MongoDB, PostgreSQL, etc.
class Database {
  constructor() {
    this.papers = new Map();
    this.projects = new Map();
    this.users = new Map();
    this.initialized = false;
  }

  async connect() {
    if (this.initialized) return;
    
    // Load papers from JSON file
    const papersData = require('../../data/papers.json');
    papersData.papers.forEach(paper => {
      this.papers.set(paper.id.toString(), {
        ...paper,
        id: paper.id.toString(),
        createdAt: new Date(),
        updatedAt: new Date()
      });
    });

    // Load projects from JSON file
    const projectsData = require('../../data/projects.json');
    projectsData.projects.forEach(project => {
      this.projects.set(project.id, {
        ...project,
        createdAt: new Date(),
        updatedAt: new Date()
      });
    });

    this.initialized = true;
    console.log(`Database initialized with ${this.papers.size} papers and ${this.projects.size} projects`);
  }

  // Paper methods
  async getAllPapers(filters = {}) {
    let results = Array.from(this.papers.values());
    
    if (filters.institution) {
      results = results.filter(p => 
        p.institution.toLowerCase().includes(filters.institution.toLowerCase())
      );
    }
    
    if (filters.type) {
      results = results.filter(p => p.type === filters.type);
    }
    
    if (filters.year) {
      results = results.filter(p => p.year === parseInt(filters.year));
    }
    
    if (filters.difficulty) {
      results = results.filter(p => p.difficulty === filters.difficulty);
    }
    
    if (filters.tag) {
      results = results.filter(p => 
        p.tags.some(t => t.toLowerCase().includes(filters.tag.toLowerCase()))
      );
    }
    
    if (filters.search) {
      const searchTerm = filters.search.toLowerCase();
      results = results.filter(p => 
        p.title.toLowerCase().includes(searchTerm) ||
        p.abstract.toLowerCase().includes(searchTerm) ||
        p.authors.some(a => a.toLowerCase().includes(searchTerm))
      );
    }
    
    // Sorting
    if (filters.sortBy) {
      const sortOrder = filters.sortOrder === 'desc' ? -1 : 1;
      results.sort((a, b) => {
        if (filters.sortBy === 'year') return (a.year - b.year) * sortOrder;
        if (filters.sortBy === 'citations') return (a.citations - b.citations) * sortOrder;
        if (filters.sortBy === 'title') return a.title.localeCompare(b.title) * sortOrder;
        return 0;
      });
    }
    
    // Pagination
    const page = parseInt(filters.page) || 1;
    const limit = parseInt(filters.limit) || 10;
    const startIndex = (page - 1) * limit;
    const endIndex = startIndex + limit;
    
    return {
      papers: results.slice(startIndex, endIndex),
      pagination: {
        currentPage: page,
        totalPages: Math.ceil(results.length / limit),
        totalItems: results.length,
        itemsPerPage: limit
      }
    };
  }

  async getPaperById(id) {
    return this.papers.get(id.toString());
  }

  async getPapersByInstitution(institution) {
    return Array.from(this.papers.values())
      .filter(p => p.institution.toLowerCase().includes(institution.toLowerCase()));
  }

  async getPapersByTag(tag) {
    return Array.from(this.papers.values())
      .filter(p => p.tags.some(t => t.toLowerCase().includes(tag.toLowerCase())));
  }

  // Project methods
  async getAllProjects(filters = {}) {
    let results = Array.from(this.projects.values());
    
    if (filters.difficulty) {
      results = results.filter(p => p.difficulty === filters.difficulty);
    }
    
    if (filters.category) {
      results = results.filter(p => p.category === filters.category);
    }
    
    if (filters.search) {
      const searchTerm = filters.search.toLowerCase();
      results = results.filter(p => 
        p.title.toLowerCase().includes(searchTerm) ||
        p.description.toLowerCase().includes(searchTerm)
      );
    }
    
    return results;
  }

  async getProjectById(id) {
    return this.projects.get(id);
  }

  // Analytics methods
  async getAnalytics() {
    const papers = Array.from(this.papers.values());
    const projects = Array.from(this.projects.values());
    
    const institutionCounts = {};
    const yearCounts = {};
    const tagCounts = {};
    const typeCounts = { institution: 0, company: 0, independent: 0 };
    const difficultyCounts = { beginner: 0, intermediate: 0, advanced: 0, expert: 0 };
    
    papers.forEach(paper => {
      // Institution counts
      institutionCounts[paper.institution] = (institutionCounts[paper.institution] || 0) + 1;
      
      // Year counts
      yearCounts[paper.year] = (yearCounts[paper.year] || 0) + 1;
      
      // Type counts
      typeCounts[paper.type] = (typeCounts[paper.type] || 0) + 1;
      
      // Difficulty counts
      difficultyCounts[paper.difficulty] = (difficultyCounts[paper.difficulty] || 0) + 1;
      
      // Tag counts
      paper.tags.forEach(tag => {
        tagCounts[tag] = (tagCounts[tag] || 0) + 1;
      });
    });
    
    return {
      totalPapers: papers.length,
      totalProjects: projects.length,
      institutionCounts,
      yearCounts,
      tagCounts,
      typeCounts,
      difficultyCounts,
      topInstitutions: Object.entries(institutionCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10),
      topTags: Object.entries(tagCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 15),
      papersByYear: Object.entries(yearCounts)
        .sort((a, b) => a[0] - b[0])
    };
  }
}

// Singleton instance
const db = new Database();

module.exports = {
  connectDB: () => db.connect(),
  getDB: () => db
};
