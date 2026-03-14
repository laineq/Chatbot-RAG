# Frontend

Next.js chat interface for the enterprise RAG chatbot MVP.

## Commands

- `npm run dev`
- `npm run lint`
- `npm run build`
- `npm run test`

## Behavior

- Generates and stores session IDs in browser local storage
- Loads chat history from `GET /session/{id}`
- Sends prompts to `POST /chat`
- Displays route badges, citations, and feedback controls
- Submits thumbs feedback to `POST /feedback`
- Includes an analytics dashboard at `/analytics` backed by `GET /analytics/overview`
