import pytest
import uuid
from app import create_app
from app.models import db, Tournament, Competitor, Match
from app.bracket_logic import generate_bracket, advance_round_if_ready
from app.services.match_service import MatchService

@pytest.fixture
def app():
    app = create_app()
    app.config.update({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def service():
    return MatchService()

def test_full_progression_4_players(app, service):
    """
    Simulate a 4-player tournament:
    1. Seed 4 players
    2. Upper Match 1: P1 vs P4 -> P1 wins, P4 drops to lower
    3. Upper Match 2: P2 vs P3 -> P2 wins, P3 drops to lower
    4. Lower Round 0: P4 vs P3 -> P4 wins, P3 eliminated
    5. Upper Round 1 (Finals): P1 vs P2 -> P1 wins, P2 drops to lower
    6. Lower Round 1: P4 vs P2 -> P2 wins, P4 eliminated
    7. GF Round 0: P1 vs P2 -> P2 wins (Reset)
    8. GF Round 1: P1 vs P2 -> P1 wins (Final Winner)
    """
    with app.app_context():
        # Setup
        t = Tournament(name="ProgressionTest", format="double_elim", status="active", default_bo=7)
        db.session.add(t)
        db.session.commit()
        
        # Add 4 competitors
        ids = ["p1", "p2", "p3", "p4"]
        comps = {}
        for i, pid in enumerate(ids):
            c = Competitor(tournament_id=t.id, user_id=100+i, pp=1000-i)
            db.session.add(c)
            db.session.flush() # Get the ID
            comps[pid] = c.id
        db.session.commit()
        
        # 1. Generate Bracket
        generate_bracket(t.id)
        
        def get_match_participants(bracket, r, idx):
            m = Match.query.filter_by(tournament_id=t.id, bracket=bracket, round_index=r, match_idx=idx).one()
            return m.id, m.player1_id, m.player2_id

        # Mapping for easier assertions
        rev_comps = {v: k for k, v in comps.items()}
        def p_name(cid): return rev_comps.get(cid, "None")
        
        # 2. Upper Match 1: P1 wins
        m1_id, p1_id, p4_id = get_match_participants('upper', 0, 0)
        print(f"\nM1: {p_name(p1_id)} vs {p_name(p4_id)}")
        service.set_match_score(m1_id, 4, 0)
        advance_round_if_ready(t.id)
        
        # 3. Upper Match 2: P2 wins
        m2_id, p2_id, p3_id = get_match_participants('upper', 0, 1)
        print(f"M2: {p_name(p2_id)} vs {p_name(p3_id)}")
        service.set_match_score(m2_id, 4, 0)
        advance_round_if_ready(t.id)
        
        # Verify Upper Round 1
        uf_id, uf_p1, uf_p2 = get_match_participants('upper', 1, 0)
        print(f"UF: {p_name(uf_p1)} vs {p_name(uf_p2)}")
        assert {p_name(uf_p1), p_name(uf_p2)} == {"p1", "p2"}
        
        # 4. Lower Round 0: P4 vs P3 (Losers of m1 and m2)
        l0_id, l0_p1, l0_p2 = get_match_participants('lower', 0, 0)
        print(f"L0: {p_name(l0_p1)} vs {p_name(l0_p2)}")
        assert {p_name(l0_p1), p_name(l0_p2)} == {"p4", "p3"}
        
        # P4 wins L0
        service.set_match_score(l0_id, 4, 0)
        advance_round_if_ready(t.id)
        
        # 5. Upper Final: P1 wins
        service.set_match_score(uf_id, 4, 0)
        advance_round_if_ready(t.id)
        
        # 6. Lower Round 1: Winner L0 (P4) vs Loser UF (P2)
        l1_id, l1_p1, l1_p2 = get_match_participants('lower', 1, 0)
        print(f"L1: {p_name(l1_p1)} vs {p_name(l1_p2)}")
        assert {p_name(l1_p1), p_name(l1_p2)} == {"p4", "p2"}
        
        # P2 wins L1 -> into GF
        service.set_match_score(l1_id, 0, 4)
        advance_round_if_ready(t.id)
        
        # 7. GF Round 0: Winner UF (P1) vs Winner L1 (P2)
        gf0_id, gf0_p1, gf0_p2 = get_match_participants('grand_finals', 0, 0)
        print(f"GF0: {p_name(gf0_p1)} vs {p_name(gf0_p2)}")
        assert {p_name(gf0_p1), p_name(gf0_p2)} == {"p1", "p2"}
        
        # P2 wins GF0 (Reset)
        service.set_match_score(gf0_id, 0, 4)
        advance_round_if_ready(t.id)
        
        # 8. GF Round 1 (Reset)
        gf1_id, gf1_p1, gf1_p2 = get_match_participants('grand_finals', 1, 0)
        print(f"GF1: {p_name(gf1_p1)} vs {p_name(gf1_p2)}")
        assert {p_name(gf1_p1), p_name(gf1_p2)} == {"p1", "p2"}
        
        service.set_match_score(gf1_id, 4, 0)
        advance_round_if_ready(t.id)
        
        # Final Verification
        final_gf1 = db.session.get(Match, gf1_id)
        assert final_gf1.winner_id == comps["p1"]
        assert final_gf1.status == 'completed'
