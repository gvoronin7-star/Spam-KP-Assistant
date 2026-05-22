# Тесты GUI

def test_wizard_import():
    """Тест импорта мастера профиля"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from gui.wizard_profile import ProfileWizard
    assert ProfileWizard is not None
    print("[OK] Мастер профиля импортирован успешно!")

if __name__ == "__main__":
    test_wizard_import()
