# PDF Tools

A modern web application for splitting and managing PDF files with an intuitive user interface.

![PDF Tools Screenshot](docs/screenshot.png)

## Features

- 📄 Load and display PDF files with page thumbnails
- ✂️ Create multiple PDF groups from selected pages
- 🎯 Intuitive page selection interface
- 📦 Download generated PDFs instantly
- 🚀 Fast and responsive UI
- 💻 Modern design with Tailwind CSS

## Prerequisites

- Python 3.8+
- Poppler (required for PDF to image conversion)
  - macOS: `brew install poppler`
  - Ubuntu: `sudo apt-get install poppler-utils`
  - Windows: [Download Poppler](http://blog.alivate.com.au/poppler-windows/)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/parthchandak02/pdf-tools.git
cd pdf-tools
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Place your PDF file in the `input` directory

2. Start the server:
```bash
uvicorn main:app --reload
```

3. Open your browser and navigate to `http://localhost:8000`

4. Use the interface to:
   - View PDF pages as thumbnails
   - Select pages by clicking checkboxes
   - Create groups of selected pages
   - Generate new PDFs from groups
   - Download the generated PDFs

## Project Structure

```
pdf-tools/
├── input/              # Place input PDFs here
├── output/             # Generated PDFs appear here
├── static/
│   └── thumbnails/     # Generated page thumbnails
├── templates/
│   └── index.html      # Main web interface
├── main.py            # FastAPI application
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## Development

The application is built with:
- FastAPI for the backend
- Tailwind CSS for styling
- PDF2Image for thumbnail generation
- PyPDF2 for PDF manipulation

To contribute:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details

## Author

Parth Chandak - [GitHub](https://github.com/parthchandak02)
