YouTube Channel Transcript Search

Ovaj projekat omogućava pretragu videa sa željenog YouTube kanala na osnovu izgovorenog sadržaja u videima.

Aplikacija:
- preuzima videe sa kanala
- preuzima ili generiše transkripte
- omogućava pretragu reči unutar svih videa
- vodi direktno na tačan trenutak u videu

Instrukcije:
1. git clone <repo>
2. cd youtube-channel-transcript-search
3. python -m venv .venv
4. .venv\Scripts\activate (za Windows), source .venv/bin/activate (za Linux/macOS)
5. pip install -r requirements.txt

Pokretanje backend-a:
- python -m uvicorn backend.main:app --reload --port 8000
- radi na http://127.0.0.1:8000

Pokretanje frontend-a:
- cd frontend/app
- npm install
- ng serve
- radi na http://localhost:4200

