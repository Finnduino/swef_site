import pytest
from app import create_app
from app.models import db, User, Tournament, Competitor, Match
from app.services.match_service import MatchService

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

@pytest.fixture
def service():
    return MatchService()

def test_set_match_score_standard(app, service):
    """Test standard score update (BO7, first to 4)"""
    with app.app_context():
        # Setup
        t = Tournament(name="T1", default_bo=7)
        db.session.add(t)
        db.session.commit()
        
        m = Match(id="m1", tournament_id=t.id, bo_size=7)
        db.session.add(m)
        db.session.commit()
        
        # Action: Set score to 4-0
        result = service.set_match_score("m1", 4, 0)
        
        assert result['type'] == 'success'
        assert m.score_p1 == 4
        assert m.status == 'completed'

def test_set_match_score_bo3(app, service):
    """Test dynamic BO logic (BO3, first to 2)"""
    with app.app_context():
        t = Tournament(name="T1")
        db.session.add(t)
        db.session.commit()
        
        # Match is BO3
        m = Match(id="m1", tournament_id=t.id, bo_size=3)
        db.session.add(m)
        db.session.commit()
        
        # Action: Set score to 2-0 (should complete)
        service.set_match_score("m1", 2, 0)
        assert m.status == 'completed'
        
        # Action: Set score to 1-0 (should be in_progress)
        m.status = 'next_up'
        m.score_p1 = 0
        service.set_match_score("m1", 1, 0)
        assert m.status == 'in_progress'

def test_manual_override_respected(app, service):
    """Test that manual_override stops auto-refresh"""
    with app.app_context():
        t = Tournament(name="T1")
        u1 = User(id=1, username="P1")
        u2 = User(id=2, username="P2")
        db.session.add_all([t, u1, u2])
        db.session.commit()
        
        c1 = Competitor(id="c1", tournament_id=t.id, user_id=u1.id)
        c2 = Competitor(id="c2", tournament_id=t.id, user_id=u2.id)
        db.session.add_all([c1, c2])
        db.session.commit()
        
        m = Match(id="m1", tournament_id=t.id, player1_id="c1", player2_id="c2", manual_override=True)
        db.session.add(m)
        db.session.commit()
        
        # refresh_match_scores should return info message about override
        result = service.refresh_match_scores("m1")
        assert "manual override" in result['message'].lower()

def test_manual_flag_sets_override(app, service):
    """Test that setting score with manual=True sets the flag"""
    with app.app_context():
        t = Tournament(name="T1")
        db.session.add(t)
        db.session.commit()
        
        m = Match(id="m1", tournament_id=t.id, manual_override=False)
        db.session.add(m)
        db.session.commit()
        
        service.set_match_score("m1", 1, 0, manual=True)
        assert m.manual_override is True
