from flask import Flask, render_template, Response
from flask_sock import Sock
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
import cv2
import numpy as np

app = Flask(__name__)
sock = Sock(app)

# In-memory dictionary to store peer connections
peers = {}

# Video track class that uses OpenCV for frame processing
class VideoTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(0)

    async def recv(self):
        success, frame = self.cap.read()
        if not success:
            raise RuntimeError("Failed to read from camera")
        
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Convert frame to the required format
        frame = np.frombuffer(frame, dtype=np.uint8)
        frame = frame.reshape((480, 640, 3))

        return frame

    def __del__(self):
        self.cap.release()

@app.route('/')
def index():
    return render_template('index.html')

@sock.route('/offer')
async def offer(ws):
    data = await ws.receive()
    offer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])

    pc = RTCPeerConnection()
    peers[ws] = pc

    @pc.on("icecandidate")
    def on_icecandidate(candidate):
        ws.send({
            "candidate": candidate,
        })

    @pc.on("datachannel")
    def on_datachannel(channel):
        channel.send("Hello from server!")

    pc.addTrack(VideoTrack())
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    await ws.send({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
