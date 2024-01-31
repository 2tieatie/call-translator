from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_title = db.Column(db.String(80), unique=False, nullable=False)
    participants = db.relationship('Participant', backref='room', lazy=True)
    messages = db.relationship('Message', backref='room', lazy=True)
    room_id = db.Column(db.String(80), unique=True, nullable=False)

    def __str__(self):
        return f'Room <id: {self.room_id}, name: {self.room_title}, participants: {self.participants}, messages: {self.messages}>'


class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    room_id = db.Column(db.String(80), db.ForeignKey('room.room_id'), nullable=False)
    user_id = db.Column(db.String(80), nullable=False)
    language = db.Column(db.String(80), nullable=False)

    def __str__(self):
        return f'Participant <id: {self.id}, username: {self.username}, room_id: {self.room_id}, user_id: {self.user_id}>'


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False)
    sender = db.relationship('Participant', backref='messages', foreign_keys=[sender_id])
    room_id = db.Column(db.String(80), db.ForeignKey('room.room_id'), nullable=False)

    def __str__(self):
        return f'Message <id: {self.id}, text: {self.text}, room_id: {self.room_id}, sender: {self.sender}>'

