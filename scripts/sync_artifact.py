from pathlib import Path

def sync_artifact():
    template_path = Path("src/dashboard/templates/compare.html")
    artifact_path = Path(r"C:\Users\jaiad\.gemini\antigravity\brain\3b3baf0c-a780-4f9a-b464-c873a4b01d8a\compare_shorts.html")
    
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Replace relative /media/ with absolute http://127.0.0.1:5000/media/
    content = content.replace('src="/media/', 'src="http://127.0.0.1:5000/media/')
    content = content.replace('"/media/', '"http://127.0.0.1:5000/media/')
    
    with open(artifact_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"Successfully updated artifact at {artifact_path} ({len(content)} chars)")

if __name__ == "__main__":
    sync_artifact()
