import { useRef, useState, useCallback } from 'react';

const WS_URL = 'ws://localhost:8000/ws';
const SAMPLE_RATE = 24000; // Hz — matches what Gemini Live API expects

export type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'error';

export interface UseLiveVoiceReturn {
    status: ConnectionStatus;
    isRecording: boolean;
    startRecording: () => Promise<void>;
    stopRecording: () => void;
}

export function useLiveVoice(): UseLiveVoiceReturn {
    const [status, setStatus] = useState<ConnectionStatus>('idle');
    const [isRecording, setIsRecording] = useState(false);

    // Refs for resources that shouldn't cause re-renders
    const wsRef = useRef<WebSocket | null>(null);
    const audioCtxRef = useRef<AudioContext | null>(null);
    const workletNodeRef = useRef<AudioWorkletNode | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const playbackQueueRef = useRef<ArrayBuffer[]>([]);
    const nextStartTimeRef = useRef(0);
    const isPlayingRef = useRef(false);

    /**
     * Dequeues and schedules PCM chunks proactively.
     * Uses a jitter buffer to smooth out network fluctuations.
     */
    const drainPlaybackQueue = useCallback(() => {
        const ctx = audioCtxRef.current;
        if (!ctx || playbackQueueRef.current.length === 0) return;

        // Start scheduling chunks
        while (playbackQueueRef.current.length > 0) {
            const raw = playbackQueueRef.current.shift()!;
            const int16 = new Int16Array(raw);
            const float32 = new Float32Array(int16.length);

            // Robust conversion: Int16 [-32768, 32767] -> Float32 [-1.0, 1.0]
            for (let i = 0; i < int16.length; i++) {
                float32[i] = int16[i] / 32768.0;
            }

            const buffer = ctx.createBuffer(1, float32.length, SAMPLE_RATE);
            buffer.copyToChannel(float32, 0);

            const source = ctx.createBufferSource();
            source.buffer = buffer;
            source.connect(ctx.destination);

            // If we've drifted significantly or just starting, sync to currentTime + jitter buffer
            if (nextStartTimeRef.current < ctx.currentTime) {
                // Initial jitter buffer of 150ms to absorb network variance
                nextStartTimeRef.current = ctx.currentTime + 0.15;
            }

            source.start(nextStartTimeRef.current);
            nextStartTimeRef.current += buffer.duration;
        }
    }, []);

    // ─── WebSocket ───────────────────────────────────────────────────────────
    const connectWebSocket = useCallback((): Promise<void> => {
        return new Promise((resolve, reject) => {
            setStatus('connecting');
            const ws = new WebSocket(WS_URL);
            ws.binaryType = 'arraybuffer';
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('[WS] Connected');
                setStatus('connected');
                resolve();
            };

            ws.onmessage = (event: MessageEvent<ArrayBuffer>) => {
                // Queue the incoming PCM chunk for playback
                playbackQueueRef.current.push(event.data);
                drainPlaybackQueue();
            };

            ws.onerror = (err) => {
                console.error('[WS] Error', err);
                setStatus('error');
                reject(err);
            };

            ws.onclose = () => {
                console.log('[WS] Closed');
                if (status !== 'error') setStatus('idle');
            };
        });
    }, [drainPlaybackQueue, status]);

    // ─── Start Recording ─────────────────────────────────────────────────────
    const startRecording = useCallback(async () => {
        if (isRecording) return;

        try {
            // 1. Connect WebSocket (if not already open)
            if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
                await connectWebSocket();
            }

            // 2. Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: SAMPLE_RATE,
                    echoCancellation: true,
                    noiseSuppression: true,
                },
            });
            streamRef.current = stream;

            // 3. Create AudioContext at the target sample rate
            const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
            audioCtxRef.current = ctx;

            // 4. Load AudioWorklet processor (served from /public)
            await ctx.audioWorklet.addModule('/pcm-capture-processor.js');

            // 5. Wire up: source → worklet node
            const source = ctx.createMediaStreamSource(stream);
            const workletNode = new AudioWorkletNode(ctx, 'pcm-capture-processor');
            workletNodeRef.current = workletNode;

            // 6. Forward PCM chunks from the worklet to the WebSocket
            workletNode.port.onmessage = (e: MessageEvent<ArrayBuffer>) => {
                const ws = wsRef.current;
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(e.data);
                }
            };

            source.connect(workletNode);
            // Do NOT connect workletNode to ctx.destination — we don't want local echo
            // (the echo comes back from the server)

            setIsRecording(true);
        } catch (err) {
            console.error('[useLiveVoice] startRecording error:', err);
            setStatus('error');
        }
    }, [isRecording, connectWebSocket]);

    // ─── Stop Recording ──────────────────────────────────────────────────────
    const stopRecording = useCallback(() => {
        if (!isRecording) return;

        // Disconnect and close worklet
        workletNodeRef.current?.disconnect();
        workletNodeRef.current = null;

        // Stop all mic tracks
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;

        // Close AudioContext
        audioCtxRef.current?.close();
        audioCtxRef.current = null;

        // Close WebSocket
        wsRef.current?.close();
        wsRef.current = null;

        playbackQueueRef.current = [];
        isPlayingRef.current = false;

        setIsRecording(false);
        setStatus('idle');
    }, [isRecording]);

    return { status, isRecording, startRecording, stopRecording };
}
