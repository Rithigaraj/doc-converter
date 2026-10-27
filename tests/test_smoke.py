from pathlib import Path


def test_structure():
    root = Path(__file__).parent.parent
    assert (root / "app" / "main.py").exists()
    assert (root / "web" / "index.html").exists()
    assert (root / "converters" / "registry.py").exists()
    assert (root / "workers" / "tasks.py").exists()
    assert (root / "README.md").exists()
