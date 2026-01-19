from fastapi import FastAPI
from pydantic import BaseModel, Field
from uuid import UUID


app = FastAPI()

class Book(BaseModel):
    id: UUID 
    title: str = Field(min_length=1)
    author: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=100)
    rating: int = Field(gt=-1, lt=101)


Books = []

@app.get("/")
def list_books():
    return Books

@app.post("/")
def add_book(book: Book):
    Books.append(book) 
    return book


@app.put("/{book_id}")
def update_book(book_id: UUID, book: Book):
    counter = 0
    for b in Books:
        counter += 1
        if b.id == book_id:
            Books[counter-1] = book
            return Books[counter-1]
        else:
            raise HTTPException(status_code=404, detail="book not found")


@app.delete("/{book_id}")
def delete_book(book_id: UUID):
    counter = 0
    for b in Books:
        counter += 1
        if b.id == book_id:
            del Books[counter-1]
            return f"Book with id {book_id} deleted"
        else:
            raise HTTPException(status_code=404, detail="Book not found")