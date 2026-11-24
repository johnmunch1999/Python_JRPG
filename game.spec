# PyInstaller spec: builds a single-file windowed executable.
#   pip install -r requirements.txt pyinstaller
#   pyinstaller game.spec        -> dist/ClassicJRPG.exe
a = Analysis(
    ["main.py"],
    datas=[("assets", "assets"), ("data", "data")],
    hiddenimports=[],
    excludes=["tkinter", "numpy", "unittest"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="ClassicJRPG",
    console=False,
    upx=False,
)
