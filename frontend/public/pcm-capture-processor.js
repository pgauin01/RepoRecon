/**
 * AudioWorklet processor that runs in a dedicated audio rendering thread.
 * It receives raw Float32 samples from the microphone, converts them to
 * Int16 (16-bit PCM), and posts the buffer back to the main thread.
 *
 * This avoids the heavy overhead of ScriptProcessorNode (now deprecated)
 * and produces raw PCM data the Gemini Live API expects — no WebM/Opus needed.
 */

class PCMCaptureProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        // Buffer raw samples until we have a chunk (~20ms at 16 kHz = 320 samples)
        this._buffer = new Float32Array(0);
        this._chunkSize = 320; // samples per chunk (16 kHz × 0.02 s)
    }

    process(inputs) {
        const input = inputs[0];
        if (!input || !input[0]) return true;

        const channelData = input[0]; // mono
        const combined = new Float32Array(this._buffer.length + channelData.length);
        combined.set(this._buffer);
        combined.set(channelData, this._buffer.length);
        this._buffer = combined;

        while (this._buffer.length >= this._chunkSize) {
            const chunk = this._buffer.slice(0, this._chunkSize);
            this._buffer = this._buffer.slice(this._chunkSize);

            // Convert Float32 [-1, 1] → Int16 [-32768, 32767]
            const pcm16 = new Int16Array(chunk.length);
            for (let i = 0; i < chunk.length; i++) {
                const s = Math.max(-1, Math.min(1, chunk[i]));
                pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
            }

            // Transfer the ArrayBuffer zero-copy to the main thread
            this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
        }

        return true; // keep processor alive
    }
}

registerProcessor('pcm-capture-processor', PCMCaptureProcessor);
