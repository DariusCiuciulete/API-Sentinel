"""
Mock API Server for Testing API Sentinel
Run this server locally to test monitoring functionality
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import random
import time

app = FastAPI(title="Mock API", version="1.0.0")


@app.get("/")
def root():
    """Root endpoint"""
    return {"message": "Mock API Server", "status": "running"}


@app.get("/health")
def health_check():
    """Health check endpoint - always returns 200"""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/api/users")
def get_users():
    """Get all users - fast response"""
    return {
        "users": [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
            {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
        ]
    }


@app.get("/api/users/{user_id}")
def get_user(user_id: int):
    """Get user by ID"""
    if user_id > 10:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user_id, "name": f"User {user_id}", "email": f"user{user_id}@example.com"}


@app.post("/api/users")
def create_user():
    """Create a new user"""
    return {"id": 999, "name": "New User", "created": True}


@app.get("/api/products")
def get_products():
    """Get all products"""
    return {
        "products": [
            {"id": 1, "name": "Widget", "price": 19.99},
            {"id": 2, "name": "Gadget", "price": 29.99},
            {"id": 3, "name": "Tool", "price": 39.99}
        ]
    }


@app.get("/api/slow")
def slow_endpoint():
    """Slow endpoint - takes 2 seconds to respond"""
    time.sleep(2)
    return {"message": "This endpoint is intentionally slow"}


@app.get("/api/random-delay")
def random_delay():
    """Random delay endpoint - 0-3 seconds"""
    delay = random.uniform(0, 3)
    time.sleep(delay)
    return {"message": f"Delayed {delay:.2f} seconds"}


@app.get("/api/random-fail")
def random_fail():
    """Randomly fails 30% of the time"""
    if random.random() < 0.3:
        raise HTTPException(status_code=500, detail="Random failure occurred")
    return {"message": "Success", "random": random.random()}


@app.get("/api/sometimes-fail")
def sometimes_fail():
    """Fails every 3rd request"""
    if not hasattr(sometimes_fail, 'counter'):
        sometimes_fail.counter = 0
    
    sometimes_fail.counter += 1
    
    if sometimes_fail.counter % 3 == 0:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    
    return {"message": "Success", "request_number": sometimes_fail.counter}


@app.get("/api/timeout")
def timeout_endpoint():
    """Very slow endpoint - takes 60 seconds (will timeout)"""
    time.sleep(60)
    return {"message": "You waited a long time!"}


if __name__ == "__main__":
    print("=" * 60)
    print("Mock API Server for API Sentinel Testing")
    print("=" * 60)
    print("\nAvailable endpoints:")
    print("  GET  /                  - Root endpoint")
    print("  GET  /health            - Health check (always healthy)")
    print("  GET  /api/users         - List users (fast)")
    print("  GET  /api/users/{id}    - Get user by ID")
    print("  POST /api/users         - Create user")
    print("  GET  /api/products      - List products")
    print("  GET  /api/slow          - Slow endpoint (2s delay)")
    print("  GET  /api/random-delay  - Random delay (0-3s)")
    print("  GET  /api/random-fail   - Fails 30% of the time")
    print("  GET  /api/sometimes-fail- Fails every 3rd request")
    print("  GET  /api/timeout       - Very slow (60s - will timeout)")
    print("\n" + "=" * 60)
    print("Server starting on http://127.0.0.1:8001")
    print("Use Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    uvicorn.run(app, host="127.0.0.1", port=8001)
