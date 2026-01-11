# SWEF Tournament Platform - Complete Rebuild Specification

## Project Overview
Transform the current monolithic tournament site into a **modern, multi-tournament platform** with proper architecture, extensible tournament formats, and professional streaming integration.

## Core Requirements Analysis

### 1. Streaming Integration Requirements
- **OBS Overlay Compatibility**: Maintain 16:9 aspect ratio with fixed dimensions for stream integration
- **Real-time Updates**: WebSocket-based overlay updates for live tournaments
- **Multiple Overlay States**: Welcome, bracket view, match interface, victory screens, AFK mode
- **Professional Broadcasting**: Frame-perfect timing and visual consistency

### 2. Tournament Format Extensibility
- **Multiple Tournament Types**: 
  - Single Elimination
  - Double Elimination (current)
  - Battle Royale/Swiss System
  - Round Robin
- **Configurable Match Formats**:
  - Best-of-3 (BO3), Best-of-5 (BO5), Best-of-7 (BO7), Best-of-9 (BO9)
  - Different formats per tournament round (e.g., BO5 quarters → BO7 finals)
  - Customizable scoring systems
- **Bracket Generation**: Local libraries or algorithms (no external API dependencies for BRACKET MANAGEMENT)
- **Multiple Seeding Methods**:
  - **PP Seeding**: Sort by osu! Performance Points (current system)
  - **Qualifier Seeding**: Sum of n qualifier rounds, sort by total score
  - **Manual Seeding**: Tournament organizer manually sets seed positions
  - **Hybrid Systems**: Combine qualifier results with PP for tiebreaking
- **Flexible Mappool System**:
  - **Monolith Mappool**: Tournament organizer creates centralized mappool
  - **User-Submitted Mappools**: Players submit individual mappools (current system)
  - **Hybrid Mappools**: Mix of organizer maps + player submissions
- **Advanced Mod Management**:
  - **Map-Level Mod Assignment**: Assign specific mods to individual maps
  - **Three-Ability System**: 
    - **Force Mod**: Both players must play with specified mod(s) on selected map
    - **Force NoMod**: Counters Force Mod ability, forces both players to play NoMod
    - **FreeMod**: Player can select any allowed mod for themselves only (countered by Force NoMod)
  - **Ability Interactions**: Force NoMod counters both Force Mod and FreeMod abilities
  - **Configurable Ability Limits**: Customize number and usability of abilities per tournament
  - **Mod Restrictions**: Ban specific mods entirely from tournament
  - **Custom Mod Support**: Add support for osu!lazer mods and custom mod definitions
  - **Flexible Mod Rules**: Per-round mod availability and restrictions

### 3. Multi-Tournament Platform
- **Tournament Management**: Create, edit, archive multiple tournaments
- **Tournament Selection**: Dropdown interface for active/past/upcoming events
- **Independent Configuration**: Each tournament has its own settings, branding, participants

### 4. Customizable Branding System
- **Per-Tournament Branding**: Logos, colors, themes, sponsor integration
- **White-label Capability**: Remove SWEF-specific branding for client tournaments
- **Template System**: Pre-defined tournament themes with customization options

## Technical Architecture Specification

### Backend Architecture (Flask + SQLAlchemy)

#### Database Schema Design
```sql
-- Tournament Management
tournaments (
    id, name, description, tournament_type, status, 
    branding_config, match_settings, mappool_format,
    created_at, updated_at
)

-- Participant Management  
participants (
    id, tournament_id, osu_id, username, pp_rank, 
    seed_position, status, mappool_submitted
)

-- Mappool Management
mappools (
    id, tournament_id, participant_id, mappool_type,
    status, created_at, updated_at
)

-- Beatmap/Map Management
beatmaps (
    id, mappool_id, osu_beatmap_id, title, artist, 
    difficulty_name, star_rating, bpm, length,
    assigned_mods, required_mods, banned_mods,
    map_category, pick_order
)

-- Mod Configuration
tournament_mods (
    id, tournament_id, mod_acronym, mod_name,
    mod_type, is_ability, ability_limit, 
    is_banned, lazer_mod_json, custom_config
)

-- Match System
matches (
    id, tournament_id, round_number, match_number,
    player1_id, player2_id, winner_id, 
    score_p1, score_p2, match_format, status,
    osu_room_url, selected_mappool_id,
    abilities_used, created_at, completed_at
)

-- Map Selection & Abilities
map_selections (
    id, match_id, map_id, selected_by, 
    selection_type, play_order, result
)

-- Ability Usage Tracking
ability_usage (
    id, match_id, map_id, player_id,
    ability_type, ability_parameters,
    countered_by_player, countered_by_ability,
    is_active, created_at
)

-- Bracket Structure
bracket_positions (
    id, tournament_id, bracket_type, round_number,
    position, match_id, advance_to_position
)

-- Tournament Configuration
tournament_settings (
    id, tournament_id, setting_key, setting_value
)

-- Branding & Assets
tournament_branding (
    id, tournament_id, logo_url, primary_color,
    secondary_color, background_image, custom_css
)
```

#### Service Layer Architecture

**1. Tournament Service** (`services/tournament_service.py`)
```python
class TournamentService:
    def create_tournament(tournament_data) -> Tournament
    def get_active_tournaments() -> List[Tournament]  
    def get_tournament_by_id(tournament_id) -> Tournament
    def update_tournament_settings(tournament_id, settings)
    def archive_tournament(tournament_id)
```

**2. Bracket Service** (`services/bracket_service.py`) 
```python
class BracketService:
    def __init__(self, bracket_generator: BracketGenerator)
    def generate_bracket(tournament_id, tournament_type) -> Bracket
    def advance_match(match_id) -> BracketUpdate
    def get_current_matches(tournament_id) -> List[Match]
    def reset_bracket(tournament_id)
```

**3. Mappool Service** (`services/mappool_service.py`)
```python
class MappoolService:
    def create_tournament_mappool(tournament_id, beatmaps) -> Mappool
    def submit_participant_mappool(participant_id, beatmaps) -> Mappool
    def validate_mappool(mappool_id) -> ValidationResult
    def get_match_mappool(match_id) -> CombinedMappool
    def assign_map_mods(map_id, mods, mod_type) -> bool
    
class MapPoolFormat(Enum):
    MONOLITH = "monolith"              # Single tournament mappool
    USER_SUBMITTED = "user_submitted"  # Players submit individual mappools
    HYBRID = "hybrid"                  # Mix of both systems
```

**4. Mod Management Service** (`services/mod_service.py`)
```python
class ModService:
    def configure_tournament_mods(tournament_id, mod_config) -> bool
    def validate_mod_combination(mods) -> ValidationResult
    def get_available_abilities(match_id, player_id) -> List[ModAbility]
    def use_force_mod_ability(match_id, player_id, map_id, mods) -> AbilityResult
    def use_force_nomod_ability(match_id, player_id, map_id) -> AbilityResult
    def use_freemod_ability(match_id, player_id, map_id, mod) -> AbilityResult
    def check_ability_counters(match_id, map_id) -> AbilityCounterStatus
    def check_mod_restrictions(tournament_id, mod) -> bool
    
class AbilityType(Enum):
    FORCE_MOD = "force_mod"      # Both players must use specified mod(s)
    FORCE_NOMOD = "force_nomod"  # Both players must play NoMod (counters other abilities)
    FREEMOD = "freemod"          # Player selects mod for themselves only
    
class AbilityResult:
    success: bool
    message: str
    countered_by: Optional[AbilityType]
    effective_mods: Dict[str, List[str]]  # player_id -> [mods]
    
class AbilityCounterStatus:
    force_nomod_active: bool     # Force NoMod counters everything
    force_mod_active: Optional[List[str]]  # Active Force Mod requirements
    freemod_selections: Dict[str, str]     # player_id -> selected_mod
    
class LazerModSupport:
    def parse_lazer_mod_json(mod_json) -> ModDefinition
    def validate_lazer_mod(mod_definition) -> bool
    def convert_to_legacy_equivalent(lazer_mod) -> LegacyMod
```

**5. Match Service** (`services/match_service.py`)
```python
class MatchService:  
    def create_match(tournament_id, player1, player2, match_format)
    def update_match_score(match_id, score_p1, score_p2)
    def complete_match(match_id, winner_id)
    def fetch_osu_results(room_url) -> MatchResult
```

**4. osu! Integration Service** (`services/osu_service.py`)
```python
class OsuService:
    """Custom osu! OAuth implementation (NOT using ossapi for SSO)"""
    def authenticate_user(auth_code) -> OsuUser
    def refresh_access_token(refresh_token) -> TokenData
    def get_user_stats(user_id) -> UserStats  
    def fetch_multiplayer_results(room_id) -> RoomResults
    def validate_beatmap(beatmap_id) -> Beatmap
    
class OsuAuthService:
    """Handles OAuth flow with proper token management"""
    def generate_auth_url() -> str
    def exchange_code_for_token(code) -> TokenResponse
    def validate_token(access_token) -> bool
```

**5. Permission Service** (`services/permission_service.py`)
```python
class PermissionService:
    """Replaces the current broken admin system"""
    def get_user_permissions(user_id, tournament_id) -> UserPermissions
    def grant_permission(user_id, tournament_id, role) -> bool
    def revoke_permission(user_id, tournament_id, role) -> bool
    def check_permission(user_id, tournament_id, action) -> bool
    
class UserPermissions:
    tournament_owner: bool
    can_manage_brackets: bool
    can_manage_participants: bool
    can_control_matches: bool
    can_manage_overlay: bool
    can_view_admin_panel: bool
```

#### Tournament Format Strategy Pattern

**Abstract Tournament Format** (`tournament_formats/base.py`)
```python
class TournamentFormat(ABC):
    @abstractmethod
    def generate_bracket(participants: List[Participant]) -> Bracket
    @abstractmethod  
    def advance_match(match_result: MatchResult) -> BracketUpdate
    @abstractmethod
    def is_tournament_complete() -> bool
    @abstractmethod
    def get_next_matches() -> List[Match]
```

**Concrete Implementations**:
- `SingleEliminationFormat` - Classic knockout tournament
- `DoubleEliminationFormat` - Winners + Losers bracket  
- `SwissSystemFormat` - Battle royale style with rounds
- `RoundRobinFormat` - Everyone plays everyone

#### Match Format Configuration
```python
@dataclass
class MatchFormatConfig:
    best_of: int  # 3, 5, 7, 9
    map_selection: str  # "pick_ban", "predetermined", "random"
    mappool_format: MapPoolFormat
    tiebreaker_enabled: bool
    overtime_rules: dict
    ability_system: AbilitySystemConfig
    
@dataclass
class AbilitySystemConfig:
    enabled: bool
    abilities_per_player: int  # Number of abilities each player gets (default: 3)
    ability_types: List[AbilityType]  # Available ability types in tournament
    force_mod_options: List[str]  # Mods available for Force Mod ability
    freemod_options: List[str]    # Mods available for FreeMod ability
    banned_mods: List[str]        # Mods completely banned from tournament
    ability_refresh_rules: str    # "per_match", "per_round", "tournament_wide"
    
@dataclass
class ModAbilityDefinition:
    ability_type: AbilityType
    name: str
    description: str
    counter_abilities: List[AbilityType]
    usage_rules: AbilityUsageRules
    
@dataclass
class AbilityUsageRules:
    max_uses_per_player: int
    max_uses_per_match: int
    can_be_countered: bool
    counter_priority: int  # Higher priority abilities override lower priority ones
    
@dataclass
class ModRestriction:
    max_uses_per_player: Optional[int]
    max_uses_per_match: Optional[int]
    rounds_available: List[int]  # Which rounds this mod is available
    requires_permission: bool    # Requires admin approval to use
    
class TournamentRoundConfig:
    round_name: str
    match_format: MatchFormatConfig
    applies_to_rounds: List[int]
    mappool_override: Optional[int]  # Use specific mappool for this round
```

#### Mappool System Architecture
```python
class MappoolSystem:
    def __init__(self, format_type: MapPoolFormat):
        self.format = format_type
        
    def generate_match_mappool(self, match_id) -> MatchMappool:
        if self.format == MapPoolFormat.MONOLITH:
            return self._get_tournament_mappool(match_id)
        elif self.format == MapPoolFormat.USER_SUBMITTED:
            return self._combine_user_mappools(match_id)
        elif self.format == MapPoolFormat.HYBRID:
            return self._merge_tournament_and_user_maps(match_id)
            
@dataclass
class BeatmapDefinition:
    osu_beatmap_id: int
    title: str
    artist: str
    difficulty_name: str
    star_rating: float
    assigned_mods: List[ModDefinition]  # Pre-assigned mods for this map
    banned_mods: List[str]              # Mods not allowed on this map
    category: str                       # "nomod", "dt", "hr", "fl", etc.
    active_abilities: List[AbilityApplication]  # Applied abilities on this map
    
@dataclass
class AbilityApplication:
    ability_type: AbilityType
    applied_by: str  # player_id who used the ability
    target_map: int  # beatmap_id
    parameters: dict # ability-specific parameters (e.g., mods for Force Mod)
    countered_by: Optional[str]  # player_id who countered this ability
    is_active: bool  # whether ability is currently in effect
    
@dataclass
class ModDefinition:
    acronym: str           # "DT", "HR", "HD", etc.
    name: str             # "Double Time", "Hard Rock", etc.
    type: ModType         # ability, assigned, free, banned
    lazer_config: Optional[dict]  # osu!lazer specific configuration
    custom_multiplier: Optional[float]  # Custom score multiplier
    ability_context: Optional[AbilityApplication]  # If part of an ability
    
class ModType(Enum):
    FORCE_MOD_APPLIED = "force_mod_applied"    # Applied via Force Mod ability
    FORCE_NOMOD_APPLIED = "force_nomod_applied" # Applied via Force NoMod ability
    FREEMOD_APPLIED = "freemod_applied"        # Applied via FreeMod ability
    MAP_ASSIGNED = "assigned"                  # Pre-assigned to specific maps
    BANNED = "banned"                          # Prohibited in tournament
```

### Frontend Architecture (Vue.js 3 + Composition API)

#### Component Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── tournament/
│   │   │   ├── TournamentSelector.vue
│   │   │   ├── TournamentCreator.vue  
│   │   │   ├── BracketVisualization.vue
│   │   │   ├── MatchInterface.vue
│   │   │   └── MappoolManager.vue
│   │   ├── mappool/
│   │   │   ├── MappoolCreator.vue
│   │   │   ├── BeatmapSelector.vue
│   │   │   ├── ModConfigurator.vue
│   │   │   ├── AbilitySystemSetup.vue
│   │   │   └── CustomModCreator.vue
│   │   ├── overlay/
│   │   │   ├── StreamOverlay.vue (16:9 fixed dimensions)
│   │   │   ├── WelcomeScreen.vue
│   │   │   ├── MatchDisplay.vue
│   │   │   ├── VictoryScreen.vue
│   │   │   ├── AFKMode.vue
│   │   │   └── ModAbilityDisplay.vue
│   │   ├── admin/
│   │   │   ├── TournamentSettings.vue
│   │   │   ├── BrandingCustomizer.vue
│   │   │   ├── ParticipantManager.vue
│   │   │   ├── MatchControls.vue
│   │   │   ├── MappoolAdministration.vue
│   │   │   └── ModRuleManager.vue
│   │   └── common/
│   │       ├── UserAuth.vue
│   │       └── ErrorBoundary.vue
│   ├── stores/ (Pinia State Management)
│   │   ├── tournament.ts
│   │   ├── match.ts  
│   │   ├── overlay.ts
│   │   ├── mappool.ts
│   │   ├── mods.ts
│   │   └── auth.ts
│   ├── services/
│   │   ├── api.ts
│   │   ├── websocket.ts
│   │   ├── osu-api.ts
│   │   ├── mappool.ts
│   │   └── mod-management.ts
│   └── router/
│       └── index.ts
```

#### Real-time Communication (WebSocket)
```typescript
// WebSocket Event Types
interface TournamentEvents {
  'match:updated': MatchUpdateData
  'bracket:changed': BracketUpdateData  
  'overlay:state_change': OverlayStateData
  'tournament:participant_joined': ParticipantData
  'mappool:updated': MappoolUpdateData
  'mod:ability_used': ModAbilityData
  'map:selected': MapSelectionData
}

// Enhanced Overlay State Management
interface OverlayState {
  currentView: 'welcome' | 'bracket' | 'match' | 'victory' | 'afk' | 'mappool'
  currentMatch?: MatchData
  tournamentBranding: BrandingConfig
  overlayDimensions: { width: 1920, height: 1080 } // Fixed 16:9
  selectedMap?: BeatmapData
  activeAbilities?: ActiveAbilities
  modRestrictions?: ModRestrictions
}

// Ability System Data Structures
interface ActiveAbilities {
  matchId: string
  mapId: string
  abilities: AbilityApplication[]
}

interface AbilityApplication {
  abilityType: 'force_mod' | 'force_nomod' | 'freemod'
  appliedBy: string  // player_id
  parameters: AbilityParameters
  counteredBy?: string  // player_id who countered
  isActive: boolean
}

interface AbilityParameters {
  // For Force Mod
  requiredMods?: string[]
  
  // For FreeMod  
  selectedMod?: string
  playerId?: string
  
  // For Force NoMod (no parameters needed)
}

interface ModAbilityData {
  matchId: string
  mapId: string
  playerId: string
  abilityType: 'force_mod' | 'force_nomod' | 'freemod'
  parameters: AbilityParameters
  success: boolean
  counteredBy?: string
}

interface PlayerAbilities {
  playerId: string
  availableAbilities: AbilityType[]
  usedAbilities: number
  maxAbilities: number
  remainingAbilities: AbilityType[]
}
```

### Bracket Generation Library Integration

#### Local Bracket Generation (No External Dependencies)
**Requirements**: 
- No external API calls (Challonge, Battlefy, etc.)
- Self-contained algorithms for all tournament formats
- Mathematically correct bracket structures
- Support for power-of-2 and non-power-of-2 participant counts

**Implementation Strategy**:
```python
class LocalBracketGenerator:
    def __init__(self, seeding_strategy: SeedingStrategy):
        self.seeding_strategy = seeding_strategy
    
    def generate_single_elimination(participants) -> Bracket
    def generate_double_elimination(participants) -> Bracket  
    def generate_swiss_system(participants, rounds) -> Bracket
    def generate_round_robin(participants) -> Bracket
    
class SeedingStrategy(ABC):
    @abstractmethod
    def seed_participants(self, participants) -> List[Participant]
    
class PPSeedingStrategy(SeedingStrategy):
    # Sort by osu! Performance Points
    
class QualifierSeedingStrategy(SeedingStrategy):
    # Sort by qualifier round total scores
    
class ManualSeedingStrategy(SeedingStrategy):
    # Use manually assigned seed positions
```

### Streaming Overlay Specifications

#### OBS Integration Requirements
```css
/* Fixed Overlay Dimensions */
.tournament-overlay {
  width: 1920px;
  height: 1080px; 
  position: relative;
  overflow: hidden;
  background: transparent;
}

/* Responsive Zones for 16:9 */
.game-area {
  width: 1366px;  /* Game capture area */
  height: 768px;
  top: 156px;
  left: 277px;
}

.tournament-info {
  position: absolute;
  top: 0;
  width: 100%;
  height: 156px; /* Top bar */
}

.player-info {
  position: absolute;
  bottom: 0;
  width: 100%;  
  height: 156px; /* Bottom bar */
}
```

#### Overlay State Machine
```typescript
type OverlayState = 
  | 'welcome'      // Tournament intro
  | 'seeding'      // Participant list
  | 'bracket'      // Bracket overview  
  | 'match_prep'   // Pre-match setup
  | 'match_live'   // Live match display
  | 'map_victory'  // Individual map result
  | 'match_victory'// Match completion
  | 'afk'          // Away screen
  | 'outro'        // Tournament end

interface OverlayTransition {
  from: OverlayState
  to: OverlayState  
  trigger: 'manual' | 'automatic' | 'websocket'
  duration: number
}
```

### Multi-Tournament Platform Features

#### Tournament Management Interface
- **Create Tournament Wizard**: Step-by-step tournament creation
- **Tournament Dashboard**: Active tournaments overview
- **Archive System**: Historical tournament data
- **Import/Export**: Tournament data portability

#### Tournament Selection System
```typescript
interface TournamentListItem {
  id: string
  name: string
  status: 'upcoming' | 'active' | 'completed' | 'archived'
  participant_count: number
  start_date: Date
  tournament_type: TournamentType
  branding: BrandingPreview
}
```

### Customizable Branding System

#### Branding Configuration
```typescript
interface TournamentBranding {
  // Visual Identity
  tournament_name: string
  logo_url?: string
  primary_color: string
  secondary_color: string
  accent_color: string
  
  // Styling
  background_image?: string
  custom_css?: string
  font_family: string
  
  // Sponsor Integration  
  sponsors: SponsorConfig[]
  sponsor_display_mode: 'rotation' | 'static' | 'overlay'
  
  // White-label Options
  hide_platform_branding: boolean
  custom_footer_text?: string
}
```

#### Theme System
- **Default Themes**: Professional, Gaming, Minimalist, Retro
- **Theme Customization**: Color overrides, font selection, layout options
- **CSS Injection**: Advanced customization for tournament organizers

### Development Implementation Plan

#### Phase 1: Core Infrastructure (Weeks 1-2)
1. **Database Setup**: SQLAlchemy models and migrations
2. **Flask Application**: Modular blueprint architecture  
3. **Authentication**: osu! OAuth integration
4. **Basic API**: CRUD operations for tournaments/matches

#### Phase 2: Tournament Logic (Weeks 3-4)  
1. **Tournament Formats**: Strategy pattern implementation
2. **Bracket Generation**: Library integration and custom algorithms
3. **Match Management**: Scoring, advancement, completion logic
4. **Real-time Events**: WebSocket infrastructure

#### Phase 3: Frontend Development (Weeks 5-7)
1. **Vue.js Setup**: Component architecture, state management
2. **Tournament Interface**: Creation, management, participant handling
3. **Admin Dashboard**: Match controls, bracket management  
4. **Responsive Design**: Multi-device support

#### Phase 4: Streaming Integration (Weeks 8-9)
1. **OBS Overlay**: Fixed-dimension overlay with all states
2. **Real-time Updates**: WebSocket-driven overlay state changes
3. **Branding System**: Dynamic theming and customization
4. **Performance Optimization**: Smooth animations, efficient updates

#### Phase 5: Polish & Launch (Week 10)
1. **Testing**: Comprehensive testing of all tournament formats
2. **Documentation**: User guides, API documentation
3. **Deployment**: Docker containerization, production setup
4. **Migration Tools**: Import existing tournament data

### Technical Stack Summary

**Backend**:
- Flask 3.x with Blueprint architecture
- SQLAlchemy ORM with Alembic migrations  
- Flask-SocketIO for real-time communication
- Celery for background tasks
- Redis for caching and session storage

**Frontend**:
- Vue.js 3 with Composition API
- Pinia for state management  
- Vue Router for navigation
- Tailwind CSS for styling
- Vite for build tooling

**Infrastructure**:
- SQLite for both development and production
- Docker containers for deployment
- Nginx for reverse proxy
- Let's Encrypt for SSL certificates

**External Integrations**:
- osu! API v2 for authentication and match data
- Challonge API for bracket generation (optional)
- WebSocket for real-time overlay updates

## Additional Critical Requirements & Issues

### Current System Problems Identified

#### 1. Broken Permission System
**Current Issues** (from admin_routes.py analysis):
- Hardcoded admin IDs in config files
- Permission levels stored in JSON file (`full_admins`, `host_admins`)
- 4 different decorators with overlapping logic
- No per-tournament permission granularity
- Session-based auth without proper token management

**Required Solution**:
- Database-backed role system
- Per-tournament permissions (owner, moderator, viewer)
- JWT-based authentication with refresh tokens
- Granular action-based permissions

#### 2. Custom osu! OAuth Implementation
**Current Working Code** (in public_routes.py):
```python
# This OAuth implementation works - wrap it into a proper service
token_data = {
    'client_id': OSU_CLIENT_ID, 
    'client_secret': OSU_CLIENT_SECRET, 
    'code': code, 
    'grant_type': 'authorization_code', 
    'redirect_uri': OSU_CALLBACK_URL
}
token_response = requests.post(TOKEN_URL, data=token_data)
access_token = token_response.json().get('access_token')
```

**Implementation Strategy**:
- Extract existing OAuth code into `OsuAuthService`
- Add proper error handling and token refresh
- Support multiple concurrent tournaments with different auth scopes

#### 3. Broken Bracket Generation Logic
**Current Issues** (from bracket_logic.py analysis):
- 443-line monolithic function with nested state management
- Hardcoded double-elimination only
- Snake seeding algorithm embedded in generation logic
- No separation between seeding strategy and bracket structure

**Required Solution**:
- Modular bracket generation with strategy pattern
- Support for multiple tournament formats
- Configurable seeding algorithms
- Local implementation (no Challonge dependency)

### Enhanced Technical Architecture

#### Database Schema Extensions
```sql
-- Enhanced permission system
user_roles (
    id, user_id, tournament_id, role, 
    permissions_json, granted_by, created_at
)

-- Seeding configuration
seeding_configs (
    id, tournament_id, seeding_method,
    qualifier_rounds, manual_seeds, pp_weight
)

-- Qualifier rounds (for score-based seeding)
qualifier_rounds (
    id, tournament_id, round_number, 
    beatmap_id, scoring_method
)

-- Participant scores
participant_scores (
    id, participant_id, qualifier_round_id,
    score, accuracy, combo, mods
)
```

#### Permission System Architecture
```python
class TournamentRole(Enum):
    OWNER = "owner"           # Full control
    ADMIN = "admin"           # Manage brackets, participants
    MODERATOR = "moderator"   # Control matches, overlay
    VIEWER = "viewer"         # Read-only access
    
class PermissionAction(Enum):
    MANAGE_TOURNAMENT = "manage_tournament"
    MANAGE_PARTICIPANTS = "manage_participants"
    MANAGE_BRACKETS = "manage_brackets"
    CONTROL_MATCHES = "control_matches"
    CONTROL_OVERLAY = "control_overlay"
    VIEW_ADMIN_PANEL = "view_admin_panel"
```

#### Seeding System Architecture
```python
class SeedingMethod(Enum):
    PP_BASED = "pp_based"
    QUALIFIER_BASED = "qualifier_based"
    MANUAL = "manual"
    HYBRID = "hybrid"
    
class QualifierScoring(Enum):
    TOTAL_SCORE = "total_score"
    ACCURACY_WEIGHTED = "accuracy_weighted"
    PP_ESTIMATED = "pp_estimated"
    RANK_BASED = "rank_based"
```

### Implementation Priorities

#### CRITICAL (Fix Immediately)
1. **Replace JSON File Storage**: Implement SQLAlchemy models
2. **Fix Permission System**: Database-backed roles with proper JWT auth
3. **Extract OAuth Service**: Wrap existing working OAuth code
4. **Implement Local Bracket Generation**: No external API dependencies
5. **Add Seeding Configuration**: Support PP, qualifier, and manual seeding

#### HIGH PRIORITY
6. **Modular Tournament Formats**: Strategy pattern for different tournament types
7. **Enhanced Admin Interface**: Per-tournament permission management
8. **Qualifier System**: Score tracking and seeding calculation
9. **Improved Error Handling**: Comprehensive exception management

#### Additional Improvements Identified
- **Caching Layer**: Tournament data caching to reduce file I/O
- **Event System**: Proper event broadcasting for real-time updates
- **API Rate Limiting**: Protect against osu! API abuse
- **Backup System**: Tournament data backup and recovery
- **Audit Logging**: Track all admin actions and bracket changes
- **Health Monitoring**: System status and performance metrics

### Success Metrics
- **Performance**: <100ms API response times, <16ms overlay frame rendering
- **Scalability**: Support 10000 concurrent tournament participants  
- **Reliability**: 99.9% uptime during tournaments
- **Usability**: <5 clicks to create and launch a tournament
- **Flexibility**: Support all major tournament formats with custom branding
- **Security**: Proper authentication, authorization, and audit trails

This specification addresses all architectural failures from the analysis while implementing your specific requirements for OBS integration, extensible tournament formats, local bracket generation, and multi-tournament platform capabilities.