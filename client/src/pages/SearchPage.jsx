import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { papersApi } from '../services/api';
import { Card } from '../components/ui';

const SearchPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  // Get query from URL or form
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const urlQuery = searchParams.get('q') || '';
    setQuery(urlQuery);
  }, [location]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    const { data } = await papersApi.search(query);
    setResults(data?.results || []);
    setIsSearching(false);
    navigate(`/search?q=${encodeURIComponent(query)}`);
  };

  return (
    <section className="search-section">
      <header className="section-header">
        <h2>Search QuantumHub</h2>
      </header>

      <div className="search-form">
        <form onSubmit={handleSearch} className="search-input-group">
          <div className="input-wrapper">
            <input
              type="text"
              placeholder="Search papers, projects, and more..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={isSearching}
            />
            <button type="submit" disabled={isSearching} className="search-btn">
              {isSearching ? 'Searching...' : 'Search'}
            </button>
          </div>
        </form>
      </div>

      {isSearching && <p>Searching for papers related to: "{query}"</p>}

      {results.length > 0 && (
        <div className="search-results">
          <p>
            Found {results.length} results for "{query}"
          </p>
          <div className="results-grid">
            {results.map((item) => {
              if (item.type === 'paper') {
                return (
                  <article key={item.id} className="search-result-item">
                    <h4>
                      <a href={`/papers/${item.id}`}>{item.title}</a>
                    </h4>
                    <p className="search-result-meta">
                      {item.institution} • {item.year}
                    </p>
                  </article>
                );
              }
              return null;
            })}
          </div>
        </div>
      )}

      {results.length === 0 && !isSearching && (
        <p className="no-results">
          No results found for "{query}". Try different keywords.
        </p>
      )}
    </section>
  );
};

export default SearchPage;