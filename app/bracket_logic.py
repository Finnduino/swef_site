from .models import db, Tournament, Competitor, Match
from .engine.bracket_engine import DoubleEliminationStrategy

def get_strategy(tournament):
    if tournament.format == 'double_elim':
        return DoubleEliminationStrategy()
    # Fallback to double_elim
    return DoubleEliminationStrategy()

def generate_bracket(tournament_id=None):
    """Bridge function for initial generation"""
    # If no ID provided, try to find the 'active' tournament
    if tournament_id:
        tournament = db.session.get(Tournament, tournament_id)
    else:
        tournament = Tournament.query.filter_by(status='active').first()
        
    if not tournament:
        return False
        
    competitors = Competitor.query.filter_by(tournament_id=tournament.id).all()
    
    # Clear existing matches for this tournament
    Match.query.filter_by(tournament_id=tournament.id).delete()
    db.session.commit()
    
    strategy = get_strategy(tournament)
    strategy.generate(tournament, competitors)
    return True

def advance_round_if_ready(tournament_id=None):
    """Bridge function for bracket advancement"""
    if tournament_id:
        tournament = db.session.get(Tournament, tournament_id)
    else:
        tournament = Tournament.query.filter_by(status='active').first()
        
    if not tournament:
        return False
        
    strategy = get_strategy(tournament)
    strategy.advance(tournament)
    return True