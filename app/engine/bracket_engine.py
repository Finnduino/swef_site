from abc import ABC, abstractmethod
import uuid
import math
from ..models import db, Match, Competitor, Tournament

class BracketStrategy(ABC):
    @abstractmethod
    def generate(self, tournament, competitors): pass
    @abstractmethod
    def advance(self, tournament): pass

class DoubleEliminationStrategy(BracketStrategy):
    def generate(self, tournament, competitors):
        # Full clear is done in bracket_logic.py bridge
        seeded = sorted(competitors, key=lambda c: (c.placement if c.placement is not None else 9999, -c.pp))
        num_players = len(seeded)
        if num_players < 2: return []

        powers_of_2 = 1 << (num_players - 1).bit_length()
        num_upper_rounds = int(math.log2(powers_of_2))
        
        # 1. Create Upper Bracket
        for r in range(num_upper_rounds):
            num_matches = powers_of_2 // (2 ** (r + 1))
            for i in range(num_matches):
                db.session.add(Match(
                    id=str(uuid.uuid4()), tournament_id=tournament.id,
                    bracket='upper', round_index=r, match_idx=i,
                    bo_size=tournament.default_bo, status='waiting'
                ))

        # 2. Create Lower Bracket
        num_lower_rounds = 2 * (num_upper_rounds - 1)
        for lr in range(num_lower_rounds):
            num_matches = powers_of_2 // (2 ** (2 + (lr // 2)))
            for i in range(num_matches):
                db.session.add(Match(
                    id=str(uuid.uuid4()), tournament_id=tournament.id,
                    bracket='lower', round_index=lr, match_idx=i,
                    bo_size=tournament.default_bo, status='waiting'
                ))
            
        # 3. Create Grand Finals (R0 = Finals, R1 = Reset)
        for r in [0, 1]:
            db.session.add(Match(
                id=str(uuid.uuid4()), tournament_id=tournament.id,
                bracket='grand_finals', round_index=r, match_idx=0,
                bo_size=tournament.default_bo, status='waiting'
            ))

        db.session.flush()

        # 4. Fill Initial Seeds
        all_matches = Match.query.filter_by(tournament_id=tournament.id).all()
        half = powers_of_2 // 2
        top = seeded[:half]
        bottom = list(reversed(seeded[half:])) # Reverse for snake
        while len(bottom) < half: bottom.append(None)

        for i in range(half):
            p1 = top[i]
            p2 = bottom[i]
            match = next(m for m in all_matches if m.bracket == 'upper' and m.round_index == 0 and m.match_idx == i)
            match.player1_id = p1.id if p1 else None
            match.player2_id = p2.id if p2 else None
            
            if p1 and not p2:
                match.status = 'completed'; match.winner_id = p1.id; match.score_p1 = (tournament.default_bo // 2) + 1
            elif not p1 and p2:
                match.status = 'completed'; match.winner_id = p2.id; match.score_p2 = (tournament.default_bo // 2) + 1
            else:
                match.status = 'next_up'

        db.session.commit()
        self.advance(tournament)
        return all_matches

    def advance(self, tournament):
        all_matches = Match.query.filter_by(tournament_id=tournament.id).all()
        matches_by_key = { (m.bracket, m.round_index, m.match_idx): m for m in all_matches }
        
        changed = True
        while changed:
            changed = False
            for m in all_matches:
                if m.status == 'completed' and m.winner_id:
                    winner_id = m.winner_id
                    loser_id = m.player2_id if m.winner_id == m.player1_id else m.player1_id
                    
                    if m.bracket == 'upper':
                        # Winner Path
                        target_u = matches_by_key.get(('upper', m.round_index + 1, m.match_idx // 2))
                        if target_u:
                            if self._fill_player(target_u, winner_id, m.match_idx % 2): changed = True
                        else:
                            # Final Upper -> GF slot 0
                            gf = matches_by_key.get(('grand_finals', 0, 0))
                            if gf and self._fill_player(gf, winner_id, 0): changed = True
                        
                        # Loser Path
                        if loser_id:
                            if m.round_index == 0:
                                # Upper R0 losers -> Lower R0
                                target_l = matches_by_key.get(('lower', 0, m.match_idx // 2))
                                if target_l and self._fill_player(target_l, loser_id, m.match_idx % 2): changed = True
                            else:
                                # Upper Rn (n>0) losers -> Lower R(2n-1)
                                target_l = matches_by_key.get(('lower', 2 * m.round_index - 1, m.match_idx))
                                if target_l and self._fill_player(target_l, loser_id, 1): changed = True

                    elif m.bracket == 'lower':
                        # Winner Path moves to next Lower Round
                        next_r = m.round_index + 1
                        # Rounds 0, 2, 4... are "Minor" rounds (feed into Major round of same match count)
                        # Rounds 1, 3, 5... are "Major" rounds (halve count for next round)
                        is_minor = (m.round_index % 2 == 0)
                        
                        target_idx = m.match_idx if is_minor else m.match_idx // 2
                        slot = 0 if is_minor else m.match_idx % 2
                        
                        target_l = matches_by_key.get(('lower', next_r, target_idx))
                        if target_l:
                            if self._fill_player(target_l, winner_id, slot): changed = True
                        else:
                            # Final Lower -> GF slot 1
                            gf = matches_by_key.get(('grand_finals', 0, 0))
                            if gf and self._fill_player(gf, winner_id, 1): changed = True

                    elif m.bracket == 'grand_finals':
                        if m.round_index == 0 and m.winner_id == m.player2_id:
                            # Lower bracket winner wins GF R0 -> RESET
                            reset_m = matches_by_key.get(('grand_finals', 1, 0))
                            if reset_m and reset_m.status == 'waiting':
                                if self._fill_player(reset_m, m.player1_id, 0): changed = True
                                if self._fill_player(reset_m, m.player2_id, 1): changed = True
                                reset_m.status = 'next_up'
                                changed = True
        
        db.session.commit()

    def _fill_player(self, match, player_id, slot):
        if not player_id: return False
        updated = False
        if slot == 0:
            if match.player1_id != player_id:
                match.player1_id = player_id; updated = True
        else:
            if match.player2_id != player_id:
                match.player2_id = player_id; updated = True
        
        if updated and match.status == 'waiting':
            if match.player1_id and match.player2_id:
                match.status = 'next_up'
        return updated
