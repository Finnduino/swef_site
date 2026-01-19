from app import create_app
from app.models import db, Match, Tournament, Competitor
from app.bracket_logic import generate_bracket, advance_round_if_ready
from app.services.match_service import MatchService

app = create_app()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
with app.app_context():
    db.create_all()
    t = Tournament(name="DebugTourney", format='double_elim', status='active', default_bo=7)
    db.session.add(t)
    db.session.commit()
    
    tid = t.id
    comps = {}
    for i in range(4):
        c = Competitor(tournament_id=tid, user_id=100+i, pp=1000-i)
        db.session.add(c)
        db.session.flush()
        comps[f"p{i+1}"] = c.id
    db.session.commit()
    
    print(f"Competitor Mapping: {comps}")
    generate_bracket(tid)
    service = MatchService()
    
    # 1. P1 wins against P4
    p1_id = comps["p1"]
    p4_id = comps["p4"]
    m1 = Match.query.filter_by(bracket='upper', round_index=0, match_idx=0).one()
    print(f"\nMatch 1: {m1.player1_id} (P1?) wins vs {m1.player2_id} (P4?)")
    service.set_match_score(m1.id, 4, 0)
    advance_round_if_ready(tid)
    
    # Check U_FINAL and LOWER R0
    u_final = Match.query.filter_by(bracket='upper', round_index=1, match_idx=0).one()
    l0 = Match.query.filter_by(bracket='lower', round_index=0, match_idx=0).one()
    print(f"After M1 win -> U_FINAL: P1={u_final.player1_id}, P2={u_final.player2_id}")
    print(f"After M1 win -> L0: P1={l0.player1_id}, P2={l0.player2_id}")

    # 2. P2 wins against P3
    p2_id = comps["p2"]
    p3_id = comps["p3"]
    m2 = Match.query.filter_by(bracket='upper', round_index=0, match_idx=1).one()
    print(f"\nMatch 2: {m2.player1_id} (P2?) wins vs {m2.player2_id} (P3?)")
    service.set_match_score(m2.id, 4, 0)
    advance_round_if_ready(tid)
    
    db.session.refresh(u_final)
    db.session.refresh(l0)
    print(f"After M2 win -> U_FINAL: P1={u_final.player1_id}, P2={u_final.player2_id}")
    print(f"After M2 win -> L0: P1={l0.player1_id}, P2={l0.player2_id}")
    
    # Verification prints with readable labels
    def get_p(cid):
        for k, v in comps.items():
            if v == cid: return k
        return "None"

    print(f"\nFINAL VERIFICATION:")
    print(f"U_FINAL: {get_p(u_final.player1_id)} vs {get_p(u_final.player2_id)}")
    print(f"L0: {get_p(l0.player1_id)} vs {get_p(l0.player2_id)}")
