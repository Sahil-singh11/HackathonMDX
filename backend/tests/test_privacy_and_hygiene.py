"""Privacy, secret-hygiene and repository-hygiene assertions."""
import io
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_no_temporary_media_persisted(client, sharp_image):
    storage = ROOT / "storage"
    before = {p.name for p in storage.glob("**/*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")}
    client.post("/api/analyse-catch",
                files={"image": ("catch.jpg", io.BytesIO(sharp_image), "image/jpeg")},
                data={"note": "test"})
    after = {p.name for p in storage.glob("**/*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")}
    assert after == before  # uploads are processed in memory and never written to disk


def test_env_file_is_gitignored():
    r = subprocess.run(["git", "check-ignore", ".env"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, ".env must be gitignored"


def test_raw_media_dir_is_gitignored():
    r = subprocess.run(["git", "check-ignore", "data/raw/x.jpg"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, "data/raw must be gitignored"


def test_no_api_key_pattern_in_tracked_files():
    needle = "AIza" + "Sy"  # built at runtime so this test file never matches itself
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    for rel in tracked:
        p = ROOT / rel
        if p.suffix in (".py", ".ts", ".tsx", ".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".env"):
            text = p.read_text(errors="ignore")
            assert needle not in text, f"potential Google API key in {rel}"


def test_coordinates_rounded_in_catch_records(client):
    body = client.post("/api/catches", json={
        "confirmed_species_id": "naso_unicornis", "measured_length_cm": 40.0,
        "latitude": -20.163657, "longitude": 57.504501}).json()
    rec = client.get(f"/api/catches/{body['catch_record_id']}").json()
    assert rec["latitude_rounded"] == -20.16
    assert rec["longitude_rounded"] == 57.5


def test_limitation_string_on_every_analysis(client):
    r = client.post("/api/analyse-catch", data={"note": "ki letan pou lapes zordi?"})
    lims = r.json()["limitations"]
    assert any("AI-assisted catch documentation" in l for l in lims)
