const roomId = new URLSearchParams(window.location.search).get('id')
const peer = new RTCPeerConnection();
let isInitiator = false
let isRemoteDescriptionSet = false
let dataArray, analyser, stream, remoteStreamSrc
const RAPID = 15
let mediaRecorder
let chunks = []
let aboveRapid = false
let lastAboveRapid = new Date().getTime()
const gap = 1000
let recorded = false
let recordingStartTime = 0
let silenceDuration = gap
let outputted = false
let start = false
const minTime = -10
const errLoss = 40
const audioQueue = []
let currentAudioIndex = 0
let audioElement
let isPlaying = false;


let handleException = (exception) => {
    console.log(exception)
}
let getUserId = () => {
    if (!localStorage.getItem('user_id')) {
        localStorage.setItem('user_id', generateUUID())
    }
    return localStorage.getItem('user_id')
}
let startChat = () => {
    const url = '/start_chat'
    const data = {
        user_id: userId,
        room_id: roomId
    }

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    }).then( (response) => {
        response.json().then( (result) => {
            if (result.status === 'success') {

            } else {
                handleException(result.status)
                window.location.href = `/join-room`
            }
        })
    })
}
const userId = getUserId()

startChat()

const socket = io.connect('http://' + document.domain + ':' + location.port)
const remoteStream = document.getElementById('remoteStream')
const localStream = document.getElementById('localStream')


socket.emit('create_instance', { room_id: roomId, user_id: userId })
socket.emit('get_chat_history', {room_id: roomId, user_id: userId})

document.addEventListener('DOMContentLoaded', async () => {
    socket.on('chat_history', addChatHistory)
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: 44100, bitrate: 128000 },
      video: true,
      preferCurrentTab: true,
    });
    const audioContext = new (window.AudioContext || window.webkitAudioContext)()
    analyser = audioContext.createAnalyser();
    // const noiseSuppression = audioContext.createDynamicsCompressor()
    // noiseSuppression.threshold.value = 100
    analyser.fftSize = 256;
    const source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);
    // noiseSuppression.connect(analyser)

    const audioElement = new Audio();
    audioElement.srcObject = stream;

    const audioSource = audioContext.createMediaElementSource(audioElement)
    // audioSource.connect(noiseSuppression);
    dataArray = new Uint8Array(analyser.frequencyBinCount);

    setInterval(updateVolumeMeter, 10);

    localStream.srcObject = stream;
    localStream.muted = true
    const audioTrack = stream.getAudioTracks()[0];
    const audioOnlyStream = new MediaStream([audioTrack])
    mediaRecorder = new MediaRecorder(audioOnlyStream, { mimeType: 'audio/webm;codecs=opus' });
    mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
            chunks.push(event.data)
        }
    };

mediaRecorder.onstop = () => {
    const audioBlob = new Blob(chunks, { type: 'audio/webm' });
    const reader = new FileReader();

    reader.onloadend = () => {
        const audioData = reader.result; // This is an ArrayBuffer
        audioContext.decodeAudioData(audioData, (buffer) => {
            console.log(buffer.duration * 1000 - gap + 40)
            console.log(1)
            if (buffer.duration * 1000 - gap + errLoss >= minTime) {
                socket.emit('new_recording', { audio: audioBlob, user_id: userId, room_id: roomId});
                console.log(buffer.duration * 1000 - gap)
            }
        });
    };

    reader.readAsArrayBuffer(audioBlob);
    chunks = [];
}


    localStream.volume = 1
    stream.getTracks().forEach(track => peer.addTrack(track, stream))
    if (!isInitiator) {
      const offer = await peer.createOffer()
      await peer.setLocalDescription(offer)
      socket.emit('offer', { data: peer.localDescription, room_id: roomId, user_id: userId })
    }
  } catch (error) {
    console.error(error)
    alert(error.message)
  }
})

socket.on('offer', async (offer) => {
    if (offer.user_id !== userId) {
          const clientSDP = offer.data.data
          await peer.setRemoteDescription(clientSDP)
          const sdp = await peer.createAnswer()
          await peer.setLocalDescription(sdp)
          socket.emit('answer', {data: peer.localDescription, room_id: roomId})
    }
})


socket.on('answer', async (answer) => {
    if (answer.user_id !== userId) {
        try {
            await peer.setRemoteDescription(answer.data.data)
            isRemoteDescriptionSet = true
        } catch (error) {
            console.error(error)
        }
    }
})


peer.addEventListener('track', (event) => {
    if (event.streams && event.streams[0]) {
        remoteStreamSrc = event.streams[0]
        remoteStream.srcObject = remoteStreamSrc
        remoteStream.style.display = 'block'
    }
})


peer.addEventListener('icecandidate', (event) => {
  if (event.candidate) {
    socket.emit('icecandidate', { data: event.candidate, room_id: roomId, user_id: userId})
  }
})

socket.on('icecandidate', async (candidate) => {
    if (candidate.user_id !== userId) {
          candidate = candidate.data.data
          await peer.addIceCandidate(new RTCIceCandidate(candidate))
    }
})

socket.on('user_joined', (data) => {
    console.log('user_joined', data.username)
})

socket.on('new_message', (data) => {
    console.log('new_message', data)
    let local = false
    if (data.user_id === userId) {
        local = true
    }
    addMessage(data.text, local, data.username)
    if (data.hasOwnProperty('audio') && data.audio !== null && data.audio !== undefined && !local) {
        addToQueue(data.audio)
    }
})

socket.on('user_left', (data) => {
    console.log('user_left', data.username)
    remoteStream.style.display = 'none'
})

let handleUserLeft = async (event) => {
    await socket.emit('user_left', { user_id: userId, room_id: roomId })
}

window.addEventListener('beforeunload', handleUserLeft)
function playVideo() {
    if (remoteStream.paused) {
        remoteStream.play().catch(error => console.error('Error playing video:', error))
    }
}

document.addEventListener('click', () => {
    playVideo()
})


function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0,
            v = c === 'x' ? r : (r & 0x3 | 0x8)
        return v.toString(16)
    })
}


function updateVolumeMeter() {
    analyser.getByteFrequencyData(dataArray)
    const averageVolume = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length
    // console.log(averageVolume)
    if (averageVolume >= RAPID) {
        outputted = false
        if (!aboveRapid) {
            if (!start) {
                console.log(('+'), averageVolume)
                // НАЧАТЬ ЗАПИСЬ
                mediaRecorder.start();
            }
            lastAboveRapid = new Date().getTime()
            aboveRapid = true
            start = true
            if (silenceDuration > gap) {
                recordingStartTime = new Date().getTime()
            }
        }
    } else {
        aboveRapid = false
        silenceDuration = new Date().getTime() - lastAboveRapid
        if (silenceDuration > gap && !outputted) {
            console.log(('-'), averageVolume, new Date().getTime() - recordingStartTime)
            outputted = true
            start = false
            mediaRecorder.stop()
        }

    }
}


let sendMessage = () => {
    const text = document.getElementById('messageInput').value.trim()
    if (text) {
        socket.emit('new_chat_message', {user_id: userId, text: text, room_id: roomId})
        document.getElementById('messageInput').value = ''
    }
}

document.getElementById('sendMessage').addEventListener('click', sendMessage)


document.getElementById('messageInput').addEventListener('keydown', function(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
    else if (event.key === 'Enter' && event.shiftKey) {
        console.log(1);
        const messageInput = document.getElementById('messageInput');
        this.value += '123';

    }
});

// let addMessage = (text, local, username) => {
//     let htmlCode = `<div class="remoteMessageBox">
//                               <div class="remoteMessageSender">${username}</div>
//                               <div class="remoteMessage">${text}</div>
//                           </div>`
//     if (local) {
//         htmlCode = `<div class="localMessageBox text-right">
//                         <div class="localMessageSender">${username}</div>
//                         <div class="localMessage">${text}</div>
//                     </div>`
//     }
//     const messagesDiv = document.getElementById('messages');
//     messagesDiv.innerHTML += htmlCode;
//     messagesDiv.scrollTop = messagesDiv.scrollHeight;
// }

let addMessage = (text, local, username) => {
    let messageDiv = document.createElement('div');
    messageDiv.classList.add(local ? 'localMessageBox' : 'remoteMessageBox');

    let senderDiv = document.createElement('div');
    senderDiv.classList.add(local ? 'localMessageSender' : 'remoteMessageSender');
    senderDiv.innerText = username;

    let textDiv = document.createElement('div');
    textDiv.classList.add(local ? 'localMessage' : 'remoteMessage');
    textDiv.innerText = text;

    messageDiv.appendChild(senderDiv);
    messageDiv.appendChild(textDiv);

    const messagesDiv = document.getElementById('messages');
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}


let addChatHistory = (data) => {
    if (data.user_id === userId) {
        console.log(data)
        document.getElementById('roomTitle').innerHTML = data.room_title
        const messages = data.messages
        messages.forEach( (message) => {
            const user_id = Object.keys(message)[0]
            const text = message[user_id][0]
            const username = message[user_id][1]
            let local = false
            if (user_id === userId) {
                local = true
            }
            console.log(user_id, text)
            addMessage(text, local, username)
        })
    }
}

let toClipboardLink = () => {
    navigator.clipboard.writeText(window.location.href)
    .catch(err => {
        console.log('Something went wrong', err)
    })
}

let toClipboardID = () => {
    navigator.clipboard.writeText(roomId)
    .catch(err => {
        console.log('Something went wrong', err)
    })
}


function addToQueue(audioData) {
    audioQueue.push(audioData);
    if (!isPlaying) {
        playNext();
    }
}


function playNext() {
    if (audioQueue.length > 0 && currentAudioIndex < audioQueue.length) {
        const audioData = audioQueue[currentAudioIndex];
        const blob = new Blob([audioData], { type: 'audio/mpeg' });
        const audioUrl = URL.createObjectURL(blob);

        if (!audioElement || audioElement.ended) {
            audioElement = new Audio(audioUrl);
            isPlaying = true;
            audioElement.play().then(() => {
                isPlaying = false;
                // if (currentAudioIndex < audioQueue.length - 1) {
                    currentAudioIndex++;
                    playNext();
                // }
            });
        } else {
            audioElement.addEventListener('ended', () => {
                currentAudioIndex++;
                playNext();
            });
        }
    }
}




document.getElementById('copyLink').addEventListener('click', toClipboardLink)
document.getElementById('copyRoomId').addEventListener('click', toClipboardID)
