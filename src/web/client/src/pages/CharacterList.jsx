import { useState, useEffect } from 'react';
import { getCharacters } from '../api/client';
import CharacterItem from '../components/Character/CharacterItem';
import Loading from '../components/Common/Loading';

function CharacterList() {
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchCharacters() {
      try {
        setLoading(true);
        setError(null);
        const data = await getCharacters(100, 0);
        setCharacters(data || []);
      } catch (err) {
        console.error('Failed to fetch characters:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchCharacters();
  }, []);

  if (loading) {
    return <Loading message="キャラクター情報を読み込み中..." />;
  }

  if (error) {
    return (
      <div className="error-page">
        <h2>エラーが発生しました</h2>
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>再読み込み</button>
      </div>
    );
  }

  return (
    <div className="character-list-page">
      <div className="page-header">
        <h1>キャラクター一覧</h1>
        <p className="character-count">全{characters.length}体のキャラクター</p>
      </div>

      {characters.length === 0 ? (
        <div className="no-characters">
          <p>まだキャラクターが登録されていません</p>
        </div>
      ) : (
        <div className="character-grid">
          {characters.map(character => (
            <CharacterItem
              key={character.id}
              character={character}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default CharacterList;
