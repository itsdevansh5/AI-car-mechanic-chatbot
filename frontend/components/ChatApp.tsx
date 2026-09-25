"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { API_URL, postJSON } from "../lib/api";

type Message = { role: "user" | "assistant"; content: string; created_at?: string };
type Diagnosis = { id:number; summary:string; likely_causes:string[]; confidence:number; checks:string[]; recommended_service:string; urgency:"low"|"medium"|"high"; safety_notes:string[] };

type Session = { session_id:string; reply:string; ready_for_diagnosis:boolean; history:Message[] };

export default function ChatApp() {
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [mediaIds, setMediaIds] = useState<number[]>([]);
  const [mediaNames, setMediaNames] = useState<string[]>([]);
  const [ready, setReady] = useState(false);
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [error, setError] = useState("");
  const [bookingOpen, setBookingOpen] = useState(false);
  const [bookingResult, setBookingResult] = useState<any>(null);
  const [booking, setBooking] = useState({ customer_name:"", phone:"", preferred_date:"", preferred_time:"", service_type:"" });
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:"smooth" }); }, [messages, diagnosis]);
  useEffect(() => {
    const id = localStorage.getItem("mechanic_session_id");
    if (id) setSessionId(id);
  }, []);

  const diagnosisButtonText = useMemo(() => diagnosis ? "Diagnosis ready" : "Get diagnosis", [diagnosis]);

  async function sendMessage(e?: React.FormEvent) {
    e?.preventDefault();
    if (!text.trim() || busy) return;
    setError(""); setBusy(true);
    const outgoing = text.trim(); setText("");
    setMessages(prev => [...prev, { role:"user", content:outgoing }]);
    try {
      const data = await postJSON<Session>("/chat/", { session_id: sessionId || undefined, message: outgoing, media_ids: mediaIds });
      setSessionId(data.session_id); localStorage.setItem("mechanic_session_id", data.session_id);
      setMessages(data.history.map(x => ({ role:x.role, content:x.content, created_at:x.created_at })));
      setReady(data.ready_for_diagnosis);
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to send message"); }
    finally { setBusy(false); }
  }

  async function uploadFile(file: File) {
    setUploading(true); setError("");
    try {
      const form = new FormData();
      form.append("file", file); if (sessionId) form.append("session_id", sessionId);
      const res = await fetch(`${API_URL}/upload/`, { method:"POST", body:form });
      const data = await res.json(); if (!res.ok) throw new Error(data.detail || "Upload failed");
      setSessionId(data.session_id); localStorage.setItem("mechanic_session_id", data.session_id);
      setMediaIds(prev => [...prev, data.media.id]); setMediaNames(prev => [...prev, file.name]);
    } catch (err) { setError(err instanceof Error ? err.message : "Upload failed"); }
    finally { setUploading(false); }
  }

  async function getDiagnosis() {
    if (!sessionId || busy) return;
    setBusy(true); setError("");
    try {
      const data = await postJSON<{diagnosis:Diagnosis}>("/diagnosis/", { session_id:sessionId });
      setDiagnosis(data.diagnosis);
    } catch (err) { setError(err instanceof Error ? err.message : "Diagnosis failed"); }
    finally { setBusy(false); }
  }

  async function createBooking(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      const data = await postJSON<{booking:any; message:string}>("/booking/", { ...booking, session_id:sessionId, diagnosis_id:diagnosis?.id });
      setBookingResult(data.booking); setBookingOpen(false);
    } catch (err) { setError(err instanceof Error ? err.message : "Booking failed"); }
    finally { setBusy(false); }
  }

  function newChat() {
    localStorage.removeItem("mechanic_session_id"); location.reload();
  }

  return <main className="page">
    <header className="topbar">
      <div><div className="brand">AutoCare<span>AI</span></div><div className="sub">Virtual senior mechanic</div></div>
      <button className="ghost" onClick={newChat}>New chat</button>
    </header>

    <section className="shell">
      <div className="hero">
        <div><p className="eyebrow">AI-assisted troubleshooting</p><h1>What’s wrong with your car?</h1><p className="muted">Describe the symptom. I’ll ask the right follow-up questions before suggesting a diagnosis.</p></div>
        <div className="status"><span className="dot"/> Online</div>
      </div>

      <div className="chat-card">
        <div className="messages">
          {messages.length === 0 && <div className="empty"><div className="car-icon">🚗</div><h2>Start with a symptom</h2><p>Example: “My 2019 Honda City makes a clicking sound when I turn left.”</p><div className="chips"><button onClick={()=>setText("My car makes a clicking noise when I turn left.")}>Clicking noise</button><button onClick={()=>setText("My car is overheating in traffic.")}>Overheating</button><button onClick={()=>setText("My brakes vibrate when I stop.")}>Brake vibration</button></div></div>}
          {messages.map((m,i)=><div key={i} className={`msg ${m.role}`}><div className="avatar">{m.role === "user" ? "You" : "AI"}</div><div className="bubble">{m.content}</div></div>)}
          {busy && <div className="msg assistant"><div className="avatar">AI</div><div className="bubble typing">Thinking<span>.</span><span>.</span><span>.</span></div></div>}
          <div ref={bottomRef}/>
        </div>

        {mediaNames.length > 0 && <div className="attachments">{mediaNames.map((name,i)=><span key={i}>📎 {name}</span>)}</div>}
        {error && <div className="error">{error}</div>}

        <form className="composer" onSubmit={sendMessage}>
          <label className="attach">＋<input type="file" accept="image/*,audio/*,video/*" disabled={uploading} onChange={e=>{const f=e.target.files?.[0]; if(f) uploadFile(f); e.currentTarget.value="";}} /></label>
          <input value={text} onChange={e=>setText(e.target.value)} placeholder="Describe what your car is doing..." />
          <button className="send" disabled={!text.trim() || busy}>{busy ? "…" : "Send"}</button>
        </form>
        <div className="composer-note">Images, audio and video up to 20 MB · Car/mechanical questions only</div>
      </div>

      {(ready || messages.length > 1) && !diagnosis && <div className="diagnosis-cta"><div><strong>Ready for a technician-style diagnosis?</strong><p>We’ll use the conversation and uploaded media, if any.</p></div><button onClick={getDiagnosis} disabled={busy}>{diagnosisButtonText}</button></div>}

      {diagnosis && <section className="diagnosis-card">
        <div className="diagnosis-head"><div><p className="eyebrow">Diagnostic assessment</p><h2>{diagnosis.summary}</h2></div><span className={`urgency ${diagnosis.urgency}`}>{diagnosis.urgency} urgency</span></div>
        <div className="confidence"><span>Confidence</span><div className="bar"><i style={{width:`${diagnosis.confidence}%`}}/></div><b>{diagnosis.confidence}%</b></div>
        <div className="diag-grid"><div><h3>Likely causes</h3><ul>{diagnosis.likely_causes.map((x,i)=><li key={i}>{x}</li>)}</ul></div><div><h3>Checks to perform</h3><ul>{diagnosis.checks.map((x,i)=><li key={i}>{x}</li>)}</ul></div></div>
        <div className="service"><span>Recommended service</span><strong>{diagnosis.recommended_service}</strong></div>
        {diagnosis.safety_notes.length > 0 && <div className="safety"><strong>Safety</strong>{diagnosis.safety_notes.map((x,i)=><p key={i}>⚠ {x}</p>)}</div>}
        <button className="book" onClick={()=>setBookingOpen(true)}>Book Mechanic →</button>
      </section>}

      {bookingResult && <div className="success"><strong>Booking request #{bookingResult.id} created.</strong><span>Service: {bookingResult.service_type} · {bookingResult.preferred_date} at {bookingResult.preferred_time}</span></div>}
    </section>

    {bookingOpen && <div className="modal-backdrop"><form className="modal" onSubmit={createBooking}><button type="button" className="close" onClick={()=>setBookingOpen(false)}>×</button><p className="eyebrow">Mechanic booking</p><h2>Request a service visit</h2><label>Name<input required value={booking.customer_name} onChange={e=>setBooking({...booking,customer_name:e.target.value})}/></label><label>Phone<input required value={booking.phone} onChange={e=>setBooking({...booking,phone:e.target.value})}/></label><label>Service<input required value={booking.service_type || diagnosis?.recommended_service || ""} onChange={e=>setBooking({...booking,service_type:e.target.value})}/></label><div className="two"><label>Date<input required type="date" value={booking.preferred_date} onChange={e=>setBooking({...booking,preferred_date:e.target.value})}/></label><label>Time<input required type="time" value={booking.preferred_time} onChange={e=>setBooking({...booking,preferred_time:e.target.value})}/></label></div><button className="book" disabled={busy}>Create booking</button></form></div>}
  </main>;
}
