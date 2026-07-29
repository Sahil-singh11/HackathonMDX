/* Note field with voice input (Lane B).
 *
 * Speech-to-text needs a network connection in every browser that ships it, so
 * offline it is simply absent. Rather than hiding the button and failing
 * silently, we fall back to recording an audio memo and attaching it to the
 * catch — the fisher still captures what they wanted to say.
 *
 * Props:
 *   note        string
 *   onNote      (v: string) => void
 *   audioBlob   Blob | null                 recorded memo, if any
 *   onAudio     (b: Blob | null) => void
 *   announce    (msg: string) => void
 */
import { Mic, Square, Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useT } from '../../i18n'
import { useAppStore } from '../../store/app'

interface SpeechRecognitionResultLike { transcript: string }
interface SpeechRecognitionEventLike { results: ArrayLike<ArrayLike<SpeechRecognitionResultLike>> }
interface SpeechRecognitionLike {
  continuous: boolean
  interimResults: boolean
  lang: string
  onresult: ((ev: SpeechRecognitionEventLike) => void) | null
  onend: (() => void) | null
  onerror: (() => void) | null
  start(): void
  stop(): void
}
type SpeechRecognitionCtor = new () => SpeechRecognitionLike

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === 'undefined') return null
  const w = window as unknown as {
    webkitSpeechRecognition?: SpeechRecognitionCtor
    SpeechRecognition?: SpeechRecognitionCtor
  }
  return w.webkitSpeechRecognition ?? w.SpeechRecognition ?? null
}

interface Props {
  note: string
  onNote: (v: string) => void
  audioBlob: Blob | null
  onAudio: (b: Blob | null) => void
  announce: (msg: string) => void
}

export default function NoteField({ note, onNote, audioBlob, onAudio, announce }: Props) {
  const t = useT()
  const { language, online } = useAppStore()
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const [listening, setListening] = useState(false)
  const [recording, setRecording] = useState(false)

  const speechCtor = getSpeechRecognitionCtor()
  // Speech recognition is a cloud service in practice — offline it will fail.
  const canDictate = speechCtor != null && online
  const canRecord = typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [note])

  useEffect(() => () => {
    recognitionRef.current?.stop()
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
  }, [])

  const toggleDictate = () => {
    if (listening) { recognitionRef.current?.stop(); return }
    if (!speechCtor) return
    const recognition = new speechCtor()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = language === 'mfe' ? 'fr-FR' : 'en-US'
    recognition.onresult = (ev) => {
      const transcript = ev.results[ev.results.length - 1][0].transcript
      onNote(note ? `${note} ${transcript}` : transcript)
      announce(t('catch.voiceCaptured'))
    }
    recognition.onerror = () => { setListening(false); announce(t('catch.voiceFailed')) }
    recognition.onend = () => setListening(false)
    recognitionRef.current = recognition
    recognition.start()
    setListening(true)
  }

  const toggleRecord = async () => {
    if (recording) {
      recorderRef.current?.stop()
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop())
        onAudio(new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' }))
        setRecording(false)
        announce(t('catch.audioAttached'))
      }
      recorderRef.current = recorder
      recorder.start()
      setRecording(true)
    } catch {
      announce(t('catch.micDenied'))
    }
  }

  return (
    <div className="note-field">
      <label className="field" htmlFor="catch-note">{t('catch.note')}</label>
      <div className="note-wrap">
        <textarea id="catch-note" ref={textareaRef} rows={2} value={note}
          placeholder={t('catch.notePlaceholder')}
          aria-describedby="catch-note-hint"
          onChange={(e) => onNote(e.target.value)} />
        {canDictate ? (
          <button type="button" className={`mic-btn${listening ? ' recording' : ''}`}
            aria-pressed={listening} aria-label={t('catch.voiceInput')} onClick={toggleDictate}>
            <Mic size={18} aria-hidden="true" />
          </button>
        ) : canRecord ? (
          <button type="button" className={`mic-btn${recording ? ' recording' : ''}`}
            aria-pressed={recording} aria-label={t('catch.recordAudio')} onClick={toggleRecord}>
            {recording ? <Square size={18} aria-hidden="true" /> : <Mic size={18} aria-hidden="true" />}
          </button>
        ) : null}
      </div>

      <p id="catch-note-hint" className="small note-hint">
        {canDictate ? t('catch.voiceHint') : canRecord ? t('catch.audioHint') : t('catch.noVoiceHint')}
      </p>

      {recording && <p className="banner warn" role="status">{t('catch.recordingNow')}</p>}

      {audioBlob && !recording && (
        <div className="audio-attached">
          <audio controls src={URL.createObjectURL(audioBlob)} />
          <button type="button" className="secondary" onClick={() => onAudio(null)}>
            <Trash2 size={16} aria-hidden="true" /> {t('catch.removeAudio')}
          </button>
        </div>
      )}
    </div>
  )
}
