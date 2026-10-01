import React, { useEffect, useState } from 'react';
import { useParams, useQuery } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { papersApi } from '../services/api';
import { Card } from '../components/ui';

const PaperDetail = () => {
  const { id } = useParams();
  const { data: paper, isLoading, isError } = useQuery({
    queryKey: ['paper', id],
    queryFn: () => papersApi.getById(id),
    enabled: !!id,
  });

  const [similarPapers, setSimilarPapers] = useState([]);

  useEffect(() => {
    if (paper) {
      // Fetch similar papers by tag or institution
      const { data } = useQuery({
        queryKey: ['similar-papers', paper.tags?.[0], paper.institution],
        queryFn: () => papersApi.getByTag(paper.tags?.[0] || ''),
        staleTime: 120000,
      });
      setSimilarPapers(data?.papers || []);
    }
  }, [paper]);

  if (!paper && isLoading) return <div>Loading paper...</div>;
  if (isError) return <div>Error loading paper</div>;

  return (
    <section className="paper-detail-section">
      <div className="paper-detail-container">
        <header className="paper-header">
          <h1>{paper?.title || 'Paper Detail'}</h1>
          <div className="paper-meta-info">
            <span>{paper?.institution}</span>
            <span>{paper?.year}</span>
          </div>
        </header>

        <div className="paper-content">
          <p className="paper-authors">
            Authors: {paper?.authors?.map((a, i) => `${a}${i < paper.authors.length - 1 && ', '}` || '—')}
          </p>
          <p className="paper-abstract-full">
            {paper?.abstract || 'No abstract available'}
          </p>
        </div>

        <div className="paper-actions">
          <a href={paper?.url} target="_blank" rel="noopener noreferrer" className="btn btn-primary">
            Read Original Paper
          </a>
          <button className="btn btn-secondary">Save to Favorites</button>
        </div>

        <h3>Similar Papers</h3>
        <div className="papers-grid">
          {similarPapers.map((p) => (
            <article key={p.id} className="paper-card-sm">
              <h4><a href={`/papers/${p.id}`}>{p.title.substring(0, 50)}{p.title.length > 50 ? '...' : ''}</a></h4>
              <span className="paper-institution-sm">{p.institution}</span>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};

export default PaperDetail;