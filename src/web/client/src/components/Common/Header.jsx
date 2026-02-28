import { Link } from 'react-router-dom';

function Header() {
  return (
    <header className="header">
      <div className="header-container">
        <Link to="/" className="logo">
          <h1>LLM Battle Game</h1>
        </Link>
        <nav className="nav">
          <Link to="/" className="nav-link">Home</Link>
          <Link to="/characters" className="nav-link">Characters</Link>
          <Link to="/leaderboard" className="nav-link">Leaderboard</Link>
        </nav>
      </div>
    </header>
  );
}

export default Header;
