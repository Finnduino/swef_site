# Player Match Management System

This extension adds comprehensive player match management functionality to the Sand World Tournament system, allowing authenticated players to manage their mappools and participate in the pick/ban phase of matches.

## New Features Added

### 1. Player Authentication System
- **OAuth Login**: Players can now log in using their osu! accounts
- **Session Management**: Persistent login sessions for tournament participants
- **Profile Access**: Only registered tournament participants can access player features
- **Navigation Updates**: All templates now show login/logout and profile links

### 2. Player Profile Management (`/player/profile`)
- **Mappool Upload**: Players can upload their 10-map playlists
- **Match Overview**: View all your scheduled, in-progress, and completed matches
- **Tournament Status**: See your seeding and tournament progress
- **Requirements Validation**: Ensures mappool meets tournament requirements (10 maps, 2+ minutes each)

### 3. Interactive Match Interface (`/player/match/<match_id>`)
- **Real-time Match State**: Live updates of match progress
- **Three-Phase System**: 
  - **Ban Phase**: Players alternate banning 6 maps total (3 each)
  - **Pick Phase**: Players alternate picking 6 maps from remaining pool
  - **Play Phase**: Ready for gameplay with finalized mappool

### 4. Player Abilities System
Players get 3 strategic abilities per match:
- **Force NoMod** (1 use): Forces both players to play a map with no modifications
- **Force Mod** (1 use): Forces both players to use a specific mod (HD, HR, DT, etc.)
- **Personal Mod** (2 uses): Player uses a mod while opponent plays NoMod
- **Mod Hierarchy**: Force NoMod overrides Personal Mod when used on the same map

### 5. Match Management Flow
1. **Pre-Match**: Players must upload their mappools before matches can begin
2. **Match Start**: When match status becomes "next_up", players can enter match interface
3. **Ban Phase**: Players take turns banning maps (total 6 maps removed)
4. **Pick Phase**: Players alternate picking maps for the final 6-map playlist
5. **Ability Usage**: Players can strategically use abilities during pick phase
6. **Play Phase**: Final mappool is ready, players proceed to multiplayer room

## Technical Implementation

### New Routes
- `GET /player/profile` - Player profile page with mappool management
- `POST /player/upload_mappool` - Upload player's mappool playlist
- `GET /player/match/<match_id>` - Interactive match management interface
- `POST /player/match/<match_id>/action` - Handle pick/ban/ability actions
- `GET /player/match/<match_id>/state` - Get current match state (AJAX)
- `GET /logout` - Logout route

### Database Schema Extensions
New fields added to tournament data:
```json
{
  "competitors": [
    {
      "mappool_url": "https://osu.ppy.sh/playlists/...",
      "mappool_uploaded": "2025-01-23T10:30:00"
    }
  ],
  "brackets": {
    "upper": [
      {
        "match_state": {
          "phase": "ban|pick|play",
          "current_turn": "player1|player2", 
          "banned_maps": ["map1", "map2"],
          "picked_maps": [{"map_id": "map1", "picked_by": "player1", "order": 1}],
          "abilities_used": {
            "player1": {"force_nomod": false, "force_mod": false, "personal_mod": 0},
            "player2": {"force_nomod": false, "force_mod": false, "personal_mod": 0}
          },
          "map_mods": {"map1": "nomod", "map2": {"type": "personal", "player": "player1", "mod": "HD"}}
        }
      }
    ]
  }
}
```

### Frontend Features
- **Vue.js 3 Integration**: Reactive match interface with real-time updates
- **Auto-refresh**: Match state updates every 3 seconds
- **Visual Feedback**: Clear indicators for whose turn it is and match phase
- **Modal Dialogs**: Mod selection interface for abilities
- **Responsive Design**: Works on desktop and mobile devices

## User Flow Example

1. **Player Registration**: 
   - Visit tournament page → Click "Login" → Authenticate with osu!
   - System automatically registers player if new, redirects to profile

2. **Mappool Upload**:
   - Navigate to Profile → Upload 10-map playlist URL
   - System validates requirements and saves mappool

3. **Match Management**:
   - When match becomes "next_up", click "Manage Match" 
   - Use ban phase to remove opponent's strongest maps
   - Use pick phase to select favorable maps
   - Apply abilities strategically (force opponent mods, counter their picks)
   - Wait for play phase to begin multiplayer room gameplay

4. **Tournament Progression**:
   - Complete matches advance through bracket
   - View match history and detailed results
   - Track tournament progress through profile

## Tournament Rules Integration

The system enforces all tournament rules from the details page:
- ✅ **Map Length**: Only 2+ minute maps allowed in playlists
- ✅ **Mappool Size**: Exactly 10 maps per player required
- ✅ **Pick/Ban Format**: 6 bans → 6 picks → play
- ✅ **Player Abilities**: 3 abilities per player with usage limits
- ✅ **Mod Restrictions**: DT/HT considered playlist-level, not ability mods
- ✅ **Best of 7**: First to 4 map wins (managed by existing admin system)

## Security Features

- **Authentication Required**: All player routes require valid osu! login
- **Participant Verification**: Only tournament participants can access features
- **Turn Validation**: Players can only act during their turn
- **State Protection**: Match state changes are validated server-side
- **Session Management**: Secure session handling with automatic cleanup

This system transforms the tournament from a spectator experience into an interactive competition where players have direct control over their match strategy and progression.
