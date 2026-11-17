"""Reference packet codec only. No MQTT connection and no model training."""
import struct
import uuid
import zlib
import numpy as np

HEADER = struct.Struct('<4sBBH16s16sIII')
SAMPLE_COUNT = 2048
SAMPLE_RATE = 12000
PACKET_BYTES = HEADER.size + SAMPLE_COUNT*4 + 4

def encode_window(samples, run_id, window_id, sequence):
    x=np.asarray(samples,dtype='<f4')
    if x.shape != (SAMPLE_COUNT,) or not np.isfinite(x).all():
        raise ValueError('Expected exactly 2048 finite raw float32 samples')
    if not 0 <= sequence <= 0xffffffff:
        raise ValueError('Sequence outside uint32 range')
    header=HEADER.pack(b'M462',1,0,0,uuid.UUID(run_id).bytes,uuid.UUID(window_id).bytes,
                       sequence,SAMPLE_RATE,SAMPLE_COUNT)
    body=header+x.tobytes(order='C')
    return body+struct.pack('<I',zlib.crc32(body)&0xffffffff)

def decode_window(packet):
    if len(packet) != PACKET_BYTES:
        raise ValueError('Wrong complete packet length')
    stored,=struct.unpack_from('<I',packet,len(packet)-4)
    if (zlib.crc32(packet[:-4])&0xffffffff) != stored:
        raise ValueError('CRC32 failed')
    magic,version,flags,reserved,run,wid,seq,fs,count=HEADER.unpack_from(packet)
    if (magic,version,flags,reserved,fs,count)!=(b'M462',1,0,0,SAMPLE_RATE,SAMPLE_COUNT):
        raise ValueError('Unsupported or invalid header')
    x=np.frombuffer(packet,dtype='<f4',count=SAMPLE_COUNT,offset=HEADER.size).copy()
    if not np.isfinite(x).all():
        raise ValueError('Non-finite raw samples')
    return dict(run_id=uuid.UUID(bytes=run).hex,window_id=uuid.UUID(bytes=wid).hex,
                sequence=seq,fs=fs,samples=x)
