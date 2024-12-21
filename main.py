from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pdf2image import convert_from_path
import os
from PyPDF2 import PdfReader, PdfWriter
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

    # Generate thumbnails if they don't exist
    if not os.listdir("static/thumbnails"):
        images = convert_from_path(pdf_path)
        for i, image in enumerate(images):
            image.save(f"static/thumbnails/page_{i + 1}.jpg", "JPEG")

    return {"page_count": page_count, "filename": pdf_files[0]}

@app.post("/pdf/split")
async def split_pdf(request: PDFSplitRequest):
    if not request.pages:
        raise HTTPException(status_code=400, detail="No pages selected")

    output_filename = request.output_filename
    if not output_filename.endswith('.pdf'):
        output_filename += '.pdf'

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
    thumbnail_path = f"static/thumbnails/page_{page}.jpg"
    if not os.path.exists(thumbnail_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(thumbnail_path)
