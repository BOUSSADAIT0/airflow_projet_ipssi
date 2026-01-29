#!/usr/bin/env python3
import uvicorn

if __name__ == "__main__":
    print("🚀 Démarrage OCR Intelligent API...")
    print("📍 http://localhost:8000")
    print("📄 http://localhost:8000/docs")
    print("🔑 aitdjoudi@gmail.com / boussad")
    print("\n🛑 Ctrl+C pour arrêter\n")
    
    uvicorn.run(
        "app.main_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )