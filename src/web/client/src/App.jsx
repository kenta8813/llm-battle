import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import BattleViewer from './pages/BattleViewer';
import CharacterList from './pages/CharacterList';
import Leaderboard from './pages/Leaderboard';
import Header from './components/Common/Header';
import Footer from './components/Common/Footer';
import './index.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Header />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/battle/:id" element={<BattleViewer />} />
            <Route path="/characters" element={<CharacterList />} />
            <Route path="/leaderboard" element={<Leaderboard />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}

export default App;
