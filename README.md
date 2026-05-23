# Insurance Claim AI Agent

## Project Overview
The **Insurance Claim AI Agent** is an intelligent assistant designed to streamline the insurance claim process. It helps users submit claims, verify policy details, and receive claim status updates in a conversational manner. The agent leverages AI to understand user queries, process relevant data, and provide accurate responses efficiently.

## Features
- Submit insurance claims via an interactive interface.
- Verify user policy details automatically.
- Track the status of existing claims.
- Intelligent conversation handling to answer user queries.
- Provides alerts and reminders for claim-related actions.

## Technology Stack
- **Programming Language:** Python
- **AI / NLP:** llamma3 via Ollamma 
- **Frontend:**  HTML,CSS,JS 
- **Backend / APIs:** FastAPI
- **Version Control:** Git & GitHub

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/insurance-claim-agent.git
   cd insurance-claim-agent
   
2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   ```bash
   # Windows
   venv\Scripts\activate

   # Mac/Linux
   source venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```

---

## Usage

1. Open the application in your browser.
2. Enter insurance-related queries or submit claim details.
3. The AI agent processes the request and provides responses in real time.
4. Users can:
   - File insurance claims
   - Verify policy information
   - Track claim status
   - Ask insurance-related questions

---

## Project Structure

```bash
insurance-claim-agent/
│
├── backend/
│   ├── main.py
│   ├── routes/
│   ├── services/
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── README.md
└── .gitignore
```

---

## Future Improvements

- Add user authentication and login system
- Integrate real insurance databases/APIs
- Add multilingual support
- Improve claim verification accuracy
- Deploy the project on cloud platforms

---

## Contributing

Contributions are welcome.

1. Fork the repository
2. Create a new branch
   ```bash
   git checkout -b feature-name
   ```
3. Commit your changes
   ```bash
   git commit -m "Added new feature"
   ```
4. Push to GitHub
   ```bash
   git push origin feature-name
   ```
5. Create a Pull Request

---

## License

This project is licensed under the MIT License.

---

## Author

**Manavi Bangani**

B.Tech Student | Aspiring Software Development Engineer (SDE)

GitHub: https://github.com/manavibangani
