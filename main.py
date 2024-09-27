from fastapi import FastAPI, BackgroundTasks, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import asyncio
import os
import shutil
import uvicorn
import threading
import time

app = FastAPI()

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class FileRecord(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    processed_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# File processing logic
async def process_files():
    while True:
        try:
            folder_path = "./uploads"
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    # Process the file
                    with open(file_path, 'r') as file:
                        content = file.read()
                        print(f"Processing file: {filename}")
                        print(f"Content: {content}")
                    
                    # Store file info in database
                    db = SessionLocal()
                    db_file = FileRecord(filename=filename)
                    db.add(db_file)
                    db.commit()
                    db.close()
                    
                    print(f"File {filename} processed and added to database")
                    
                    # Move the processed file to a 'processed' folder instead of deleting
                    processed_folder = "./processed"
                    os.makedirs(processed_folder, exist_ok=True)
                    shutil.move(file_path, os.path.join(processed_folder, filename))
            
            # Wait for 10 seconds before next iteration (for testing purposes)
            await asyncio.sleep(10)
        except Exception as e:
            print(f"Error in file processing: {str(e)}")
            await asyncio.sleep(10)  # Wait before retrying

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(process_files())

@app.get("/")
async def root():
    return {
        "message": "Welcome to the File Processor API",
        "endpoints": {
            "/upload/": "POST - Upload a file (use multipart/form-data with 'file' field)",
            "/trigger-processing/": "POST - Manually trigger file processing"
        }
    }

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    try:
        upload_dir = "./uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"File saved to: {file_path}")
        return JSONResponse(content={"message": f"File '{file.filename}' uploaded successfully"}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

@app.post("/trigger-processing/")
async def trigger_processing(background_tasks: BackgroundTasks):
    background_tasks.add_task(process_files)
    return {"message": "File processing triggered"}

@app.get("/list-files/")
async def list_files():
    upload_dir = "./uploads"
    processed_dir = "./processed"
    uploaded_files = os.listdir(upload_dir) if os.path.exists(upload_dir) else []
    processed_files = os.listdir(processed_dir) if os.path.exists(processed_dir) else []
    return {
        "uploaded_files": uploaded_files,
        "processed_files": processed_files
    }

@app.get("/list-database/")
async def list_database():
    db = SessionLocal()
    records = db.query(FileRecord).all()
    db.close()
    return {"records": [{"id": record.id, "filename": record.filename, "processed_at": record.processed_at} for record in records]}

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    print("Server is running. Press CTRL+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Server stopped.")