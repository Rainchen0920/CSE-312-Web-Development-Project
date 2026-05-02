import base64
import hashlib

class Frame:
    def __init__(self):
        self.fin_bit = 0
        self.opcode = 0
        self.payload_length = 0
        self.payload = b""

def compute_accept(socket_key):
    websocket_guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    combined = (socket_key + websocket_guid).encode()
    sha1_result = hashlib.sha1(combined).digest()
    accept = base64.b64encode(sha1_result).decode()
    return accept

def parse_ws_frame(frame_bytes):
    frame = Frame()

    frame.fin_bit = (frame_bytes[0] >> 7) & 1
    frame.opcode = frame_bytes[0] & 0b00001111
    mask_bool = (frame_bytes[1] >> 7) & 1
    payload_len_indicator = frame_bytes[1] & 0b01111111
    index = 2

    if payload_len_indicator < 126:
        payload_length = payload_len_indicator
    elif payload_len_indicator == 126:
        payload_length = int.from_bytes(frame_bytes[index:index + 2], "big")
        index += 2
    else:
        payload_length = int.from_bytes(frame_bytes[index:index + 8], "big")
        index += 8

    frame.payload_length = payload_length

    if mask_bool:
        masking_key = frame_bytes[index:index + 4]
        index += 4
    else:
        masking_key = b""

    payload = frame_bytes[index:index + payload_length]

    if mask_bool:
        unmasked_payload = bytearray()
        for i in range(payload_length):
            unmasked_payload.append(payload[i] ^ masking_key[i % 4])
        frame.payload = bytes(unmasked_payload)
    else:
        frame.payload = payload

    return frame


def parse_ws_frame_buffered(frame_bytes):
    if len(frame_bytes) < 2:
        return None, 0

    frame = Frame()
    frame.fin_bit = (frame_bytes[0] >> 7) & 1
    frame.opcode = frame_bytes[0] & 0b00001111

    mask_bool = (frame_bytes[1] >> 7) & 1
    payload_len_indicator = frame_bytes[1] & 0b01111111
    index = 2

    if payload_len_indicator < 126:
        payload_length = payload_len_indicator
    elif payload_len_indicator == 126:
        if len(frame_bytes) < index + 2:
            return None, 0
        payload_length = int.from_bytes(frame_bytes[index:index + 2], "big")
        index += 2
    else:
        if len(frame_bytes) < index + 8:
            return None, 0
        payload_length = int.from_bytes(frame_bytes[index:index + 8], "big")
        index += 8
    
    if mask_bool:
        if len(frame_bytes) < index + 4:
            return None, 0
        index += 4

    if len(frame_bytes) < index + payload_length:
        return None, 0

    total_bytes_used = index + payload_length
    frame = parse_ws_frame(frame_bytes[:total_bytes_used])
    return frame, total_bytes_used

def generate_ws_frame(payload):
    frame = b""

    first_byte = 0b10000001
    frame += bytes([first_byte])

    payload_length = len(payload)

    if payload_length < 126:
        frame += bytes([payload_length])
    elif payload_length <= 65535:
        frame += bytes([126])
        frame += payload_length.to_bytes(2, "big")
    else:
        frame += bytes([127])
        frame += payload_length.to_bytes(8, "big")

    frame += payload
    return frame

