import json
import os
from app import create_app
from app.models import db, User, Tournament, Competitor, Match, AbilityUsage
from datetime import datetime

def migrate():
    app = create_app()
    with app.app_context():
        # Load JSON data
        json_path = 'tournament.json'
        if not os.path.exists(json_path):
            print("Error: tournament.json not found.")
            return

        with open(json_path, 'r') as f:
            data = json.load(f)

        print("Starting migration...")

        # 1. Create Default Tournament
        tourney_name = data.get('tournament_name', 'SWEF 2026')
        tournament = Tournament.query.filter_by(name=tourney_name).first()
        if not tournament:
            tournament = Tournament(
                name=tourney_name,
                year=2026,
                status='active',
                format='double_elim',
                signups_locked=data.get('signups_locked', False)
            )
            db.session.add(tournament)
            db.session.commit()
            print(f"Created tournament: {tourney_name}")

        # 2. Migrate Competitors/Users
        competitors_map = {} # map json user_id to db competitor id
        for comp_data in data.get('competitors', []):
            user_id = comp_data.get('id')
            if not user_id: continue
            
            # Create/Update User
            user = User.query.get(user_id)
            if not user:
                user = User(
                    id=user_id,
                    username=comp_data.get('name', 'Unknown'),
                    avatar_url=comp_data.get('avatar_url'),
                    permission_level='player'
                )
                db.session.add(user)
            
            # Create Competitor entry for this tournament
            competitor = Competitor.query.filter_by(tournament_id=tournament.id, user_id=user_id).first()
            if not competitor:
                competitor = Competitor(
                    tournament_id=tournament.id,
                    user_id=user_id,
                    placement=comp_data.get('placement'),
                    pp=comp_data.get('pp', 0),
                    mappool_url=comp_data.get('mappool_url'),
                    mappool_data=comp_data.get('mappool_details')
                )
                db.session.add(competitor)
                db.session.flush() # Get the ID
            
            competitors_map[user_id] = competitor.id
        
        db.session.commit()
        print(f"Migrated {len(competitors_map)} competitors.")

        # 3. Migrate Matches
        match_count = 0
        brackets = data.get('brackets', {})
        for bracket_name, rounds in brackets.items():
            if not rounds: continue
            
            # Handle list of rounds (upper/lower) or single dict (grand_finals)
            rounds_list = rounds if isinstance(rounds, list) else [rounds]
            
            for round_idx, round_matches in enumerate(rounds_list):
                # Sometimes round_matches is a list, sometimes a dict (for GF)
                matches_to_process = round_matches if isinstance(round_matches, list) else [round_matches]
                
                for m_data in matches_to_process:
                    if not m_data or not isinstance(m_data, dict): continue
                    
                    match_id = m_data.get('id')
                    if not match_id: continue
                    
                    p1_id = m_data.get('player1', {}).get('id')
                    p2_id = m_data.get('player2', {}).get('id')
                    winner_id_json = m_data.get('winner', {}).get('id') if m_data.get('winner') else None
                    
                    match = Match.query.get(match_id)
                    if not match:
                        match = Match(
                            id=match_id,
                            tournament_id=tournament.id,
                            bracket=bracket_name,
                            round_index=round_idx,
                            player1_id=competitors_map.get(p1_id),
                            player2_id=competitors_map.get(p2_id),
                            score_p1=m_data.get('score_p1', 0),
                            score_p2=m_data.get('score_p2', 0),
                            winner_id=competitors_map.get(winner_id_json),
                            status=m_data.get('status', 'waiting'),
                            mp_room_url=m_data.get('mp_room_url'),
                            state=m_data.get('match_state'),
                            bo_size=7 # Default
                        )
                        db.session.add(match)
                        match_count += 1
        
        db.session.commit()
        print(f"Migrated {match_count} matches.")
        print("Migration complete!")

if __name__ == '__main__':
    migrate()
