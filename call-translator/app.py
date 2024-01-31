import datetime
from io import BytesIO

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, join_room, leave_room
from models.models import db, Room, Participant, Message
from flask import request
from dotenv import load_dotenv
import os
from utils.translate import Translator
from uuid import uuid4
from languages.get_languages import languages, names, get_language

dotenv_path = os.path.join("config", "config.env")
load_dotenv(dotenv_path=dotenv_path)
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
socketio = SocketIO(app)
rooms = {}
USER_ALREADY_JOINED = os.getenv('USER_ALREADY_JOINED')
ROOM_IS_FOOL = os.getenv('ROOM_IS_FOOL')


class DBManager:
    db = db

    @classmethod
    def update_participant(cls, user_id, username, room_id, language):
        existing_participant = Participant.query.filter_by(user_id=user_id).first()

        if existing_participant:
            existing_participant.username = username
            existing_participant.room_id = room_id
            existing_participant.language = language
        else:
            new_participant = Participant(user_id=user_id, username=username, room_id=room_id, language=language)
            db.session.add(new_participant)
        db.session.commit()

    @classmethod
    def create_room(cls, user_id: str, username: str, room_id: str, room_title: str, language: str):
        cls.update_participant(user_id=user_id, username=username, room_id=room_id, language=language)
        room_ = Room(room_id=room_id, room_title=room_title)
        db.session.add(room_)
        db.session.commit()
        participant = Participant.query.filter_by(user_id=user_id).first()
        room_.participants.append(participant)
        db.session.commit()
        return 'success'

    @classmethod
    def join_room(cls, user_id: str, username: str, room_id: str, language: str):
        room_ = Room.query.filter_by(room_id=room_id).first()
        if len(room_.participants) >= 2:
            return ROOM_IS_FOOL

        for participant in room_.participants:
            if participant.id == user_id:
                return USER_ALREADY_JOINED

        cls.update_participant(user_id=user_id, username=username, room_id=room_id, language=language)
        participant = Participant.query.filter_by(user_id=user_id).first()

        room_.participants.append(participant)
        db.session.commit()

        return 'success'

    @classmethod
    def add_message(cls, text: str, user_id: str, room_id: str):
        message = Message(text=text, sender_id=user_id, room_id=room_id)
        db.session.add(message)
        db.session.commit()


@app.route('/languages', methods=['GET'])
def get_languages():
    langs = names
    return jsonify({'names': names})


@app.route('/create_room', methods=['POST'])
def create_room():
    data = request.get_json()
    user_id = data.get('user_id')
    username = data.get('username')
    room_title = data.get('room_title')
    room_id = data.get('room_id')
    language = data.get('language')
    print(language)
    status = DBManager.create_room(
        user_id=user_id,
        username=username,
        room_id=room_id,
        room_title=room_title,
        language=language
    )

    return jsonify({'status': status})


@app.route('/start_chat', methods=['POST'])
def start_chat():
    data = request.get_json()
    user_id = data.get('user_id')
    room_id = data.get('room_id')
    status = 'success'

    if not Participant.query.filter_by(user_id=user_id).first():
        status = 'error'

    return jsonify({'status': status})


@app.route('/join_room', methods=['POST'])
def join_r():
    data = request.get_json()
    user_id = data.get('user_id')
    username = data.get('username')
    room_id = data.get('room_id')
    language = data.get('language')
    print(language)
    status = DBManager.join_room(user_id=user_id, username=username, room_id=room_id, language=language)
    return jsonify({'status': status})


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/room')
def room():
    room_id = request.args.get('id')
    return render_template('room.html')


@app.route('/join-room')
def join():
    return render_template('joinRoom.html')


@app.route('/create-room')
def create():
    return render_template('createRoom.html')


@socketio.on('create_instance')
def create_instance(data):
    room_id = data['room_id']
    user_id = data['user_id']
    join_room(room_id)
    participant = Participant.query.filter_by(user_id=user_id).first()
    username = participant.username
    socketio.emit('user_joined', {'username': username}, room=room_id)


@socketio.on('user_left')
def user_left(data):
    room_id = data['room_id']
    user_id = data['user_id']
    leave_room(room_id)
    participant = Participant.query.filter_by(user_id=user_id).first()
    username = participant.username
    room_ = Room.query.filter_by(room_id=room_id).first()
    room_.participants.remove(participant)
    socketio.emit('user_left', {'username': username, 'user_id': user_id}, room=room_id)


@socketio.on('offer')
def offer(data):

    user_id = None
    try:
        user_id = data['user_id']
    except:
        pass
    room_id = data['room_id']
    socketio.emit('offer', {'data': data, 'user_id': user_id}, room=room_id)


@socketio.on('answer')
def answer(data):
    user_id = None
    try:
        user_id = data['user_id']
    except:
        pass
    room_id = data['room_id']
    socketio.emit('answer', {'data': data, 'user_id': user_id}, room=room_id)


@socketio.on('icecandidate')
def icecandidate(data):
    user_id = None
    try:
        user_id = data['user_id']
    except:
        pass
    room_id = data['room_id']
    socketio.emit('icecandidate', {'data': data, 'user_id': user_id}, room=room_id)


@socketio.on('new_recording')
def new_recording(data):
    user_id = data['user_id']
    room_id = data['room_id']
    audio_blob = BytesIO(data['audio'])
    # participant_language = Participant.query.filter_by(user_id=user_id).first().language
    room_ = Room.query.filter_by(room_id=room_id).first()
    sender = None
    receiver = None

    if len(room_.participants) > 1:
        for participant in room_.participants:
            if participant.user_id == user_id:
                sender = participant
            else:
                receiver = participant
    else:
        sender = room_.participants[0]
        receiver = room_.participants[0]

    deepl_language = get_language(receiver.language, 'deepl')
    deepgram_language = get_language(sender.language, 'deepgram')
    gtts_language = get_language(receiver.language, 'gtts')
    result = Translator.translate(
        audio_bytes=audio_blob, deepl_language=deepl_language, deepgram_language=deepgram_language
    )
    if result['status'] == 'success':
        text = result['text']
        audio_bytes = Translator.make_audio(text, language=gtts_language)
        DBManager.add_message(text=text, user_id=user_id, room_id=room_id)
        username = Participant.query.filter_by(user_id=user_id).first().username
        socketio.emit('new_message', {'username': username, 'user_id': user_id, 'text': text, 'audio': audio_bytes},
                      room=room_id)


@socketio.on('new_chat_message')
def new_chat_message(data):
    user_id = data['user_id']
    room_id = data['room_id']
    text = data['text']
    username = Participant.query.filter_by(user_id=user_id).first().username
    DBManager.add_message(text=text, user_id=user_id, room_id=room_id)
    socketio.emit('new_message', {'username': username, 'user_id': user_id, 'text': text}, room=room_id)


@socketio.on('get_chat_history')
def get_chat_history(data):
    room_id = data['room_id']
    user_id = data['user_id']
    messages = [
        {
            message.sender_id: [message.text, Participant.query.filter_by(user_id=message.sender_id).first().username]
        } for message in Message.query.filter_by(room_id=room_id).all()
    ]
    room_title = Room.query.filter_by(room_id=room_id).first().room_title
    socketio.emit('chat_history', {'messages': messages, 'user_id': user_id, 'room_title': room_title})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, port=8080)
