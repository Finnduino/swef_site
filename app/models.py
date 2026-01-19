from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)  # osu! ID
    username = db.Column(db.String(100), nullable=False)
    avatar_url = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)
    permission_level = db.Column(db.String(20), default='player')  # 'player', 'host', 'admin', 'dev'
    
    # Relationships
    competitions = db.relationship('Competitor', backref='user', lazy=True)

class Tournament(db.Model):
    __tablename__ = 'tournaments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, default=lambda: datetime.now().year)
    status = db.Column(db.String(20), default='draft')  # 'draft', 'active', 'completed'
    format = db.Column(db.String(20), default='double_elim')  # 'double_elim', 'single_elim', 'round_robin'
    default_bo = db.Column(db.Integer, default=7)
    signups_locked = db.Column(db.Boolean, default=False)
    
    # Relationships
    competitors = db.relationship('Competitor', backref='tournament', lazy=True)
    matches = db.relationship('Match', backref='tournament', lazy=True)

class Competitor(db.Model):
    __tablename__ = 'competitors'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    placement = db.Column(db.Integer)  # Seeding placement
    pp = db.Column(db.Float, default=0)
    mappool_url = db.Column(db.String(255))
    mappool_data = db.Column(db.JSON)  # Store details of the user's 10 maps
    
    # Relationships
    matches_as_p1 = db.relationship('Match', foreign_keys='Match.player1_id', backref='p1', lazy=True)
    matches_as_p2 = db.relationship('Match', foreign_keys='Match.player2_id', backref='p2', lazy=True)

class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    bracket = db.Column(db.String(20))  # 'upper', 'lower', 'grand_finals'
    round_index = db.Column(db.Integer)
    match_idx = db.Column(db.Integer)  # Index within the round (0, 1, 2...)
    
    player1_id = db.Column(db.String(36), db.ForeignKey('competitors.id'))
    player2_id = db.Column(db.String(36), db.ForeignKey('competitors.id'))
    
    score_p1 = db.Column(db.Integer, default=0)
    score_p2 = db.Column(db.Integer, default=0)
    winner_id = db.Column(db.String(36), db.ForeignKey('competitors.id'))
    
    status = db.Column(db.String(20), default='waiting')  # 'waiting', 'next_up', 'in_progress', 'completed'
    mp_room_url = db.Column(db.String(255))
    
    manual_override = db.Column(db.Boolean, default=False)  # If True, API sync is disabled
    bo_size = db.Column(db.Integer, default=7)
    
    # Match State (JSON for now to preserve complexity but in DB)
    state = db.Column(db.JSON)  # {phase, current_turn, banned_maps, picked_maps, etc}
    
    ability_usages = db.relationship('AbilityUsage', backref='match', lazy=True)

class AbilityUsage(db.Model):
    __tablename__ = 'ability_usages'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.String(36), db.ForeignKey('matches.id'), nullable=False)
    competitor_id = db.Column(db.String(36), db.ForeignKey('competitors.id'), nullable=False)
    ability_type = db.Column(db.String(50))  # 'force_nomod', 'force_mod', 'personal_mod'
    target_map_id = db.Column(db.String(100))
    mod_choice = db.Column(db.String(10))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
