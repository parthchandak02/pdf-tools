from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pdf2image import convert_from_path
import os
import re
from pypdf import PdfReader, PdfWriter
from typing import List
import shutil
from pydantic import BaseModel

app = FastAPI()

# Create directories if they don't exist
os.makedirs("input", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("static/thumbnails", exist_ok=True)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")
# Mount output directory for PDF downloads
app.mount("/output", StaticFiles(directory="output"), name="output")

# Templates
templates = Jinja2Templates(directory="templates")

# Pydantic model for PDF split request
class PDFSplitRequest(BaseModel):
    pages: List[int]
    output_filename: str

THUMBNAIL_DIR = "static/thumbnails"
THUMBNAIL_SOURCE_FILE = os.path.join(THUMBNAIL_DIR, ".source")


def safe_pdf_filename(name: str) -> str:
    """Reduce a client-supplied output name to a plain file name inside output/.

    Drops any directory part (so "../x" or "/etc/x" cannot escape output/), keeps only
    letters, digits, spaces, dots, dashes and underscores, and adds the .pdf extension.
    """
    base = os.path.basename(name.replace("\\", "/")).strip()
    base = re.sub(r"[^A-Za-z0-9 ._-]", "_", base).lstrip(".").strip()
    if base.lower().endswith(".pdf"):
        base = base[:-4].rstrip()
    if not base:
        raise HTTPException(status_code=400, detail="Invalid output filename")
    return base[:120] + ".pdf"


def pdf_signature(pdf_path: str) -> str:
    """Identify a PDF by name, size and modification time to detect when it changes."""
    stat = os.stat(pdf_path)
    return f"{os.path.basename(pdf_path)}|{stat.st_size}|{stat.st_mtime_ns}"


def ensure_thumbnails(pdf_path: str, page_count: int) -> None:
    """Render thumbnails unless the cached ones already belong to this exact PDF."""
    signature = pdf_signature(pdf_path)
    try:
        with open(THUMBNAIL_SOURCE_FILE) as f:
            cached = f.read()
    except OSError:
        cached = None
    if cached == signature and all(
        os.path.exists(os.path.join(THUMBNAIL_DIR, f"page_{i}.jpg")) for i in range(1, page_count + 1)
    ):
        return

    # Different or edited PDF: drop the old thumbnails and render new ones
    for name in os.listdir(THUMBNAIL_DIR):
        if name.startswith("page_") and name.endswith(".jpg"):
            os.remove(os.path.join(THUMBNAIL_DIR, name))
    images = convert_from_path(pdf_path)
    for i, image in enumerate(images):
        image.save(os.path.join(THUMBNAIL_DIR, f"page_{i + 1}.jpg"), "JPEG")
    with open(THUMBNAIL_SOURCE_FILE, "w") as f:
        f.write(signature)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/pdf/info")
async def get_pdf_info():
    # Get the first PDF file in the input directory
    pdf_files = [f for f in os.listdir("input") if f.endswith('.pdf')]
    if not pdf_files:
        raise HTTPException(status_code=404, detail="No PDF file found in input directory")

    pdf_path = os.path.join("input", pdf_files[0])
    reader = PdfReader(pdf_path)
    page_count = len(reader.pages)

    if page_count > 100:
        raise HTTPException(status_code=400, detail="PDF exceeds 100 pages limit")

    # Generate thumbnails for this PDF (regenerated whenever the PDF changes)
    ensure_thumbnails(pdf_path, page_count)

    return {"page_count": page_count, "filename": pdf_files[0]}

@app.post("/pdf/split")
async def split_pdf(request: PDFSplitRequest):
    if not request.pages:
        raise HTTPException(status_code=400, detail="No pages selected")

    output_filename = safe_pdf_filename(request.output_filename)

    pdf_files = [f for f in os.listdir("input") if f.endswith('.pdf')]
    if not pdf_files:
        raise HTTPException(status_code=404, detail="No PDF file found in input directory")

    input_pdf = os.path.join("input", pdf_files[0])
    output_path = os.path.join("output", output_filename)

    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    # Validate page numbers
    max_pages = len(reader.pages)
    valid_pages = [p for p in request.pages if 1 <= p <= max_pages]

    if not valid_pages:
        raise HTTPException(status_code=400, detail="No valid pages selected")

    try:
        for page_num in valid_pages:
            writer.add_page(reader.pages[page_num - 1])

        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

        # Verify the file was created
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Failed to create PDF file")

        return {
            "message": "PDF created successfully",
            "filename": output_filename,
            "download_url": f"/output/{output_filename}"
        }
    except Exception as e:
        # If something goes wrong, clean up any partially created file
        if os.path.exists(output_path):
            os.remove(output_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/thumbnails/{page}")
async def get_thumbnail(page: int):
    thumbnail_path = os.path.join(THUMBNAIL_DIR, f"page_{page}.jpg")
    if not os.path.exists(thumbnail_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    # The same URL shows a different image after the PDF changes, so don't let the browser cache it
    return FileResponse(thumbnail_path, headers={"Cache-Control": "no-store"})
