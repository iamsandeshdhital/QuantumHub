import React, { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { papersApi } from '../services/api';
import { Card, LoadingSpinner, ErrorMessage } from '../components/ui';

const PapersList = () => {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['all-papers'],
    queryFn: () => papersApi.getAll({ limit: 20 }),
    staleTime: 60000,
  });

  if (isLoading) return <LoadingSpinner />;
  if (isError) return <ErrorMessage error={error} />

  return (
    <section className="papers-section">
      <header className="section-header">
        <h2>Quantum Computing Papers</h2>
        <span className="paper-count">
          {data?.papers?.length} papers found
        </span>
      </header>

      <div className="papers-filters">
        <div className="filter-group">
          <label>Filter by Type:</label>
          <select>
            <option value="">All Types</option>
            <option value="institution">Institution</option>
            <option value="company">Company</option>
            <option value="independent">Independent</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Filter by Difficulty:</label>
          <select>
            <option value="">All Levels</option>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
            <option value="expert">Expert</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Search:</label>
          <input type="text" placeholder="Search papers..." />
        </div>
      </div>

      <div className="papers-grid">
        {data?.papers?.map((paper) => (
          <article key={paper.id} className="paper-card">
            <div className="paper-header">
              <h3 className="paper-title">
                <a href={`/papers/${paper.id}`}>{paper.title}</a>
              </h3>
              <span className="paper-type-badge">{paper.type}</span>
            </div>
            <p className="paper-abstract">
              {paper.abstract.substring(0, 150)}{paper.abstract.length > 150 ? '...' : ''}
            </p>
            <div className="paper-meta">
              <span>{paper.institution}</span>
              <span>{paper.year}</span>
              <span>{paper.tags?.slice(0, 2).join(', ') || '—'}</span>
            </div>
            <a href={`/papers/${paper.id}`} className="paper-link-view">View Details</a>
          </article>
        ))}
      </div>

      <div className="pagination">
        <button>Prev</button>
        <span>1</span>
        <span>2</span>
        <span>3</span>
        <button>Next</button>
      </div>
    </section>
  );
};

export default PapersList;