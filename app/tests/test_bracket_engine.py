import pytest
import uuid
from app import create_app
from app.models import db, Tournament, Competitor, Match
from app.bracket_logic import generate_bracket

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

def test_bracket_generation_4_players(app):
    """Test standard double elimination generation for 4 players"""
    with app.app_context():
        t = Tournament(name="T4", format="double_elim", status="active", default_bo=7)
        db.session.add(t)
        db.session.commit()
        
        # Add 4 competitors
        for i in range(4):
            u = Competitor(tournament_id=t.id, user_id=100+i, pp=1000-i)
            db.session.add(u)
        db.session.commit()
        
        # Action
        generate_bracket(t.id)
        
        # Verify full double-elim structure for 4 players:
        # Upper: R0 (2 matches) + R1 (1 match) = 3
        # Lower: R0 (1 match) + R1 (1 match) = 2
        # Grand Finals: R0 + R1 (reset) = 2
        # Total = 7
        matches = Match.query.filter_by(tournament_id=t.id).all()
        upper = [m for m in matches if m.bracket == 'upper']
        lower = [m for m in matches if m.bracket == 'lower']
        gf = [m for m in matches if m.bracket == 'grand_finals']
        
        assert len(matches) == 7, f"Expected 7 total matches, got {len(matches)}"
        assert len(upper) == 3, f"Expected 3 upper matches, got {len(upper)}"
        assert len(lower) == 2, f"Expected 2 lower matches, got {len(lower)}"
        assert len(gf) == 2, f"Expected 2 GF matches, got {len(gf)}"
        
        # Verify Upper R0 has the players seeded
        upper_r0 = [m for m in upper if m.round_index == 0]
        assert len(upper_r0) == 2
        assert all(m.player1_id is not None for m in upper_r0)

def test_bracket_generation_3_players_with_bye(app):
    """Test 3 players (should create 1 BYE in 4-player bracket)"""
    with app.app_context():
        t = Tournament(name="T3", format="double_elim", status="active")
        db.session.add(t)
        db.session.commit()
        
        for i in range(3):
            u = Competitor(tournament_id=t.id, user_id=200+i, pp=1000-i)
            db.session.add(u)
        db.session.commit()
        
        generate_bracket(t.id)
        
        # 3 players rounds up to 4-player bracket = 7 total matches
        matches = Match.query.filter_by(tournament_id=t.id).all()
        assert len(matches) == 7, f"Expected 7 total matches, got {len(matches)}"
        
        # In upper R0, there should be one match where player2 is None (BYE)
        upper_r0 = [m for m in matches if m.bracket == 'upper' and m.round_index == 0]
        bye_matches = [m for m in upper_r0 if m.player2_id is None]
        assert len(bye_matches) == 1, f"Expected 1 BYE match, got {len(bye_matches)}"
        
        # BYE match should be auto-completed with winner set
        assert bye_matches[0].status == 'completed'
        assert bye_matches[0].winner_id is not None
        assert bye_matches[0].winner_id == bye_matches[0].player1_id
