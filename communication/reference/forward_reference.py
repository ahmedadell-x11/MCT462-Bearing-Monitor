"""Independent FP32 Dense/ReLU/Softmax reference inference. No training.
Limited to the current exported graph; not an ESP32/LiteRT runtime test.
"""
import struct
import numpy as np

def load_reference_model(model_content):
    model_bytes = bytes(model_content)
    class FlatBuffer:
        def u32(self, p): return struct.unpack_from('<I', model_bytes, p)[0]
        def i32(self, p): return struct.unpack_from('<i', model_bytes, p)[0]
        def u16(self, p): return struct.unpack_from('<H', model_bytes, p)[0]
        def field(self, table, number):
            v = table - self.i32(table)
            slot = 4 + 2 * number
            offset = self.u16(v + slot) if slot < self.u16(v) else 0
            return table + offset if offset else 0
        def scalar(self, table, number, fmt, default=0):
            p = self.field(table, number)
            return struct.unpack_from(fmt, model_bytes, p)[0] if p else default
        def ref(self, table, number):
            p = self.field(table, number)
            return p + self.u32(p) if p else 0
        def table_vector(self, table, number):
            p = self.ref(table, number)
            return [p+4+4*i+self.u32(p+4+4*i) for i in range(self.u32(p))] if p else []
        def ints(self, table, number):
            p = self.ref(table, number)
            return list(struct.unpack_from('<'+'i'*self.u32(p), model_bytes, p+4)) if p else []
        def data(self, table):
            p = self.ref(table, 0)
            return model_bytes[p+4:p+4+self.u32(p)] if p else b''

    fb = FlatBuffer()
    assert model_bytes[4:8] == b'TFL3'
    root = fb.u32(0)
    subgraphs = fb.table_vector(root, 2)
    assert len(subgraphs) == 1
    graph = subgraphs[0]
    tensors = fb.table_vector(graph, 0)
    buffers = fb.table_vector(root, 4)
    codes = fb.table_vector(root, 1)
    constants = {}
    for i, tensor in enumerate(tensors):
        b = buffers[fb.scalar(tensor, 2, '<I')]
        content = fb.data(b)
        if content:
            assert fb.scalar(tensor, 1, '<b') == 0, 'Expected FP32 constant'
            constants[i] = np.frombuffer(content, dtype='<f4').reshape(fb.ints(tensor, 0))
    operations = []
    for op in fb.table_vector(graph, 3):
        code_table = codes[fb.scalar(op, 0, '<I')]
        opcode = max(fb.scalar(code_table, 0, '<b'), fb.scalar(code_table, 3, '<i'))
        inputs, outputs = fb.ints(op, 1), fb.ints(op, 2)
        options = fb.ref(op, 4)
        assert opcode in (9, 25), f'Unsupported audit operation {opcode}'
        activation = fb.scalar(options, 0, '<b') if opcode == 9 else 0
        beta = fb.scalar(options, 0, '<f') if opcode == 25 else 0
        assert activation in (0, 1)
        operations.append((opcode, inputs, outputs, activation, beta))
    assert [op[0] for op in operations] == [9, 9, 9, 25]
    input_id, = fb.ints(graph, 1)
    output_id, = fb.ints(graph, 2)
    def inference(features):
        values = dict(constants)
        values[input_id] = features.astype(np.float32)
        for opcode, inputs, outputs, activation, beta in operations:
            if opcode == 9:
                x, weights, bias = [values[t] for t in inputs]
                y = (x @ weights.T + bias).astype(np.float32)
                if activation == 1:
                    y = np.maximum(y, 0)
            else:
                x = values[inputs[0]] * beta
                e = np.exp(x - x.max(axis=1, keepdims=True))
                y = e / e.sum(axis=1, keepdims=True)
            values[outputs[0]] = y
        return values[output_id]
    return inference
