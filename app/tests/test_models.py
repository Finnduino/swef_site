import pytest
from app import create_app
from app.models import db, User, Tournament, Competitor, Match

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False
    })

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_user_model(app):
    """Test User model creation"""
    with app.app_context():
        user = User(id=123, username="TestUser", permission_level="admin")
        db.session.add(user)
        db.session.commit()
        
        saved_user = db.session.get(User, 123)
        assert saved_user.username == "TestUser"
        assert saved_user.permission_level == "admin"

def test_tournament_model(app):
    """Test Tournament model creation"""
    with app.app_context():
        tourney = Tournament(name="Test Tourney", format="double_elim", default_bo=7)
        db.session.add(tourney)
        db.session.commit()
        
        saved_tourney = Tournament.query.first()
        assert saved_tourney.name == "Test Tourney"
        assert saved_tourney.default_bo == 7

def test_competitor_relation(app):
    """Test Relationship between Tournament, User and Competitor"""
    with app.app_context():
        user = User(id=1, username="Player1")
        tourney = Tournament(name="Tourney1")
        db.session.add_all([user, tourney])
        db.session.commit()
        
        comp = Competitor(tournament_id=tourney.id, user_id=user.id, pp=5000)
        db.session.add(comp)
        db.session.commit()
        
        assert len(tourney.competitors) == 1
        assert tourney.competitors[0].user.username == "Player1"
        assert tourney.competitors[0].pp == 5000

def test_match_override_logic(app):
    """Test that manual_override flag works in the model"""
    with app.app_context():
        match = Match(id="test-match", tournament_id=1, manual_override=True)
        db.session.add(match)
        db.session.commit()
        
        saved_match = db.session.get(Match, "test-match")
        assert saved_match.manual_override is True
