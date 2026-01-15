import { useState, useRef, useCallback, useEffect } from 'react'
import './Dashboard.css'

const API_BASE = 'http://localhost:8000'
const WS_BASE = 'ws://localhost:8000'

function Dashboard() {
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [status, setStatus] = useState('')
  const [transcription, setTranscription] = useState('')
  const [answer, setAnswer] = useState('')
  const [chunks, setChunks] = useState([])
  const [error, setError] = useState(null)
  const [resultType, setResultType] = useState(null) // 'rag', 'vision', or 'chat'
  const [screenSharing, setScreenSharing] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)

  // Text-to-speech function
  const speakText = useCallback((text) => {
    if (!text || !window.speechSynthesis) return

    // Cancel any ongoing speech
    window.speechSynthesis.cancel()

    // Clean up text (remove markdown formatting)
    const cleanText = text
      .replace(/\*\*/g, '')
      .replace(/\*/g, '')
      .replace(/#{1,3}\s/g, '')
      .replace(/- /g, '')
      .trim()

    const utterance = new SpeechSynthesisUtterance(cleanText)
    utterance.rate = 1.0
    utterance.pitch = 1.0
    utterance.volume = 1.0

    // Try to get a good English voice
    const voices = window.speechSynthesis.getVoices()
    const englishVoice = voices.find(v => v.lang.startsWith('en') && v.name.includes('Google')) ||
                         voices.find(v => v.lang.startsWith('en-US')) ||
                         voices.find(v => v.lang.startsWith('en'))
    if (englishVoice) {
      utterance.voice = englishVoice
    }

    utterance.onstart = () => setIsSpeaking(true)
    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)

    window.speechSynthesis.speak(utterance)
  }, [])

  // Stop speaking
  const stopSpeaking = useCallback(() => {
    window.speechSynthesis.cancel()
    setIsSpeaking(false)
  }, [])

  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const wsRef = useRef(null)
  const pendingQuestionRef = useRef('')
  const screenStreamRef = useRef(null)
  const screenVideoRef = useRef(null)
  const screenShareRequestedRef = useRef(false)

  // Request screen sharing on component mount
  useEffect(() => {
    // Prevent double request from StrictMode
    if (screenShareRequestedRef.current) return
    screenShareRequestedRef.current = true

    const requestScreenShare = async () => {
      try {
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: { mediaSource: 'screen' }
        })
        screenStreamRef.current = stream

        // Create persistent video element
        const video = document.createElement('video')
        video.srcObject = stream
        video.play()
        screenVideoRef.current = video

        setScreenSharing(true)

        // Handle stream ending (user stops sharing)
        stream.getVideoTracks()[0].onended = () => {
          setScreenSharing(false)
          screenStreamRef.current = null
          screenVideoRef.current = null
          screenShareRequestedRef.current = false // Allow re-request if needed
        }
      } catch (err) {
        console.log('Screen sharing declined or failed:', err.message)
        setScreenSharing(false)
        screenShareRequestedRef.current = false // Allow retry on error
      }
    }

    requestScreenShare()

    // Cleanup on unmount
    return () => {
      if (screenStreamRef.current) {
        screenStreamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  // Capture screenshot and send to backend (uses pre-shared screen)
  const captureScreenshot = useCallback(async (question) => {
    try {
      if (!screenVideoRef.current || !screenSharing) {
        setError('Screen sharing not active. Please refresh and allow screen sharing.')
        setIsProcessing(false)
        return
      }

      setStatus('Capturing screenshot...')

      const video = screenVideoRef.current

      // Capture frame to canvas
      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      const ctx = canvas.getContext('2d')
      ctx.drawImage(video, 0, 0)

      // Convert to base64
      const imageBase64 = canvas.toDataURL('image/jpeg', 0.8)

      // Send to backend
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        setStatus('Analyzing screenshot...')
        wsRef.current.send(JSON.stringify({
          type: 'screenshot',
          image: imageBase64,
          question: question
        }))
      }
    } catch (err) {
      setError(`Screen capture failed: ${err.message}`)
      setIsProcessing(false)
    }
  }, [screenSharing])

  const audioStreamRef = useRef(null)
  const shouldRestartRef = useRef(false)
  const audioContextRef = useRef(null)
  const analyserRef = useRef(null)
  const silenceTimeoutRef = useRef(null)
  const hasSpokenRef = useRef(false)
  const audioCheckIntervalRef = useRef(null)

  // Start continuous listening session
  const startListening = useCallback(async () => {
    if (isRecording) return

    try {
      setError(null)
      shouldRestartRef.current = true

      // Connect WebSocket if not connected
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        wsRef.current = new WebSocket(`${WS_BASE}/ws/voice`)

        wsRef.current.onopen = () => {
          setStatus('Listening...')
        }

        wsRef.current.onmessage = (event) => {
          const data = JSON.parse(event.data)

          switch (data.type) {
            case 'status':
              setStatus(data.data.message)
              break
            case 'transcription':
              setTranscription(data.data.text)
              setStatus('Processing...')
              break
            case 'request_screenshot':
              pendingQuestionRef.current = data.data.question
              captureScreenshot(data.data.question)
              break
            case 'rag_result':
              setResultType('rag')
              setChunks(data.data.retrieved_chunks || [])
              const ragAnswer = data.data.answer || data.data.context || ''
              setAnswer(ragAnswer)
              setIsProcessing(false)
              speakText(ragAnswer)
              if (shouldRestartRef.current) {
                const checkSpeechDone = setInterval(() => {
                  if (!window.speechSynthesis.speaking) {
                    clearInterval(checkSpeechDone)
                    setTimeout(() => startNewRecording(), 300)
                  }
                }, 100)
              }
              break
            case 'vision_result':
              setResultType('vision')
              setChunks([])
              const visionAnswer = data.data.answer || ''
              setAnswer(visionAnswer)
              setIsProcessing(false)
              speakText(visionAnswer)
              if (shouldRestartRef.current) {
                const checkSpeechDone = setInterval(() => {
                  if (!window.speechSynthesis.speaking) {
                    clearInterval(checkSpeechDone)
                    setTimeout(() => startNewRecording(), 300)
                  }
                }, 100)
              }
              break
            case 'chat_result':
              setResultType('chat')
              setChunks([])
              const chatAnswer = data.data.answer || ''
              setAnswer(chatAnswer)
              setIsProcessing(false)
              speakText(chatAnswer)
              if (shouldRestartRef.current) {
                const checkSpeechDone = setInterval(() => {
                  if (!window.speechSynthesis.speaking) {
                    clearInterval(checkSpeechDone)
                    setTimeout(() => startNewRecording(), 300)
                  }
                }, 100)
              }
              break
            case 'error':
              setError(data.data.message)
              setIsProcessing(false)
              setStatus('Ready')
              break
          }
        }

        wsRef.current.onerror = () => {
          setError('WebSocket connection failed')
          setIsProcessing(false)
          setIsRecording(false)
        }

        wsRef.current.onclose = () => {
          setStatus('')
          setIsRecording(false)
        }
      }

      // Get audio stream once
      if (!audioStreamRef.current) {
        audioStreamRef.current = await navigator.mediaDevices.getUserMedia({ audio: true })
      }

      startNewRecording()
    } catch (err) {
      setError(`Microphone access denied: ${err.message}`)
    }
  }, [isRecording, captureScreenshot])

  // Silence detection settings
  const SILENCE_THRESHOLD = 15 // Audio level below this = silence (0-255)
  const SILENCE_DURATION = 1500 // ms of silence before sending
  const MAX_RECORDING_TIME = 30000 // Max 30 seconds

  // Start a new recording segment with silence detection
  const startNewRecording = useCallback(() => {
    if (!audioStreamRef.current || !shouldRestartRef.current) return

    setStatus('Listening...')
    audioChunksRef.current = []
    hasSpokenRef.current = false

    // Set up audio analysis for silence detection
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext()
    }

    const analyser = audioContextRef.current.createAnalyser()
    analyser.fftSize = 512
    analyser.smoothingTimeConstant = 0.5
    analyserRef.current = analyser

    const source = audioContextRef.current.createMediaStreamSource(audioStreamRef.current)
    source.connect(analyser)

    mediaRecorderRef.current = new MediaRecorder(audioStreamRef.current, { mimeType: 'audio/webm' })

    mediaRecorderRef.current.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunksRef.current.push(event.data)
      }
    }

    mediaRecorderRef.current.onstop = async () => {
      // Clear silence detection
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current)
        silenceTimeoutRef.current = null
      }

      if (audioChunksRef.current.length === 0 || !hasSpokenRef.current) {
        // No speech detected, restart listening
        if (shouldRestartRef.current) {
          setTimeout(() => startNewRecording(), 100)
        }
        return
      }

      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })

      try {
        const arrayBuffer = await audioBlob.arrayBuffer()
        const decodeContext = new AudioContext({ sampleRate: 16000 })
        const audioBuffer = await decodeContext.decodeAudioData(arrayBuffer)
        const wavBuffer = audioBufferToWav(audioBuffer)
        const wavBlob = new Blob([wavBuffer], { type: 'audio/wav' })

        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(wavBlob)
          wsRef.current.send(JSON.stringify({ type: 'end' }))
          setIsProcessing(true)
          setStatus('Processing...')
        }

        await decodeContext.close()
      } catch (err) {
        console.error('Audio processing error:', err)
        if (shouldRestartRef.current) {
          setTimeout(() => startNewRecording(), 500)
        }
      }
    }

    mediaRecorderRef.current.start(100) // Collect data every 100ms
    setIsRecording(true)

    // Monitor audio levels for silence detection using setInterval (works in background tabs)
    const dataArray = new Uint8Array(analyser.frequencyBinCount)

    const checkAudioLevel = () => {
      if (!mediaRecorderRef.current || mediaRecorderRef.current.state !== 'recording') {
        if (audioCheckIntervalRef.current) {
          clearInterval(audioCheckIntervalRef.current)
          audioCheckIntervalRef.current = null
        }
        return
      }

      analyser.getByteFrequencyData(dataArray)
      const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length

      if (average > SILENCE_THRESHOLD) {
        // User is speaking
        hasSpokenRef.current = true
        setStatus('Listening... (speaking)')

        // Clear any pending silence timeout
        if (silenceTimeoutRef.current) {
          clearTimeout(silenceTimeoutRef.current)
          silenceTimeoutRef.current = null
        }
      } else if (hasSpokenRef.current && !silenceTimeoutRef.current) {
        // Silence detected after speech - start countdown
        setStatus('Listening... (silence detected)')
        silenceTimeoutRef.current = setTimeout(() => {
          if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
            mediaRecorderRef.current.stop()
          }
        }, SILENCE_DURATION)
      }
    }

    // Use setInterval instead of requestAnimationFrame - works in background tabs
    audioCheckIntervalRef.current = setInterval(checkAudioLevel, 100)

    // Max recording time safety
    setTimeout(() => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop()
      }
    }, MAX_RECORDING_TIME)
  }, [])

  // Stop listening session entirely
  const stopListening = useCallback(() => {
    shouldRestartRef.current = false
    setIsRecording(false)
    setStatus('')

    // Clear audio check interval
    if (audioCheckIntervalRef.current) {
      clearInterval(audioCheckIntervalRef.current)
      audioCheckIntervalRef.current = null
    }

    // Clear silence detection timeout
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current)
      silenceTimeoutRef.current = null
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
    }

    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach(track => track.stop())
      audioStreamRef.current = null
    }

    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  // Toggle listening on click
  const toggleListening = useCallback(() => {
    if (isRecording || isProcessing) {
      stopListening()
    } else {
      startListening()
    }
  }, [isRecording, isProcessing, startListening, stopListening])

  // Manual send - click while recording to send current audio
  const sendCurrentAudio = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }, [])

  // Convert AudioBuffer to WAV
  function audioBufferToWav(buffer) {
    const numChannels = 1
    const sampleRate = buffer.sampleRate
    const format = 1 // PCM
    const bitDepth = 16

    const data = buffer.getChannelData(0)
    const dataLength = data.length * (bitDepth / 8)
    const bufferLength = 44 + dataLength

    const arrayBuffer = new ArrayBuffer(bufferLength)
    const view = new DataView(arrayBuffer)

    // WAV header
    writeString(view, 0, 'RIFF')
    view.setUint32(4, 36 + dataLength, true)
    writeString(view, 8, 'WAVE')
    writeString(view, 12, 'fmt ')
    view.setUint32(16, 16, true)
    view.setUint16(20, format, true)
    view.setUint16(22, numChannels, true)
    view.setUint32(24, sampleRate, true)
    view.setUint32(28, sampleRate * numChannels * (bitDepth / 8), true)
    view.setUint16(32, numChannels * (bitDepth / 8), true)
    view.setUint16(34, bitDepth, true)
    writeString(view, 36, 'data')
    view.setUint32(40, dataLength, true)

    // Write audio data
    let offset = 44
    for (let i = 0; i < data.length; i++) {
      const sample = Math.max(-1, Math.min(1, data[i]))
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true)
      offset += 2
    }

    return arrayBuffer
  }

  function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i))
    }
  }

  // Simple markdown-like formatter
  function formatAnswer(text) {
    if (!text) return null

    const lines = text.split('\n')
    const elements = []
    let listItems = []
    let listKey = 0

    const flushList = () => {
      if (listItems.length > 0) {
        elements.push(<ul key={`list-${listKey++}`}>{listItems}</ul>)
        listItems = []
      }
    }

    lines.forEach((line, i) => {
      const trimmed = line.trim()

      // Bullet points (* or -)
      if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
        const content = trimmed.slice(2)
        // Handle bold **text**
        const formatted = content.split(/(\*\*[^*]+\*\*)/).map((part, j) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return <strong key={j}>{part.slice(2, -2)}</strong>
          }
          return part
        })
        listItems.push(<li key={i}>{formatted}</li>)
      }
      // Headers
      else if (trimmed.startsWith('### ')) {
        flushList()
        elements.push(<h4 key={i}>{trimmed.slice(4)}</h4>)
      }
      else if (trimmed.startsWith('## ')) {
        flushList()
        elements.push(<h3 key={i}>{trimmed.slice(3)}</h3>)
      }
      else if (trimmed.startsWith('# ')) {
        flushList()
        elements.push(<h2 key={i}>{trimmed.slice(2)}</h2>)
      }
      // Empty line
      else if (trimmed === '') {
        flushList()
      }
      // Regular paragraph
      else {
        flushList()
        // Handle bold **text**
        const formatted = trimmed.split(/(\*\*[^*]+\*\*)/).map((part, j) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return <strong key={j}>{part.slice(2, -2)}</strong>
          }
          return part
        })
        elements.push(<p key={i}>{formatted}</p>)
      }
    })

    flushList()
    return elements
  }

  return (
    <div className="dashboard-page">
      <div className="page-header">
        <h1>Voice Query Dashboard</h1>
        <p>Ask about documents or say "look at my screen" for visual analysis</p>
        <div className={`screen-status ${screenSharing ? 'active' : 'inactive'}`}>
          <span className="status-dot"></span>
          {screenSharing ? 'Screen sharing active' : 'Screen sharing inactive'}
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={() => setError(null)}>&times;</button>
        </div>
      )}

      <div className="voice-section">
        <button
          className={`voice-button ${isRecording ? 'recording' : ''} ${isProcessing ? 'processing' : ''}`}
          onClick={toggleListening}
        >
          <div className="voice-icon">
            {isProcessing ? (
              <svg className="animate-spin" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" strokeDasharray="32" strokeDashoffset="12" />
              </svg>
            ) : isRecording ? (
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
              </svg>
            ) : (
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
              </svg>
            )}
          </div>
          <span className="voice-text">
            {isProcessing ? 'Processing...' : isRecording ? 'Click to stop' : 'Click to start'}
          </span>
        </button>

        {isRecording && !isProcessing && (
          <button className="send-button" onClick={sendCurrentAudio}>
            Send now
          </button>
        )}

        {status && <div className="status-text">{status}</div>}

        {isSpeaking && (
          <button className="stop-speaking-btn" onClick={stopSpeaking}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
            </svg>
            Stop Speaking
          </button>
        )}
      </div>

      {transcription && (
        <div className="result-section">
          <div className="transcription-card card">
            <h3>Your Question</h3>
            <p>{transcription}</p>
          </div>
        </div>
      )}

      {answer && (
        <div className="answer-section">
          <div className={`answer-card card ${resultType === 'vision' ? 'vision-answer' : ''} ${resultType === 'chat' ? 'chat-answer' : ''}`}>
            <h3>
              {resultType === 'vision' ? (
                <>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                  Screen Analysis
                </>
              ) : resultType === 'chat' ? (
                <>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{marginRight: '8px', verticalAlign: 'middle'}}>
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                  Response
                </>
              ) : 'Answer'}
            </h3>
            <div className="answer-text">{formatAnswer(answer)}</div>
          </div>
        </div>
      )}

      {chunks.length > 0 && (
        <div className="sources-section">
          <h3>Source Documents</h3>
          <div className="sources-grid">
            {chunks.map((chunk, i) => (
              <div key={i} className="source-card card">
                <div className="source-header">
                  <span className="source-file">{chunk.filename}</span>
                  <span className="source-score">
                    {(1 / (1 + chunk.distance) * 100).toFixed(0)}% match
                  </span>
                </div>
                <p className="source-text">{chunk.text}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard
