"""Bundle the browser calculator into one offline HTML file."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
engine = (ROOT / "web/calculator.mjs").read_text().replace("export ", "")
template = (ROOT / "web/template.html").read_text()
output = ROOT / "Mudda-Freedom-Calculator.html"
output.write_text(template.replace("/* CALCULATOR_ENGINE */", engine))
print(output)
