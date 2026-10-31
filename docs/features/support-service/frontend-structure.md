# Frontend

Static HTML/CSS/JavaScript in src/ui. Same-origin API, sessionStorage bearer session, textContent rendering, responsive chat/history/action cards.

Outgoing messages appear immediately and clear the composer. Pending replies show an assistant waiting indicator. Failed requests remain as message bubbles with a retry button that reuses client_message_id. Drafts typed during a response are preserved. Successful history reload replaces optimistic bubbles with persisted messages without duplicates.
