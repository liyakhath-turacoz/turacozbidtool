import { useEffect, useState } from 'react';
import { api } from './api.js';

export function mergeMessages(...groups) {
  return [...new Map(groups.flat().map((message) => [message.id, message])).values()]
    .sort((a, b) => String(a.created_at).localeCompare(String(b.created_at)) || a.id.localeCompare(b.id));
}

export default function BidConversation(props) {
  if (props.user?.role !== 'admin') return null;
  return <AdminBidConversation {...props} readOnly />;
}

function AdminBidConversation({ bidId, user, liveMessages = [], readOnly = false }) {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  useEffect(() => {
    let cancelled = false;
    setMessages([]); setError('');
    const load = () => api.bidMessages(user.access_token, bidId).then((rows) => {
      if (!cancelled) setMessages((current) => mergeMessages(rows, current));
    }).catch((err) => { if (!cancelled) setError(err.message); });
    load();
    window.addEventListener('bid-chat-reconnected', load);
    return () => { cancelled = true; window.removeEventListener('bid-chat-reconnected', load); };
  }, [bidId, user.access_token]);
  const visible = mergeMessages(messages, liveMessages);
  const send = async (event) => {
    event.preventDefault();
    if (!draft.trim() || sending) return;
    setSending(true); setError('');
    try {
      const sent = await api.sendBidMessage(user.access_token, bidId, draft.trim());
      setMessages((current) => mergeMessages(current, [sent])); setDraft('');
    } catch (err) { setError(err.message); }
    finally { setSending(false); }
  };
  return <section className="bid-conversation" aria-label="Private bid conversation">
    <h4>{readOnly ? 'Bid conversation' : 'Private conversation with your buyer / winning dealer'}</h4>
    <div className="message-list chat-thread" aria-live="polite">{visible.map((message) => <div className={`message bubble ${message.sender_id === user.id ? 'mine' : ''}`} key={message.id}>
      <strong>{message.sender_name}</strong><p>{message.message}</p><small>{message.created_at}</small>
    </div>)}{!visible.length && <p>No messages yet.</p>}</div>
    {error && <p role="alert">{error}</p>}
    {!readOnly && <form className="inline-form" onSubmit={send}><label>Bid message<input maxLength={4000} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Discuss delivery or your finalized order" /></label><button type="submit" disabled={sending || !draft.trim()}>{sending ? 'Sending…' : 'Send bid message'}</button></form>}
  </section>;
}
