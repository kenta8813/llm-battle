# LLM Battle Game - Web Client

## Overview

This is a simple, CDN-based React web client for viewing LLM Battle Game data. It provides an interactive interface to view leaderboards, character information, and battle details.

## Features

- **Leaderboard**: View top-ranked characters sorted by rating
- **Character List**: Browse all characters with their stats and battle records
- **Battle List**: View all battles with real-time status updates
- **Character Details**: Click any character to see detailed stats, abilities, and battle history
- **Battle Details**: Click any battle to see turn-by-turn action logs

## Architecture

This is a **build-free** implementation using:
- React 18 (CDN)
- ReactDOM 18 (CDN)
- Babel Standalone (CDN for JSX transformation)
- Pure CSS (dark theme)

No npm install or build step required for the client!

## Files

```
public/
├── index.html    # HTML entry point with CDN scripts
├── app.jsx       # React application (all components)
├── style.css     # Dark theme styling
└── README.md     # This file
```

## Usage

1. **Start the server**:
   ```bash
   npm start
   ```

2. **Open browser**:
   Navigate to `http://localhost:3000`

3. **Explore**:
   - Click on the tabs to switch between views
   - Click on character names in the leaderboard to see details
   - Click on character cards to see full information
   - Click on battles to see turn-by-turn logs

## API Endpoints Used

The client consumes these REST API endpoints:

- `GET /api/leaderboard` - Get top characters by rating
- `GET /api/characters` - Get all characters
- `GET /api/characters/:id` - Get character details
- `GET /api/battles` - Get all battles
- `GET /api/battles/:id` - Get battle details
- `GET /api/battles/:id/turns` - Get battle turn log

## Auto-Reload

The following views auto-reload every 5 seconds:
- Leaderboard
- Battle List

This ensures you see the latest data without manual refresh.

## Responsive Design

The UI is responsive and works on:
- Desktop (1024px+)
- Tablet (640px - 1024px)
- Mobile (< 640px)

## Customization

### Colors

Edit `style.css` to change the color scheme:

```css
:root {
  --bg-dark: #1a1a2e;        /* Main background */
  --bg-medium: #16213e;      /* Card background */
  --bg-light: #0f3460;       /* Hover background */
  --accent-primary: #e94560; /* Primary accent color */
  --accent-secondary: #533483; /* Secondary accent */
}
```

### API Base URL

By default, the client uses `window.location.origin` as the API base URL. To change this, edit `app.jsx`:

```javascript
const API_BASE = 'http://your-server:3000';
```

## Development

Since this uses Babel Standalone, JSX is transformed in the browser. This means:
- No build step required
- Instant changes (just refresh browser)
- Slower initial load (JSX transformation on-the-fly)

For production, consider:
1. Using a proper build tool (Vite, Webpack)
2. Pre-compiling JSX
3. Minifying assets
4. Adding code splitting

## Browser Compatibility

Requires a modern browser with:
- ES6+ support
- Fetch API
- CSS Grid/Flexbox

Tested on:
- Chrome 90+
- Firefox 90+
- Safari 14+
- Edge 90+

## Future Enhancements

Potential improvements:
- WebSocket integration for real-time battle updates
- Character comparison tool
- Battle replay with animation
- Search and filter functionality
- Dark/light theme toggle
- Export battle logs
- Character stats visualization (charts)

## Troubleshooting

**Problem**: Page is blank
- Check browser console for errors
- Ensure server is running on port 3000
- Verify all CDN scripts loaded correctly

**Problem**: API errors
- Check server logs
- Verify database exists and has data
- Test API endpoints directly (e.g., `/api/leaderboard`)

**Problem**: Styles not applied
- Clear browser cache
- Verify `style.css` loads correctly
- Check for CSS syntax errors

## License

Part of LLM Battle Game project.
