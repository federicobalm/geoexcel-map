from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    map_type = db.Column(db.String(50), nullable=False)
    
    map_params = db.Column(db.Text, nullable=True)
    lat_lon_cols = db.Column(db.Text, nullable=True)

    excel_path = db.Column(db.String(300), nullable=True)
    latest_map_html = db.Column(db.String(300), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Project {self.id}: {self.name}>'

    def get_map_params(self):
        return json.loads(self.map_params) if self.map_params else {}

    def get_lat_lon_cols(self):
        return json.loads(self.lat_lon_cols) if self.lat_lon_cols else {}